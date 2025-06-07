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


class SceneTracker:
    def __init__(self, global_config: GlobalConfig, pixels_per_cm: float):
        self.global_config = global_config
        self.pixels_per_cm = pixels_per_cm
        self.active_trajectories: List[Trajectory] = []
        self.conveyor_velocity_cm_per_sec: Optional[float] = None
        self.lock = threading.Lock()

        # Parameters for trajectory management
        self.max_trajectory_age_ms = 30000  # 30 seconds
        self.min_observations_for_speed = 4
        self.num_trajectories_for_speed_estimate = 10

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

            # Update speed estimate and clean up old trajectories
            self._updateConveyorSpeed()
            self._cleanupOldTrajectories()

    def calculateTravelTime(self, distance_cm: float) -> Optional[float]:
        with self.lock:
            speed = self.conveyor_velocity_cm_per_sec
        if speed is None or speed <= 0:
            return None
        return distance_cm / speed

    def getTrajectoriesToTrigger(self, trigger_position: float) -> List[Trajectory]:
        with self.lock:
            trajectories_to_trigger = []

            for trajectory in self.active_trajectories:
                if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                    continue

                if trajectory.shouldTriggerAction(self.global_config):
                    trajectories_to_trigger.append(trajectory)

            return trajectories_to_trigger.copy()

    def markTrajectoryInTransit(self, trajectory_id: str) -> None:
        with self.lock:
            for trajectory in self.active_trajectories:
                if trajectory.trajectory_id == trajectory_id:
                    trajectory.lifecycle_stage = TrajectoryLifecycleStage.IN_TRANSIT
                    break

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
            speed = self._calculateTrajectorySpeed(trajectory)
            if speed is not None:
                trajectory_speeds.append(speed)

        if trajectory_speeds:
            self.conveyor_velocity_cm_per_sec = sum(trajectory_speeds) / len(
                trajectory_speeds
            )

    def _calculateTrajectorySpeed(self, trajectory: Trajectory) -> Optional[float]:
        if len(trajectory.observations) < 2:
            return None

        total_distance_cm = 0.0
        total_time_ms = 0.0

        for i in range(1, len(trajectory.observations)):
            obs_prev = trajectory.observations[i - 1]
            obs_curr = trajectory.observations[i]

            time_delta_ms = obs_curr.timestamp_ms - obs_prev.timestamp_ms
            if time_delta_ms <= 0:
                continue

            dx_px = obs_curr.center_x - obs_prev.center_x
            dy_px = obs_curr.center_y - obs_prev.center_y
            distance_px = (dx_px * dx_px + dy_px * dy_px) ** 0.5
            distance_cm = distance_px / self.pixels_per_cm

            total_distance_cm += distance_cm
            total_time_ms += time_delta_ms

        if total_time_ms <= 0:
            return None

        # Convert from cm/ms to cm/sec
        return total_distance_cm / (total_time_ms / 1000.0)

    def _cleanupOldTrajectories(self) -> None:
        current_time_ms = int(time.time() * 1000)

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

        # Keep a reasonable number of trajectories for speed estimation
        max_trajectories = 50
        if len(self.active_trajectories) > max_trajectories:
            # Sort by most recent observation and keep the newest ones
            self.active_trajectories.sort(
                key=lambda t: max(obs.timestamp_ms for obs in t.observations),
                reverse=True,
            )
            self.active_trajectories = self.active_trajectories[:max_trajectories]
