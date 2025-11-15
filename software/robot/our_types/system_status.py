from typing import TypedDict, Dict
from robot.our_types.motor import MotorStatus
from robot.our_types.sorting import SortingState
from robot.our_types import SystemLifecycleStage


class SystemStatus(TypedDict):
    lifecycle_stage: SystemLifecycleStage
    sorting_state: SortingState
    motors: Dict[str, MotorStatus]
