from typing import Optional
import threading
from robot.states.istate_machine import IStateMachine
from robot.our_types.sorting import SortingState
from robot.our_types.vision_system import MainCameraState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.global_config import GlobalConfig


class BaseState(IStateMachine):
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
    ):
        self.global_config = global_config
        self.vision_system = vision_system
        self.websocket_manager = websocket_manager
        self.irl_interface = irl_interface
        self._execution_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _determineNextStateFromFrameAnalysis(self) -> Optional[SortingState]:
        main_camera_state = self.vision_system.determineMainCameraState()

        if main_camera_state == MainCameraState.OBJECT_CENTERED_UNDER_MAIN_CAMERA:
            return SortingState.CLASSIFYING
        elif (
            main_camera_state
            == MainCameraState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            return SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA

        if self.vision_system.hasObjectOnMainConveyorInFeederView():
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA

        return None

    def _setMainConveyorToDefaultSpeed(self) -> None:
        if not self.global_config["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)

    def cleanup(self) -> None:
        self._stopExecutionThread()

    def _ensureExecutionThreadStarted(self) -> None:
        if self._execution_thread is None or not self._execution_thread.is_alive():
            self._stop_event.clear()
            self._execution_thread = threading.Thread(
                target=self._executionLoop, daemon=True
            )
            self._execution_thread.start()

    def _executionLoop(self) -> None:
        pass

    def _stopExecutionThread(self) -> None:
        if self._execution_thread is not None and self._execution_thread.is_alive():
            self._stop_event.set()
            self._execution_thread.join(timeout=2.0)
