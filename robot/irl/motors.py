from pyfirmata import Arduino, util, PWM
import time
from typing import Dict, Any, List, Optional, cast

class PCA9685:
    def __init__(self, dev: Arduino, addr: int):
        self.dev = dev
        self.addr = addr
        dev.send_sysex(0x01, [0x07, self.addr])

class Servo:
    def __init__(self, channel: int, dev: PCA9685):
        self.channel = channel
        self.dev = dev

    def setAngle(self, angle: int) -> None:
        print(f"Setting servo on channel {self.channel} and board {self.dev.addr} to {angle} degrees")
        data = [0x08, self.dev.addr, self.channel, util.to_two_bytes(angle)[0], util.to_two_bytes(angle)[1]]
        self.dev.dev.send_sysex(0x01, data)