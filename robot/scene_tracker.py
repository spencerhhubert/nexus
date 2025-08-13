import threading
import time
from typing import List, Optional
from robot.global_config import GlobalConfig
from robot.irl.motors import Encoder
from robot.trajectories import (
    Trajectory,
    TrajectoryLifecycleStage,
    Observation,
    createTrajectory,
)


class SceneTracker:
    def __init__(self, global_config: GlobalConfig, encoder: Encoder):
        self.global_config = global_config
        self.encoder: Encoder = encoder
        self.active_trajectories: List[Trajectory] = []
        self.objects_in_frame: int = 0
        self.lock = threading.Lock()

        self.current_speed_cm_per_ms = 0.0
        self.last_speed_update_time = time.time()

        self.max_trajectory_age_ms = 30000
        self.min_trajectories_to_keep = 16
        self.max_trajectories = 50

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
        speed = self._getConveyorSpeed()

        if speed is None or speed <= 0:
            self.global_config["logger"].info(
                f"Cannot calculate travel time: distance={distance_cm:.1f}cm, speed={speed} cm/ms"
            )
            return None

        travel_time_ms = distance_cm / speed
        self.global_config["logger"].info(
            f"Travel time calculation: distance={distance_cm:.1f}cm, speed={speed:.6f}cm/ms, time={travel_time_ms:.1f}ms"
        )
        return travel_time_ms

    def predictTimeAtPosition(
        self, trajectory: Trajectory, target_position_percent: float
    ) -> Optional[int]:
        if len(trajectory.observations) < 2:
            return None

        # Check if any observation is already at or past target position
        for obs in trajectory.observations:
            if obs.leading_edge_x_percent <= target_position_percent:
                return obs.captured_at_ms

        # Find the two observations that bracket the target position
        for i in range(len(trajectory.observations) - 1):
            obs1 = trajectory.observations[i]
            obs2 = trajectory.observations[i + 1]

            if (
                obs1.leading_edge_x_percent > target_position_percent
                and obs2.leading_edge_x_percent <= target_position_percent
            ):
                # Interpolate between these two observations
                x_range = obs1.leading_edge_x_percent - obs2.leading_edge_x_percent
                if x_range <= 0:
                    continue

                x_progress = (
                    obs1.leading_edge_x_percent - target_position_percent
                ) / x_range
                time_range = obs2.captured_at_ms - obs1.captured_at_ms
                predicted_time = obs1.captured_at_ms + int(x_progress * time_range)
                return predicted_time

        # If we haven't found it in observations, extrapolate from the last two
        if len(trajectory.observations) >= 2:
            obs1 = trajectory.observations[-2]
            obs2 = trajectory.observations[-1]

            time_delta = obs2.captured_at_ms - obs1.captured_at_ms
            x_delta = obs2.leading_edge_x_percent - obs1.leading_edge_x_percent

            if time_delta > 0 and x_delta != 0:
                x_remaining = obs2.leading_edge_x_percent - target_position_percent
                time_to_position = int(x_remaining * time_delta / x_delta)
                return obs2.captured_at_ms + time_to_position

        return None

    def predictTimeAtCameraCenter(self, trajectory: Trajectory) -> Optional[int]:
        camera_center_reference_position = self.global_config[
            "camera_center_reference_position"
        ]
        return self.predictTimeAtPosition(trajectory, camera_center_reference_position)

    def getTrajectoriesToTrigger(self) -> List[Trajectory]:
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

    def stepScene(self) -> None:
        with self.lock:
            self._updateConveyorSpeed()
            self._checkForTrajectoriesLeavingCamera()
            self._cleanupOldTrajectories()
            self._updateObjectCount()

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
        current_time = time.time()
        time_interval_s = current_time - self.last_speed_update_time

        if time_interval_s >= 0.25:  # Update speed every 250ms minimum
            pulse_count = self.encoder.getPulseCount()

            if pulse_count > 0:
                revolutions = pulse_count / self.encoder.getPulsesPerRevolution()
                distance_cm = revolutions * self.encoder.getWheelCircumferenceCm()

                speed_cm_per_s = distance_cm / time_interval_s
                self.current_speed_cm_per_ms = speed_cm_per_s / 1000

                self.global_config["logger"].info(
                    f"Conveyor speed update: {pulse_count} pulses, {distance_cm:.2f}cm, {self.current_speed_cm_per_ms:.6f}cm/ms"
                )

                self.encoder.resetPulseCount()

            self.last_speed_update_time = current_time

    def _getConveyorSpeed(self) -> float:
        return self.current_speed_cm_per_ms

    def _checkForTrajectoriesLeavingCamera(self) -> None:
        TIME_SINCE_UNDER_CAMERA_THRESHOLD_MS = 2000
        current_time_ms = int(time.time() * 1000)

        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                continue

            latest_observation = trajectory.getLatestObservation()
            if not latest_observation:
                continue

            LEADING_EDGE_X_PERCENT_CONSIDERED_OFF_CAMERA = 0.15
            if (
                latest_observation.leading_edge_x_percent
                <= LEADING_EDGE_X_PERCENT_CONSIDERED_OFF_CAMERA
            ):
                time_since_last_observation = (
                    current_time_ms - latest_observation.captured_at_ms
                )
                if time_since_last_observation >= TIME_SINCE_UNDER_CAMERA_THRESHOLD_MS:
                    trajectory.setLifecycleStage(TrajectoryLifecycleStage.IN_TRANSIT)
                    self.global_config["logger"].info(
                        f"Trajectory {trajectory.trajectory_id} left camera view, marking as in transit"
                    )

    def _cleanupOldTrajectories(self) -> None:
        current_time_ms = int(time.time() * 1000)

        if len(self.active_trajectories) <= self.min_trajectories_to_keep:
            return

        self.active_trajectories = [
            t
            for t in self.active_trajectories
            if (
                current_time_ms - t.observations[0].captured_at_ms
                < self.max_trajectory_age_ms
                and t.lifecycle_stage != TrajectoryLifecycleStage.DOORS_CLOSED
            )
        ]

        if len(self.active_trajectories) < self.min_trajectories_to_keep:
            return

        if len(self.active_trajectories) > self.max_trajectories:
            self.active_trajectories.sort(
                key=lambda t: max(obs.captured_at_ms for obs in t.observations),
                reverse=True,
            )
            self.active_trajectories = self.active_trajectories[: self.max_trajectories]

    def _updateObjectCount(self) -> None:
        self.objects_in_frame = self._countObjectsInFrame()

    def _countObjectsInFrame(self) -> int:
        current_time_ms = int(time.time() * 1000)
        recent_observation_threshold_ms = 2000

        count = 0
        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage == TrajectoryLifecycleStage.UNDER_CAMERA:
                latest_obs = trajectory.getLatestObservation()
                if (
                    latest_obs
                    and (current_time_ms - latest_obs.captured_at_ms)
                    <= recent_observation_threshold_ms
                ):
                    count += 1

        return count

    def isObjectCentered(self) -> bool:
        if not self.active_trajectories:
            return False

        center_threshold = self.global_config["object_center_threshold_percent"]
        frame_center = 0.5

        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage == TrajectoryLifecycleStage.UNDER_CAMERA:
                latest_obs = trajectory.getLatestObservation()
                if latest_obs:
                    object_center_x = latest_obs.center_x_percent
                    distance_from_center = abs(object_center_x - frame_center)
                    if distance_from_center <= center_threshold:
                        return True

        return False
