from typing import Optional
from robot.states.base_state import BaseState
from robot.our_types.sorting import SortingState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager


class GettingNewObjectFromFeeder(BaseState):
    def __init__(
        self,
        global_config,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.logger = global_config["logger"].ctx(state="GettingNewObjectFromFeeder")

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state

    def cleanup(self) -> None:
        self.logger.info("CLEANUP: Cleared GETTING_NEW_OBJECT_FROM_FEEDER state")
