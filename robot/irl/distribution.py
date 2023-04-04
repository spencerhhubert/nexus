import time
from threading import Thread

#pair is a pair of servo objects
#when is in milliseconds
def openDoors(dm, bin, when:int):

    def _openDoors(dm, bin, when:int):
        #wait n milliseconds until we presume the piece has arrived
        wait = 7
        time.sleep(when/1000)
        dm.servo.setAngle(135)
        time.sleep(0.25)
        bin.servo.setAngle(135)
        time.sleep(wait)
        dm.servo.setAngle(95)
        time.sleep(0.25)
        bin.servo.setAngle(170)
        time.sleep(0.25)

    t = Thread(target=_openDoors, args=(dm, bin, when))
    t.start()
