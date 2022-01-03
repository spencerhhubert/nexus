import numpy as np
import cv2 as cv
from datetime import datetime
import math
import time
import os

cap = cv.VideoCapture(0)
resolution = [cap.get(cv.CAP_PROP_FRAME_WIDTH), cap.get(cv.CAP_PROP_FRAME_HEIGHT)]
width_prime = resolution[0] // 10
x1 = int(width_prime * 4)
x2 = int(width_prime * 6)
y1 = int(0)
y2 = int(resolution[1])

#Focus control for Logitech C920 on Ubuntu
#Will be switching to more permanent solution later
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0')
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50')

#let camera exposure adjust
x_seconds_future = time.time() + 5
while time.time() < x_seconds_future:
    ret, frame = cap.read()
    #cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        break
cv.destroyAllWindows()

def piece_detected(frame_change):
    if frame_change > scan_detec_threshold or frame_change < (scan_detec_threshold * -1):
        return True
    else:
        return False

def blank_frame():
    return np.full((y2-y1, x2-x1), 0)

scan_cooldown = 1000 #in milliseconds
current_cooldown = 0
scan_detec_threshold = 1

prev_frames = [blank_frame()]
frames_averaged = 16
average_frame = blank_frame()

if not cap.isOpened():
    print("Cannot open camera")
    exit()
while True:
    #clear frame buffer
    for i in range(4):
        cap.grab()
    #initialize the frame
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    color_frame = frame
    grayscale_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    if current_cooldown < time.time():
        analysis_region = grayscale_frame[y1:y2, x1:x2]
    else:
        analysis_region = average_frame

    if len(prev_frames) >= frames_averaged:
        average_frame = np.average(np.array(prev_frames),axis=0)
        frame_change = np.average(np.subtract(average_frame, analysis_region))
        prev_frames.pop(0)
    else:
        frame_change = 0

    current_moment = datetime.now()
    timestamp = math.floor(datetime.timestamp(current_moment))
    if piece_detected(frame_change):
        current_cooldown = time.time() + (scan_cooldown / 1000)
        prev_frames.append(average_frame)
        cv.imwrite(f'piece_photos/piece-{timestamp}.jpg', color_frame)
        print("captured")
    else:
        prev_frames.append(analysis_region)

    print(f"scan: {timestamp} change: {frame_change} {piece_detected(frame_change)}")

    imageRectangle = color_frame
    cv.rectangle(imageRectangle,     # source image
              (x1, y1),          # upper left corner vertex
              (x2, y2),         # lower right corner vertex
              (0, 255, 0),        # color
              thickness=2,        # line thickness
              lineType=cv.LINE_8  # line type
    )
    cv.imshow("rectangle", imageRectangle)

    if cv.waitKey(1) == ord('q'):
        break

cap.release()
cv.destroyAllWindows()
