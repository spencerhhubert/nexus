from pyfirmata import util, PWM, OUTPUT
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

    def setAngle(self, angle: int) -> None:
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


class DCMotor:
    def __init__(self, gc: GlobalConfig, dev: OurArduinoMega, enable_pin: int, input_1_pin: int, input_2_pin: int):
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
        logger.info(f"Using pins: enable={self.enable_pin}, input1={self.input_1_pin}, input2={self.input_2_pin}")

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
