import threading
import time
from typing import List, Optional, NamedTuple
from robot.global_config import GlobalConfig
from robot.irl.motors import Encoder
from robot.trajectories import (
    Trajectory,
    TrajectoryLifecycleStage,
    Observation,
    createTrajectory,
)


class DistanceReading(NamedTuple):
    timestamp_ms: int
    distance_traveled_cm: float


class SceneTracker:
    def __init__(self, global_config: GlobalConfig, encoder: Encoder):
        self.global_config = global_config
        self.encoder: Encoder = encoder
        self.trajectories: List[Trajectory] = []
        self.observations: List[Observation] = []
        self.objects_in_frame: int = 0
        self.lock = threading.Lock()

        self.distance_readings: List[DistanceReading] = []
        self.last_distance_update_time = time.time()
        self.max_distance_readings = global_config.get("max_distance_readings", 1000)

        self.max_trajectory_age_ms = 30000
        self.min_trajectories_to_keep = 16
        self.max_trajectories = 50

    def addObservation(self, observation: Observation) -> None:
        with self.lock:
            self.observations.append(observation)
            self.collapseObservationsIntoTrajectories()
            self.global_config["logger"].info(
                f"Added observation {observation.observation_id}, now have {len(self.trajectories)} trajectories"
            )

    def stepScene(self) -> None:
        with self.lock:
            self._updateDistanceReadings()
            self.updateTrajectoryLifecycleStages()
            self._cleanupOldTrajectories()
            self._cleanupProbablyInBinTrajectories()
            self._updateObjectCount()

    def getTrajectories(self) -> List[Trajectory]:
        with self.lock:
            return self.trajectories.copy()

    def _findMatchingTrajectory(
        self, new_observation: Observation
    ) -> Optional[Trajectory]:
        best_trajectory = None
        best_score = 0.0

        for trajectory in self.trajectories:
            if trajectory.lifecycle_stage not in [
                TrajectoryLifecycleStage.ENTERED_CAMERA_VIEW,
                TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA,
            ]:
                continue

            score = trajectory.getCompatibilityScore(
                new_observation, self.global_config
            )

            if score > best_score:
                best_score = score
                best_trajectory = trajectory

        return best_trajectory

    def _updateDistanceReadings(self) -> None:
        current_time = time.time()
        time_interval_s = current_time - self.last_distance_update_time

        if time_interval_s >= self.global_config["encoder_polling_delay_ms"] / 1000.0:
            pulse_count = self.encoder.getPulseCount()

            if pulse_count > 0:
                revolutions = pulse_count / self.encoder.getPulsesPerRevolution()
                distance_cm = revolutions * self.encoder.getWheelCircumferenceCm()

                timestamp_ms = int(current_time * 1000)
                self.distance_readings.append(
                    DistanceReading(timestamp_ms, distance_cm)
                )

                if len(self.distance_readings) > self.max_distance_readings:
                    self.distance_readings = self.distance_readings[
                        -self.max_distance_readings :
                    ]

                self.global_config["logger"].info(
                    f"Distance reading: {pulse_count} pulses, {distance_cm:.2f}cm at {timestamp_ms}ms"
                )

                self.encoder.resetPulseCount()

            self.last_distance_update_time = current_time

    def getDistanceTraveledSince(self, timestamp_ms: int) -> Optional[float]:
        if not self.distance_readings:
            return None

        total_distance = 0.0
        for reading in self.distance_readings:
            if reading.timestamp_ms >= timestamp_ms:
                total_distance += reading.distance_traveled_cm

        return total_distance

    def getAverageSpeed(self, duration_ms: int) -> Optional[float]:
        if not self.distance_readings:
            return None

        current_time_ms = int(time.time() * 1000)
        cutoff_time_ms = current_time_ms - duration_ms

        total_distance = 0.0
        actual_duration_ms = 0
        earliest_timestamp = current_time_ms

        for reading in self.distance_readings:
            if reading.timestamp_ms >= cutoff_time_ms:
                total_distance += reading.distance_traveled_cm
                earliest_timestamp = min(earliest_timestamp, reading.timestamp_ms)

        actual_duration_ms = current_time_ms - earliest_timestamp

        if actual_duration_ms <= 0:
            return None

        return total_distance / actual_duration_ms  # cm/ms

    def collapseObservationsIntoTrajectories(self) -> None:
        if not self.observations:
            return

        # Step 1: Build new trajectories from observations (like before)
        temp_new_trajectories = self._buildTrajectoriesFromObservations()

        # Step 2: Reconcile with existing trajectories
        final_trajectories = self._reconcileTrajectories(temp_new_trajectories)

        # Step 3: Only now update the real list
        self.trajectories = final_trajectories

    def _buildTrajectoriesFromObservations(self) -> List[Trajectory]:
        temp_trajectories: List[Trajectory] = []
        sorted_observations = sorted(
            self.observations, key=lambda obs: obs.captured_at_ms
        )

        for observation in sorted_observations:
            best_trajectory = None
            best_score = 0.0

            for trajectory in temp_trajectories:
                score = trajectory.getCompatibilityScore(
                    observation, self.global_config
                )
                if score > best_score:
                    best_score = score
                    best_trajectory = trajectory

            print("observation id", observation.observation_id, "score", best_score)
            if best_trajectory and best_score >= 0.1:
                observation.trajectory_id = best_trajectory.trajectory_id
                best_trajectory.addObservation(observation)
            else:
                new_trajectory = createTrajectory(self.global_config, observation)
                temp_trajectories.append(new_trajectory)

        return temp_trajectories

    def _reconcileTrajectories(
        self, new_trajectories: List[Trajectory]
    ) -> List[Trajectory]:
        if not self.trajectories:
            # No existing trajectories, just use the new ones
            for trajectory in new_trajectories:
                self.global_config["logger"].info(
                    f"Created new trajectory {trajectory.trajectory_id} during collapse"
                )
            return new_trajectories

        final_trajectories = []
        used_existing_trajectories = set()

        for new_traj in new_trajectories:
            new_obs_ids = set(obs.observation_id for obs in new_traj.observations)
            best_existing_match = None
            best_overlap_ratio = 0.0

            # Find the existing trajectory with the highest observation overlap
            for existing_traj in self.trajectories:
                if existing_traj.trajectory_id in used_existing_trajectories:
                    continue

                existing_obs_ids = set(
                    obs.observation_id for obs in existing_traj.observations
                )
                overlap = len(new_obs_ids & existing_obs_ids)
                union_size = len(new_obs_ids | existing_obs_ids)

                if union_size > 0:
                    overlap_ratio = overlap / union_size
                    if overlap_ratio > best_overlap_ratio:
                        best_overlap_ratio = overlap_ratio
                        best_existing_match = existing_traj

            # Decide whether to reuse existing trajectory or create new one
            if (
                best_existing_match and best_overlap_ratio >= 0.3
            ):  # At least 50% overlap
                # Reuse existing trajectory but update its observations
                existing_obs_ids = set(
                    obs.observation_id for obs in best_existing_match.observations
                )
                new_obs_ids = set(obs.observation_id for obs in new_traj.observations)

                if new_obs_ids.issubset(existing_obs_ids):
                    # New trajectory is subset - keep existing trajectory unchanged
                    final_trajectories.append(best_existing_match)
                    self.global_config["logger"].info(
                        f"Keeping existing trajectory {best_existing_match.trajectory_id} (subset)"
                    )
                elif existing_obs_ids.issubset(new_obs_ids):
                    # New trajectory is superset - update existing trajectory with new observations
                    self._updateTrajectoryObservations(
                        best_existing_match, new_traj.observations
                    )
                    final_trajectories.append(best_existing_match)
                    self.global_config["logger"].info(
                        f"Updated existing trajectory {best_existing_match.trajectory_id} with new observations"
                    )
                else:
                    # Different observation sets - update existing trajectory completely
                    self._updateTrajectoryObservations(
                        best_existing_match, new_traj.observations
                    )
                    final_trajectories.append(best_existing_match)
                    self.global_config["logger"].info(
                        f"Updated existing trajectory {best_existing_match.trajectory_id} with different observations"
                    )

                used_existing_trajectories.add(best_existing_match.trajectory_id)
            else:
                # No good match found - keep as new trajectory
                final_trajectories.append(new_traj)
                self.global_config["logger"].info(
                    f"Created new trajectory {new_traj.trajectory_id} during reconciliation"
                )

        # Add any existing trajectories that weren't matched (lost their observations)
        for existing_traj in self.trajectories:
            if existing_traj.trajectory_id not in used_existing_trajectories:
                # This trajectory lost all its observations - keep it but log it
                final_trajectories.append(existing_traj)
                self.global_config["logger"].info(
                    f"Kept orphaned trajectory {existing_traj.trajectory_id} (no observations matched)"
                )

        return final_trajectories

    def _updateTrajectoryObservations(
        self, trajectory: Trajectory, new_observations: List[Observation]
    ) -> None:
        # Update all observation trajectory_ids to match
        for obs in new_observations:
            obs.trajectory_id = trajectory.trajectory_id

        # Replace observations
        trajectory.observations = new_observations
        trajectory.updated_at = int(time.time() * 1000)

    def updateTrajectoryLifecycleStages(self) -> None:
        current_time_ms = int(time.time() * 1000)

        for trajectory in self.trajectories:
            latest_obs = trajectory.getLatestObservation()
            if not latest_obs:
                continue

            # Check if trajectory should be marked as expired
            if trajectory.lifecycle_stage in [
                TrajectoryLifecycleStage.ENTERED_CAMERA_VIEW,
                TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA,
            ]:
                trajectory_age = current_time_ms - trajectory.created_at
                latest_observation_age = current_time_ms - latest_obs.captured_at_ms

                if (
                    trajectory_age > self.global_config["max_trajectory_age"]
                    and latest_observation_age
                    > self.global_config["max_trajectory_age"]
                ):
                    trajectory.setLifecycleStage(TrajectoryLifecycleStage.EXPIRED)
                    self.global_config["logger"].info(
                        f"Trajectory {trajectory.trajectory_id} expired after {trajectory_age}ms"
                    )
                    continue

            if (
                trajectory.lifecycle_stage
                == TrajectoryLifecycleStage.ENTERED_CAMERA_VIEW
            ):
                center_threshold = self.global_config["object_center_threshold_percent"]
                frame_center = 0.5
                object_center_x = latest_obs.center_x_percent
                distance_from_center = abs(object_center_x - frame_center)

                if distance_from_center <= center_threshold:
                    trajectory.setLifecycleStage(
                        TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA
                    )
                    self.global_config["logger"].info(
                        f"Trajectory {trajectory.trajectory_id} centered under camera"
                    )
            elif (
                trajectory.lifecycle_stage
                == TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA
            ):
                LEADING_EDGE_X_PERCENT_CONSIDERED_OFF_CAMERA = 0.15
                if (
                    latest_obs.leading_edge_x_percent
                    <= LEADING_EDGE_X_PERCENT_CONSIDERED_OFF_CAMERA
                ):
                    time_since_last_observation = (
                        current_time_ms - latest_obs.captured_at_ms
                    )
                    if time_since_last_observation >= 2000:
                        trajectory.setLifecycleStage(
                            TrajectoryLifecycleStage.OFF_CAMERA
                        )
                        self.global_config["logger"].info(
                            f"Trajectory {trajectory.trajectory_id} left camera view, marking as off camera"
                        )
            elif trajectory.lifecycle_stage == TrajectoryLifecycleStage.DOORS_OPENED:
                time_since_doors_opened = current_time_ms - trajectory.updated_at
                if time_since_doors_opened >= 5000:
                    trajectory.setLifecycleStage(
                        TrajectoryLifecycleStage.PROBABLY_IN_BIN
                    )
                    self.global_config["logger"].info(
                        f"Trajectory {trajectory.trajectory_id} probably in bin"
                    )

    def _cleanupOldTrajectories(self) -> None:
        current_time_ms = int(time.time() * 1000)

        if len(self.trajectories) <= self.min_trajectories_to_keep:
            return

        self.trajectories = [
            t
            for t in self.trajectories
            if (
                current_time_ms - t.observations[0].captured_at_ms
                < self.max_trajectory_age_ms
                and t.lifecycle_stage != TrajectoryLifecycleStage.PROBABLY_IN_BIN
            )
        ]

        if len(self.trajectories) < self.min_trajectories_to_keep:
            return

        if len(self.trajectories) > self.max_trajectories:
            self.trajectories.sort(
                key=lambda t: max(obs.captured_at_ms for obs in t.observations),
                reverse=True,
            )
            self.trajectories = self.trajectories[: self.max_trajectories]

    def _cleanupProbablyInBinTrajectories(self) -> None:
        current_time_ms = int(time.time() * 1000)
        cleanup_age_threshold_ms = 60 * 1000

        trajectories_to_remove = []
        observation_ids_to_remove = set()

        for trajectory in self.trajectories:
            if trajectory.lifecycle_stage == TrajectoryLifecycleStage.PROBABLY_IN_BIN:
                age_ms = current_time_ms - trajectory.created_at
                if age_ms > cleanup_age_threshold_ms:
                    trajectories_to_remove.append(trajectory)
                    for obs in trajectory.observations:
                        observation_ids_to_remove.add(obs.observation_id)

        for trajectory in trajectories_to_remove:
            self.trajectories.remove(trajectory)
            self.global_config["logger"].info(
                f"Cleaned up trajectory {trajectory.trajectory_id} that was probably in bin"
            )
        self.observations = [
            obs
            for obs in self.observations
            if obs.observation_id not in observation_ids_to_remove
        ]

        if observation_ids_to_remove:
            self.global_config["logger"].info(
                f"Cleaned up {len(observation_ids_to_remove)} observations from probably-in-bin trajectories"
            )

    def _updateObjectCount(self) -> None:
        self.objects_in_frame = self._countObjectsInFrame()

    def _countObjectsInFrame(self) -> int:
        count = 0
        for trajectory in self.trajectories:
            if trajectory.lifecycle_stage in [
                TrajectoryLifecycleStage.ENTERED_CAMERA_VIEW,
                TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA,
            ]:
                count += 1
        return count

    def getValidNewTrajectories(self) -> List[Trajectory]:
        valid_trajectories = []
        min_observations = self.global_config["min_number_observations_for_centering"]

        for trajectory in self.trajectories:
            # Skip expired trajectories
            if trajectory.lifecycle_stage == TrajectoryLifecycleStage.EXPIRED:
                continue

            # Only include trajectories in centered or off camera stages
            if trajectory.lifecycle_stage not in [
                TrajectoryLifecycleStage.CENTERED_UNDER_CAMERA,
                TrajectoryLifecycleStage.OFF_CAMERA,
            ]:
                continue

            # Only include trajectories with enough observations
            if len(trajectory.observations) < min_observations:
                continue

            valid_trajectories.append(trajectory)

        return valid_trajectories
