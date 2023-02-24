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

if __name__ == '__main__':
    cam = cv2.VideoCapture(0)
    res = [cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT)]
    os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0');
    os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50');
    # let exposure and white balance adjust
    stop = time.time() + 5;
    while time.time() < stop:
        ret, frame = cam.read();
    takePicEveryNms(cam, 1000, 'data/', 10*60)
