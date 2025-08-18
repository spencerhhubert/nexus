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
from typing import List, Optional, Dict, Any, TypedDict
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


class StateMachineTimestamps(TypedDict):
    getting_new_object_start_time: Optional[int]
    classification_start_time_ms: Optional[int]
    sending_to_bin_state_start_time_ms: Optional[int]
    waiting_for_object_to_appear_start_time_ms: Optional[int]
    break_beam_last_query_timestamp: int


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
        self.timestamps["getting_new_object_start_time"] = None

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

        self.scene_tracker = SceneTracker(
            self.global_config,
            self.irl_system["conveyor_encoder"],
        )

        self.segmentation_model = initializeSegmentationModel(self.global_config)

        self.api_server = RobotAPI(self.global_config, self)

        self.max_worker_threads = global_config["max_worker_threads"]
        self.max_queue_size = global_config["max_queue_size"]
        self.frame_processor_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_worker_threads, thread_name_prefix="frame_processor"
        )
        self.frame_processing_futures: List[concurrent.futures.Future] = []

        self.main_conveyor_speed = 0
        self.feeder_conveyor_speed = 0
        self.vibration_hopper_speed = 0

        self.timestamps: StateMachineTimestamps = {
            "getting_new_object_start_time": None,
            "classification_start_time_ms": None,
            "sending_to_bin_state_start_time_ms": None,
            "waiting_for_object_to_appear_start_time_ms": None,
            "break_beam_last_query_timestamp": int(time.time() * 1000),
        }

        # Thread-safe communication with API server
        self.thread_safe_state = ThreadSafeState()

    def initialize(self) -> None:
        self.global_config["logger"].info("Initializing sorting controller...")

        ensureBlobStorageExists(self.global_config)
        initializeDatabase(self.global_config)

        initializeAsyncProfiling(self.global_config)

        self._resetServos()

        self.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_SYSTEM

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

                    cleanup_start_ms = time.time() * 1000
                    self._cleanupCompletedFutures()
                    cleanup_duration_ms = time.time() * 1000 - cleanup_start_ms

                    if self.system_lifecycle_stage == SystemLifecycleStage.RUNNING:
                        self._updateSortingStateMachine()
                        if self.sorting_state in [
                            SortingState.GETTING_NEW_OBJECT,
                            SortingState.WAITING_FOR_OBJECT_TO_APPEAR,
                            SortingState.WAITING_FOR_OBJECT_TO_CENTER,
                        ]:
                            self._submitFrameForProcessing()

                    update_start_ms = time.time() * 1000
                    self._updateTrajectories()
                    update_duration_ms = time.time() * 1000 - update_start_ms

                    step_start_ms = time.time() * 1000
                    self.scene_tracker.stepScene()
                    step_duration_ms = time.time() * 1000 - step_start_ms

                    tick_duration_ms = time.time() * 1000 - tick_start_time_ms
                    frame_processing_futures_count = len(self.frame_processing_futures)

                    if self.global_config["enable_profiling"] and tick_count % 20 == 0:
                        printAggregateProfilingReport(20)

                    self.global_config["logger"].info(
                        f"Main tick [{self.sorting_state.value}]: {tick_duration_ms:.1f}ms (update: {update_duration_ms:.1f}ms, step: {step_duration_ms:.1f}ms, cleanup: {cleanup_duration_ms:.1f}ms, queue: {frame_processing_futures_count}/{self.max_queue_size}, objects: {self.scene_tracker.objects_in_frame})"
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
        self.global_config["logger"].info(
            f"Updating sorting state machine - current state: {self.sorting_state.value}"
        )
        current_time_ms = int(time.time() * 1000)

        if self.sorting_state == SortingState.GETTING_NEW_OBJECT:
            if self.timestamps["getting_new_object_start_time"] is None:
                self.timestamps["getting_new_object_start_time"] = current_time_ms
                self._setMotorSpeeds(
                    main_conveyor=self.global_config["main_conveyor_speed"],
                    feeder_conveyor=self.global_config["feeder_conveyor_speed"],
                    vibration_hopper=self.global_config["vibration_hopper_speed"],
                )
                self.global_config["logger"].info("Started motors to get new object")

            break_timestamp, latest_timestamp = self.irl_system[
                "break_beam_sensor"
            ].queryBreakings(self.timestamps["break_beam_last_query_timestamp"])
            self.timestamps["break_beam_last_query_timestamp"] = latest_timestamp

            if break_timestamp != -1:
                self.sorting_state = SortingState.WAITING_FOR_OBJECT_TO_APPEAR
                self.timestamps["waiting_for_object_to_appear_start_time_ms"] = (
                    current_time_ms
                )
                self._setMotorSpeeds(
                    main_conveyor=self.global_config["main_conveyor_speed"],
                    feeder_conveyor=0,
                    vibration_hopper=0,
                )
                self.global_config["logger"].info(
                    f"Break beam triggered at {break_timestamp}, switching to WAITING_FOR_OBJECT_TO_APPEAR"
                )
                return

            if self.scene_tracker.objects_in_frame > 0:
                self.sorting_state = SortingState.WAITING_FOR_OBJECT_TO_CENTER
                self.global_config["logger"].info(
                    "Object appeared in camera, switching to WAITING_FOR_OBJECT_TO_CENTER"
                )
                return

            time_running = (
                current_time_ms - self.timestamps["getting_new_object_start_time"]
            )
            if time_running > self.global_config["getting_new_object_timeout_ms"]:
                self.global_config["logger"].info(
                    "Timeout waiting for object, pausing system"
                )
                self.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_SYSTEM
                self._setMotorSpeeds(0, 0, 0)
                return

        elif self.sorting_state == SortingState.WAITING_FOR_OBJECT_TO_APPEAR:
            if self.scene_tracker.objects_in_frame > 0:
                self.sorting_state = SortingState.WAITING_FOR_OBJECT_TO_CENTER
                self.global_config["logger"].info(
                    "Object appeared in camera, switching to WAITING_FOR_OBJECT_TO_CENTER"
                )
                return

            assert (
                self.timestamps["waiting_for_object_to_appear_start_time_ms"]
                is not None
            )
            time_waiting = (
                current_time_ms
                - self.timestamps["waiting_for_object_to_appear_start_time_ms"]
            )
            if (
                time_waiting
                > self.global_config["waiting_for_object_to_appear_timeout_ms"]
            ):
                self.global_config["logger"].info(
                    "Timeout waiting for object to appear, returning to GETTING_NEW_OBJECT"
                )
                self.sorting_state = SortingState.GETTING_NEW_OBJECT
                self.timestamps["getting_new_object_start_time"] = None
                self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
                return

        elif self.sorting_state == SortingState.WAITING_FOR_OBJECT_TO_CENTER:
            self._setMotorSpeeds(
                main_conveyor=self.global_config["main_conveyor_speed"],
                feeder_conveyor=0,
                vibration_hopper=0,
            )

            if self.scene_tracker.objects_in_frame > 1:
                self.global_config["logger"].info(
                    "Multiple objects detected, returning to GETTING_NEW_OBJECT"
                )
                self.sorting_state = SortingState.GETTING_NEW_OBJECT
                self.timestamps["getting_new_object_start_time"] = None
                self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
                return

            valid_trajectories = self.scene_tracker.getValidNewTrajectories()
            if valid_trajectories:
                self.sorting_state = SortingState.TRYING_TO_CLASSIFY
                self.timestamps["classification_start_time_ms"] = current_time_ms
                self._setMotorSpeeds(
                    main_conveyor=0, feeder_conveyor=0, vibration_hopper=0
                )
                self.global_config["logger"].info(
                    "Object centered, switching to TRYING_TO_CLASSIFY"
                )
                return

            # Check for timeout while waiting for object to center
            start_time = (
                self.timestamps["waiting_for_object_to_appear_start_time_ms"]
                if self.timestamps["waiting_for_object_to_appear_start_time_ms"]
                else self.timestamps["getting_new_object_start_time"]
            )
            if start_time is not None:
                time_waiting = current_time_ms - start_time
                if (
                    time_waiting
                    > self.global_config["waiting_for_object_to_center_timeout_ms"]
                ):
                    self.global_config["logger"].info(
                        "Timeout waiting for object to center, returning to GETTING_NEW_OBJECT"
                    )
                    self.sorting_state = SortingState.GETTING_NEW_OBJECT
                    self.timestamps["getting_new_object_start_time"] = None
                    self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
                    return

        elif self.sorting_state == SortingState.TRYING_TO_CLASSIFY:
            active_classification_threads = len(self.frame_processing_futures)
            valid_trajectories = self.scene_tracker.getValidNewTrajectories()

            has_classified_trajectory = any(
                t.getConsensusClassification() is not None for t in valid_trajectories
            )

            if has_classified_trajectory and active_classification_threads == 0:
                for trajectory in valid_trajectories:
                    if trajectory.getConsensusClassification() is not None:
                        trajectory.setSendingToBinStartTime(current_time_ms)

                self.sorting_state = SortingState.SENDING_ITEM_TO_BIN
                self.timestamps["sending_to_bin_state_start_time_ms"] = current_time_ms
                self.global_config["logger"].info(
                    "Classification complete, switching to SENDING_ITEM_TO_BIN"
                )
                return

            if self.timestamps["classification_start_time_ms"]:
                time_since_classification_start = (
                    current_time_ms - self.timestamps["classification_start_time_ms"]
                )
                if (
                    time_since_classification_start
                    > self.global_config["classification_timeout_ms"]
                ):
                    self.global_config["logger"].info(
                        "Classification timeout, switching to GETTING_NEW_OBJECT"
                    )
                    self.sorting_state = SortingState.GETTING_NEW_OBJECT
                    self.timestamps["getting_new_object_start_time"] = None
                    self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
                    self.timestamps["classification_start_time_ms"] = None
                    return

            if (
                self.scene_tracker.objects_in_frame == 0
                and active_classification_threads == 0
            ):
                self.sorting_state = SortingState.GETTING_NEW_OBJECT
                self.timestamps["getting_new_object_start_time"] = None
                self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
                self.timestamps["classification_start_time_ms"] = None
                self.global_config["logger"].info(
                    "No objects to classify, switching to GETTING_NEW_OBJECT"
                )
                return

        elif self.sorting_state == SortingState.SENDING_ITEM_TO_BIN:
            self._handleSendingItemToBin(current_time_ms)

    def _setMotorSpeeds(
        self, main_conveyor: int, feeder_conveyor: int, vibration_hopper: int
    ) -> None:
        if feeder_conveyor == 0 and vibration_hopper == 0 and main_conveyor != 0:
            main_conveyor -= 30
        if self.main_conveyor_speed != main_conveyor:
            self.main_conveyor_speed = main_conveyor
            if not self.global_config["disable_main_conveyor"]:
                self.irl_system["main_conveyor_dc_motor"].setSpeed(main_conveyor)

        if self.feeder_conveyor_speed != feeder_conveyor:
            self.feeder_conveyor_speed = feeder_conveyor
            if not self.global_config["disable_feeder_conveyor"]:
                self.irl_system["feeder_conveyor_dc_motor"].setSpeed(feeder_conveyor)

        if self.vibration_hopper_speed != vibration_hopper:
            self.vibration_hopper_speed = vibration_hopper
            if not self.global_config["disable_vibration_hopper"]:
                self.irl_system["vibration_hopper_dc_motor"].setSpeed(vibration_hopper)

    def _submitFrameForProcessing(self) -> None:
        captured_at_ms = int(time.time() * 1000)
        frame = self.irl_system["main_camera"].captureFrame()
        if frame is None:
            return

        if self.global_config["camera_preview"]:
            display_frame = cv2.resize(frame, (854, 480))
            cv2.imshow("Camera Feed", display_frame)
            cv2.waitKey(1)

        self.thread_safe_state.set("latest_camera_frame", frame)

        if len(self.frame_processing_futures) >= self.max_queue_size:
            self.global_config["logger"].info(
                f"Frame queue full ({len(self.frame_processing_futures)}/{self.max_queue_size}), dropping frame"
            )
            return

        profiling_record = createFrameProfilingRecord()

        future = self.frame_processor_pool.submit(
            self._processFrame, frame.copy(), profiling_record, captured_at_ms
        )
        self.frame_processing_futures.append(future)

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
            classification_result = self.sorter.classifySegment(frame)
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
                captured_at_ms,
            )

            self.scene_tracker.addObservation(observation)

            profiling_record["observations_saved_count"] += 1

        completeFrameProcessing(profiling_record)

    def _handleSendingItemToBin(self, current_time_ms: int) -> None:
        valid_trajectories = self.scene_tracker.getValidNewTrajectories()
        classified_trajectories = [
            t for t in valid_trajectories if t.getConsensusClassification() is not None
        ]

        trajectory_info = [
            (
                t.trajectory_id,
                t.lifecycle_stage.value
                if hasattr(t, "lifecycle_stage") and t.lifecycle_stage
                else "unknown",
            )
            for t in classified_trajectories
        ]
        self.global_config["logger"].info(
            f"Handling classified trajectories - IDs and lifecycle stages: {trajectory_info}"
        )

        if classified_trajectories and len(classified_trajectories) > 0:
            trajectory = classified_trajectories[0]
            consensus_item_id = trajectory.getConsensusClassification()

            if consensus_item_id and not self.global_config["disable_classification"]:
                # One-time setup: find bin, open doors, reserve bin, set start time
                if trajectory.target_bin is None:
                    category_id = self.sorter.sorting_profile.getCategoryId(
                        consensus_item_id
                    )
                    target_bin = None

                    if category_id:
                        target_bin = self.bin_state_tracker.findAvailableBin(
                            category_id
                        )
                        if target_bin:
                            target_key = binCoordinatesToKey(target_bin)
                            current_bin_category = (
                                self.bin_state_tracker.current_state.get(target_key)
                            )
                            if (
                                current_bin_category
                                == self.bin_state_tracker.fallback_category_id
                            ):
                                category_id = (
                                    self.bin_state_tracker.fallback_category_id
                                )
                    else:
                        target_bin = self.bin_state_tracker.findAvailableBin(
                            self.bin_state_tracker.misc_category_id
                        )
                        category_id = self.bin_state_tracker.misc_category_id

                    if target_bin:
                        # Open doors immediately
                        dm_idx = target_bin["distribution_module_idx"]
                        bin_idx = target_bin["bin_idx"]

                        conveyor_servo = self.irl_system["distribution_modules"][
                            dm_idx
                        ].servo
                        bin_servo = (
                            self.irl_system["distribution_modules"][dm_idx]
                            .bins[bin_idx]
                            .servo
                        )

                        conveyor_servo.setAngle(
                            self.global_config["conveyor_door_open_angle"]
                        )
                        bin_servo.setAngle(self.global_config["bin_door_open_angle"])

                        # Set up trajectory tracking
                        trajectory.setSendingToBinStartTime(current_time_ms)
                        trajectory.setTargetBin(target_bin)
                        trajectory.setLifecycleStage(
                            TrajectoryLifecycleStage.DOORS_OPENED
                        )
                        self.bin_state_tracker.reserveBin(target_bin, category_id)

                        self.global_config["logger"].info(
                            f"Set up bin {target_bin} for trajectory {trajectory.trajectory_id}"
                        )
                    else:
                        self.global_config["logger"].warning(
                            "No available bins, moving to GETTING_NEW_OBJECT"
                        )
                        self.sorting_state = SortingState.GETTING_NEW_OBJECT
                        self.timestamps["getting_new_object_start_time"] = None
                        self.timestamps[
                            "waiting_for_object_to_appear_start_time_ms"
                        ] = None
                        return

                # Continue with existing target bin
                if trajectory.target_bin is not None:
                    self.global_config["logger"].info(
                        f"Sending to target bin: {trajectory.target_bin}"
                    )
                    target_bin = trajectory.target_bin
                    dm_idx = target_bin["distribution_module_idx"]
                    bin_idx = target_bin["bin_idx"]

                    # Set trajectory to in transit if not already
                    if (
                        trajectory.lifecycle_stage
                        == TrajectoryLifecycleStage.DOORS_OPENED
                    ):
                        trajectory.setLifecycleStage(
                            TrajectoryLifecycleStage.IN_TRANSIT
                        )
                        self.global_config["logger"].info(
                            f"Trajectory {trajectory.trajectory_id} now in transit"
                        )

                    self._setMotorSpeeds(
                        main_conveyor=self.global_config["main_conveyor_speed"] + 50,
                        feeder_conveyor=0,
                        vibration_hopper=0,
                    )
                    self.global_config["logger"].info(f"Increased speed")

                    # Check if we've traveled far enough
                    target_distance_cm = self.irl_system["distribution_modules"][
                        dm_idx
                    ].distance_from_camera_center_to_door_begin_cm
                    distance_traveled = None
                    if trajectory.sending_to_bin_start_time_ms is not None:
                        distance_traveled = self.scene_tracker.getDistanceTraveledSince(
                            trajectory.sending_to_bin_start_time_ms
                        )

                    if distance_traveled is None:
                        self.global_config["logger"].warning(
                            "Distance traveled is None - unable to determine object position"
                        )
                    else:
                        self.global_config["logger"].info(
                            f"Trajectory {trajectory.trajectory_id}: traveled {distance_traveled:.1f}cm, target is {target_distance_cm}cm"
                        )

                    if (
                        distance_traveled is not None
                        and distance_traveled >= target_distance_cm
                    ):
                        self.global_config["logger"].info(
                            f"Object reached target distance - Trajectory {trajectory.trajectory_id}: traveled {distance_traveled:.1f}cm, target was {target_distance_cm}cm"
                        )
                        conveyor_servo = self.irl_system["distribution_modules"][
                            dm_idx
                        ].servo
                        bin_servo = (
                            self.irl_system["distribution_modules"][dm_idx]
                            .bins[bin_idx]
                            .servo
                        )

                        # Close conveyor door first, then bin door with separate timing
                        time.sleep(
                            self.global_config["conveyor_door_close_delay_ms"] / 1000.0
                        )
                        conveyor_servo.setAngle(
                            self.global_config["conveyor_door_closed_angle"],
                            self.global_config[
                                "conveyor_door_gradual_close_duration_ms"
                            ],
                        )
                        self.global_config["logger"].info(
                            "Conveyor door closing gradually"
                        )

                        time.sleep(
                            self.global_config["bin_door_close_delay_ms"] / 1000.0
                        )
                        bin_servo.setAngle(self.global_config["bin_door_closed_angle"])
                        self.global_config["logger"].info("Bin door closed")

                        trajectory.setLifecycleStage(
                            TrajectoryLifecycleStage.PROBABLY_IN_BIN
                        )

                        self.sorting_state = SortingState.GETTING_NEW_OBJECT
                        self.timestamps["getting_new_object_start_time"] = None
                        self.timestamps[
                            "waiting_for_object_to_appear_start_time_ms"
                        ] = None
                        self.timestamps["sending_to_bin_state_start_time_ms"] = None
                        self.global_config["logger"].info(
                            f"Item {trajectory.trajectory_id} sent to bin, distance traveled: {distance_traveled:.1f}cm, switching to GETTING_NEW_OBJECT"
                        )
                        return
            else:
                self.global_config["logger"].warning(
                    "No classification or classification disabled"
                )
        else:
            # No classification or no valid trajectories - close doors and return to getting new object
            self.global_config["logger"].info(
                "No valid trajectories in SENDING_ITEM_TO_BIN state, closing doors and returning to GETTING_NEW_OBJECT"
            )

            # Close all open doors
            for distribution_module in self.irl_system["distribution_modules"]:
                distribution_module.servo.setAngle(
                    self.global_config["conveyor_door_closed_angle"]
                )
                for bin_servo in distribution_module.bins:
                    bin_servo.servo.setAngle(
                        self.global_config["bin_door_closed_angle"]
                    )

            self.sorting_state = SortingState.GETTING_NEW_OBJECT
            self.timestamps["getting_new_object_start_time"] = None
            self.timestamps["waiting_for_object_to_appear_start_time_ms"] = None
            self.timestamps["sending_to_bin_state_start_time_ms"] = None
            return

    def _updateTrajectories(self) -> None:
        trajectories_to_update = self.scene_tracker.getTrajectories()

        for trajectory in trajectories_to_update:
            try:
                saveTrajectory(self.global_config, trajectory)
            except Exception as e:
                self.global_config["logger"].error(
                    f"Failed to save trajectory {trajectory.trajectory_id}: {e}"
                )

    def _cleanupCompletedFutures(self) -> None:
        completed_futures = [f for f in self.frame_processing_futures if f.done()]

        for future in completed_futures:
            try:
                future.result()
            except Exception as e:
                self.global_config["logger"].error(f"Frame processing error: {e}")

        self.frame_processing_futures = [
            f for f in self.frame_processing_futures if not f.done()
        ]

    def _shutdownFrameProcessor(self) -> None:
        self.global_config["logger"].info("Shutting down frame processor...")

        if self.frame_processing_futures:
            self.global_config["logger"].info(
                f"Waiting for {len(self.frame_processing_futures)} frames to complete..."
            )
            concurrent.futures.wait(self.frame_processing_futures, timeout=10.0)

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

    def _resetServos(self) -> None:
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
