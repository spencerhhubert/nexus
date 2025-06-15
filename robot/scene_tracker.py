import threading
import time
import uuid
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from robot.global_config import GlobalConfig
from robot.trajectories import (
    Trajectory,
    TrajectoryLifecycleStage,
    Observation,
    createTrajectory,
)
from robot.util.bricklink import splitBricklinkId
from robot.irl.camera_calibration import CameraCalibration


class SceneTracker:
    def __init__(self, global_config: GlobalConfig, calibration: CameraCalibration):
        self.global_config = global_config
        self.calibration = calibration
        self.active_trajectories: List[Trajectory] = []
        self.conveyor_velocity_cm_per_ms: Optional[float] = None
        self.lock = threading.Lock()

        # Parameters for trajectory management
        self.max_trajectory_age_ms = 30000  # 30 seconds
        self.min_observations_for_speed = 4
        self.num_trajectories_for_speed_estimate = 16
        self.min_trajectories_to_keep = 10

    def addObservation(self, observation: Observation) -> None:
        with self.lock:
            matching_trajectory = self._findMatchingTrajectory(observation)

            if matching_trajectory is None:
                new_trajectory = createTrajectory(self.global_config, observation)
                self.active_trajectories.append(new_trajectory)
                self.global_config["logger"].info(
                    f"Created new trajectory {new_trajectory.trajectory_id}"
                )
            else:
                observation.trajectory_id = matching_trajectory.trajectory_id
                matching_trajectory.addObservation(observation)
                self.global_config["logger"].info(
                    f"Added observation to trajectory {matching_trajectory.trajectory_id}"
                )

    def calculateTravelTime(self, distance_cm: float) -> Optional[float]:
        with self.lock:
            speed = self.conveyor_velocity_cm_per_ms

        if speed is None or speed <= 0:
            self.global_config["logger"].info(
                f"Cannot calculate travel time: distance={distance_cm:.1f}cm, speed={speed} cm/ms"
            )
            return None

        travel_time_ms = distance_cm / speed
        self.global_config["logger"].info(
            f"Travel time calculation: distance={distance_cm:.1f}cm, speed={speed:.4f}cm/ms, time={travel_time_ms:.1f}ms"
        )
        return travel_time_ms

    def predictTimeAtCameraCenter(self, trajectory: Trajectory) -> Optional[int]:
        if len(trajectory.observations) < 2:
            return None

        camera_center_x_percent = 0.5

        # Check if any observation is already at or past center
        for obs in trajectory.observations:
            if obs.center_x_percent <= camera_center_x_percent:
                return obs.timestamp_ms

        # Find the two observations that bracket the center position
        for i in range(len(trajectory.observations) - 1):
            obs1 = trajectory.observations[i]
            obs2 = trajectory.observations[i + 1]

            if (
                obs1.center_x_percent > camera_center_x_percent
                and obs2.center_x_percent <= camera_center_x_percent
            ):
                # Interpolate between these two observations
                x_range = obs1.center_x_percent - obs2.center_x_percent
                if x_range <= 0:
                    continue

                x_progress = (obs1.center_x_percent - camera_center_x_percent) / x_range
                time_range = obs2.timestamp_ms - obs1.timestamp_ms
                predicted_time = obs1.timestamp_ms + int(x_progress * time_range)
                return predicted_time

        # If we haven't found it in observations, extrapolate from the last two
        if len(trajectory.observations) >= 2:
            obs1 = trajectory.observations[-2]
            obs2 = trajectory.observations[-1]

            time_delta = obs2.timestamp_ms - obs1.timestamp_ms
            x_delta = obs2.center_x_percent - obs1.center_x_percent

            if time_delta > 0 and x_delta != 0:
                x_remaining = obs2.center_x_percent - camera_center_x_percent
                time_to_center = int(x_remaining * time_delta / x_delta)
                return obs2.timestamp_ms + time_to_center

        return None

    def getTrajectoriesToTrigger(self, trigger_position: float) -> List[Trajectory]:
        with self.lock:
            trajectories_to_trigger = []

            for trajectory in self.active_trajectories:
                if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                    continue

                if trajectory.target_bin is not None:
                    continue

                if trajectory.shouldTriggerAction(self.global_config):
                    trajectories_to_trigger.append(trajectory)

            return trajectories_to_trigger.copy()

    def markTrajectoryInTransit(self, trajectory_id: str) -> None:
        with self.lock:
            for trajectory in self.active_trajectories:
                if trajectory.trajectory_id == trajectory_id:
                    trajectory.setLifecycleStage(TrajectoryLifecycleStage.IN_TRANSIT)
                    break

    def stepScene(self) -> None:
        with self.lock:
            self._updateConveyorSpeed()
            self._checkForTrajectoriesLeavingCamera()
            self._cleanupOldTrajectories()

    def getActiveTrajectories(self) -> List[Trajectory]:
        with self.lock:
            return self.active_trajectories.copy()

    def _findMatchingTrajectory(
        self, new_observation: Observation
    ) -> Optional[Trajectory]:
        best_trajectory = None
        best_score = 0.0

        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                continue

            score = trajectory.getCompatibilityScore(
                new_observation, self.global_config
            )

            if score > best_score:
                best_score = score
                best_trajectory = trajectory

        return best_trajectory

    def _updateConveyorSpeed(self) -> None:
        # Filter trajectories with enough observations for speed calculation
        valid_trajectories = [
            t
            for t in self.active_trajectories
            if len(t.observations) >= self.min_observations_for_speed
        ]

        recent_trajectories = valid_trajectories[
            -self.num_trajectories_for_speed_estimate :
        ]

        if not recent_trajectories:
            return

        trajectory_speeds = []

        for trajectory in recent_trajectories:
            self._calcAndSetTrajectoryVelocity(trajectory)
            if trajectory.velocity_cm_per_ms is not None:
                trajectory_speeds.append(trajectory.velocity_cm_per_ms)

        self.global_config["logger"].info(f"Trajectory speeds: {trajectory_speeds}")

        if trajectory_speeds:
            self.conveyor_velocity_cm_per_ms = sum(trajectory_speeds) / len(
                trajectory_speeds
            )

    def _calcAndSetTrajectoryVelocity(self, trajectory: Trajectory) -> None:
        if len(trajectory.observations) < 2:
            return

        total_distance_cm = 0.0
        total_time_ms = 0.0

        for i in range(1, len(trajectory.observations)):
            obs_prev = trajectory.observations[i - 1]
            obs_curr = trajectory.observations[i]

            time_delta_ms = obs_curr.timestamp_ms - obs_prev.timestamp_ms
            if time_delta_ms <= 0:
                self.global_config["logger"].error(
                    f"Observations out of order, invalid time delta: {time_delta_ms}"
                )
                continue

            distance_cm = self.calibration.getPhysicalDistanceBetweenPoints(
                obs_prev.center_x_px,
                obs_prev.center_y_px,
                obs_curr.center_x_px,
                obs_curr.center_y_px,
            )

            total_distance_cm += distance_cm
            total_time_ms += time_delta_ms

        if total_time_ms <= 0:
            return

        velocity_cm_per_ms = total_distance_cm / total_time_ms
        trajectory.setVelocity(velocity_cm_per_ms)

    def _checkForTrajectoriesLeavingCamera(self) -> None:
        TIME_SINCE_UNDER_CAMERA_THRESHOLD_MS = 500
        current_time_ms = int(time.time() * 1000)

        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                continue

            latest_observation = trajectory.getLatestObservation()
            if not latest_observation:
                continue

            # Check if trajectory has left camera view (moved off left side)
            if latest_observation.center_x_percent <= 0.0:
                time_since_last_observation = (
                    current_time_ms - latest_observation.timestamp_ms
                )
                if time_since_last_observation >= TIME_SINCE_UNDER_CAMERA_THRESHOLD_MS:
                    trajectory.setLifecycleStage(TrajectoryLifecycleStage.IN_TRANSIT)
                    self.global_config["logger"].info(
                        f"Trajectory {trajectory.trajectory_id} left camera view, marking as in transit"
                    )

    def _cleanupOldTrajectories(self) -> None:
        current_time_ms = int(time.time() * 1000)

        # Don't clean up if we have too few trajectories
        if len(self.active_trajectories) <= self.min_trajectories_to_keep:
            return

        # Remove trajectories that are too old or have completed their lifecycle
        self.active_trajectories = [
            t
            for t in self.active_trajectories
            if (
                current_time_ms - t.observations[0].timestamp_ms
                < self.max_trajectory_age_ms
                and t.lifecycle_stage != TrajectoryLifecycleStage.DOORS_CLOSED
            )
        ]

        # Ensure we still have minimum trajectories after cleanup
        if len(self.active_trajectories) < self.min_trajectories_to_keep:
            return

        # Keep a reasonable number of trajectories for speed estimation
        max_trajectories = 50
        if len(self.active_trajectories) > max_trajectories:
            # Sort by most recent observation and keep the newest ones
            self.active_trajectories.sort(
                key=lambda t: max(obs.timestamp_ms for obs in t.observations),
                reverse=True,
            )
            self.active_trajectories = self.active_trajectories[:max_trajectories]
