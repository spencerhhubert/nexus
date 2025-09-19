import time
from robot.our_types.sorting import SortingState
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface

# Pixel distance threshold for second feeder priority logic
SECOND_FEEDER_DISTANCE_THRESHOLD = 30


class SortingStateMachine:
    def __init__(
        self, vision_system: SegmentationModelManager, irl_interface: IRLSystemInterface
    ):
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.logger = vision_system.logger

        # Feeder motor timing state
        self.feeder_motor_running = False
        self.feeder_motor_start_time = 0
        self.current_motor_type = None  # 'first' or 'second'

    def step(self):
        # handle current state, then figure out what to do next
        # ie, analysis always happens after state's action
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
        # Check if we're still busy with pulsing or pausing
        if self._checkPulseState():
            return  # Still busy, nothing to do

        # Ready for new action - determine where objects are
        object_location = self.vision_system.determineObjectLocation()

        self.logger.info(f"FEEDER DECISION: Object location = {object_location}")

        if object_location == "second":
            # Priority: Clear second feeder first
            self.logger.info(
                "MOTOR DECISION: Objects on second feeder - running second motor to clear it"
            )
            self._startMotorPulse("second")
        elif object_location == "first":
            # Run first feeder to move objects to second
            self.logger.info(
                "MOTOR DECISION: Objects on first feeder - running first motor to move to second"
            )
            self._startMotorPulse("first")
        else:
            # No action needed
            self.logger.info("MOTOR DECISION: No objects on feeders - no action needed")

    def _checkPulseState(self):
        """Check if we're currently pulsing or pausing. Returns True if busy."""
        current_time = time.time() * 1000
        runtime_params = self.irl_interface["runtime_params"]

        if self.feeder_motor_running:
            # Check if pulse should end
            if self.current_motor_type == "first":
                pulse_duration = runtime_params["first_vibration_hopper_motor_pulse_ms"]
            else:  # 'second'
                pulse_duration = runtime_params[
                    "second_vibration_hopper_motor_pulse_ms"
                ]

            if (current_time - self.feeder_motor_start_time) >= pulse_duration:
                self._stopMotorPulse()
                return True  # Still busy (now pausing)
            return True  # Still pulsing
        else:
            # Check if pause should end
            if self.current_motor_type == "first":
                pause_duration = runtime_params["first_vibration_hopper_motor_pause_ms"]
            else:  # 'second'
                pause_duration = runtime_params[
                    "second_vibration_hopper_motor_pause_ms"
                ]

            if (current_time - self.feeder_motor_start_time) < pause_duration:
                return True  # Still pausing
            return False  # Ready for new action

    def _startMotorPulse(self, motor_type):
        """Start a motor pulse for the specified motor type."""
        current_time = time.time() * 1000
        runtime_params = self.irl_interface["runtime_params"]

        if motor_type == "first":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
            self.logger.info(f"MOTOR: Starting first feeder motor at speed {speed}")
        elif motor_type == "second":
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            motor = self.irl_interface["second_vibration_hopper_motor"]
            self.logger.info(f"MOTOR: Starting second feeder motor at speed {speed}")
        else:
            self.logger.error(f"Unknown motor type: {motor_type}")
            return

        motor.setSpeed(speed)
        self.feeder_motor_running = True
        self.feeder_motor_start_time = current_time
        self.current_motor_type = motor_type

    def _stopMotorPulse(self):
        if not self.feeder_motor_running:
            return

        current_time = time.time() * 1000
        runtime_params = self.irl_interface["runtime_params"]

        if self.current_motor_type == "first":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
            pulse_duration = runtime_params["first_vibration_hopper_motor_pulse_ms"]
        else:  # 'second'
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            motor = self.irl_interface["second_vibration_hopper_motor"]
            pulse_duration = runtime_params["second_vibration_hopper_motor_pulse_ms"]

        self.logger.info(
            f"MOTOR: Backstopping {self.current_motor_type} motor after {pulse_duration}ms pulse"
        )
        motor.backstop(speed)

        self.feeder_motor_running = False
        self.feeder_motor_start_time = current_time  # Start pause timer

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
