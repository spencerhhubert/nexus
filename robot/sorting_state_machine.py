import time
from typing import Dict, Optional, Union, TypedDict, Literal
from robot.our_types.sorting import SortingState
from robot.our_types.vision_system import FeederState, MainCameraState
from robot.vision_system import (
    SegmentationModelManager,
    YOLO_CLASSES,
    SECOND_FEEDER_DISTANCE_THRESHOLD,
    MAIN_CONVEYOR_THRESHOLD,
)
from robot.irl.config import IRLSystemInterface


SECOND_FEEDER_THRESHOLD = 0.5  # 50% object coverage for second feeder

# Type definitions
MotorType = Literal[
    "first_vibration_hopper_motor",
    "second_vibration_hopper_motor",
    "feeder_conveyor_motor",
]


# Motor states runtime variables
class MotorStateRuntimeVariables(TypedDict, total=False):
    motor_start_time: Optional[float]
    motor_type: Optional[MotorType]
    motor_running: Optional[bool]


# Timeout states runtime variables
class ClassifyingRuntimeVariables(TypedDict, total=False):
    classifying_timeout_start_ts: Optional[float]


class WaitingForObjectToAppearRuntimeVariables(TypedDict, total=False):
    waiting_for_object_to_appear_timeout_start_ts: Optional[float]


class WaitingForObjectToCenterRuntimeVariables(TypedDict, total=False):
    waiting_for_object_to_center_timeout_start_ts: Optional[float]


# States with no runtime variables
class EmptyRuntimeVariables(TypedDict, total=False):
    pass


StateMachineRuntimeVariables = Dict[SortingState, Dict]

"""
STATE MACHINE OVERVIEW:

GETTING_NEW_OBJECT_FROM_FEEDER:
- Analyzes feeder camera to determine which feeder state to transition to
- Does not run motors directly, only determines next state
- CLEAN RULE HIERARCHY:
  1. Main camera: Object centered → CLASSIFYING
  2. Main camera: Object detected but not centered → WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
  3. Feeder camera: Object touching main conveyor edges → WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
  4. Objects on second feeder >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder → FS_OBJECT_AT_END_OF_SECOND_FEEDER (run second feeder)
  5. Objects on second feeder close to first + objects on first feeder → FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER (run first feeder)
  6. Objects on second feeder + empty first feeder → FS_FIRST_FEEDER_EMPTY (wait)
  7. Objects only on first feeder → FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER (run first feeder)
  8. No objects anywhere → FS_FIRST_FEEDER_EMPTY

FS_OBJECT_AT_END_OF_SECOND_FEEDER:
- Pulses second feeder motor to move objects forward
- Triggered when object >50% surrounded by second feeder AND >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder
- Represents objects in the dropzone that are far from the first feeder
- Transitions when objects move or are cleared

FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
- Pulses second feeder motor to clear objects blocking first feeder exit
- Transitions when first feeder exit is clear

FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
- Pulses first feeder motor to move objects from first to second feeder
- Triggered when: object >50% on second feeder and >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder, OR object >50% in first feeder
- Transitions when objects appear underneath first feeder exit

FS_FIRST_FEEDER_EMPTY:
- Wait state - no objects detected in first feeder
- Transitions when objects appear in first feeder

WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA:
- Wait state - object detected touching main conveyor edges in feeder camera (using edge proximity detection)
- Triggered when >50% of object pixels are within 3px of main conveyor mask edges
- Transitions when object appears under main camera

WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA:
- Wait state - object detected under main camera but not centered
- Transitions when object moves to center position

CLASSIFYING:
- Wait state - object is centered and ready for classification
- Transitions to SENDING_OBJECT_TO_BIN after classification

SENDING_OBJECT_TO_BIN:
- Wait state - object is being sorted to appropriate bin
- Transitions back to GETTING_NEW_OBJECT_FROM_FEEDER when complete
"""


class SortingStateMachine:
    def __init__(
        self, vision_system: SegmentationModelManager, irl_interface: IRLSystemInterface
    ):
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.logger = vision_system.logger

        # Initialize runtime variables for all states
        self.runtime_variables: StateMachineRuntimeVariables = {}
        for state in SortingState:
            self.runtime_variables[state] = {}

    def step(self):
        # Execute current state's action and get next state
        next_state = None
        if self.current_state == SortingState.GETTING_NEW_OBJECT_FROM_FEEDER:
            next_state = self._runGettingNewObjectFromFeeder()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
        ):
            next_state = self._runWaitingForObjectToAppearUnderMainCamera()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            next_state = self._runWaitingForObjectToCenterUnderMainCamera()
        elif self.current_state == SortingState.CLASSIFYING:
            next_state = self._runClassifying()
        elif self.current_state == SortingState.SENDING_OBJECT_TO_BIN:
            next_state = self._runSendingObjectToBin()
        elif self.current_state == SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER:
            next_state = self._runFsObjectAtEndOfSecondFeeder()
        elif (
            self.current_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            next_state = self._runFsObjectUnderneathExitOfFirstFeeder()
        elif (
            self.current_state
            == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            next_state = self._runFsNoObjectUnderneathExitOfFirstFeeder()
        elif self.current_state == SortingState.FS_FIRST_FEEDER_EMPTY:
            next_state = self._runFsFirstFeederEmpty()

        # Transition if needed
        if next_state and next_state != self.current_state:
            self.logger.info(
                f"STATE TRANSITION: {self.current_state.value} -> {next_state.value}"
            )
            self.cleanupRuntimeVariables(self.current_state)
            self.setMotorsToDefaultSpeed()
            self.current_state = next_state
        time.sleep(0.02)

    def _runGettingNewObjectFromFeeder(self) -> SortingState:
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runWaitingForObjectToAppearUnderMainCamera(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "waiting_for_object_to_appear_timeout_start_ts" not in state_vars:
            state_vars["waiting_for_object_to_appear_timeout_start_ts"] = current_time

        start_time = state_vars["waiting_for_object_to_appear_timeout_start_ts"]
        timeout_duration = gc["waiting_for_object_to_appear_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runWaitingForObjectToCenterUnderMainCamera(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "waiting_for_object_to_center_timeout_start_ts" not in state_vars:
            state_vars["waiting_for_object_to_center_timeout_start_ts"] = current_time

        start_time = state_vars["waiting_for_object_to_center_timeout_start_ts"]
        timeout_duration = gc["waiting_for_object_to_center_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runClassifying(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "classifying_timeout_start_ts" not in state_vars:
            state_vars["classifying_timeout_start_ts"] = current_time

        start_time = state_vars["classifying_timeout_start_ts"]
        timeout_duration = gc["classifying_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return self.current_state

    def _runSendingObjectToBin(self) -> SortingState:
        return self.current_state

    def _runFsObjectAtEndOfSecondFeeder(self) -> SortingState:
        self._startMotorPulseIfNeeded("second_vibration_hopper_motor")
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsObjectUnderneathExitOfFirstFeeder(self) -> SortingState:
        self._startMotorPulseIfNeeded("second_vibration_hopper_motor")
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsNoObjectUnderneathExitOfFirstFeeder(self) -> SortingState:
        self._startMotorPulseIfNeeded("first_vibration_hopper_motor")
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsFirstFeederEmpty(self) -> SortingState:
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _startMotorPulseIfNeeded(self, motor_type: MotorType):
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        runtime_params = self.irl_interface["runtime_params"]

        # Check if motor is already running
        if (
            state_vars.get("motor_running")
            and state_vars.get("motor_type") == motor_type
        ):
            # Check if pulse duration has elapsed
            if motor_type == "first_vibration_hopper_motor":
                pulse_duration = (
                    runtime_params["first_vibration_hopper_motor_pulse_ms"] / 1000.0
                )
            elif motor_type == "second_vibration_hopper_motor":
                pulse_duration = (
                    runtime_params["second_vibration_hopper_motor_pulse_ms"] / 1000.0
                )
            else:  # feeder_conveyor_motor
                pulse_duration = runtime_params["feeder_conveyor_pulse_ms"] / 1000.0

            start_time = state_vars.get("motor_start_time") or 0.0
            if current_time - start_time >= pulse_duration:
                # Stop pulse and start backstop
                self._stopMotorPulse(motor_type)
                state_vars["motor_running"] = False
                state_vars["motor_start_time"] = current_time  # Start pause timer
            return

        # Check if we're in pause period
        if not state_vars.get("motor_running") and state_vars.get("motor_start_time"):
            if motor_type == "first_vibration_hopper_motor":
                pause_duration = (
                    runtime_params["first_vibration_hopper_motor_pause_ms"] / 1000.0
                )
            elif motor_type == "second_vibration_hopper_motor":
                pause_duration = (
                    runtime_params["second_vibration_hopper_motor_pause_ms"] / 1000.0
                )
            else:  # feeder_conveyor_motor
                pause_duration = runtime_params["feeder_conveyor_pause_ms"] / 1000.0

            start_time = state_vars.get("motor_start_time") or 0.0
            if current_time - start_time < pause_duration:
                return  # Still pausing

        # Start new pulse
        if not state_vars.get("motor_running"):
            self._startMotorPulse(motor_type)
            state_vars["motor_running"] = True
            state_vars["motor_type"] = motor_type
            state_vars["motor_start_time"] = current_time

    def _startMotorPulse(self, motor_type: MotorType):
        runtime_params = self.irl_interface["runtime_params"]

        if motor_type == "first_vibration_hopper_motor":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
            self.logger.info(f"MOTOR: Starting first feeder motor at speed {speed}")
        elif motor_type == "second_vibration_hopper_motor":
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            motor = self.irl_interface["second_vibration_hopper_motor"]
            self.logger.info(f"MOTOR: Starting second feeder motor at speed {speed}")
        elif motor_type == "feeder_conveyor_motor":
            speed = runtime_params["feeder_conveyor_speed"]
            motor = self.irl_interface["feeder_conveyor_dc_motor"]
            self.logger.info(f"MOTOR: Starting feeder conveyor motor at speed {speed}")
        else:
            self.logger.error(f"Unknown motor type: {motor_type}")
            return

        motor.setSpeed(speed)

    def _stopMotorPulse(self, motor_type: MotorType):
        runtime_params = self.irl_interface["runtime_params"]

        if motor_type == "first_vibration_hopper_motor":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
        elif motor_type == "second_vibration_hopper_motor":
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            motor = self.irl_interface["second_vibration_hopper_motor"]
        elif motor_type == "feeder_conveyor_motor":
            speed = runtime_params["feeder_conveyor_speed"]
            motor = self.irl_interface["feeder_conveyor_dc_motor"]
        else:
            self.logger.error(f"Unknown motor type: {motor_type}")
            return

        self.logger.info(f"MOTOR: Backstopping {motor_type} motor after pulse")
        motor.backstop(speed)

    def _determineFeederState(self) -> Optional[SortingState]:
        feeder_state = self.vision_system.determineFeederState()

        self.logger.info(f"FEEDER ANALYSIS: Feeder state = {feeder_state}")

        if feeder_state is None:
            return None

        # Map FeederState to SortingState
        if feeder_state == FeederState.OBJECT_AT_END_OF_SECOND_FEEDER:
            return SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER
        elif feeder_state == FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            return SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        elif feeder_state == FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            return SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        elif feeder_state == FeederState.FIRST_FEEDER_EMPTY:
            return SortingState.FS_FIRST_FEEDER_EMPTY
        else:
            self.logger.error(f"Unknown feeder state: {feeder_state}")
            return None

    def _determineNextStateFromFrameAnalysis(self) -> Optional[SortingState]:
        # Check main camera first for higher priority states
        main_camera_state = self.vision_system.determineMainCameraState()

        # Map MainCameraState to SortingState
        if main_camera_state == MainCameraState.OBJECT_CENTERED_UNDER_MAIN_CAMERA:
            return SortingState.CLASSIFYING
        elif (
            main_camera_state
            == MainCameraState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            return SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA

        # Check feeder camera for objects on main conveyor (in feeder view)
        if self.vision_system.hasObjectOnMainConveyorInFeederView():
            # note: going to need to add a threshold wait in this state while the object goes from camera to camera
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA

        # Check feeder states in priority order
        feeder_state = self._determineFeederState()
        if feeder_state:
            if feeder_state == SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER:
                return SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER
            elif feeder_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
                return SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            elif (
                feeder_state
                == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            ):
                return SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            elif feeder_state == SortingState.FS_FIRST_FEEDER_EMPTY:
                return SortingState.FS_FIRST_FEEDER_EMPTY

        return None

    def cleanupRuntimeVariables(self, state: SortingState):
        self.runtime_variables[state] = {}

    def setMotorsToDefaultSpeed(self):
        gc = self.vision_system.global_config

        # Stop vibration motors with backstop
        if not gc["disable_first_vibration_hopper_motor"]:
            first_motor = self.irl_interface["first_vibration_hopper_motor"]
            first_speed = self.irl_interface["runtime_params"][
                "first_vibration_hopper_motor_speed"
            ]
            first_motor.backstop(first_speed)

        if not gc["disable_second_vibration_hopper_motor"]:
            second_motor = self.irl_interface["second_vibration_hopper_motor"]
            second_speed = self.irl_interface["runtime_params"][
                "second_vibration_hopper_motor_speed"
            ]
            second_motor.backstop(second_speed)

        # Set main conveyor to default speed
        if not gc["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)
