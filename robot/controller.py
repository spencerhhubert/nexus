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
    classifySegment,
    maskSegment,
    calculateNormalizedBounds,
)
from robot.ai.segment import initializeSegmentationModel
from robot.ai.brickognize_types import BrickognizeClassificationResult
from robot.storage.sqlite3.migrations import initializeDatabase
from robot.storage.sqlite3.operations import saveObservationToDatabase
from robot.storage.blob import ensureBlobStorageExists, saveTrajectory
from robot.trajectories import (
    Observation,
    Trajectory,
    TrajectoryLifecycleStage,
)
from robot.scene_tracker import SceneTracker
from robot.sorting import Category, SortingProfile
from robot.bin_state_tracker import BinStateTracker, BinCoordinates, BinState
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


class SystemLifecycleStage(Enum):
    INITIALIZING = "initializing"
    STARTING_HARDWARE = "starting_hardware"
    RUNNING = "running"
    STOPPING = "stopping"
    SHUTDOWN = "shutdown"


class SortingController:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_system: IRLSystemInterface,
    ):
        self.global_config = global_config
        self.irl_system = irl_system
        self.lifecycle_stage = SystemLifecycleStage.INITIALIZING

        self.sorting_profile = SortingProfile(
            self.global_config, "hardcoded_profile", {}
        )

        self.bin_state_tracker = BinStateTracker(
            self.global_config,
            self.irl_system["distribution_modules"],
            self.sorting_profile,
        )

        self.door_scheduler = DoorScheduler(
            self.global_config, self.irl_system["distribution_modules"]
        )

        self.scene_tracker = SceneTracker(
            self.global_config, self.irl_system["main_camera"].calibration
        )

        self.segmentation_model = initializeSegmentationModel(self.global_config)

        self.max_worker_threads = global_config["max_worker_threads"]
        self.max_queue_size = global_config["max_queue_size"]
        self.frame_processor_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_worker_threads, thread_name_prefix="frame_processor"
        )
        self.active_futures: List[concurrent.futures.Future] = []

    def initialize(self) -> None:
        self.global_config["logger"].info("Initializing sorting controller...")

        ensureBlobStorageExists(self.global_config)
        initializeDatabase(self.global_config)

        initializeAsyncProfiling(self.global_config)

        self.lifecycle_stage = SystemLifecycleStage.STARTING_HARDWARE

    def startHardware(self) -> None:
        self.global_config["logger"].info("Starting hardware systems...")

        if not self.global_config["disable_main_conveyor"]:
            self.irl_system["main_conveyor_dc_motor"].setSpeed(100)
        if not self.global_config["disable_feeder_conveyor"]:
            self.irl_system["feeder_conveyor_dc_motor"].setSpeed(200)
        if not self.global_config["disable_vibration_hopper"]:
            self.irl_system["vibration_hopper_dc_motor"].setSpeed(65)

        self.lifecycle_stage = SystemLifecycleStage.RUNNING

    def run(self) -> None:
        self.global_config["logger"].info("Starting main control loop...")

        cv2.namedWindow("Camera Feed", cv2.WINDOW_AUTOSIZE)

        enable_profiling = self.global_config.get("enable_profiling", False)
        profiler = None
        if enable_profiling:
            profiler = cProfile.Profile()
            profiler.enable()
            self.global_config["logger"].info("Performance profiling enabled")

        tick_count = 0
        try:
            while self.lifecycle_stage == SystemLifecycleStage.RUNNING:
                try:
                    tick_start_time_ms = time.time() * 1000

                    self._submitFrameForProcessing()

                    update_start_ms = time.time() * 1000
                    self._updateTrajectories()
                    update_duration_ms = time.time() * 1000 - update_start_ms

                    step_start_ms = time.time() * 1000
                    self.scene_tracker.stepScene()
                    step_duration_ms = time.time() * 1000 - step_start_ms

                    trigger_start_ms = time.time() * 1000
                    self._processTriggerActions()
                    trigger_duration_ms = time.time() * 1000 - trigger_start_ms

                    cleanup_start_ms = time.time() * 1000
                    self._cleanupCompletedFutures()
                    cleanup_duration_ms = time.time() * 1000 - cleanup_start_ms

                    tick_duration_ms = time.time() * 1000 - tick_start_time_ms
                    active_futures_count = len(self.active_futures)

                    # Print aggregate profiling report every 20 ticks when profiling enabled
                    if self.global_config["enable_profiling"] and tick_count % 20 == 0:
                        printAggregateProfilingReport(20)

                    self.global_config["logger"].info(
                        f"Main tick: {tick_duration_ms:.1f}ms (update: {update_duration_ms:.1f}ms, step: {step_duration_ms:.1f}ms, trigger: {trigger_duration_ms:.1f}ms, cleanup: {cleanup_duration_ms:.1f}ms, queue: {active_futures_count}/{self.max_queue_size})"
                    )

                    tick_count += 1

                    time.sleep(self.global_config["capture_delay_ms"] / 1000.0)

                except KeyboardInterrupt:
                    self.global_config["logger"].info("Interrupt received, stopping...")
                    self.lifecycle_stage = SystemLifecycleStage.STOPPING
                    break
                except Exception as e:
                    self.global_config["logger"].error(f"Error in main loop: {e}")
                    self.lifecycle_stage = SystemLifecycleStage.STOPPING
                    break
        finally:
            if enable_profiling and profiler is not None:
                profiler.disable()
                saveProfilingResults(self.global_config, profiler)

            # Wait for remaining frame processing to complete
            self._shutdownFrameProcessor()

    def _submitFrameForProcessing(self) -> None:
        frame = self.irl_system["main_camera"].captureFrame()
        if frame is None:
            return

        # Resize frame for display (480p)
        display_frame = cv2.resize(frame, (640, 480))
        cv2.imshow("Camera Feed", display_frame)
        cv2.waitKey(1)

        # Check if we have too many queued frames
        if len(self.active_futures) >= self.max_queue_size:
            self.global_config["logger"].info(
                f"Frame queue full ({len(self.active_futures)}/{self.max_queue_size}), dropping frame"
            )
            return

        profiling_record = createFrameProfilingRecord()

        # Submit frame for processing
        future = self.frame_processor_pool.submit(
            self._processFrame, frame.copy(), profiling_record
        )
        self.active_futures.append(future)

    def _processFrame(
        self, frame: np.ndarray, profiling_record: AsyncFrameProfilingRecord
    ) -> None:
        startFrameProcessing(profiling_record)

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
            classification_result = classifySegment(masked_image, self.global_config)
            classification_duration_ms = (time.time() * 1000) - classification_start_ms

            profiling_record[
                "classification_total_duration_ms"
            ] += classification_duration_ms
            profiling_record["classification_calls_count"] += 1

            if not classification_result.get("items", []):
                self.global_config["logger"].info(
                    "No items found in classification result, skipping segment"
                )
                continue

            BRICKOGNIZE_SCORE_THRESHOLD = 0.25
            max_score = (
                max(item["score"] for item in classification_result["items"])
                if classification_result["items"]
                else 0.0
            )
            if max_score < BRICKOGNIZE_SCORE_THRESHOLD:
                self.global_config["logger"].info(
                    f"No items above score threshold {BRICKOGNIZE_SCORE_THRESHOLD} (max: {max_score:.3f}), skipping segment"
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

    def _processTriggerActions(self) -> None:
        camera_trigger_position = self.global_config["camera_trigger_position"]
        trajectories_to_trigger = self.scene_tracker.getTrajectoriesToTrigger(
            camera_trigger_position
        )

        for trajectory in trajectories_to_trigger:
            item_id = trajectory.getConsensusClassification()
            target_bin = self._getTargetBin(item_id)

            if not target_bin:
                continue

            delay_ms = self._calculateDoorDelay(trajectory, target_bin)
            if delay_ms is None:
                self.global_config["logger"].info(
                    f"Cannot schedule action for trajectory {trajectory.trajectory_id} - conveyor speed unknown"
                )
                continue

            self.door_scheduler.scheduleDoorAction(target_bin, delay_ms)
            self.bin_state_tracker.reserveBin(target_bin, "default")
            self.scene_tracker.markTrajectoryInTransit(trajectory.trajectory_id)

            self.global_config["logger"].info(
                f"Scheduled action for trajectory {trajectory.trajectory_id} -> bin {target_bin} with delay {delay_ms}ms"
            )

    def _calculateDoorDelay(
        self, trajectory: Trajectory, target_bin: BinCoordinates
    ) -> Optional[int]:
        if target_bin["distribution_module_idx"] >= len(
            self.irl_system["distribution_modules"]
        ):
            return None

        # Get when trajectory was at camera center
        time_at_center_ms = self.scene_tracker.predictTimeAtCameraCenter(trajectory)
        if time_at_center_ms is None:
            return None

        # Get distance from camera center to door beginning
        target_distance_cm = self.irl_system["distribution_modules"][
            target_bin["distribution_module_idx"]
        ].distance_from_camera_center_to_door_begin_cm

        travel_time_ms = self.scene_tracker.calculateTravelTime(target_distance_cm)
        if travel_time_ms is None:
            return None

        # Calculate delay: time for object to travel from center to door, minus time already elapsed since center
        current_time_ms = int(time.time() * 1000)
        time_since_center_ms = current_time_ms - time_at_center_ms
        delay_ms = int(travel_time_ms) - time_since_center_ms

        return max(0, delay_ms)

    def _getTargetBin(self, item_id: str) -> Optional[BinCoordinates]:
        # needs to map item id to category id
        # todo
        return self.bin_state_tracker.findAvailableBin("default")

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

        # Wait for remaining futures to complete
        if self.active_futures:
            self.global_config["logger"].info(
                f"Waiting for {len(self.active_futures)} frames to complete..."
            )
            concurrent.futures.wait(self.active_futures, timeout=10.0)

        self.frame_processor_pool.shutdown(wait=True)

    def stop(self) -> None:
        self.global_config["logger"].info("Stopping sorting controller...")
        self.lifecycle_stage = SystemLifecycleStage.STOPPING

        self.irl_system["main_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["feeder_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["vibration_hopper_dc_motor"].setSpeed(0)

        self._shutdownFrameProcessor()

        cv2.destroyAllWindows()

        self.irl_system["arduino"].flush()
        self.irl_system["arduino"].close()
        self.irl_system["main_camera"].release()

        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN
