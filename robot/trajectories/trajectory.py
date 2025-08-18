import time
import uuid
from typing import List, Optional, Dict, Any, TypedDict
from enum import Enum
from robot.global_config import GlobalConfig
from robot.trajectories.observation import Observation
from robot.util.bricklink import splitBricklinkId
from robot.bin_state_tracker import BinCoordinates


class TrajectoryLifecycleStage(Enum):
    ENTERED_CAMERA_VIEW = "entered_camera_view"
    CENTERED_UNDER_CAMERA = "centered_under_camera"
    OFF_CAMERA = "off_camera"
    IN_TRANSIT = "in_transit"
    DOORS_OPENED = "doors_opened"
    PROBABLY_IN_BIN = "probably_in_bin"
    EXPIRED = "expired"


class TrajectoryJSON(TypedDict):
    trajectory_id: str
    created_at: int
    updated_at: int
    observation_ids: List[str]
    consensus_classification: Optional[str]
    lifecycle_stage: str
    target_bin: Optional[Dict[str, Any]]


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
        self.lifecycle_stage: TrajectoryLifecycleStage = (
            TrajectoryLifecycleStage.ENTERED_CAMERA_VIEW
        )
        self.target_bin: Optional[BinCoordinates] = None
        self.sending_to_bin_start_time_ms: Optional[int] = None

        current_time_ms = int(time.time() * 1000)
        self.created_at = current_time_ms
        self.updated_at = current_time_ms

    def addObservation(self, observation: Observation) -> None:
        observation.trajectory_id = self.trajectory_id
        self.observations.append(observation)
        self.updated_at = int(time.time() * 1000)

    def setLifecycleStage(self, new_stage: TrajectoryLifecycleStage) -> None:
        self.lifecycle_stage = new_stage
        self.updated_at = int(time.time() * 1000)

    def getLatestObservation(self) -> Optional[Observation]:
        return (
            max(self.observations, key=lambda obs: obs.captured_at_ms)
            if self.observations
            else None
        )

    def getConsensusClassification(self) -> Optional[str]:
        if not self.observations:
            return None

        classification_counts: Dict[str, int] = {}

        for observation in self.observations:
            result = observation.classification_result
            if result.tag == "piece_classification" and result.data.get("item_id"):
                item_id = result.data["item_id"]
                classification_counts[item_id] = (
                    classification_counts.get(item_id, 0) + 1
                )

        if not classification_counts:
            return None

        return max(classification_counts.keys(), key=lambda k: classification_counts[k])

    def setTargetBin(self, target_bin: BinCoordinates) -> None:
        self.target_bin = target_bin
        self.updated_at = int(time.time() * 1000)

    def setSendingToBinStartTime(self, timestamp_ms: int) -> None:
        self.sending_to_bin_start_time_ms = timestamp_ms
        self.updated_at = int(time.time() * 1000)

    def _calculateSpatialDistance(self, obs: Observation) -> float:
        if not self.observations:
            return 0.0

        closest_obs = min(
            self.observations,
            key=lambda existing_obs: abs(
                existing_obs.leading_edge_x_px - obs.leading_edge_x_px
            ),
        )

        dx_px = obs.leading_edge_x_px - closest_obs.leading_edge_x_px
        dy_px = obs.center_y_px - closest_obs.center_y_px
        return (dx_px * dx_px + dy_px * dy_px) ** 0.5

    def _calculateSizeRatio(self, obs: Observation) -> float:
        latest = self.getLatestObservation()
        if not latest:
            return 1.0

        obs_area = obs.bbox_width_px * obs.bbox_height_px
        latest_area = latest.bbox_width_px * latest.bbox_height_px

        if latest_area <= 0:
            return 1.0

        return obs_area / latest_area

    def _calculateClassificationConsistency(self, obs: Observation) -> float:
        trajectory_consensus = self.getConsensusClassification()

        result = obs.classification_result
        if result.tag != "piece_classification" or not result.data.get("item_id"):
            return 0.0

        item_id = result.data["item_id"]
        if not item_id or not trajectory_consensus:
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
        time_gap = obs.captured_at_ms - latest.captured_at_ms
        if time_gap > max_time_gap_ms:
            return 0.0

        # Check spatial distance
        spatial_score = self.getSpatialScore(obs, max_position_distance_px)
        if spatial_score == 0.0:
            print(
                f"ZERO SPATIAL SCORE: observation_id={obs.observation_id}, trajectory_id={self.trajectory_id}"
            )
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
        return TrajectoryJSON(
            trajectory_id=self.trajectory_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            observation_ids=[obs.observation_id for obs in self.observations],
            consensus_classification=self.getConsensusClassification(),
            lifecycle_stage=self.lifecycle_stage.value,
            target_bin=dict(self.target_bin) if self.target_bin else None,
        )


def createTrajectory(
    global_config: GlobalConfig, initial_observation: Observation
) -> Trajectory:
    trajectory_id = str(uuid.uuid4())
    initial_observation.trajectory_id = trajectory_id
    return Trajectory(global_config, trajectory_id, initial_observation)
