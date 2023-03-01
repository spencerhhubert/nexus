import cv2
import numpy as np
import time
import os

def takePicEveryNms(cam, n, path, how_long):
    end = time.time() + how_long
    i = 0
    while time.time() < end:
        ret, img = cam.read()
        cv2.imwrite(path + str(i) + '.jpg', img)
        i += 1
        time.sleep(n/1000.0)

#take pics for n ms (burst) and then pause for n ms
def takePicInBurst(cam, path, pause_time, burst_time, fps):
    burst_number = 0
    while True:
        print("Beginning burst in three seconds")
        time.sleep(3)
        end = (time.time()*1000) + burst_time
        i = 0
        while (time.time()*1000) < end:
            ret, img = cam.read()
            cv2.imwrite(path + str(burst_number) + '_' + str(i) + '.jpg', img)
            i += 1
            time.sleep((1000/fps)/1000)
        print("Burst complete")
        time.sleep(pause_time/1000.0)
        burst_number += 1

if __name__ == '__main__':
    cam = cv2.VideoCapture(0)
    res = [cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT)]
    os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0');
    os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50');
    # let exposure and white balance adjust
    stop = time.time() + 5;
    while time.time() < stop:
        ret, frame = cam.read();
    #pause for 5 seconds and do 2.5 second bursts of pics
    takePicInBurst(cam, 'data/source/', 5000, 2500, 2)
