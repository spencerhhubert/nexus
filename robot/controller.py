import time
import numpy as np
import uuid
import cProfile
import pstats
import io
import os
import concurrent.futures
import threading
from typing import List, Optional, Dict, Any
from enum import Enum
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface, DistributionModuleConfig
from robot.ai import segmentFrame, classifySegment
from robot.ai.segment import initializeSegmentationModel
from robot.ai.brickognize_types import BrickognizeClassificationResult
from robot.storage.sqlite3.migrations import initializeDatabase
from robot.storage.sqlite3.operations import saveObservationToDatabase
from robot.storage.blob import ensureBlobStorageExists, saveTrajectory
from robot.trajectories import (
    Observation,
    ObjectTrajectory,
    createTrajectory,
    findMatchingTrajectory,
    TrajectoryLifecycleStage,
)
from robot.sorting import Category, SortingProfile
from robot.bin_state_tracker import BinStateTracker, BinCoordinates, BinState
from robot.door_scheduler import DoorScheduler
from robot.conveyor_speed_tracker import estimateConveyorSpeed
from robot.async_profiling import (
    initializeAsyncProfiling,
    createFrameProfilingRecord,
    startFrameProcessing,
    completeFrameProcessing,
    printAggregateProfilingReport,
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
        distribution_module_configs: List[DistributionModuleConfig],
    ):
        self.global_config = global_config
        self.irl_system = irl_system
        self.distribution_module_configs = distribution_module_configs
        self.lifecycle_stage = SystemLifecycleStage.INITIALIZING

        self.sorting_profile: Optional[SortingProfile] = None
        self.bin_state_tracker: Optional[BinStateTracker] = None
        self.door_scheduler: Optional[DoorScheduler] = None

        self.active_trajectories: List[ObjectTrajectory] = []
        self.completed_trajectories: List[ObjectTrajectory] = []
        self.segmentation_model = None

        self.max_worker_threads = global_config["max_worker_threads"]
        self.max_queue_size = global_config["max_queue_size"]
        self.frame_processor_pool: Optional[
            concurrent.futures.ThreadPoolExecutor
        ] = None
        self.active_futures: List[concurrent.futures.Future] = []
        self.trajectory_lock = threading.Lock()

    def initialize(self) -> None:
        self.global_config["logger"].info("Initializing sorting controller...")

        ensureBlobStorageExists(self.global_config)
        initializeDatabase(self.global_config)

        self.sorting_profile = SortingProfile(
            self.global_config, "hardcoded_profile", {}
        )

        available_bins = self._buildAvailableBinCoordinates()
        self.bin_state_tracker = BinStateTracker(
            self.global_config, available_bins, self.sorting_profile
        )
        self.door_scheduler = DoorScheduler(self.global_config)
        self.segmentation_model = initializeSegmentationModel(self.global_config)

        initializeAsyncProfiling(self.global_config)

        self.frame_processor_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_worker_threads, thread_name_prefix="frame_processor"
        )

        self.lifecycle_stage = SystemLifecycleStage.STARTING_HARDWARE

    def _buildAvailableBinCoordinates(self) -> List[BinCoordinates]:
        available_bins = []
        sorted_configs = sorted(
            self.distribution_module_configs, key=lambda x: x["distance_from_camera"]
        )

        for dm_idx, config in enumerate(sorted_configs):
            for bin_idx in range(config["num_bins"]):
                available_bins.append(
                    {"distribution_module_idx": dm_idx, "bin_idx": bin_idx}
                )

        return available_bins

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

                    trigger_start_ms = time.time() * 1000
                    self._processTriggerActions()
                    trigger_duration_ms = time.time() * 1000 - trigger_start_ms

                    cleanup_start_ms = time.time() * 1000
                    self._cleanupCompletedTrajectories()
                    self._cleanupCompletedFutures()
                    cleanup_duration_ms = time.time() * 1000 - cleanup_start_ms

                    tick_duration_ms = time.time() * 1000 - tick_start_time_ms
                    active_futures_count = len(self.active_futures)

                    # Print aggregate profiling report every 20 ticks when profiling enabled
                    if self.global_config["enable_profiling"] and tick_count % 20 == 0:
                        printAggregateProfilingReport(20)

                    self.global_config["logger"].info(
                        f"Main tick: {tick_duration_ms:.1f}ms (update: {update_duration_ms:.1f}ms, trigger: {trigger_duration_ms:.1f}ms, cleanup: {cleanup_duration_ms:.1f}ms, queue: {active_futures_count}/{self.max_queue_size})"
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
                self._saveProfilingResults(profiler)

            # Wait for remaining frame processing to complete
            self._shutdownFrameProcessor()

    def _submitFrameForProcessing(self) -> None:
        frame = self.irl_system["main_camera"].captureFrame()
        if frame is None:
            return

        # Check if we have too many queued frames
        if len(self.active_futures) >= self.max_queue_size:
            self.global_config["logger"].info(
                f"Frame queue full ({len(self.active_futures)}/{self.max_queue_size}), dropping frame"
            )
            return

        profiling_record = createFrameProfilingRecord()

        # Submit frame for processing
        if self.frame_processor_pool is not None:
            future = self.frame_processor_pool.submit(
                self._processFrame, frame.copy(), profiling_record
            )
            self.active_futures.append(future)

    def _processFrame(self, frame: np.ndarray, profiling_record) -> None:
        if profiling_record is not None:
            startFrameProcessing(profiling_record)

        # Segmentation
        segmentation_start_ms = time.time() * 1000
        segments = segmentFrame(frame, self.segmentation_model, self.global_config)
        segmentation_duration_ms = (time.time() * 1000) - segmentation_start_ms

        if profiling_record is not None:
            profiling_record["segmentation_start_ms"] = segmentation_start_ms
            profiling_record["segmentation_duration_ms"] = segmentation_duration_ms
            profiling_record["segments_found_count"] = len(segments)

        for segment in segments:
            masked_image = self._maskSegment(frame, segment)
            if masked_image is None:
                continue

            classification_start_ms = time.time() * 1000
            classification_result = classifySegment(masked_image, self.global_config)
            classification_duration_ms = (time.time() * 1000) - classification_start_ms

            if profiling_record is not None:
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
            ) = self._calculateNormalizedBounds(frame, segment)

            with self.trajectory_lock:
                observation, new_trajectory = self._assignToTrajectory(
                    center_x,
                    center_y,
                    bbox_width,
                    bbox_height,
                    frame,
                    masked_image,
                    classification_result,
                )

            if profiling_record is not None:
                profiling_record["observations_saved_count"] += 1

        # Complete frame processing profiling
        if profiling_record is not None:
            completeFrameProcessing(profiling_record)

    def _maskSegment(self, full_frame: np.ndarray, segment) -> Optional[np.ndarray]:
        y_min, y_max, x_min, x_max = segment.bbox

        if y_min >= y_max or x_min >= x_max:
            return None

        y_min = max(0, y_min)
        y_max = min(full_frame.shape[0] - 1, y_max)
        x_min = max(0, x_min)
        x_max = min(full_frame.shape[1] - 1, x_max)

        cropped_image = full_frame[y_min : y_max + 1, x_min : x_max + 1]

        mask_np = segment.mask.cpu().numpy()
        cropped_mask = mask_np[y_min : y_max + 1, x_min : x_max + 1]
        masked_image = cropped_image.copy()
        masked_image[~cropped_mask] = 0

        return masked_image

    def _calculateNormalizedBounds(
        self, full_frame: np.ndarray, segment
    ) -> tuple[float, float, float, float]:
        y_min, y_max, x_min, x_max = segment.bbox

        center_x = (x_min + x_max) / 2.0 / full_frame.shape[1]
        center_y = (y_min + y_max) / 2.0 / full_frame.shape[0]
        bbox_width = (x_max - x_min) / full_frame.shape[1]
        bbox_height = (y_max - y_min) / full_frame.shape[0]

        return center_x, center_y, bbox_width, bbox_height

    def _assignToTrajectory(
        self,
        center_x: float,
        center_y: float,
        bbox_width: float,
        bbox_height: float,
        full_frame: np.ndarray,
        masked_image: np.ndarray,
        classification_result: BrickognizeClassificationResult,
    ) -> tuple[Observation, Optional[ObjectTrajectory]]:
        temp_observation = Observation(
            None,
            center_x,
            center_y,
            bbox_width,
            bbox_height,
            full_frame,
            masked_image,
            classification_result,
        )

        matching_trajectory = findMatchingTrajectory(
            self.global_config,
            temp_observation,
            self.active_trajectories,
        )

        if matching_trajectory is None:
            new_trajectory = createTrajectory(self.global_config, temp_observation)
            self.active_trajectories.append(new_trajectory)
            return temp_observation, new_trajectory
        else:
            observation = Observation(
                matching_trajectory.trajectory_id,
                center_x,
                center_y,
                bbox_width,
                bbox_height,
                full_frame,
                masked_image,
                classification_result,
            )
            matching_trajectory.addObservation(observation)
            return observation, None

    def _updateTrajectories(self) -> None:
        with self.trajectory_lock:
            trajectories_to_update = self.active_trajectories.copy()

        for trajectory in trajectories_to_update:
            try:
                saveTrajectory(self.global_config, trajectory)
            except Exception as e:
                self.global_config["logger"].error(
                    f"Failed to save trajectory {trajectory.trajectory_id}: {e}"
                )

    def _processTriggerActions(self) -> None:
        with self.trajectory_lock:
            trajectories_to_check = self.active_trajectories.copy()

        for trajectory in trajectories_to_check:
            if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                continue

            if not trajectory.shouldTriggerAction(self.global_config):
                continue

            item_id = trajectory.getConsensusClassification()
            target_bin = self._getTargetBin(item_id)

            if (
                not target_bin
                or self.door_scheduler is None
                or self.bin_state_tracker is None
            ):
                continue

            delay_ms = self._calculateDoorDelay(trajectory, target_bin)
            if delay_ms is None:
                self.global_config["logger"].info(
                    f"Cannot schedule action for trajectory {trajectory.trajectory_id} - conveyor speed unknown"
                )
                continue

            self.door_scheduler.scheduleDoorAction(target_bin, delay_ms)
            self.bin_state_tracker.reserveBin(target_bin, "default")

            with self.trajectory_lock:
                trajectory.lifecycle_stage = TrajectoryLifecycleStage.IN_TRANSIT

            self.global_config["logger"].info(
                f"Scheduled action for trajectory {trajectory.trajectory_id} -> bin {target_bin} with delay {delay_ms}ms"
            )

    def _calculateDoorDelay(
        self, trajectory: ObjectTrajectory, target_bin: BinCoordinates
    ) -> Optional[int]:
        conveyor_speed = estimateConveyorSpeed(
            self.active_trajectories, self.completed_trajectories
        )
        if conveyor_speed is None:
            return None

        # Calculate distance from current position to target bin
        # For now, use a simple estimate based on distribution module distance
        if target_bin["distribution_module_idx"] < len(
            self.distribution_module_configs
        ):
            target_distance = self.distribution_module_configs[
                target_bin["distribution_module_idx"]
            ]["distance_from_camera"]
            travel_time_ms = (
                int((target_distance / conveyor_speed) * 1000)
                if conveyor_speed > 0
                else None
            )
            return max(0, travel_time_ms) if travel_time_ms is not None else None

        return None

    def _getTargetBin(self, item_id: str) -> Optional[BinCoordinates]:
        if self.bin_state_tracker is None:
            return None
        return self.bin_state_tracker.findAvailableBin("default")

    def _cleanupCompletedTrajectories(self) -> None:
        with self.trajectory_lock:
            completed = [
                t
                for t in self.active_trajectories
                if t.lifecycle_stage == TrajectoryLifecycleStage.DOORS_CLOSED
            ]

            self.completed_trajectories.extend(completed)

            # Keep only recent completed trajectories for speed estimation
            max_completed = 50
            if len(self.completed_trajectories) > max_completed:
                self.completed_trajectories = self.completed_trajectories[
                    -max_completed:
                ]

            self.active_trajectories = [
                t
                for t in self.active_trajectories
                if t.lifecycle_stage != TrajectoryLifecycleStage.DOORS_CLOSED
            ]

    def _cleanupCompletedFutures(self) -> None:
        completed_futures = [f for f in self.active_futures if f.done()]

        for future in completed_futures:
            try:
                future.result()  # This will raise any exceptions that occurred
            except Exception as e:
                self.global_config["logger"].error(f"Frame processing error: {e}")

        self.active_futures = [f for f in self.active_futures if not f.done()]

    def _shutdownFrameProcessor(self) -> None:
        if self.frame_processor_pool is not None:
            self.global_config["logger"].info("Shutting down frame processor...")

            # Wait for remaining futures to complete
            if self.active_futures:
                self.global_config["logger"].info(
                    f"Waiting for {len(self.active_futures)} frames to complete..."
                )
                concurrent.futures.wait(self.active_futures, timeout=10.0)

            self.frame_processor_pool.shutdown(wait=True)
            self.frame_processor_pool = None

    def stop(self) -> None:
        self.global_config["logger"].info("Stopping sorting controller...")
        self.lifecycle_stage = SystemLifecycleStage.STOPPING

        self.irl_system["main_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["feeder_conveyor_dc_motor"].setSpeed(0)
        self.irl_system["vibration_hopper_dc_motor"].setSpeed(0)

        self._shutdownFrameProcessor()

        self.irl_system["arduino"].flush()
        self.irl_system["arduino"].close()
        self.irl_system["main_camera"].release()

        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN

    def _saveProfilingResults(self, profiler: cProfile.Profile) -> None:
        self.global_config["logger"].info("Saving profiling results...")

        profiles_dir = "./profiles"
        os.makedirs(profiles_dir, exist_ok=True)

        profile_file = os.path.join(
            profiles_dir, f"profile_{self.global_config['run_id']}.prof"
        )
        profiler.dump_stats(profile_file)

        # Log top time-consuming functions
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(20)  # Top 20 functions

        self.global_config["logger"].info(f"Profiling results saved to {profile_file}")
        self.global_config["logger"].info("Top time-consuming functions:")
        for line in s.getvalue().split("\n")[:25]:  # Log first 25 lines
            if line.strip():
                self.global_config["logger"].info(line)
