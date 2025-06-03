import time
import uuid
from typing import List, Optional, Dict, Any
from enum import Enum
from robot.global_config import GlobalConfig
from robot.trajectories.observation import Observation


class TrajectoryLifecycleStage(Enum):
    UNDER_CAMERA = "under_camera"
    IN_TRANSIT = "in_transit"
    DOORS_OPEN = "doors_open"
    DOORS_CLOSED = "doors_closed"


class ObjectTrajectory:
    def __init__(
        self,
        global_config: GlobalConfig,
        trajectory_id: str,
        initial_observation: Observation,
    ):
        self.global_config = global_config
        self.trajectory_id = trajectory_id
        self.observations: List[Observation] = [initial_observation]
        self.lifecycle_stage = TrajectoryLifecycleStage.UNDER_CAMERA

    def addObservation(self, observation: Observation) -> None:
        observation["trajectory_id"] = self.trajectory_id
        self.observations.append(observation)

    def getLatestObservation(self) -> Optional[Observation]:
        return self.observations[-1] if self.observations else None

    def getConsensusClassification(self) -> str:
        if not self.observations:
            return "unknown"

        classification_counts: Dict[str, int] = {}

        for observation in self.observations:
            result = observation["classification_result"]
            if "items" in result and result["items"]:
                item_id = result["items"][0].get("id", "unknown")
                classification_counts[item_id] = (
                    classification_counts.get(item_id, 0) + 1
                )

        if not classification_counts:
            return "unknown"

        return max(classification_counts.keys(), key=lambda k: classification_counts[k])

    def shouldTriggerAction(self, global_config: GlobalConfig) -> bool:
        camera_trigger_position = global_config["camera_trigger_position"]

        latest_observation = self.getLatestObservation()
        if not latest_observation:
            return False

        return latest_observation["center_x"] >= camera_trigger_position

    def getPredictedPosition(self, timestamp_ms: int) -> tuple[float, float]:
        if len(self.observations) < 2:
            latest = self.getLatestObservation()
            return (latest["center_x"], latest["center_y"]) if latest else (0.0, 0.0)

        # Use all observations to calculate average velocity
        total_velocity_x = 0.0
        total_velocity_y = 0.0
        velocity_samples = 0

        for i in range(1, len(self.observations)):
            obs_prev = self.observations[i - 1]
            obs_curr = self.observations[i]

            time_delta = obs_curr["timestamp_ms"] - obs_prev["timestamp_ms"]
            if time_delta > 0:
                velocity_x = (obs_curr["center_x"] - obs_prev["center_x"]) / time_delta
                velocity_y = (obs_curr["center_y"] - obs_prev["center_y"]) / time_delta
                total_velocity_x += velocity_x
                total_velocity_y += velocity_y
                velocity_samples += 1

        if velocity_samples == 0:
            latest = self.getLatestObservation()
            return (latest["center_x"], latest["center_y"]) if latest else (0.0, 0.0)

        avg_velocity_x = total_velocity_x / velocity_samples
        avg_velocity_y = total_velocity_y / velocity_samples

        latest = self.getLatestObservation()
        if not latest:
            return (0.0, 0.0)

        prediction_time_delta = timestamp_ms - latest["timestamp_ms"]

        predicted_x = latest["center_x"] + avg_velocity_x * prediction_time_delta
        predicted_y = latest["center_y"] + avg_velocity_y * prediction_time_delta

        return (predicted_x, predicted_y)


def createTrajectory(
    global_config: GlobalConfig, initial_observation: Observation
) -> ObjectTrajectory:
    trajectory_id = str(uuid.uuid4())
    initial_observation["trajectory_id"] = trajectory_id
    return ObjectTrajectory(global_config, trajectory_id, initial_observation)


def calculateSpatialDistance(
    obs: Observation, predicted_x: float, predicted_y: float
) -> float:
    dx = obs["center_x"] - predicted_x
    dy = obs["center_y"] - predicted_y
    return (dx * dx + dy * dy) ** 0.5


def calculateSizeRatio(obs: Observation, trajectory: ObjectTrajectory) -> float:
    latest = trajectory.getLatestObservation()
    if not latest:
        return 1.0

    obs_area = obs["bbox_width"] * obs["bbox_height"]
    latest_area = latest["bbox_width"] * latest["bbox_height"]

    if latest_area <= 0:
        return 1.0

    return obs_area / latest_area


def calculateClassificationConsistency(
    obs: Observation, trajectory: ObjectTrajectory
) -> float:
    trajectory_consensus = trajectory.getConsensusClassification()

    result = obs["classification_result"]
    if "items" not in result or not result["items"]:
        return 0.0

    obs_item_id = result["items"][0].get("id", "unknown")

    return 1.0 if obs_item_id == trajectory_consensus else 0.0


def findMatchingTrajectory(
    global_config: GlobalConfig,
    new_observation: Observation,
    active_trajectories: List[ObjectTrajectory],
) -> Optional[ObjectTrajectory]:
    max_time_gap_ms = global_config["trajectory_matching_max_time_gap_ms"]
    max_position_distance_px = global_config[
        "trajectory_matching_max_position_distance_px"
    ]
    min_bbox_size_ratio = global_config["trajectory_matching_min_bbox_size_ratio"]
    max_bbox_size_ratio = global_config["trajectory_matching_max_bbox_size_ratio"]
    classification_weight = global_config[
        "trajectory_matching_classification_consistency_weight"
    ]
    spatial_weight = global_config["trajectory_matching_spatial_weight"]

    best_trajectory = None
    best_score = 0.0

    for trajectory in active_trajectories:
        if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
            continue

        latest = trajectory.getLatestObservation()
        if not latest:
            continue

        time_gap = new_observation["timestamp_ms"] - latest["timestamp_ms"]
        if time_gap > max_time_gap_ms:
            continue

        predicted_x, predicted_y = trajectory.getPredictedPosition(
            new_observation["timestamp_ms"]
        )
        spatial_distance = calculateSpatialDistance(
            new_observation, predicted_x, predicted_y
        )

        if spatial_distance > max_position_distance_px:
            continue

        size_ratio = calculateSizeRatio(new_observation, trajectory)
        if size_ratio < min_bbox_size_ratio or size_ratio > max_bbox_size_ratio:
            continue

        spatial_score = max(0.0, 1.0 - spatial_distance / max_position_distance_px)
        classification_score = calculateClassificationConsistency(
            new_observation, trajectory
        )

        combined_score = (
            spatial_weight * spatial_score
            + classification_weight * classification_score
        )

        if combined_score > best_score:
            best_score = combined_score
            best_trajectory = trajectory

    return best_trajectory
