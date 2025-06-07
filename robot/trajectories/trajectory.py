import time
import uuid
from typing import List, Optional, Dict, Any, TypedDict
from enum import Enum
from robot.global_config import GlobalConfig
from robot.trajectories.observation import Observation
from robot.util.bricklink import splitBricklinkId


class TrajectoryLifecycleStage(Enum):
    UNDER_CAMERA = "under_camera"
    IN_TRANSIT = "in_transit"
    DOORS_OPEN = "doors_open"
    DOORS_CLOSED = "doors_closed"


class TrajectoryJSON(TypedDict):
    trajectory_id: str
    created_at: int
    updated_at: int
    observation_ids: List[str]
    estimated_velocity_x: float
    estimated_velocity_y: float
    consensus_classification: str
    lifecycle_stage: str


class Trajectory:
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
        observation.trajectory_id = self.trajectory_id
        self.observations.append(observation)

    def getLatestObservation(self) -> Optional[Observation]:
        return (
            max(self.observations, key=lambda obs: obs.timestamp_ms)
            if self.observations
            else None
        )

    def getConsensusClassification(self) -> str:
        if not self.observations:
            return "unknown"

        classification_counts: Dict[str, int] = {}

        for observation in self.observations:
            result = observation.classification_result
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

        should_trigger = latest_observation.center_x <= camera_trigger_position
        global_config["logger"].info(
            f"should_trigger: {should_trigger}, latest_observation.center_x: {latest_observation.center_x}"
        )
        return should_trigger

    def getPredictedPosition(self, timestamp_ms: int) -> tuple[float, float]:
        if len(self.observations) < 2:
            latest = self.getLatestObservation()
            return (latest.center_x, latest.center_y) if latest else (0.0, 0.0)

        # Use all observations to calculate average velocity
        total_velocity_x_px_per_ms = 0.0
        total_velocity_y_px_per_ms = 0.0
        velocity_samples = 0

        for i in range(1, len(self.observations)):
            obs_prev = self.observations[i - 1]
            obs_curr = self.observations[i]

            time_delta_ms = obs_curr.timestamp_ms - obs_prev.timestamp_ms
            if time_delta_ms > 0:
                dx_px = obs_curr.center_x - obs_prev.center_x
                dy_px = obs_curr.center_y - obs_prev.center_y
                velocity_x_px_per_ms = dx_px / time_delta_ms
                velocity_y_px_per_ms = dy_px / time_delta_ms
                total_velocity_x_px_per_ms += velocity_x_px_per_ms
                total_velocity_y_px_per_ms += velocity_y_px_per_ms
                velocity_samples += 1

        if velocity_samples == 0:
            latest = self.getLatestObservation()
            return (latest.center_x, latest.center_y) if latest else (0.0, 0.0)

        avg_velocity_x_px_per_ms = total_velocity_x_px_per_ms / velocity_samples
        avg_velocity_y_px_per_ms = total_velocity_y_px_per_ms / velocity_samples

        latest = self.getLatestObservation()
        if not latest:
            return (0.0, 0.0)

        prediction_time_delta_ms = timestamp_ms - latest.timestamp_ms

        predicted_x_px = (
            latest.center_x + avg_velocity_x_px_per_ms * prediction_time_delta_ms
        )
        predicted_y_px = (
            latest.center_y + avg_velocity_y_px_per_ms * prediction_time_delta_ms
        )

        return (predicted_x_px, predicted_y_px)

    def getEstimatedVelocity(self) -> tuple[float, float]:
        if len(self.observations) < 2:
            return (0.0, 0.0)

        total_velocity_x_px_per_ms = 0.0
        total_velocity_y_px_per_ms = 0.0
        velocity_samples = 0

        for i in range(1, len(self.observations)):
            obs_prev = self.observations[i - 1]
            obs_curr = self.observations[i]

            time_delta_ms = obs_curr.timestamp_ms - obs_prev.timestamp_ms
            if time_delta_ms > 0:
                dx_px = obs_curr.center_x - obs_prev.center_x
                dy_px = obs_curr.center_y - obs_prev.center_y
                velocity_x_px_per_ms = dx_px / time_delta_ms
                velocity_y_px_per_ms = dy_px / time_delta_ms
                total_velocity_x_px_per_ms += velocity_x_px_per_ms
                total_velocity_y_px_per_ms += velocity_y_px_per_ms
                velocity_samples += 1

        if velocity_samples == 0:
            return (0.0, 0.0)

        return (
            total_velocity_x_px_per_ms / velocity_samples,
            total_velocity_y_px_per_ms / velocity_samples,
        )

    def _calculateSpatialDistance(self, obs: Observation) -> float:
        predicted_x_px, predicted_y_px = self.getPredictedPosition(obs.timestamp_ms)
        dx_px = obs.center_x - predicted_x_px
        dy_px = obs.center_y - predicted_y_px
        return (dx_px * dx_px + dy_px * dy_px) ** 0.5

    def _calculateSizeRatio(self, obs: Observation) -> float:
        latest = self.getLatestObservation()
        if not latest:
            return 1.0

        obs_area = obs.bbox_width * obs.bbox_height
        latest_area = latest.bbox_width * latest.bbox_height

        if latest_area <= 0:
            return 1.0

        return obs_area / latest_area

    def _calculateClassificationConsistency(self, obs: Observation) -> float:
        trajectory_consensus = self.getConsensusClassification()

        result = obs.classification_result
        if "items" not in result or not result["items"]:
            return 0.0

        item_id = result["items"][0].get("id", "unknown")
        if item_id == "unknown":
            return 0.0

        obs_item_id = splitBricklinkId(item_id)[0]
        return 1.0 if obs_item_id == trajectory_consensus else 0.0

    def getSpatialScore(self, obs: Observation, max_distance_px: float) -> float:
        distance_px = self._calculateSpatialDistance(obs)
        return max(0.0, 1.0 - distance_px / max_distance_px)

    def getSizeScore(
        self, obs: Observation, min_ratio: float, max_ratio: float
    ) -> float:
        size_ratio = self._calculateSizeRatio(obs)
        return 1.0 if min_ratio <= size_ratio <= max_ratio else 0.0

    def getClassificationScore(self, obs: Observation) -> float:
        return self._calculateClassificationConsistency(obs)

    def getCompatibilityScore(
        self, obs: Observation, global_config: GlobalConfig
    ) -> float:
        max_position_distance_px = global_config[
            "trajectory_matching_max_position_distance_px"
        ]
        min_bbox_size_ratio = global_config["trajectory_matching_min_bbox_size_ratio"]
        max_bbox_size_ratio = global_config["trajectory_matching_max_bbox_size_ratio"]
        classification_weight = global_config[
            "trajectory_matching_classification_consistency_weight"
        ]
        spatial_weight = global_config["trajectory_matching_spatial_weight"]

        # Check time gap
        latest = self.getLatestObservation()
        if not latest:
            return 0.0

        max_time_gap_ms = global_config["trajectory_matching_max_time_gap_ms"]
        time_gap = obs.timestamp_ms - latest.timestamp_ms
        if time_gap > max_time_gap_ms:
            return 0.0

        # Check spatial distance
        spatial_score = self.getSpatialScore(obs, max_position_distance_px)
        if spatial_score == 0.0:
            return 0.0

        # Check size ratio
        size_score = self.getSizeScore(obs, min_bbox_size_ratio, max_bbox_size_ratio)
        if size_score == 0.0:
            return 0.0

        # Calculate weighted score
        classification_score = self.getClassificationScore(obs)
        combined_score = (
            spatial_weight * spatial_score
            + classification_weight * classification_score
        )

        return combined_score

    def toJSON(self) -> TrajectoryJSON:
        est_vel_x_px_per_ms, est_vel_y_px_per_ms = self.getEstimatedVelocity()

        return TrajectoryJSON(
            trajectory_id=self.trajectory_id,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000),
            observation_ids=[obs.observation_id for obs in self.observations],
            estimated_velocity_x=est_vel_x_px_per_ms,
            estimated_velocity_y=est_vel_y_px_per_ms,
            consensus_classification=self.getConsensusClassification(),
            lifecycle_stage=self.lifecycle_stage.value,
        )


def createTrajectory(
    global_config: GlobalConfig, initial_observation: Observation
) -> Trajectory:
    trajectory_id = str(uuid.uuid4())
    initial_observation.trajectory_id = trajectory_id
    return Trajectory(global_config, trajectory_id, initial_observation)
