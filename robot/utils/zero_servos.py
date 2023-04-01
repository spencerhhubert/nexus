from robot.irl.motors import Servo, PCA9685
from pyfirmata import Arduino, util
import time

#iterate over doors to set them to the right angles and make sure they work

#will need to customize this per setup
#todo in the future, make a bunch of these scripts and make them general

mc = Arduino("/dev/ttyACM0")
controllers = [PCA9685(mc, 0x40), PCA9685(mc, 0x41), PCA9685(mc, 0x42)]

#bin doors
servos = []
for controller in controllers:
    for i in range(4):
        servos.append(Servo(i, controller))

for servo in servos:
    servo.setAngle(135)
    time.sleep(0.5)

for servo in servos:
    servo.setAngle(170)
    time.sleep(0.5)

#chute doors
servos = []
for controller in controllers:
    servos.append(Servo(15, controller))

for servo in servos:
    servo.setAngle(135)
    time.sleep(0.5)

for servo in servos:
    servo.setAngle(90)
    time.sleep(0.5)
