from pyfirmata import util
import time
from typing import Dict, Any, List, Optional, cast
from robot.global_config import GlobalConfig
from robot.irl.our_arduino import OurArduinoMega


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

        logger = gc["logger"]
        logger.info(f"Setting pin {self.input_1_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_1_pin, 1])
        logger.info(f"Setting pin {self.input_2_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_2_pin, 1])
        logger.info(f"Setting pin {self.enable_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.enable_pin, 1])

    def setSpeed(self, speed: int) -> None:
        original_speed = speed
        speed = max(-255, min(255, speed))

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
