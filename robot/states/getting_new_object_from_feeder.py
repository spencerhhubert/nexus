import time
from typing import Optional
from robot.states.base_state import BaseState
from robot.our_types.sorting import SortingState
from robot.our_types.feeder_state import FeederState
from robot.our_types.vision_system import FeederRegion
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.global_config import GlobalConfig


class GettingNewObjectFromFeeder(BaseState):
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.gc = global_config
        self.logger = global_config["logger"].ctx(state="GettingNewObjectFromFeeder")

        self.feeder_state: Optional[FeederState] = None
        self.pulse_start_time: Optional[float] = None
        self.current_pulse_type: Optional[str] = None
        self.pulse_count = 0
        self.pause_start_time: Optional[float] = None
        self.is_pausing = False
        self.paused_pulse_type: Optional[str] = None

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()

        # Check for feeder state changes
        new_feeder_state = self._determineFeederState()
        if new_feeder_state and new_feeder_state != self.feeder_state:
            self._stopCurrentPulse()
            self._endPause()
            self.feeder_state = new_feeder_state
            self.logger.info(f"FEEDER STATE CHANGE: {self.feeder_state.value}")

            # Broadcast feeder state to frontend
            self.websocket_manager.broadcast_feeder_status(self.feeder_state)

            # Start appropriate pulsing for new state
            self._startPulseForState(self.feeder_state)

        # Handle current pulsing or pausing
        self.logger.info(
            f"CYCLE DEBUG: is_pausing={self.is_pausing}, current_pulse_type={self.current_pulse_type}, feeder_state={self.feeder_state}"
        )

        if self.is_pausing and self.pause_start_time:
            self.logger.info("CYCLE DEBUG: In pause phase, checking if should stop")
            if self._shouldStopCurrentPause():
                self.logger.info("CYCLE DEBUG: Pause should stop, ending pause")
                self._endPause()
                # Continue pulsing for states that need loops
                if self.feeder_state in [
                    FeederState.FIRST_FEEDER_EMPTY,
                    FeederState.OBJECT_AT_END_OF_SECOND_FEEDER,
                    FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER,
                    FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER,
                ]:
                    self.logger.info(
                        f"CYCLE RESTART: Starting next pulse after pause for {self.feeder_state}"
                    )
                    self._startPulseForState(self.feeder_state)
        elif self.current_pulse_type and self.pulse_start_time:
            self.logger.info("CYCLE DEBUG: In pulse phase, checking if should stop")
            if self._shouldStopCurrentPulse():
                self.logger.info("CYCLE DEBUG: Pulse should stop, stopping pulse")
                # Store pulse type before stopping (which clears it)
                pulse_type_for_pause = self.current_pulse_type
                self._stopCurrentPulse()
                # For states that need continuous pulsing, start pause before next pulse
                if self.feeder_state == FeederState.FIRST_FEEDER_EMPTY:
                    self.logger.info(
                        "CYCLE DEBUG: Starting pause for FIRST_FEEDER_EMPTY"
                    )
                    self._startPause(pulse_type_for_pause)
                elif self.feeder_state in [
                    FeederState.OBJECT_AT_END_OF_SECOND_FEEDER,
                    FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER,
                    FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER,
                ]:
                    self.logger.info(
                        f"CYCLE DEBUG: Starting pause for {self.feeder_state}"
                    )
                    self._startPause(pulse_type_for_pause)
        else:
            self.logger.info("CYCLE DEBUG: Not in pulse or pause phase")

        # Check if we should transition to main camera
        if self.feeder_state == FeederState.OBJECT_ON_MAIN_CONVEYOR:
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state

    def cleanup(self) -> None:
        self._stopCurrentPulse()
        self._endPause()
        self.feeder_state = None
        self.pulse_count = 0
        self.paused_pulse_type = None
        self.logger.info("CLEANUP: Cleared GETTING_NEW_OBJECT_FROM_FEEDER state")

    def _determineFeederState(self) -> Optional[FeederState]:
        # Get object detections from the last 500ms
        window_ms = 500.0
        window_seconds = window_ms / 1000.0
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        with self.vision_system.detection_lock:
            # Analyze recent object readings to determine state
            recent_detections = []
            for detection in self.vision_system.object_detections:
                recent_readings = [
                    reading
                    for reading in detection.region_readings
                    if reading.timestamp >= cutoff_time
                ]
                if recent_readings:
                    recent_detections.append(recent_readings)

            if not recent_detections:
                return None

            # Check for objects on main conveyor (highest priority)
            for readings in recent_detections:
                for reading in readings:
                    if reading.region == FeederRegion.MAIN_CONVEYOR:
                        return FeederState.OBJECT_ON_MAIN_CONVEYOR

            # Check for objects at exit of second feeder that went MIA (likely on main conveyor)
            for readings in recent_detections:
                exit_readings = [
                    reading
                    for reading in readings
                    if reading.region == FeederRegion.EXIT_OF_SECOND_FEEDER
                ]
                if exit_readings:
                    last_exit_time = max(reading.timestamp for reading in exit_readings)
                    post_exit_readings = [
                        reading
                        for reading in readings
                        if reading.timestamp > last_exit_time
                    ]
                    if not post_exit_readings:
                        return FeederState.OBJECT_ON_MAIN_CONVEYOR

            # Check for objects at end of second feeder
            for readings in recent_detections:
                for reading in readings:
                    if reading.region == FeederRegion.EXIT_OF_SECOND_FEEDER:
                        return FeederState.OBJECT_AT_END_OF_SECOND_FEEDER

            # Analyze object locations to determine feeder state
            objects_on_first_feeder = False
            objects_on_second_feeder = False
            objects_under_exit_of_first_feeder = False

            for readings in recent_detections:
                for reading in readings:
                    if reading.region == FeederRegion.FIRST_FEEDER_MASK:
                        objects_on_first_feeder = True
                    elif reading.region == FeederRegion.SECOND_FEEDER_MASK:
                        objects_on_second_feeder = True
                    elif reading.region == FeederRegion.UNDER_EXIT_OF_FIRST_FEEDER:
                        objects_under_exit_of_first_feeder = True

            # First feeder empty only if no objects detected on first feeder
            if not objects_on_first_feeder:
                return FeederState.FIRST_FEEDER_EMPTY

            # If we have objects on first feeder, determine based on dropzone
            if objects_on_first_feeder:
                if objects_under_exit_of_first_feeder:
                    return FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
                else:
                    return FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

        return None

    def _startPulseForState(self, state: FeederState) -> None:
        current_time = time.time()
        self.pulse_start_time = current_time

        if state == FeederState.OBJECT_AT_END_OF_SECOND_FEEDER:
            # Pulse second feeder with 1/2 length
            if not self.gc["disable_second_vibration_hopper_motor"]:
                motor = self.irl_interface["second_vibration_hopper_motor"]
                speed = self.gc["second_vibration_hopper_motor_speed"]
                motor.setSpeed(speed)
                self.current_pulse_type = "second_feeder_half"
                self.logger.info("FEEDER PULSE: Second feeder (half duration)")

        elif state == FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            # Pulse second feeder
            if not self.gc["disable_second_vibration_hopper_motor"]:
                motor = self.irl_interface["second_vibration_hopper_motor"]
                speed = self.gc["second_vibration_hopper_motor_speed"]
                motor.setSpeed(speed)
                self.current_pulse_type = "second_feeder"
                self.logger.info("FEEDER PULSE: Second feeder")

        elif state == FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            # Pulse first feeder
            if not self.gc["disable_first_vibration_hopper_motor"]:
                motor = self.irl_interface["first_vibration_hopper_motor"]
                speed = self.gc["first_vibration_hopper_motor_speed"]
                motor.setSpeed(speed)
                self.current_pulse_type = "first_feeder"
                self.logger.info("FEEDER PULSE: First feeder")

        elif state == FeederState.FIRST_FEEDER_EMPTY:
            # First pulse: feeder conveyor once
            if self.pulse_count == 0:
                if not self.gc["disable_feeder_conveyor"]:
                    motor = self.irl_interface["feeder_conveyor_dc_motor"]
                    speed = self.gc["feeder_conveyor_speed"]
                    motor.setSpeed(speed)
                    self.current_pulse_type = "feeder_conveyor"
                    self.logger.info(
                        "FEEDER PULSE: Feeder conveyor (FIRST_FEEDER_EMPTY)"
                    )
            else:
                # Subsequent pulses: first feeder
                if not self.gc["disable_first_vibration_hopper_motor"]:
                    motor = self.irl_interface["first_vibration_hopper_motor"]
                    speed = self.gc["first_vibration_hopper_motor_speed"]
                    motor.setSpeed(speed)
                    self.current_pulse_type = "first_feeder"
                    self.logger.info(
                        f"FEEDER PULSE: First feeder (FIRST_FEEDER_EMPTY, pulse {self.pulse_count})"
                    )

    def _shouldStopCurrentPulse(self) -> bool:
        if not self.pulse_start_time or not self.current_pulse_type:
            return False

        current_time = time.time()
        elapsed_ms = (current_time - self.pulse_start_time) * 1000

        should_stop = False
        if self.current_pulse_type == "second_feeder_half":
            should_stop = elapsed_ms >= (
                self.gc["second_vibration_hopper_motor_pulse_ms"] / 2
            )
        elif self.current_pulse_type == "second_feeder":
            should_stop = (
                elapsed_ms >= self.gc["second_vibration_hopper_motor_pulse_ms"]
            )
        elif self.current_pulse_type == "first_feeder":
            should_stop = elapsed_ms >= self.gc["first_vibration_hopper_motor_pulse_ms"]
        elif self.current_pulse_type == "feeder_conveyor":
            should_stop = elapsed_ms >= self.gc["feeder_conveyor_pulse_duration_ms"]

        if should_stop:
            self.logger.info(
                f"CYCLE DEBUG: Pulse {self.current_pulse_type} should stop after {elapsed_ms}ms"
            )

        return should_stop

    def _stopCurrentPulse(self) -> None:
        if not self.current_pulse_type:
            return

        if self.current_pulse_type in ["second_feeder", "second_feeder_half"]:
            if not self.gc["disable_second_vibration_hopper_motor"]:
                motor = self.irl_interface["second_vibration_hopper_motor"]
                motor.backstop(self.gc["second_vibration_hopper_motor_speed"])
        elif self.current_pulse_type == "first_feeder":
            if not self.gc["disable_first_vibration_hopper_motor"]:
                motor = self.irl_interface["first_vibration_hopper_motor"]
                motor.backstop(self.gc["first_vibration_hopper_motor_speed"])
        elif self.current_pulse_type == "feeder_conveyor":
            if not self.gc["disable_feeder_conveyor"]:
                motor = self.irl_interface["feeder_conveyor_dc_motor"]
                motor.setSpeed(0)

        self.logger.info(f"FEEDER PULSE STOP: {self.current_pulse_type}")

        # Increment pulse count for FIRST_FEEDER_EMPTY state
        if self.feeder_state == FeederState.FIRST_FEEDER_EMPTY:
            self.pulse_count += 1
            # Reset count after feeder conveyor + 5 first feeder pulses
            if self.pulse_count >= 20:
                self.pulse_count = 0

        self.current_pulse_type = None
        self.pulse_start_time = None

    def _startPause(self, pulse_type: str) -> None:
        current_time = time.time()
        self.pause_start_time = current_time
        self.is_pausing = True
        self.paused_pulse_type = pulse_type
        self.logger.info(f"PAUSE START: {self.paused_pulse_type}")

    def _shouldStopCurrentPause(self) -> bool:
        if not self.pause_start_time or not self.paused_pulse_type:
            return False

        current_time = time.time()
        elapsed_ms = (current_time - self.pause_start_time) * 1000

        should_stop = False
        if self.paused_pulse_type in ["second_feeder", "second_feeder_half"]:
            should_stop = (
                elapsed_ms >= self.gc["second_vibration_hopper_motor_pause_ms"]
            )
        elif self.paused_pulse_type == "first_feeder":
            should_stop = elapsed_ms >= self.gc["first_vibration_hopper_motor_pause_ms"]
        elif self.paused_pulse_type == "feeder_conveyor":
            should_stop = elapsed_ms >= self.gc["feeder_conveyor_pause_ms"]

        if should_stop:
            self.logger.info(
                f"CYCLE DEBUG: Pause {self.paused_pulse_type} should stop after {elapsed_ms}ms"
            )

        return should_stop

    def _endPause(self) -> None:
        if self.is_pausing:
            self.logger.info(f"PAUSE END: {self.paused_pulse_type}")
        self.is_pausing = False
        self.pause_start_time = None
        self.paused_pulse_type = None
