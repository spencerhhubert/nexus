import time
from typing import Optional
from robot.states.base_state import BaseState
from robot.our_types.sorting import SortingState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.global_config import GlobalConfig


class WaitingForObjectToAppearUnderMainCamera(BaseState):
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.logger = global_config["logger"].ctx(
            state="WaitingForObjectToAppearUnderMainCamera"
        )

        self.timeout_start_ts: Optional[float] = None

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()

        current_time = time.time()

        if self.timeout_start_ts is None:
            self.timeout_start_ts = current_time

        timeout_duration = (
            self.global_config["waiting_for_object_to_appear_timeout_ms"] / 1000.0
        )
        if current_time - self.timeout_start_ts >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state

    def cleanup(self) -> None:
        self.timeout_start_ts = None
        self.logger.info(
            "CLEANUP: Cleared WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA state"
        )
