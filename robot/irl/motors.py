from pyfirmata import ArduinoMega, util, PWM, OUTPUT
import time
from typing import Dict, Any, List, Optional, cast
from robot.global_config import GlobalConfig


class PCA9685:
    def __init__(self, global_config: GlobalConfig, dev: ArduinoMega, addr: int):
        self.global_config = global_config
        self.dev = dev
        self.addr = addr
        dev.send_sysex(0x01, [0x07, self.addr])


class Servo:
    def __init__(self, global_config: GlobalConfig, channel: int, dev: PCA9685):
        self.global_config = global_config
        self.channel = channel
        self.dev = dev

    def setAngle(self, angle: int) -> None:
        print(
            f"Setting servo on channel {self.channel} and board {self.dev.addr} to {angle} degrees"
        )
        data = [
            0x08,
            self.dev.addr,
            self.channel,
            util.to_two_bytes(angle)[0],
            util.to_two_bytes(angle)[1],
        ]
        self.dev.dev.send_sysex(0x01, data)


class DCMotor:
    def __init__(self, global_config: GlobalConfig, dev: ArduinoMega, enable_pin: int, input_1_pin: int, input_2_pin: int):
        self.global_config = global_config
        self.debug_level = global_config["debug_level"]
        self.dev = dev
        self.enable_pin = enable_pin
        self.input_1_pin = input_1_pin
        self.input_2_pin = input_2_pin

        # Use sysex commands to set pin modes (OUTPUT = 1)
        if self.debug_level > 0:
            print(f"Setting pin {self.input_1_pin} to OUTPUT via sysex")
        self.dev.send_sysex(0x02, [0x01, self.input_1_pin, 1])
        if self.debug_level > 0:
            print(f"Setting pin {self.input_2_pin} to OUTPUT via sysex")
        self.dev.send_sysex(0x02, [0x01, self.input_2_pin, 1])
        # Set enable pin to PWM mode for speed control via sysex
        if self.debug_level > 0:
            print(f"Setting pin {self.enable_pin} to PWM via sysex")
        self.dev.send_sysex(0x02, [0x01, self.enable_pin, 3])  # mode 3 = PWM



    def setSpeed(self, speed: int) -> None:
        original_speed = speed
        speed = max(-255, min(255, speed))
        
        if self.debug_level > 0:
            print(f"DCMotor setSpeed: requested={original_speed}, clamped={speed}")
            print(f"  Using pins: enable={self.enable_pin}, input1={self.input_1_pin}, input2={self.input_2_pin}")

        if speed > 0:
            if self.debug_level > 0:
                print(f"  Setting FORWARD: IN1=HIGH, IN2=LOW")
            self.dev.send_sysex(0x02, [0x02, self.input_1_pin, 1])
            self.dev.send_sysex(0x02, [0x02, self.input_2_pin, 0])
        elif speed < 0:
            if self.debug_level > 0:
                print(f"  Setting REVERSE: IN1=LOW, IN2=HIGH")
            self.dev.send_sysex(0x02, [0x02, self.input_1_pin, 0])
            self.dev.send_sysex(0x02, [0x02, self.input_2_pin, 1])
        else:
            if self.debug_level > 0:
                print(f"  Setting STOP: IN1=LOW, IN2=LOW")
            self.dev.send_sysex(0x02, [0x02, self.input_1_pin, 0])
            self.dev.send_sysex(0x02, [0x02, self.input_2_pin, 0])

        pwm_value = int(abs(speed))
        if self.debug_level > 0:
            print(f"  Setting enable pin {self.enable_pin} to PWM value: {pwm_value}")
        self.dev.send_sysex(0x02, [0x03, self.enable_pin, pwm_value])
        if self.debug_level > 0:
            print(f"  DCMotor setSpeed complete")
