import time
from typing import Dict
from robot.our_types.sorting import SortingState
from robot.global_config import GlobalConfig
from robot.states.istate_machine import IStateMachine
from robot.states.getting_new_object_from_feeder import GettingNewObjectFromFeeder
from robot.states.waiting_for_object_to_appear_under_main_camera import (
    WaitingForObjectToAppearUnderMainCamera,
)
from robot.states.waiting_for_object_to_center_under_main_camera import (
    WaitingForObjectToCenterUnderMainCamera,
)
from robot.states.classifying import Classifying
from robot.states.sending_object_to_bin import SendingObjectToBin
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.encoder_manager import EncoderManager
from robot.bin_state_tracker import BinStateTracker


class SortingStateMachine:
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
        encoder_manager: EncoderManager,
        bin_state_tracker: BinStateTracker,
    ):
        self.global_config = global_config
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.websocket_manager = websocket_manager
        self.encoder_manager = encoder_manager
        self.bin_state_tracker = bin_state_tracker
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.logger = vision_system.logger

        self.states_map: Dict[SortingState, IStateMachine] = {
            SortingState.GETTING_NEW_OBJECT_FROM_FEEDER: GettingNewObjectFromFeeder(
                self.global_config, vision_system, websocket_manager, irl_interface
            ),
            SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA: WaitingForObjectToAppearUnderMainCamera(
                self.global_config, vision_system, websocket_manager, irl_interface
            ),
            SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA: WaitingForObjectToCenterUnderMainCamera(
                self.global_config, vision_system, websocket_manager, irl_interface
            ),
            SortingState.CLASSIFYING: Classifying(
                self.global_config,
                vision_system,
                websocket_manager,
                irl_interface,
                bin_state_tracker,
            ),
            SortingState.SENDING_OBJECT_TO_BIN: SendingObjectToBin(
                self.global_config,
                vision_system,
                websocket_manager,
                irl_interface,
                encoder_manager,
            ),
        }

    def step(self):
        next_state = None

        if self.current_state in self.states_map:
            next_state = self.states_map[self.current_state].step()

        if next_state and next_state != self.current_state:
            self.logger.info(
                f"STATE TRANSITION: {self.current_state.value} -> {next_state.value}"
            )

            if self.current_state in self.states_map:
                self.states_map[self.current_state].cleanup()

            self.current_state = next_state

        steps_per_second = self.global_config["state_machine_steps_per_second"]
        time.sleep(1.0 / steps_per_second)
