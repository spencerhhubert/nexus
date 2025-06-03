import time
import uuid
import numpy as np
from typing import TypedDict, Optional
from robot.ai.brickognize_types import BrickognizeClassificationResult


class ObservationJSON(TypedDict):
    observation_id: str
    trajectory_id: Optional[str]
    timestamp_ms: int
    center_x: float
    center_y: float
    bbox_width: float
    bbox_height: float
    full_image_path: Optional[str]
    masked_image_path: Optional[str]
    classification_file_path: Optional[str]
    classification_result: BrickognizeClassificationResult


class Observation:
    def __init__(
        self,
        trajectory_id: Optional[str],
        center_x: float,
        center_y: float,
        bbox_width: float,
        bbox_height: float,
        full_frame: np.ndarray,
        masked_image: np.ndarray,
        classification_result: BrickognizeClassificationResult,
    ):
        self.observation_id = str(uuid.uuid4())
        self.trajectory_id = trajectory_id
        self.timestamp_ms = int(time.time() * 1000)
        self.center_x = center_x
        self.center_y = center_y
        self.bbox_width = bbox_width
        self.bbox_height = bbox_height
        self.full_frame = full_frame
        self.masked_image = masked_image
        self.classification_result = classification_result
        self.full_image_path: Optional[str] = None
        self.masked_image_path: Optional[str] = None
        self.classification_file_path: Optional[str] = None

    def toJSON(self) -> ObservationJSON:
        return ObservationJSON(
            observation_id=self.observation_id,
            trajectory_id=self.trajectory_id,
            timestamp_ms=self.timestamp_ms,
            center_x=self.center_x,
            center_y=self.center_y,
            bbox_width=self.bbox_width,
            bbox_height=self.bbox_height,
            full_image_path=self.full_image_path,
            masked_image_path=self.masked_image_path,
            classification_file_path=self.classification_file_path,
            classification_result=self.classification_result,
        )
