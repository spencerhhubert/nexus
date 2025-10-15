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

DEFAULT_EXEC_LOOP_WAIT_MS = 200


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
        self.pulse_count = 0

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()
        self._ensureExecutionThreadStarted()

        new_feeder_state = self._determineFeederState()
        if new_feeder_state and new_feeder_state != self.feeder_state:
            self.feeder_state = new_feeder_state
            self.logger.info(f"FEEDER STATE CHANGE: {self.feeder_state.value}")
            self.websocket_manager.broadcast_feeder_status(self.feeder_state)

        if self.feeder_state == FeederState.OBJECT_ON_MAIN_CONVEYOR:
            self.logger.info(
                "TRANSITION: Object detected on main conveyor, transitioning to main camera"
            )
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state

    def cleanup(self) -> None:
        super().cleanup()
        self.feeder_state = None
        self.pulse_count = 0
        self.logger.info("CLEANUP: Cleared GETTING_NEW_OBJECT_FROM_FEEDER state")

    def _executionLoop(self) -> None:
        while not self._stop_event.is_set():
            if self.feeder_state is None:
                time.sleep(DEFAULT_EXEC_LOOP_WAIT_MS / 1000.0)
                continue

            if self.feeder_state == FeederState.OBJECT_AT_END_OF_SECOND_FEEDER:
                if not self.gc["disable_second_vibration_hopper_motor"]:
                    motor = self.irl_interface["second_vibration_hopper_motor"]
                    runtime = self.irl_interface["runtime_params"]
                    speed = runtime["second_vibration_hopper_motor_speed"]
                    pulse_ms = runtime["second_vibration_hopper_motor_pulse_ms"] / 2
                    pause_ms = runtime["second_vibration_hopper_motor_pause_ms"]

                    motor.setSpeed(speed)
                    self.logger.info("FEEDER PULSE: Second feeder (half duration)")
                    time.sleep(pulse_ms / 1000.0)
                    motor.backstop(speed)
                    time.sleep(pause_ms / 1000.0)

            elif (
                self.feeder_state == FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            ):
                if not self.gc["disable_second_vibration_hopper_motor"]:
                    motor = self.irl_interface["second_vibration_hopper_motor"]
                    runtime = self.irl_interface["runtime_params"]
                    speed = runtime["second_vibration_hopper_motor_speed"]
                    pulse_ms = runtime["second_vibration_hopper_motor_pulse_ms"]
                    pause_ms = runtime["second_vibration_hopper_motor_pause_ms"]

                    motor.setSpeed(speed)
                    self.logger.info("FEEDER PULSE: Second feeder")
                    time.sleep(pulse_ms / 1000.0)
                    motor.backstop(speed)
                    time.sleep(pause_ms / 1000.0)

            elif (
                self.feeder_state
                == FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            ):
                if not self.gc["disable_first_vibration_hopper_motor"]:
                    motor = self.irl_interface["first_vibration_hopper_motor"]
                    runtime = self.irl_interface["runtime_params"]
                    speed = runtime["first_vibration_hopper_motor_speed"]
                    pulse_ms = runtime["first_vibration_hopper_motor_pulse_ms"]
                    pause_ms = runtime["first_vibration_hopper_motor_pause_ms"]

                    motor.setSpeed(speed)
                    self.logger.info("FEEDER PULSE: First feeder")
                    time.sleep(pulse_ms / 1000.0)
                    motor.backstop(speed)
                    time.sleep(pause_ms / 1000.0)

            elif self.feeder_state == FeederState.FIRST_FEEDER_EMPTY:
                if self.pulse_count == 0:
                    if not self.gc["disable_feeder_conveyor"]:
                        motor = self.irl_interface["feeder_conveyor_dc_motor"]
                        runtime = self.irl_interface["runtime_params"]
                        speed = runtime["feeder_conveyor_speed"]
                        pulse_ms = runtime["feeder_conveyor_pulse_ms"]
                        pause_ms = runtime["feeder_conveyor_pause_ms"]

                        motor.setSpeed(speed)
                        self.logger.info(
                            "FEEDER PULSE: Feeder conveyor (FIRST_FEEDER_EMPTY)"
                        )
                        time.sleep(pulse_ms / 1000.0)
                        motor.setSpeed(0)
                        self.pulse_count += 1
                        time.sleep(pause_ms / 1000.0)
                else:
                    if not self.gc["disable_first_vibration_hopper_motor"]:
                        motor = self.irl_interface["first_vibration_hopper_motor"]
                        runtime = self.irl_interface["runtime_params"]
                        speed = runtime["first_vibration_hopper_motor_speed"]
                        pulse_ms = runtime["first_vibration_hopper_motor_pulse_ms"]
                        pause_ms = runtime["first_vibration_hopper_motor_pause_ms"]

                        motor.setSpeed(speed)
                        self.logger.info(
                            f"FEEDER PULSE: First feeder (FIRST_FEEDER_EMPTY, pulse {self.pulse_count})"
                        )
                        time.sleep(pulse_ms / 1000.0)
                        motor.backstop(speed)
                        self.pulse_count += 1
                        if self.pulse_count >= 20:
                            self.pulse_count = 0
                        time.sleep(pause_ms / 1000.0)
            else:
                time.sleep(DEFAULT_EXEC_LOOP_WAIT_MS / 1000.0)

    def _determineFeederState(self) -> Optional[FeederState]:
        steps_per_second = self.gc["state_machine_steps_per_second"]
        step_duration_ms = (1.0 / steps_per_second) * 1000
        window_ms = step_duration_ms
        window_seconds = window_ms / 1000.0
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        with self.vision_system.detection_lock:
            # Analyze recent object readings to determine state
            recent_detections = []

            # remove this in future: log object detections for debugging
            self.logger.info(
                f"OBJECT DETECTIONS: Found {len(self.vision_system.object_detections)} total detections"
            )
            for i, detection in enumerate(self.vision_system.object_detections):
                self.logger.info(
                    f"  Detection {i}: {len(detection.region_readings)} readings"
                )
                for j, reading in enumerate(detection.region_readings):
                    if reading.timestamp >= cutoff_time:
                        self.logger.info(
                            f"    Reading {j}: region={reading.region}, timestamp={reading.timestamp}"
                        )

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

            # Check for objects on main conveyor - only use direct detection within recent timeframe
            current_time = time.time()
            recent_threshold_ms = step_duration_ms  # Within one step

            for readings in recent_detections:
                for reading in readings:
                    time_since_reading_ms = (current_time - reading.timestamp) * 1000
                    if (
                        reading.region == FeederRegion.MAIN_CONVEYOR
                        and time_since_reading_ms < recent_threshold_ms
                    ):
                        self.logger.info(
                            f"MAIN CONVEYOR DETECTED: Object on main conveyor {time_since_reading_ms:.1f}ms ago"
                        )
                        return FeederState.OBJECT_ON_MAIN_CONVEYOR

            # # Check for objects at exit of second feeder that went MIA (likely on main conveyor)
            # current_time = time.time()
            # steps_per_second = self.gc["state_machine_steps_per_second"]
            # step_duration_ms = (1.0 / steps_per_second) * 1000
            # disappearance_threshold_ms = step_duration_ms * 3  # 3 steps worth of time

            # for readings in recent_detections:
            #     exit_readings = [
            #         reading
            #         for reading in readings
            #         if reading.region == FeederRegion.EXIT_OF_SECOND_FEEDER
            #     ]
            #     if exit_readings:
            #         last_exit_time = max(reading.timestamp for reading in exit_readings)
            #         time_since_exit_ms = (current_time - last_exit_time) * 1000

            #         # If object was at exit recently but no readings after, assume it fell onto main conveyor
            #         post_exit_readings = [
            #             reading
            #             for reading in readings
            #             if reading.timestamp > last_exit_time
            #         ]
            #         if not post_exit_readings and time_since_exit_ms < disappearance_threshold_ms:
            #             self.logger.info(f"OBJECT DISAPPEARED: Object at exit {time_since_exit_ms:.1f}ms ago, assuming on main conveyor")
            #             return FeederState.OBJECT_ON_MAIN_CONVEYOR

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

            # Check dropzone first - clear it before dealing with first feeder
            if objects_under_exit_of_first_feeder:
                return FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

            # First feeder empty only if no objects on first feeder AND dropzone is clear
            if not objects_on_first_feeder:
                return FeederState.FIRST_FEEDER_EMPTY

            # Objects on first feeder but not in dropzone
            return FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

        return None
