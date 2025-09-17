import time
from robot.our_types.sorting import SortingState
from robot.our_types.feeder import FeederState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface


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
        self.current_motor_type = None  # 'first' or 'second'

    def step(self):
        if self.current_state == SortingState.GETTING_NEW_OBJECT_FROM_FEEDER:
            self._runGettingNewObjectFromFeeder()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
        ):
            self._runWaitingForObjectToAppearUnderMainCamera()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            self._runWaitingForObjectToCenterUnderMainCamera()
        elif self.current_state == SortingState.CLASSIFYING:
            self._runClassifying()
        elif self.current_state == SortingState.SENDING_OBJECT_TO_BIN:
            self._runSendingObjectToBin()
        elif self.current_state == SortingState.FS_OBJECT_AT_END_OF_2ND_FEEDER:
            self._runFsObjectAtEndOf2ndFeeder()
        elif self.current_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_1ST_FEEDER:
            self._runFsObjectUnderneathExitOf1stFeeder()
        elif (
            self.current_state
            == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            self._runFsNoObjectUnderneathExitOfFirstFeeder()
        elif self.current_state == SortingState.FS_FIRST_FEEDER_EMPTY:
            self._runFsFirstFeederEmpty()

    def _runGettingNewObjectFromFeeder(self):
        current_time = time.time() * 1000  # Convert to milliseconds

        # Check if motor should stop (after pulse)
        runtime_params = self.irl_interface["runtimeParams"]

        # Get pulse duration based on which motor is running
        if self.current_motor_type == "first":
            pulse_duration = runtime_params["first_vibration_hopper_motor_pulse_ms"]
        else:  # 'second'
            pulse_duration = runtime_params["second_vibration_hopper_motor_pulse_ms"]

        if (
            self.feeder_motor_running
            and (current_time - self.feeder_motor_start_time) >= pulse_duration
        ):
            first_speed = runtime_params["first_vibration_hopper_motor_speed"]
            second_speed = runtime_params["second_vibration_hopper_motor_speed"]
            first_use_hard_stop = runtime_params[
                "first_vibration_hopper_motor_use_hard_stop"
            ]
            second_use_hard_stop = runtime_params[
                "second_vibration_hopper_motor_use_hard_stop"
            ]

            # Stop the motor that was running
            if self.current_motor_type == "first":
                if first_use_hard_stop:
                    self.logger.info(
                        f"MOTOR: Backstopping first feeder motor after {pulse_duration}ms pulse"
                    )
                    self.irl_interface["first_vibration_hopper_motor"].backstop(
                        first_speed
                    )
                else:
                    self.logger.info(
                        f"MOTOR: Regular stopping first feeder motor after {pulse_duration}ms pulse"
                    )
                    self.irl_interface["first_vibration_hopper_motor"].setSpeed(0)
            elif self.current_motor_type == "second":
                if second_use_hard_stop:
                    self.logger.info(
                        f"MOTOR: Backstopping second feeder motor after {pulse_duration}ms pulse"
                    )
                    self.irl_interface["second_vibration_hopper_motor"].backstop(
                        second_speed
                    )
                else:
                    self.logger.info(
                        f"MOTOR: Regular stopping second feeder motor after {pulse_duration}ms pulse"
                    )
                    self.irl_interface["second_vibration_hopper_motor"].setSpeed(0)

            self.feeder_motor_running = False
            self.feeder_motor_start_time = current_time  # Start pause timer

        # Check if pause is over (after pause)
        # Get pause duration based on which motor was running
        if self.current_motor_type == "first":
            pause_duration = runtime_params["first_vibration_hopper_motor_pause_ms"]
        else:  # 'second'
            pause_duration = runtime_params["second_vibration_hopper_motor_pause_ms"]

        if (
            not self.feeder_motor_running
            and (current_time - self.feeder_motor_start_time) >= pause_duration
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
                runtime_params = self.irl_interface["runtimeParams"]
                speed = runtime_params["second_vibration_hopper_motor_speed"]
                self.logger.info(
                    f"MOTOR: Starting second feeder motor at speed {speed} - moving object from second to first feeder"
                )
                self.irl_interface["second_vibration_hopper_motor"].setSpeed(speed)
                self.feeder_motor_running = True
                self.feeder_motor_start_time = current_time
                self.current_motor_type = "second"
            elif not has_second:
                # Run first feeder motor to move object from first to second
                runtime_params = self.irl_interface["runtimeParams"]
                speed = runtime_params["first_vibration_hopper_motor_speed"]
                self.logger.info(
                    f"MOTOR: Starting first feeder motor at speed {speed} - moving object from first to second feeder"
                )
                self.irl_interface["first_vibration_hopper_motor"].setSpeed(speed)
                self.feeder_motor_running = True
                self.feeder_motor_start_time = current_time
                self.current_motor_type = "first"
            else:
                self.logger.info("MOTOR: No action - unexpected state")

    def _runWaitingForObjectToAppearUnderMainCamera(self):
        pass

    def _runWaitingForObjectToCenterUnderMainCamera(self):
        pass

    def _runClassifying(self):
        pass

    def _runSendingObjectToBin(self):
        pass

    def _runFsObjectAtEndOf2ndFeeder(self):
        pass

    def _runFsObjectUnderneathExitOf1stFeeder(self):
        pass

    def _runFsNoObjectUnderneathExitOfFirstFeeder(self):
        pass

    def _runFsFirstFeederEmpty(self):
        pass
