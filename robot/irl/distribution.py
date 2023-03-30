import time
from threading import Thread

#pair is a pair of servo objects
#when is in milliseconds
def openDoors(dm, bin, when:int):

    def _openDoors(dm, bin, when:int):
        #wait n milliseconds until we presume the piece has arrived
        time.sleep(when/1000)
        dm.servo.setAngle(45)
        bin.servo.setAngle(45)
        time.sleep(1.5)
        dm.servo.setAngle(90)
        bin.servo.setAngle(90)

    t = Thread(target=_openDoors, args=(dm, bin, when))
    t.start()
