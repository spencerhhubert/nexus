import time
import uuid
from typing import Dict, Any, TypedDict, Optional
from robot.global_config import GlobalConfig
from robot.ai.brickognize_types import BrickognizeClassificationResult


class Observation(TypedDict):
    observation_id: Optional[str]
    trajectory_id: Optional[str]
    timestamp_ms: int
    center_x: float
    center_y: float
    bbox_width: float
    bbox_height: float
    full_image_path: str
    masked_image_path: str
    classification_file_path: str
    classification_result: BrickognizeClassificationResult


def createObservation(
    global_config: GlobalConfig,
    trajectory_id: Optional[str],
    center_x: float,
    center_y: float,
    bbox_width: float,
    bbox_height: float,
    full_image_path: str,
    masked_image_path: str,
    classification_result: BrickognizeClassificationResult,
) -> Observation:
    observation_id = str(uuid.uuid4())
    timestamp_ms = int(time.time() * 1000)

    return Observation(
        observation_id=observation_id,
        trajectory_id=trajectory_id,
        timestamp_ms=timestamp_ms,
        center_x=center_x,
        center_y=center_y,
        bbox_width=bbox_width,
        bbox_height=bbox_height,
        full_image_path=full_image_path,
        masked_image_path=masked_image_path,
        classification_file_path="",
        classification_result=classification_result,
    )
