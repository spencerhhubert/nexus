from pyfirmata import Arduino, util, PWM
from threading import Thread

class Stepper:
    def __init__(self, dir_pin:int, step_pin:int, steps_per_rev:int, dev:Arduino):
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.steps_per_rev = steps_per_rev
        self.dev = dev
        self.running = False

    def run(self, dir:bool, rpm:int):
        self.running = True
        self.dev.digital[self.dir_pin].write(dir)
        t = Thread(target=self._run, args=(rpm,))
        t.start()

    def _run(self, rpm:int):
        delay = 0
        while self.running:
            self.dev.digital[self.step_pin].write(1)
            self.dev.pass_time(delay)
            self.dev.digital[self.step_pin].write(0)
            self.dev.pass_time(delay)

    def stop(self):
        self.running = False

    def restart(self):
        self.running = True

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
        dev.send_sys_ex(0x01, 0x07, self.addr)

class Servo:
    def __init__(self, channel:int, dev:PCA9685):
        self.channel = channel
        self.dev = dev

    def setAngle(self, angle:int):
        self.dev.dev.send_sys_ex(0x01, 0x08, self.dev.addr, self.channel, util.to_two_bytes(angle)[0], util.to_two_bytes(angle)[1])
