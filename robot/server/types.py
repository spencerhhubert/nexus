from typing import Literal, Union, Optional, List
from typing_extensions import TypedDict
from enum import Enum


class SystemLifecycleStage(Enum):
    INITIALIZING = "initializing"
    STARTING_HARDWARE = "starting_hardware"
    PAUSED_BY_USER = "paused_by_user"
    RUNNING = "running"
    STOPPING = "stopping"
    SHUTDOWN = "shutdown"


class SortingState(Enum):
    GETTING_NEW_OBJECT = "getting_new_object"
    OBJECT_IN_VIEW = "object_in_view"
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
    frame_data: str  # base64 encoded image


class StatusUpdateEvent(TypedDict):
    type: Literal["status_update"]
    status: SystemStatus


WebSocketEvent = Union[CameraFrameEvent, StatusUpdateEvent]
