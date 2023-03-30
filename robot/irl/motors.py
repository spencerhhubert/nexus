from pyfirmata import Arduino, util, PWM
from threading import Thread
import time
from robot.utils import toHex

class Stepper:
    def __init__(self, dir_pin:int, step_pin:int, microstep:int, dev:Arduino, dev_num:int):
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.microstep = microstep
        self.dev = dev
        self.running = False
        self.dev_num = dev_num
        #data = [0x01, toHex(dev_num), toHex(dir_pin), toHex(step_pin), util.to_two_bytes(steps_per_rev)[0], util.to_two_bytes(steps_per_rev)[1]]
        #dev.send_sysex(0x02, data)

    def runWithAccelStepper(self, dir:bool, rpm:int):
        print(f"Running stepper on pin {self.step_pin} at {rpm} RPM")
        self.running = True
        data = [0x02, toHex(self.dev_num), util.to_two_bytes(rpm)[0], util.to_two_bytes(rpm)[1], toHex(dir)]
        self.dev.send_sysex(0x02, data)
        time.sleep(0.1) #wait for microcontroller to process command

    def stopAccelStepper(self):
        self.running = False
        data = [3, self.dev_num]
        data = list(map(toHex, data))
        self.dev.send_sysex(0x02, data)

    def run(self, dir:bool, sps):
        self.running = True
        self.dev.digital[self.dir_pin].write(dir)
        t = Thread(target=self._run, args=(sps,))
        t.start()

    def _run(self, sps:int):
        #delay in seconds, given steps per second and steps per revolution
        delay = 1 / (sps * self.microstep)

        #this is hell. so many weird properties with stepper motors. need ultra clean super fast signals otherwise they bug out like crazy
        #serial is not good for this lol
        #going to redo with regular dc motor in v2 circuit
        while self.running:
            self.dev.digital[self.step_pin].write(1)
            #self.dev.pass_time(delay)
            #time.sleep(delay)
            self.dev.digital[self.step_pin].write(0)
            #self.dev.pass_time(delay)
            #time.sleep(delay)

    def step(self, dir:bool, speed:int, steps:int):
        delay = 60e6 / (self.steps_per_rev * speed)
        self.dev.digital[self.dir_pin].write(dir)
        for i in range(steps):
            self.dev.digital[self.step_pin].write(1)
            self.dev.pass_time(delay)
            self.dev.digital[self.step_pin].write(0)
            self.dev.pass_time(delay)

class VibrationMotor:
    def __init__(self, pwm_pin:int, dev:Arduino):
        self.pwd_pin = pwm_pin
        self.dev = dev
        dev.digital[pwm_pin].mode = PWM

    def run(self, speed:int):
        self.dev.analog[self.pwd_pin].write(speed)

class PCA9685:
    def __init__(self, dev:Arduino, addr:int):
        self.dev = dev
        self.addr = hex(addr)
        self.addr = int(self.addr, 16)
        dev.send_sysex(0x01, [0x07, self.addr])

class Servo:
    def __init__(self, channel:int, dev:PCA9685):
        self.channel = channel
        self.dev = dev

    def setAngle(self, angle:int):
        print(f"Setting servo on channel {self.channel} and board {self.dev.addr} to {angle} degrees")
        data = [0x08, self.dev.addr, self.channel, util.to_two_bytes(angle)[0], util.to_two_bytes(angle)[1]]
        self.dev.dev.send_sysex(0x01, data)

