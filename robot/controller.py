import time
import numpy as np
import uuid
import cProfile
import pstats
import io
import os
import concurrent.futures
import threading
import cv2
from typing import List, Optional, Dict, Any
from enum import Enum
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.ai import (
    segmentFrame,
    maskSegment,
    calculateNormalizedBounds,
)
from robot.ai.segment import initializeSegmentationModel
from robot.sorting.bricklink_categories_sorting_profile import (
    mkBricklinkCategoriesSortingProfile,
)
from robot.sorting.sorter import ClassificationResult
from robot.storage.sqlite3.migrations import initializeDatabase
from robot.storage.sqlite3.operations import saveObservationToDatabase
from robot.storage.blob import ensureBlobStorageExists, saveTrajectory
from robot.trajectories import (
    Observation,
    Trajectory,
    TrajectoryLifecycleStage,
)
from robot.scene_tracker import SceneTracker
from robot.sorting import PieceSorter, PieceSortingProfile
from robot.bin_state_tracker import (
    BinStateTracker,
    BinCoordinates,
    BinState,
    binCoordinatesToKey,
)
from robot.door_scheduler import DoorScheduler

from robot.async_profiling import (
    AsyncFrameProfilingRecord,
    initializeAsyncProfiling,
    createFrameProfilingRecord,
    startFrameProcessing,
    completeFrameProcessing,
    printAggregateProfilingReport,
    saveProfilingResults,
)


from robot.server.types import SystemLifecycleStage, SortingState
from robot.server.api import RobotAPI
from robot.server.thread_safe_state import ThreadSafeState


class SortingController:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_system: IRLSystemInterface,
    ):
        self.global_config = global_config
        self.irl_system = irl_system
        self.system_lifecycle_stage = SystemLifecycleStage.INITIALIZING
        self.sorting_state = SortingState.GETTING_NEW_OBJECT
        self.getting_new_object_start_time = None

        piece_sorting_profile = mkBricklinkCategoriesSortingProfile(self.global_config)

        self.sorter = PieceSorter(self.global_config, piece_sorting_profile)

        self.bin_state_tracker = BinStateTracker(
            self.global_config,
            self.irl_system["distribution_modules"],
            piece_sorting_profile,
            self.global_config["use_prev_bin_state"],
        )

        self.global_config["logger"].info(
            f"Using bin state ID: {self.bin_state_tracker.current_bin_state_id}"
        )

        self.door_scheduler = DoorScheduler(
            self.global_config, self.irl_system["distribution_modules"]
        )

        self.scene_tracker = SceneTracker(
            self.global_config, self.irl_system["main_camera"].calibration
        )

        self.segmentation_model = initializeSegmentationModel(self.global_config)

        self.api_server = RobotAPI(self.global_config, self)

        self.max_worker_threads = global_config["max_worker_threads"]
        self.max_queue_size = global_config["max_queue_size"]
        self.frame_processor_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_worker_threads, thread_name_prefix="frame_processor"
        )
        self.active_futures: List[concurrent.futures.Future] = []

        self.main_conveyor_speed = 0
        self.feeder_conveyor_speed = 0
        self.vibration_hopper_speed = 0

        # Thread-safe communication with API server
        self.thread_safe_state = ThreadSafeState()

    def initialize(self) -> None:
        self.global_config["logger"].info("Initializing sorting controller...")

        ensureBlobStorageExists(self.global_config)
        initializeDatabase(self.global_config)

        initializeAsyncProfiling(self.global_config)

        self.resetServos()

        self.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_USER

    def resetServos(self) -> None:
        conveyor_closed_angle = self.global_config["conveyor_door_closed_angle"]
        bin_closed_angle = self.global_config["bin_door_closed_angle"]

        self.global_config["logger"].info(
            f"Resetting all servos - conveyor doors: {conveyor_closed_angle}°, bin doors: {bin_closed_angle}°"
        )

        for distribution_module in self.irl_system["distribution_modules"]:
            # Reset conveyor door servo
            distribution_module.servo.setAngleAndTurnOff(conveyor_closed_angle, 1000)

            # Reset all bin door servos
            for bin_servo in distribution_module.bins:
                bin_servo.servo.setAngleAndTurnOff(bin_closed_angle, 1000)

        self.global_config["logger"].info("All servos reset to closed positions")

    def startHardware(self) -> None:
        self.global_config["logger"].info("Starting hardware systems...")

        self.system_lifecycle_stage = SystemLifecycleStage.RUNNING

    def run(self) -> None:
        self.global_config["logger"].info("Starting main control loop...")

        if self.global_config["camera_preview"]:
            cv2.namedWindow("Camera Feed", cv2.WINDOW_AUTOSIZE)

        enable_profiling = self.global_config.get("enable_profiling", False)
        profiler = None
        if enable_profiling:
            profiler = cProfile.Profile()
            profiler.enable()
            self.global_config["logger"].info("Performance profiling enabled")

        tick_count = 0
        try:
            while self.system_lifecycle_stage in [
                SystemLifecycleStage.RUNNING,
                SystemLifecycleStage.PAUSED_BY_USER,
                SystemLifecycleStage.PAUSED_BY_SYSTEM,
            ]:
                try:
                    tick_start_time_ms = time.time() * 1000

                    if self.system_lifecycle_stage == SystemLifecycleStage.RUNNING:
                        self._updateSortingStateMachine()
                        self._submitFrameForProcessing()

                    update_start_ms = time.time() * 1000
                    self._updateTrajectories()
                    update_duration_ms = time.time() * 1000 - update_start_ms

                    step_start_ms = time.time() * 1000
                    self.scene_tracker.stepScene()
                    step_duration_ms = time.time() * 1000 - step_start_ms

                    trigger_start_ms = time.time() * 1000
                    self._scheduleDoorTriggersForTrajectories()
                    trigger_duration_ms = time.time() * 1000 - trigger_start_ms

                    cleanup_start_ms = time.time() * 1000
                    self._cleanupCompletedFutures()
                    cleanup_duration_ms = time.time() * 1000 - cleanup_start_ms

                    tick_duration_ms = time.time() * 1000 - tick_start_time_ms
                    active_futures_count = len(self.active_futures)

                    if self.global_config["enable_profiling"] and tick_count % 20 == 0:
                        printAggregateProfilingReport(20)

                    self.global_config["logger"].info(
                        f"Main tick [{self.sorting_state.value}]: {tick_duration_ms:.1f}ms (update: {update_duration_ms:.1f}ms, step: {step_duration_ms:.1f}ms, trigger: {trigger_duration_ms:.1f}ms, cleanup: {cleanup_duration_ms:.1f}ms, queue: {active_futures_count}/{self.max_queue_size}, objects: {self.scene_tracker.objects_in_frame})"
                    )

                    tick_count += 1

                    time.sleep(self.global_config["capture_delay_ms"] / 1000.0)

                except KeyboardInterrupt:
                    self.global_config["logger"].info("Interrupt received, stopping...")
                    self.system_lifecycle_stage = SystemLifecycleStage.STOPPING
                    break
                except Exception as e:
                    self.global_config["logger"].error(f"Error in main loop: {e}")
                    self.system_lifecycle_stage = SystemLifecycleStage.STOPPING
                    break
        finally:
            if enable_profiling and profiler is not None:
                profiler.disable()
                saveProfilingResults(self.global_config, profiler)

            self._shutdownFrameProcessor()

    def _updateSortingStateMachine(self) -> None:
        current_time_ms = int(time.time() * 1000)

        if self.sorting_state == SortingState.GETTING_NEW_OBJECT:
            if self.getting_new_object_start_time is None:
                self.getting_new_object_start_time = current_time_ms
                self._setMotorSpeeds(
                    main_conveyor=self.global_config["main_conveyor_speed"],
                    feeder_conveyor=self.global_config["feeder_conveyor_speed"],
                    vibration_hopper=self.global_config["vibration_hopper_speed"],
                )
                self.global_config["logger"].info("Started motors to get new object")

            if self.scene_tracker.objects_in_frame > 0:
                self.sorting_state = SortingState.OBJECT_IN_VIEW
                self.global_config["logger"].info(
                    "Object detected, switching to OBJECT_IN_VIEW"
                )
                return

            time_running = current_time_ms - self.getting_new_object_start_time
            if time_running > self.global_config["getting_new_object_timeout_ms"]:
                self.global_config["logger"].info(
                    "Timeout waiting for object, pausing system"
                )
                self.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_SYSTEM
                self._setMotorSpeeds(0, 0, 0)
                return

        elif self.sorting_state == SortingState.OBJECT_IN_VIEW:
            # Stop feeder motors, keep main conveyor running
            self._setMotorSpeeds(
                main_conveyor=self.global_config["main_conveyor_speed"],
                feeder_conveyor=0,
                vibration_hopper=0,
            )

            if self.scene_tracker.isObjectCentered():
                self.sorting_state = SortingState.TRYING_TO_CLASSIFY
                self._setMotorSpeeds(
                    main_conveyor=0, feeder_conveyor=0, vibration_hopper=0
                )
                self.global_config["logger"].info(
                    "Object centered, switching to TRYING_TO_CLASSIFY"
                )
                return

        elif self.sorting_state == SortingState.TRYING_TO_CLASSIFY:
            # Motors should be stopped, wait for classification to complete
            # Check if we have trajectories ready to trigger (handled in _scheduleDoorTriggersForTrajectories)
            # If no trajectories after some time, go back to getting new object
            if self.scene_tracker.objects_in_frame == 0:
                self.sorting_state = SortingState.GETTING_NEW_OBJECT
                self.getting_new_object_start_time = None
                self.global_config["logger"].info(
                    "No objects to classify, switching to GETTING_NEW_OBJECT"
                )
                return

        elif self.sorting_state == SortingState.SENDING_ITEM_TO_BIN:
            # Keep main conveyor running for door scheduling
            self._setMotorSpeeds(
                main_conveyor=self.global_config["main_conveyor_speed"],
                feeder_conveyor=0,
                vibration_hopper=0,
            )

            # Check if all trajectories have been processed and no more objects in frame
            active_trajectories = self.scene_tracker.getActiveTrajectories()
            trajectories_under_camera = [
                t
                for t in active_trajectories
                if t.lifecycle_stage == TrajectoryLifecycleStage.UNDER_CAMERA
            ]

            if (
                len(trajectories_under_camera) == 0
                and self.scene_tracker.objects_in_frame == 0
            ):
                self.sorting_state = SortingState.GETTING_NEW_OBJECT
                self.getting_new_object_start_time = None
                self.global_config["logger"].info(
                    "Item sent, switching to GETTING_NEW_OBJECT"
                )
                return

    def _setMotorSpeeds(
        self, main_conveyor: int, feeder_conveyor: int, vibration_hopper: int
    ) -> None:
        # Track speeds
        self.main_conveyor_speed = main_conveyor
        self.feeder_conveyor_speed = feeder_conveyor
        self.vibration_hopper_speed = vibration_hopper

        if not self.global_config["disable_main_conveyor"]:
            self.irl_system["main_conveyor_dc_motor"].setSpeed(main_conveyor)
        if not self.global_config["disable_feeder_conveyor"]:
            self.irl_system["feeder_conveyor_dc_motor"].setSpeed(feeder_conveyor)
        if not self.global_config["disable_vibration_hopper"]:
            self.irl_system["vibration_hopper_dc_motor"].setSpeed(vibration_hopper)

    def _submitFrameForProcessing(self) -> None:
        captured_at_ms = int(time.time() * 1000)
        frame = self.irl_system["main_camera"].captureFrame()
        if frame is None:
            return

        if self.global_config["camera_preview"]:
            # Resize frame for display (480p)
            display_frame = cv2.resize(frame, (854, 480))
            cv2.imshow("Camera Feed", display_frame)
            cv2.waitKey(1)

        self.thread_safe_state.set("latest_camera_frame", frame)

        # Check if we have too many queued frames
        if len(self.active_futures) >= self.max_queue_size:
            self.global_config["logger"].info(
                f"Frame queue full ({len(self.active_futures)}/{self.max_queue_size}), dropping frame"
            )
            return

        profiling_record = createFrameProfilingRecord()

        # Submit frame for processing
        future = self.frame_processor_pool.submit(
            self._processFrame, frame.copy(), profiling_record, captured_at_ms
        )
        self.active_futures.append(future)

    def _processFrame(
        self,
        frame: np.ndarray,
        profiling_record: AsyncFrameProfilingRecord,
        captured_at_ms: int,
    ) -> None:
        startFrameProcessing(profiling_record)

        if self.global_config["disable_classification"]:
            completeFrameProcessing(profiling_record)
            return

        # Segmentation
        segmentation_start_ms = time.time() * 1000
        segments = segmentFrame(frame, self.segmentation_model, self.global_config)
        segmentation_duration_ms = (time.time() * 1000) - segmentation_start_ms

        profiling_record["segmentation_start_ms"] = segmentation_start_ms
        profiling_record["segmentation_duration_ms"] = segmentation_duration_ms
        profiling_record["segments_found_count"] = len(segments)

        for segment in segments:
            masked_image = maskSegment(frame, segment)
            if masked_image is None:
                continue

            classification_start_ms = time.time() * 1000
            classification_result = self.sorter.classifySegment(masked_image)
            classification_duration_ms = (time.time() * 1000) - classification_start_ms

            profiling_record["classification_total_duration_ms"] += (
                classification_duration_ms
            )
            profiling_record["classification_calls_count"] += 1

            CLASSIFICATION_THRESHOLD = 0.25
            if classification_result.confidence < CLASSIFICATION_THRESHOLD:
                self.global_config["logger"].info(
                    f"Classification confidence too low: {classification_result.confidence:.3f}, skipping segment"
                )
                continue

            (
                center_x,
                center_y,
                bbox_width,
                bbox_height,
            ) = calculateNormalizedBounds(frame, segment)

            observation = Observation(
                None,
                center_x,
                center_y,
                bbox_width,
                bbox_height,
                frame,
                masked_image,
                classification_result,
                self.global_config["speed_estimation_border_threshold_percent"],
                captured_at_ms,
            )

            self.scene_tracker.addObservation(observation)

            profiling_record["observations_saved_count"] += 1

        completeFrameProcessing(profiling_record)

    def _updateTrajectories(self) -> None:
        trajectories_to_update = self.scene_tracker.getActiveTrajectories()

        for trajectory in trajectories_to_update:
            try:
                saveTrajectory(self.global_config, trajectory)
            except Exception as e:
                self.global_config["logger"].error(
                    f"Failed to save trajectory {trajectory.trajectory_id}: {e}"
                )

    def _scheduleDoorTriggersForTrajectories(self) -> None:
        # Skip door triggers if classification is disabled
        if self.global_config["disable_classification"]:
            return

        trajectories_to_trigger = self.scene_tracker.getTrajectoriesToTrigger()

        # If we have trajectories to trigger and we're in TRYING_TO_CLASSIFY, switch to SENDING_ITEM_TO_BIN
        if (
            trajectories_to_trigger
            and self.sorting_state == SortingState.TRYING_TO_CLASSIFY
        ):
            self.sorting_state = SortingState.SENDING_ITEM_TO_BIN
            self.global_config["logger"].info(
                "Trajectories ready to trigger, switching to SENDING_ITEM_TO_BIN"
            )

        # Only schedule door triggers when in SENDING_ITEM_TO_BIN state
        if self.sorting_state != SortingState.SENDING_ITEM_TO_BIN:
            return

        for trajectory in trajectories_to_trigger:
            consensus_item_id = trajectory.getConsensusClassification()
            if not consensus_item_id:
                continue

            category_id = self.sorter.sorting_profile.getCategoryId(consensus_item_id)
            target_bin = None

            if category_id:
                target_bin = self.bin_state_tracker.findAvailableBin(category_id)

                # Check if we got the fallback bin for overflow categorized items
                if target_bin:
                    target_key = binCoordinatesToKey(target_bin)
                    current_bin_category = self.bin_state_tracker.current_state.get(
                        target_key
                    )
                    if (
                        current_bin_category
                        == self.bin_state_tracker.fallback_category_id
                    ):
                        self.global_config["logger"].info(
                            f"No available bin for category '{category_id}', using fallback bin for trajectory {trajectory.trajectory_id}"
                        )
                        category_id = self.bin_state_tracker.fallback_category_id
            else:
                self.global_config["logger"].info(
                    f"Unknown item '{consensus_item_id}', using misc bin for trajectory {trajectory.trajectory_id}"
                )
                target_bin = self.bin_state_tracker.findAvailableBin(
                    self.bin_state_tracker.misc_category_id
                )
                category_id = self.bin_state_tracker.misc_category_id

            if not target_bin:
                self.global_config["logger"].warning(
                    f"No available bins (including misc and fallback) for trajectory {trajectory.trajectory_id}"
                )
                continue

            delay_ms = self._calculateDoorDelay(trajectory, target_bin)
            if delay_ms is None:
                self.global_config["logger"].info(
                    f"Cannot schedule action for trajectory {trajectory.trajectory_id}"
                )
                continue

            trajectory.setTargetBin(target_bin)
            self.door_scheduler.scheduleDoorAction(target_bin, delay_ms)
            self.bin_state_tracker.reserveBin(target_bin, category_id)

            self.global_config["logger"].info(
                f"Scheduled action for trajectory {trajectory.trajectory_id} -> bin {target_bin} with delay {delay_ms}ms"
            )

    def _calculateDoorDelay(
        self, trajectory: Trajectory, target_bin: BinCoordinates
    ) -> Optional[int]:
        if target_bin["distribution_module_idx"] >= len(
            self.irl_system["distribution_modules"]
        ):
            self.global_config["logger"].info(
                f"Invalid target bin distribution_module_idx {target_bin['distribution_module_idx']}"
            )
            return None

        # Get when trajectory was at camera center
        time_at_center_ms = self.scene_tracker.predictTimeAtCameraCenter(trajectory)
        if time_at_center_ms is None:
            self.global_config["logger"].info(
                "Could not predict time at camera center for trajectory"
            )
            return None

        # Get distance from camera center to door beginning
        target_distance_cm = self.irl_system["distribution_modules"][
            target_bin["distribution_module_idx"]
        ].distance_from_camera_center_to_door_begin_cm

        travel_time_ms = self.scene_tracker.calculateTravelTime(target_distance_cm)
        if travel_time_ms is None:
            self.global_config["logger"].info("Could not calculate travel time")
            return None

        # Calculate delay: time for object to travel from center to door, minus time already elapsed since center
        current_time_ms = int(time.time() * 1000)
        time_since_center_ms = current_time_ms - time_at_center_ms
        delay_ms = int(travel_time_ms) - time_since_center_ms

        return max(0, delay_ms)

    def _cleanupCompletedFutures(self) -> None:
        completed_futures = [f for f in self.active_futures if f.done()]

        for future in completed_futures:
            try:
                future.result()  # This will raise any exceptions that occurred
            except Exception as e:
                self.global_config["logger"].error(f"Frame processing error: {e}")

        self.active_futures = [f for f in self.active_futures if not f.done()]

    def _shutdownFrameProcessor(self) -> None:
        self.global_config["logger"].info("Shutting down frame processor...")

        if self.active_futures:
            self.global_config["logger"].info(
                f"Waiting for {len(self.active_futures)} frames to complete..."
            )
            concurrent.futures.wait(self.active_futures, timeout=10.0)

        self.frame_processor_pool.shutdown(wait=True)

    def stop(self) -> None:
        self.global_config["logger"].info("Stopping sorting controller...")
        self.system_lifecycle_stage = SystemLifecycleStage.STOPPING

        self.irl_system["main_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["feeder_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["vibration_hopper_dc_motor"].setSpeed(0)

        self._shutdownFrameProcessor()

        if self.global_config["camera_preview"]:
            cv2.destroyAllWindows()

        self.irl_system["arduino"].flush()
        self.irl_system["arduino"].close()
        self.irl_system["main_camera"].release()

        self.system_lifecycle_stage = SystemLifecycleStage.SHUTDOWN
