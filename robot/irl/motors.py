from pyfirmata import util
import time
import threading
from typing import Dict, Any, List, Optional, cast
from robot.global_config import GlobalConfig
from robot.irl.our_arduino import OurArduinoMega
from robot.irl.encoder import Encoder


class PCA9685:
    def __init__(self, gc: GlobalConfig, dev: OurArduinoMega, addr: int):
        self.gc = gc
        self.dev = dev
        self.addr = addr
        dev.sysex(0x01, [0x07, self.addr])


class Servo:
    def __init__(self, gc: GlobalConfig, channel: int, dev: PCA9685):
        self.gc = gc
        self.channel = channel
        self.dev = dev
        self._current_angle = 0

    def setAngle(self, angle: int, duration: Optional[int] = None) -> None:
        if duration is None:
            self.gc["logger"].info(
                f"Setting servo on channel {self.channel} and board {self.dev.addr} to {angle} degrees"
            )
            data = [
                0x08,
                self.dev.addr,
                self.channel,
                util.to_two_bytes(angle)[0],
                util.to_two_bytes(angle)[1],
            ]
            self.dev.dev.sysex(0x01, data)
            self._current_angle = angle
        else:
            self._setAngleGradually(angle, duration)

    def _setAngleGradually(
        self, target_angle: int, duration_ms: int, step_delay_ms: int = 50
    ) -> None:
        current_angle = self._current_angle

        total_steps = max(1, duration_ms // step_delay_ms)
        angle_step = (target_angle - current_angle) / total_steps

        self.gc["logger"].info(
            f"Moving servo on channel {self.channel} from {current_angle} to {target_angle} degrees over {duration_ms}ms"
        )

        for step in range(total_steps):
            intermediate_angle = int(current_angle + (angle_step * step))
            data = [
                0x08,
                self.dev.addr,
                self.channel,
                util.to_two_bytes(intermediate_angle)[0],
                util.to_two_bytes(intermediate_angle)[1],
            ]
            self.dev.dev.sysex(0x01, data)
            time.sleep(step_delay_ms / 1000.0)

        # Ensure we end at the exact target angle
        data = [
            0x08,
            self.dev.addr,
            self.channel,
            util.to_two_bytes(target_angle)[0],
            util.to_two_bytes(target_angle)[1],
        ]
        self.dev.dev.sysex(0x01, data)
        self._current_angle = target_angle

    def turnOff(self) -> None:
        self.gc["logger"].info(
            f"Turning off servo on channel {self.channel} and board {self.dev.addr}"
        )
        data = [
            0x09,
            self.dev.addr,
            self.channel,
        ]
        self.dev.dev.sysex(0x01, data)

    def setAngleAndTurnOff(self, angle: int, turn_off_delay_ms: int) -> None:
        self.setAngle(angle)

        def turnOffAfterDelay():
            time.sleep(turn_off_delay_ms / 1000.0)
            self.turnOff()

        thread = threading.Thread(target=turnOffAfterDelay, daemon=True)
        thread.start()


class DCMotor:
    def __init__(
        self,
        gc: GlobalConfig,
        dev: OurArduinoMega,
        enable_pin: int,
        input_1_pin: int,
        input_2_pin: int,
    ):
        self.gc = gc
        self.dev = dev
        self.enable_pin = enable_pin
        self.input_1_pin = input_1_pin
        self.input_2_pin = input_2_pin
        self.current_speed: Optional[int] = None

        logger = gc["logger"]
        logger.info(f"Setting pin {self.input_1_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_1_pin, 1])
        logger.info(f"Setting pin {self.input_2_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_2_pin, 1])
        logger.info(f"Setting pin {self.enable_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.enable_pin, 1])

    def setSpeed(self, speed: int, override: bool = False) -> None:
        original_speed = speed
        speed = max(-255, min(255, speed))

        if self.current_speed == speed and not override:
            logger = self.gc["logger"]
            logger.info(
                f"DCMotor setSpeed: speed unchanged at {speed}, skipping command"
            )
            return

        logger = self.gc["logger"]
        logger.info(f"DCMotor setSpeed: requested={original_speed}, clamped={speed}")
        logger.info(
            f"Using pins: enable={self.enable_pin}, input1={self.input_1_pin}, input2={self.input_2_pin}"
        )

        if speed > 0:
            logger.info("Setting FORWARD: IN1=HIGH, IN2=LOW")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 1])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 0])
        elif speed < 0:
            logger.info("Setting REVERSE: IN1=LOW, IN2=HIGH")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 0])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 1])
        else:
            logger.info("Setting STOP: IN1=LOW, IN2=LOW")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 0])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 0])

        pwm_value = int(abs(speed))
        logger.info(f"Setting enable pin {self.enable_pin} to PWM value: {pwm_value}")
        self.dev.sysex(0x03, [0x03, self.enable_pin, pwm_value])

        self.current_speed = speed

    def backstop(
        self, currentSpeed: int, backstopSpeed: int = 75, backstopDurationMs: int = 10
    ) -> None:
        DO_BACKSTOP = True
        if not DO_BACKSTOP:
            self.setSpeed(0)
            return
        backstopSpeed = max(-255, min(255, backstopSpeed))

        if currentSpeed > 0:
            backstopDirection = -backstopSpeed
        elif currentSpeed < 0:
            backstopDirection = backstopSpeed
        else:
            return

        self.setSpeed(backstopDirection)
        time.sleep(backstopDurationMs / 1000.0)
        self.setSpeed(0)


class BreakBeamSensor:
    def __init__(self, gc: GlobalConfig, dev: OurArduinoMega, sensor_pin: int):
        self.gc = gc
        self.dev = dev
        self.sensor_pin = sensor_pin
        self.last_query_timestamp = 0

        logger = gc["logger"]
        logger.info(f"Setting up break beam sensor on pin {sensor_pin}")

        self.last_break_timestamp = -1
        self.last_query_timestamp = int(time.time() * 1000)

        self.dev.add_cmd_handler(0x60, self._onBreakBeamResponse)
        self.dev.sysex(0x60, [0x01, sensor_pin])

        time.sleep(0.1)
        logger.info(f"Break beam sensor initialized on pin {sensor_pin}")

    def queryBreakings(self, since_timestamp: int) -> tuple[int, int, bool]:
        timestamp_bytes = [
            (since_timestamp >> 0) & 0x7F,
            (since_timestamp >> 7) & 0x7F,
            (since_timestamp >> 14) & 0x7F,
            (since_timestamp >> 21) & 0x7F,
            (since_timestamp >> 28) & 0x7F,
        ]

        self.gc["logger"].info(
            f"Sending break beam query: since_timestamp={since_timestamp}, bytes={timestamp_bytes}"
        )

        self.dev.sysex(0x60, [0x02] + timestamp_bytes)
        time.sleep(0.02)

        if (
            hasattr(self, "last_break_timestamp")
            and hasattr(self, "last_query_timestamp")
            and hasattr(self, "current_break_state")
        ):
            self.gc["logger"].info(
                f"Break beam query result: break={self.last_break_timestamp}, latest={self.last_query_timestamp}, currently_broken={self.current_break_state}"
            )
            return (
                self.last_break_timestamp,
                self.last_query_timestamp,
                self.current_break_state,
            )
        else:
            fallback_time = int(time.time() * 1000)
            self.gc["logger"].info(
                f"No break beam response yet, returning fallback: (-1, {fallback_time}, False)"
            )
            return (-1, fallback_time, False)

    def _onBreakBeamResponse(self, *args):
        self.gc["logger"].info(
            f"Break beam response received: {len(args)} args = {list(args)}"
        )

        # Firmata converts each byte to two 7-bit values, so we expect 22 args (11 bytes * 2)
        if len(args) >= 22:
            # Extract the actual bytes from the doubled format: [val, 0, val, 0, ...]
            actual_bytes = [args[i] for i in range(0, 22, 2)]
            self.gc["logger"].info(f"Extracted bytes: {actual_bytes}")

            # Reconstruct timestamps from 7-bit bytes
            break_timestamp = (
                actual_bytes[0]
                | (actual_bytes[1] << 7)
                | (actual_bytes[2] << 14)
                | (actual_bytes[3] << 21)
                | (actual_bytes[4] << 28)
            )
            latest_timestamp = (
                actual_bytes[5]
                | (actual_bytes[6] << 7)
                | (actual_bytes[7] << 14)
                | (actual_bytes[8] << 21)
                | (actual_bytes[9] << 28)
            )
            current_break_state = actual_bytes[10] == 0  # 0 = broken, 1 = unbroken

            self.gc["logger"].info(
                f"Reconstructed: break={break_timestamp}, latest={latest_timestamp}, currently_broken={current_break_state}"
            )

            # Check for "no break found" sentinel value
            if break_timestamp == 0xFFFFFFFF:
                self.gc["logger"].info(
                    "Break timestamp is sentinel value 0xFFFFFFFF, converting to -1"
                )
                break_timestamp = -1

            self.last_break_timestamp = break_timestamp
            self.last_query_timestamp = latest_timestamp
            self.current_break_state = current_break_state
        else:
            self.gc["logger"].warning(
                f"Break beam response too short: got {len(args)} args, expected 22"
            )
