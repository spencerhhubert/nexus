from typing import Optional
from robot.states.istate_machine import IStateMachine
from robot.our_types.sorting import SortingState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager


class GettingNewObjectFromFeeder(IStateMachine):
    def __init__(
        self,
        global_config,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
    ):
        self.global_config = global_config
        self.vision_system = vision_system
        self.websocket_manager = websocket_manager
        self.irl_interface = irl_interface
        self.logger = global_config["logger"]

    def step(self) -> Optional[SortingState]:
        # Set main conveyor to default speed
        if not self.global_config["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)

        # TODO: Implement complex feeder state machine logic
        # For now, just stay in current state
        return None

    def cleanup(self) -> None:
        self.logger.info("CLEANUP: Cleared GETTING_NEW_OBJECT_FROM_FEEDER state")
