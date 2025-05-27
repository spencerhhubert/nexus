from pyfirmata import ArduinoMega, util, PWM, OUTPUT
import time
from typing import Dict, Any, List, Optional, cast


class PCA9685:
    def __init__(self, dev: ArduinoMega, addr: int):
        self.dev = dev
        self.addr = addr
        dev.send_sysex(0x01, [0x07, self.addr])


class Servo:
    def __init__(self, channel: int, dev: PCA9685):
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
    def __init__(self, dev: ArduinoMega, enable_pin: int, input_1_pin: int, input_2_pin: int):
        self.dev = dev
        self.enable_pin = enable_pin
        self.input_1_pin = input_1_pin
        self.input_2_pin = input_2_pin

        self.dev.digital[self.input_1_pin].mode = OUTPUT
        self.dev.digital[self.input_2_pin].mode = OUTPUT
        self.dev.digital[self.enable_pin].mode = PWM

    def setSpeed(self, speed: int) -> None:
        speed = max(-255, min(255, speed))

        if speed > 0:
            self.dev.digital[self.input_1_pin].write(1)
            self.dev.digital[self.input_2_pin].write(0)
        elif speed < 0:
            self.dev.digital[self.input_1_pin].write(0)
            self.dev.digital[self.input_2_pin].write(1)
        else:
            self.dev.digital[self.input_1_pin].write(0)
            self.dev.digital[self.input_2_pin].write(0)

        pwm_value = abs(speed) / 255.0
        self.dev.digital[self.enable_pin].write(pwm_value)
