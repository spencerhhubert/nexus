from typing import Literal, Union, Optional, List, Dict, Any
from typing_extensions import TypedDict
from enum import Enum


class SystemLifecycleStage(Enum):
    INITIALIZING = "initializing"
    STARTING_HARDWARE = "starting_hardware"
    PAUSED_BY_USER = "paused_by_user"
    PAUSED_BY_SYSTEM = "paused_by_system"
    RUNNING = "running"
    STOPPING = "stopping"
    SHUTDOWN = "shutdown"


class SortingState(Enum):
    GETTING_NEW_OBJECT = "getting_new_object"
    WAITING_FOR_OBJECT_TO_APPEAR = "waiting_for_object_to_appear"
    WAITING_FOR_OBJECT_TO_CENTER = "waiting_for_object_to_center"
    TRYING_TO_CLASSIFY = "trying_to_classify"
    SENDING_ITEM_TO_BIN = "sending_item_to_bin"


class MotorInfo(TypedDict):
    motor_id: str
    display_name: str
    current_speed: int
    min_speed: int
    max_speed: int


class SystemStatus(TypedDict):
    lifecycle_stage: str
    sorting_state: str
    objects_in_frame: int
    conveyor_speed: Optional[float]
    average_speed_1s: Optional[float]
    average_speed_5s: Optional[float]
    motors: List[MotorInfo]


class SetMotorSpeedRequest(TypedDict):
    motor_id: str
    speed: int


class StartSystemRequest(TypedDict):
    pass


class StopSystemRequest(TypedDict):
    pass


class CameraFrameEvent(TypedDict):
    type: Literal["camera_frame"]
    frame_data: str


class StatusUpdateEvent(TypedDict):
    type: Literal["status_update"]
    status: SystemStatus


class ObservationJSON(TypedDict):
    observation_id: str
    trajectory_id: Optional[str]
    created_at: int
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
    classification_result: Dict[str, Any]


class ObservationJSONForWeb(ObservationJSON):
    masked_image: str


class TrajectoryJSON(TypedDict):
    trajectory_id: str
    created_at: int
    updated_at: int
    observation_ids: List[str]
    consensus_classification: Optional[str]
    lifecycle_stage: str
    target_bin: Optional[Dict[str, Any]]


class NewObservationEvent(TypedDict):
    type: Literal["new_observation"]
    observation: ObservationJSONForWeb


class TrajectoriesUpdateEvent(TypedDict):
    type: Literal["trajectories_update"]
    trajectories: List[TrajectoryJSON]


class BricklinkPartData(TypedDict):
    no: str
    name: str
    type: str
    category_id: int
    alternate_no: str
    image_url: str
    thumbnail_url: str
    weight: str
    dim_x: str
    dim_y: str
    dim_z: str
    year_released: int
    description: str
    is_obsolete: bool


WebSocketEvent = Union[
    CameraFrameEvent, StatusUpdateEvent, NewObservationEvent, TrajectoriesUpdateEvent
]
