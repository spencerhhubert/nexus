import time
import threading
from typing import Dict
from robot.global_config import GlobalConfig
from robot.bin_state_tracker import BinCoordinates
from robot.irl.distribution import DistributionModule
from robot.irl.motors import Servo


class DoorScheduler:
    def __init__(
        self,
        global_config: GlobalConfig,
        distribution_modules: list[DistributionModule],
    ):
        self.global_config = global_config
        self.distribution_modules = distribution_modules
        self.servo_states: Dict[str, str] = {}  # "closed" or "open"
        self.pending_close_threads: Dict[str, threading.Thread] = {}
        self.pending_conveyor_close_times: Dict[
            str, int
        ] = {}  # servo_key -> scheduled_close_time_ms
        self.lock = threading.Lock()

    def _getServoKey(self, dm_idx: int, servo_type: str, bin_idx: int = -1) -> str:
        if servo_type == "conveyor":
            return f"dm_{dm_idx}_conveyor"
        elif servo_type == "bin":
            return f"dm_{dm_idx}_bin_{bin_idx}"
        else:
            raise ValueError(f"Unknown servo type: {servo_type}")

    def _getConveyorServo(self, dm_idx: int) -> Servo:
        assert dm_idx < len(self.distribution_modules), (
            f"Distribution module index {dm_idx} out of range"
        )
        return self.distribution_modules[dm_idx].servo

    def _getBinServo(self, dm_idx: int, bin_idx: int) -> Servo:
        assert dm_idx < len(self.distribution_modules), (
            f"Distribution module index {dm_idx} out of range"
        )
        dm = self.distribution_modules[dm_idx]
        assert bin_idx < len(dm.bins), (
            f"Bin index {bin_idx} out of range for distribution module {dm_idx}"
        )
        return dm.bins[bin_idx].servo

    def _openServo(self, servo_key: str, servo: Servo, open_angle: int) -> None:
        self.global_config["logger"].info(f"Opening servo {servo_key} to {open_angle}°")
        servo.setAngleAndTurnOff(open_angle, 1000)  # Turn off after 1 second

    def _closeServo(
        self, servo_key: str, servo: Servo, close_angle: int, gradual_duration: int = 0
    ) -> None:
        self.global_config["logger"].info(
            f"Closing servo {servo_key} to {close_angle}°"
        )
        if gradual_duration > 0:
            servo.setAngle(close_angle, duration=gradual_duration)
            # Turn off servo after gradual movement completes + 500ms buffer
            turn_off_delay = gradual_duration + 500
            servo.setAngleAndTurnOff(close_angle, turn_off_delay)
        else:
            servo.setAngleAndTurnOff(close_angle, 1000)  # Turn off after 1 second

    def _scheduleServoClose(
        self,
        servo_key: str,
        servo: Servo,
        close_angle: int,
        delay_ms: int,
        gradual_duration: int = 0,
    ) -> threading.Thread:
        def closeAfterDelay():
            time.sleep(delay_ms / 1000.0)

            with self.lock:
                # Only close if this thread is still the active close thread
                if (
                    servo_key in self.pending_close_threads
                    and self.pending_close_threads[servo_key]
                    == threading.current_thread()
                ):
                    if "conveyor" in servo_key:
                        # Conveyor doors close gradually
                        self._closeServo(
                            servo_key, servo, close_angle, gradual_duration
                        )
                        # Add chute fall delay for conveyor doors
                        delay_for_chute_fall_ms = self.global_config[
                            "delay_for_chute_fall_ms"
                        ]
                        time.sleep(delay_for_chute_fall_ms / 1000.0)
                    else:
                        # Bin doors close immediately
                        self._closeServo(servo_key, servo, close_angle)

                    self.servo_states[servo_key] = "closed"
                    del self.pending_close_threads[servo_key]
                    # Clean up conveyor door close time tracking
                    if (
                        "conveyor" in servo_key
                        and servo_key in self.pending_conveyor_close_times
                    ):
                        del self.pending_conveyor_close_times[servo_key]
                    self.global_config["logger"].info(f"Servo {servo_key} closed")

        thread = threading.Thread(target=closeAfterDelay, daemon=True)
        thread.start()
        return thread

    def _scheduleServoAction(
        self,
        servo_key: str,
        servo: Servo,
        open_angle: int,
        close_angle: int,
        delay_ms: int,
    ) -> None:
        def executeAction():
            # Apply delay offset
            delay_ms_adjusted = delay_ms + self.global_config["door_delay_offset_ms"]
            if delay_ms_adjusted < 0:
                self.global_config["logger"].info(
                    "door needs to open too early for offset to apply, using delay of 0"
                )
                delay_ms_adjusted = 0

            if delay_ms_adjusted > 0:
                time.sleep(delay_ms_adjusted / 1000.0)

            current_time_ms = int(time.time() * 1000)
            door_open_duration_ms = self.global_config["door_open_duration_ms"]

            # Check for overlapping conveyor door windows
            if "conveyor" in servo_key:
                overlapping_threshold_ms = self.global_config[
                    "overlapping_conveyor_door_windows_threshold_ms"
                ]
                scheduled_close_time = current_time_ms + door_open_duration_ms

                # Check if this conveyor door has a pending close within the threshold
                with self.lock:
                    if servo_key in self.pending_conveyor_close_times:
                        existing_close_time = self.pending_conveyor_close_times[
                            servo_key
                        ]
                        time_gap = scheduled_close_time - existing_close_time

                        # If the gap is within threshold, extend the existing window
                        if 0 <= time_gap <= overlapping_threshold_ms:
                            self.global_config["logger"].info(
                                f"Extending conveyor door {servo_key} window by {time_gap}ms to avoid close/reopen"
                            )
                            # Update the close time to the new piece's requirement
                            self.pending_conveyor_close_times[servo_key] = (
                                scheduled_close_time
                            )
                            return  # Don't create new action, just extend existing

            with self.lock:
                # Open servo if not already open
                if self.servo_states.get(servo_key) != "open":
                    self._openServo(servo_key, servo, open_angle)
                    self.servo_states[servo_key] = "open"
                    self.global_config["logger"].info(f"Servo {servo_key} opened")
                else:
                    self.global_config["logger"].info(
                        f"Servo {servo_key} already open, extending open time"
                    )

                # Cancel any pending close operation
                if servo_key in self.pending_close_threads:
                    del self.pending_close_threads[servo_key]

                # Schedule new close operation
                if "conveyor" in servo_key:
                    # Track the scheduled close time for conveyor doors
                    self.pending_conveyor_close_times[servo_key] = (
                        current_time_ms + door_open_duration_ms
                    )
                    close_thread = self._scheduleServoClose(
                        servo_key, servo, close_angle, door_open_duration_ms, 500
                    )
                else:
                    # Bin door waits for conveyor close (500ms) + chute fall (1000ms) after door_open_duration
                    delay_for_chute_fall_ms = self.global_config[
                        "delay_for_chute_fall_ms"
                    ]
                    bin_close_delay_ms = (
                        door_open_duration_ms + 500 + delay_for_chute_fall_ms
                    )
                    close_thread = self._scheduleServoClose(
                        servo_key, servo, close_angle, bin_close_delay_ms
                    )

                self.pending_close_threads[servo_key] = close_thread

        thread = threading.Thread(target=executeAction, daemon=True)
        thread.start()

    def scheduleDoorAction(
        self, bin_coordinates: BinCoordinates, delay_ms: int = 0
    ) -> None:
        dm_idx = bin_coordinates["distribution_module_idx"]
        bin_idx = bin_coordinates["bin_idx"]

        # Schedule conveyor door action
        conveyor_servo_key = self._getServoKey(dm_idx, "conveyor")
        conveyor_servo = self._getConveyorServo(dm_idx)
        conveyor_open_angle = self.global_config["conveyor_door_open_angle"]
        conveyor_close_angle = self.global_config["conveyor_door_closed_angle"]

        self._scheduleServoAction(
            conveyor_servo_key,
            conveyor_servo,
            conveyor_open_angle,
            conveyor_close_angle,
            delay_ms,
        )

        # Schedule bin door action
        bin_servo_key = self._getServoKey(dm_idx, "bin", bin_idx)
        bin_servo = self._getBinServo(dm_idx, bin_idx)
        bin_open_angle = self.global_config["bin_door_open_angle"]
        bin_close_angle = self.global_config["bin_door_closed_angle"]

        self._scheduleServoAction(
            bin_servo_key, bin_servo, bin_open_angle, bin_close_angle, delay_ms
        )

        self.global_config["logger"].info(
            f"Scheduled door action for bin {bin_coordinates} with delay {delay_ms}ms"
        )
