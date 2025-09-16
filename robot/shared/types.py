from typing import Literal, Union, Optional, List
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


class MotorInfo(TypedDict):
    motor_id: str
    display_name: str
    current_speed: int
    min_speed: int
    max_speed: int


class SystemStatus(TypedDict):
    lifecycle_stage: str
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


WebSocketEvent = Union[CameraFrameEvent, StatusUpdateEvent]
