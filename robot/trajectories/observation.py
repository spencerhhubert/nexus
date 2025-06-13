import time
import uuid
import numpy as np
from typing import TypedDict, Optional
from robot.sorting.sorter import ClassificationResult


class ObservationJSON(TypedDict):
    observation_id: str
    trajectory_id: Optional[str]
    timestamp_ms: int
    center_x_percent: float
    center_y_percent: float
    bbox_width_percent: float
    bbox_height_percent: float
    center_x_px: int
    center_y_px: int
    bbox_width_px: int
    bbox_height_px: int
    full_image_path: Optional[str]
    masked_image_path: Optional[str]
    classification_file_path: Optional[str]
    classification_result: dict


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
        classification_result: ClassificationResult,
    ):
        self.observation_id = str(uuid.uuid4())
        self.trajectory_id = trajectory_id
        self.timestamp_ms = int(time.time() * 1000)
        self.center_x_percent = center_x
        self.center_y_percent = center_y
        self.bbox_width_percent = bbox_width
        self.bbox_height_percent = bbox_height

        frame_height, frame_width = full_frame.shape[:2]
        self.center_x_px = int(center_x * frame_width)
        self.center_y_px = int(center_y * frame_height)
        self.bbox_width_px = int(bbox_width * frame_width)
        self.bbox_height_px = int(bbox_height * frame_height)

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
            center_x_percent=self.center_x_percent,
            center_y_percent=self.center_y_percent,
            bbox_width_percent=self.bbox_width_percent,
            bbox_height_percent=self.bbox_height_percent,
            center_x_px=self.center_x_px,
            center_y_px=self.center_y_px,
            bbox_width_px=self.bbox_width_px,
            bbox_height_px=self.bbox_height_px,
            full_image_path=self.full_image_path,
            masked_image_path=self.masked_image_path,
            classification_file_path=self.classification_file_path,
            classification_result=self.classification_result.toJSON(),
        )
