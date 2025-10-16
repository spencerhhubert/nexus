from typing import TypedDict, Optional, Dict, Any
from .camera import CameraType
from .lifecycle import SystemLifecycleStage
from .sorting import SortingState
from .motor import MotorStatus
from .bin import BinCoordinates
from .vision_system import CameraPerformanceMetrics
from .feeder_state import FeederState


class CameraFrameMessage(TypedDict):
    type: str
    camera: str
    data: str


class SystemStatusMessage(TypedDict):
    type: str
    lifecycle_stage: str
    sorting_state: str
    motors: Dict[str, MotorStatus]
    encoder: Optional[Dict[str, Any]]


class KnownObjectUpdateMessage(TypedDict, total=False):
    type: str
    uuid: str
    main_camera_id: Optional[str]
    image: Optional[str]
    classification_id: Optional[str]
    bin_coordinates: Optional[Dict[str, int]]


class BinStateUpdateMessage(TypedDict):
    type: str
    bin_contents: Dict[str, Optional[str]]
    timestamp: float


class CameraPerformanceMessage(TypedDict):
    type: str
    camera: str
    fps_1s: float
    fps_5s: float
    latency_1s: float
    latency_5s: float


class FeederStatusMessage(TypedDict):
    type: str
    feeder_state: Optional[str]


class SortingStatsMessage(TypedDict):
    type: str
    total_known_objects: int
    average_time_between_known_objects_seconds: Optional[float]
