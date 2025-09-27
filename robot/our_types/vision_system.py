from enum import Enum
from dataclasses import dataclass
from typing import List


@dataclass
class CameraPerformanceMetrics:
    fps_1s: float
    fps_5s: float
    latency_1s: float
    latency_5s: float


class FeederState(Enum):
    OBJECT_AT_END_OF_SECOND_FEEDER = "object_at_end_of_second_feeder"
    OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = "object_underneath_exit_of_first_feeder"
    NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = (
        "no_object_underneath_exit_of_first_feeder"
    )
    FIRST_FEEDER_EMPTY = "first_feeder_empty"
    OBJECT_ON_MAIN_CONVEYOR = "object_on_main_conveyor"


class MainCameraState(Enum):
    NO_OBJECT_UNDER_CAMERA = "no_object_under_camera"
    WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA = (
        "waiting_for_object_to_center_under_main_camera"
    )
    OBJECT_CENTERED_UNDER_MAIN_CAMERA = "object_centered_under_main_camera"


class FeederRegion(Enum):
    FIRST_FEEDER_MASK = "first_feeder_mask"
    UNDER_EXIT_OF_SECOND_FEEDER = "under_exit_of_second_feeder"
    SECOND_FEEDER_MASK = "second_feeder_mask"
    EXIT_OF_SECOND_FEEDER = "exit_of_second_feeder"
    MAIN_CONVEYOR = "main_conveyor"
    UNKNOWN = "unknown"


@dataclass
class RegionReading:
    timestamp: float
    region: FeederRegion


@dataclass
class ObjectDetection:
    yolo_id: int
    region_readings: List[RegionReading]
