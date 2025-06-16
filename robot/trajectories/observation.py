import time
import uuid
import numpy as np
from typing import TypedDict, Optional
from robot.sorting.sorter import ClassificationResult


class ObservationJSON(TypedDict):
    observation_id: str
    trajectory_id: Optional[str]
    timestamp_ms: int
    captured_at_ms: int
    center_x_percent: float
    center_y_percent: float
    bbox_width_percent: float
    bbox_height_percent: float
    leading_edge_x_percent: float
    center_x_px: int
    center_y_px: int
    bbox_width_px: int
    bbox_height_px: int
    leading_edge_x_px: int
    full_image_path: Optional[str]
    masked_image_path: Optional[str]
    classification_file_path: Optional[str]
    classification_result: dict
    fully_visible_for_speed_estimation: bool


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
        border_threshold: float,
        captured_at_ms: int,
    ):
        self.observation_id = str(uuid.uuid4())
        self.trajectory_id = trajectory_id
        self.timestamp_ms = int(time.time() * 1000)
        self.captured_at_ms = captured_at_ms
        self.center_x_percent = center_x
        self.center_y_percent = center_y
        self.bbox_width_percent = bbox_width
        self.bbox_height_percent = bbox_height

        frame_height, frame_width = full_frame.shape[:2]
        self.center_x_px = int(center_x * frame_width)
        self.center_y_px = int(center_y * frame_height)
        self.bbox_width_px = int(bbox_width * frame_width)
        self.bbox_height_px = int(bbox_height * frame_height)

        # Calculate leading edge (leftmost point of bounding box)
        self.leading_edge_x_percent = center_x - bbox_width / 2
        self.leading_edge_x_px = int(self.leading_edge_x_percent * frame_width)

        self.full_frame = full_frame
        self.masked_image = masked_image
        self.classification_result = classification_result
        self.full_image_path: Optional[str] = None
        self.masked_image_path: Optional[str] = None
        self.classification_file_path: Optional[str] = None

        self.border_threshold = border_threshold

        # Calculate and store visibility for speed estimation
        left_edge = center_x - bbox_width / 2
        right_edge = center_x + bbox_width / 2
        top_edge = center_y - bbox_height / 2
        bottom_edge = center_y + bbox_height / 2

        self.fully_visible_for_speed_estimation = bool(
            left_edge >= border_threshold
            and right_edge <= (1.0 - border_threshold)
            and top_edge >= border_threshold
            and bottom_edge <= (1.0 - border_threshold)
        )

    def toJSON(self) -> ObservationJSON:
        return ObservationJSON(
            observation_id=self.observation_id,
            trajectory_id=self.trajectory_id,
            timestamp_ms=self.timestamp_ms,
            captured_at_ms=self.captured_at_ms,
            center_x_percent=self.center_x_percent,
            center_y_percent=self.center_y_percent,
            bbox_width_percent=self.bbox_width_percent,
            bbox_height_percent=self.bbox_height_percent,
            leading_edge_x_percent=self.leading_edge_x_percent,
            center_x_px=self.center_x_px,
            center_y_px=self.center_y_px,
            bbox_width_px=self.bbox_width_px,
            bbox_height_px=self.bbox_height_px,
            leading_edge_x_px=self.leading_edge_x_px,
            full_image_path=self.full_image_path,
            masked_image_path=self.masked_image_path,
            classification_file_path=self.classification_file_path,
            classification_result=self.classification_result.toJSON(),
            fully_visible_for_speed_estimation=self.fully_visible_for_speed_estimation,
        )
