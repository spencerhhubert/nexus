import time
from robot.our_types.sorting import SortingState
from robot.our_types.feeder import FeederState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface

FEEDER_MOTOR_PULSE_MS = 1000
FEEDER_MOTOR_PAUSE_MS = 200


class SortingStateMachine:
    def __init__(
        self, vision_system: SegmentationModelManager, irl_interface: IRLSystemInterface
    ):
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.feeder_state = FeederState
        self.logger = vision_system.logger

        # Feeder motor timing state
        self.feeder_motor_running = False
        self.feeder_motor_start_time = 0

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
        current_time = time.time() * 1000  # Convert to milliseconds

        # Check if motor should stop (after pulse)
        if (
            self.feeder_motor_running
            and (current_time - self.feeder_motor_start_time) >= FEEDER_MOTOR_PULSE_MS
        ):
            # Hard stop both feeder motors
            self.logger.info(
                f"MOTOR: Hard stopping feeder motors after {FEEDER_MOTOR_PULSE_MS}ms pulse"
            )
            first_speed = self.vision_system.global_config["first_vibration_hopper_motor_speed"]
            second_speed = self.vision_system.global_config["second_vibration_hopper_motor_speed"]

            self.irl_interface["first_vibration_hopper_motor"].hardStop(first_speed)
            self.irl_interface["second_vibration_hopper_motor"].hardStop(second_speed)
            # self.irl_interface["first_vibration_hopper_motor"].setSpeed(0)
            # self.irl_interface["second_vibration_hopper_motor"].setSpeed(0)
            self.feeder_motor_running = False
            self.feeder_motor_start_time = current_time  # Start pause timer

        # Check if pause is over (after pause)
        elif (
            not self.feeder_motor_running
            and (current_time - self.feeder_motor_start_time) >= FEEDER_MOTOR_PAUSE_MS
        ):
            # Check which feeder to run
            has_second = self.vision_system.hasObjectOnSecondFeeder()
            has_first = self.vision_system.hasObjectOnFirstFeeder()

            # Get total object count to determine if we should feed at all
            masks_by_class = self.vision_system.getDetectedMasksByClass()
            total_objects = len(masks_by_class.get("object", []))

            self.logger.info(
                f"FEEDER STATE: total_objects={total_objects}, has_object_on_second={has_second}, has_object_on_first={has_first}"
            )

            if total_objects == 0:
                self.logger.info("MOTOR: No objects detected - no feeding needed")
            elif has_second:
                # Run second feeder motor to move object from second to first
                speed = self.vision_system.global_config[
                    "second_vibration_hopper_motor_speed"
                ]
                self.logger.info(
                    f"MOTOR: Starting second feeder motor at speed {speed} - moving object from second to first feeder"
                )
                self.irl_interface["second_vibration_hopper_motor"].setSpeed(speed)
                self.feeder_motor_running = True
                self.feeder_motor_start_time = current_time
            elif not has_second:
                # Run first feeder motor to move object from first to second
                speed = self.vision_system.global_config[
                    "first_vibration_hopper_motor_speed"
                ]
                self.logger.info(
                    f"MOTOR: Starting first feeder motor at speed {speed} - moving object from first to second feeder"
                )
                self.irl_interface["first_vibration_hopper_motor"].setSpeed(speed)
                self.feeder_motor_running = True
                self.feeder_motor_start_time = current_time
            else:
                self.logger.info("MOTOR: No action - unexpected state")

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
