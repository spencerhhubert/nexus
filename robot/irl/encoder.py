import time
import math
from typing import Optional
from robot.global_config import GlobalConfig
from robot.irl.our_arduino import OurArduinoMega


class Encoder:
    def __init__(
        self,
        gc: GlobalConfig,
        dev: OurArduinoMega,
        clk_pin: int,
        dt_pin: int,
        pulses_per_revolution: int,
        wheel_diameter_mm: float,
    ):
        self.gc = gc
        self.dev = dev
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.pulses_per_revolution = pulses_per_revolution
        self.wheel_diameter_cm = wheel_diameter_mm / 10
        self.wheel_circumference_cm = math.pi * self.wheel_diameter_cm

        self.last_encoder_position = 0

        logger = gc["logger"]
        logger.info(f"Setting up encoder with CLK={self.clk_pin}, DT={self.dt_pin}")

        self.dev.add_cmd_handler(0x50, self._onEncoderResponse)
        self.dev.sysex(0x50, [0x01, self.clk_pin, self.dt_pin])

        time.sleep(0.1)

        logger.info(
            f"Encoder initialized: CLK={clk_pin}, DT={dt_pin}, PPR={pulses_per_revolution}, wheel_diameter={self.wheel_diameter_cm}cm"
        )

    def requestLivePosition(self) -> None:
        self.dev.sysex(0x50, [0x02])

    def getCachedPosition(self) -> int:
        return self.last_encoder_position

    def resetPulseCount(self) -> None:
        self.dev.sysex(0x50, [0x03])
        self.last_encoder_position = 0

    def getPulsesPerRevolution(self) -> int:
        return self.pulses_per_revolution

    def getWheelCircumferenceCm(self) -> float:
        return self.wheel_circumference_cm

    def _onEncoderResponse(self, *args):
        if len(args) >= 4:
            position = args[0] | (args[2] << 7)
            self.last_encoder_position = position
