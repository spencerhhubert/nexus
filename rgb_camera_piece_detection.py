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
scan_cooldown = 1000 #in milliseconds
cooldown = 0
#this should be changed. it should still be a cooldown but instead the cooldown is right after taking a picture, but constantly. constantly be looking, but then wait once the pic is taken

scan_detec_threshold = 1

#Focus control for Logitech C920 on Ubuntu
#Will be switching to more permanent solution later
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0')
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50')

init_frame = np.full((x2-x1, y2-y1), 0) 
last_x_frames = [init_frame]
frames_to_check = 16 

def piece_detected(frame_change):
    if frame_change > scan_detec_threshold or frame_change < (scan_detec_threshold * -1):
        return True
    else:
        return False

#let camera exposure adjust
x_seconds_future = time.time() + 5
while time.time() < x_seconds_future:
    ret, frame = cap.read()
    #cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        break
cv.destroyAllWindows()

if not cap.isOpened():
    print("Cannot open camera")
    exit()
while True:
    #clear frame buffer
    for i in range(4):
        cap.grab()
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break

    color_frame = frame
    grayscale_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    analysis_region = grayscale_frame[y1:y2, x1:x2]
    #cv.imshow('frame', analysis_region)
    
    #frame_change = np.average(np.subtract(init_frame, analysis_region))
    #init_frame = analysis_region

    piece_detected2 = False
    if len(last_x_frames) > frames_to_check:
        last_x_frames.pop(0)
        average_last_x_frames = np.average(np.array(last_x_frames),axis=0)
        frame_change2 = np.average(np.subtract(average_last_x_frames, analysis_region))
        if piece_detected(frame_change2):
            piece_detected2 = True
    else:
        frame_change2 = 0
    
    if piece_detected2 == False:
        last_x_frames.append(analysis_region)

    current_moment = datetime.now()
    timestamp = math.floor(datetime.timestamp(current_moment))
    if cooldown < time.time() and piece_detected(frame_change2):
        cv.imwrite(f'piece_photos/piece-{timestamp}.jpg', color_frame)
        cooldown = time.time() + (scan_cooldown / 1000)
        print("captured")
        #last_x_frames.fill(average_last_x_frames)
    print(f"scan: {timestamp} change: {frame_change2} {piece_detected(frame_change2)}")

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
