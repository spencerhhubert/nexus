from robot.our_types.sorting import SortingState
from robot.our_types.feeder import FeederState
from robot.vision_system import VisionSystem
from robot.irl.config import IRLSystemInterface


class SortingStateMachine:
    def __init__(self, vision_system: VisionSystem, irl_interface: IRLSystemInterface):
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.feeder_state = FeederState

    def step(self):
        if self.current_state == SortingState.GETTING_NEW_OBJECT_FROM_FEEDER:
            self._run_getting_new_object_from_feeder()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
        ):
            self._run_waiting_for_object_to_appear_under_main_camera()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            self._run_waiting_for_object_to_center_under_main_camera()
        elif self.current_state == SortingState.CLASSIFYING:
            self._run_classifying()
        elif self.current_state == SortingState.SENDING_OBJECT_TO_BIN:
            self._run_sending_object_to_bin()
        elif self.current_state == SortingState.FS_OBJECT_AT_END_OF_2ND_FEEDER:
            self._run_fs_object_at_end_of_2nd_feeder()
        elif self.current_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_1ST_FEEDER:
            self._run_fs_object_underneath_exit_of_1st_feeder()
        elif (
            self.current_state
            == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            self._run_fs_no_object_underneath_exit_of_first_feeder()
        elif self.current_state == SortingState.FS_FIRST_FEEDER_EMPTY:
            self._run_fs_first_feeder_empty()

    def _run_getting_new_object_from_feeder(self):
        pass

    def _run_waiting_for_object_to_appear_under_main_camera(self):
        pass

    def _run_waiting_for_object_to_center_under_main_camera(self):
        pass

    def _run_classifying(self):
        pass

    def _run_sending_object_to_bin(self):
        pass

    def _run_fs_object_at_end_of_2nd_feeder(self):
        pass

    def _run_fs_object_underneath_exit_of_1st_feeder(self):
        pass

    def _run_fs_no_object_underneath_exit_of_first_feeder(self):
        pass

    def _run_fs_first_feeder_empty(self):
        pass
