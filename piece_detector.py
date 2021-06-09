import numpy as np
import cv2 as cv
from datetime import datetime
import math
import time
import os

cap = cv.VideoCapture(0)
resolution = [cap.get(cv.CAP_PROP_FRAME_WIDTH), cap.get(cv.CAP_PROP_FRAME_HEIGHT)]
#analysis region resolution
AX1, AX2, AY1, AY2 = int((resolution[0] // 10) * 4), int((resolution[0] // 10) * 6), int(0), int(resolution[1])

#Focus control for Logitech C920 on Ubuntu
#Will be switching to more permanent solution later
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0')
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50')

#let camera exposure adjust
x_seconds_from_now = time.time() + 5
while time.time() < x_seconds_from_now:
    ret, frame = cap.read()
    #cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        break
cv.destroyAllWindows()

def blank_analysis_region():
    return np.full((AY2-AY1, AX2-AX1), 0)

def diff_frame(frame1, frame2):
    return np.subtract(frame1, frame2)

def avg_frame(frames_arr):
    return np.average(np.array(frames_arr), axis=0)

def frame_avg_val(frame):
    return np.average(frame)

def frame_root_mean_sqr(frame):
    return np.sqrt(np.mean(frame**2))

def clear_buffer():
    for i in range(4):
        cap.grab()

def timestamp():
    current_moment = datetime.now()
    timestamp = math.floor(datetime.timestamp(current_moment))
    return timestamp

def display_w_rect(source_frame):
    cv.rectangle(source_frame,     # source image
              (AX1, AY1),          # upper left corner vertex
              (AX2, AY2),         # lower right corner vertex
              (0, 255, 0),        # color
              thickness=2,        # line thickness
              lineType=cv.LINE_8  # line type
    )
    cv.imshow("Piece Scanner View", source_frame)

def trim_avg_frames(frames_arr):
    if len(frames_arr) >= frames_avgd + 1:
        print("trimmed")
        return frames_arr.pop(0)
    else:
        return frames_arr

def avg_frames_ready(prev_frames):
    if (len(prev_frames)) < (frames_avgd):
        return False
    else:
        return True

def record_frame(frame):
    cv.imwrite(f'piece_photos/piece-{timestamp()}.jpg', frame)

def piece_detected(scan, prev_frames):
    avg_frame_change = frame_root_mean_sqr(diff_frame(avg_frame(prev_frames), scan))
    print(math.floor(avg_frame_change))
    if abs(avg_frame_change) > detection_threshold:
        return True
    else:
        return False

cooldown = 8 #in frames
current_cooldown = 0
detection_threshold = 10
prev_frames = [blank_analysis_region()]
frames_avgd = 16 

if not cap.isOpened():
    print("Cannot open camera")
    exit()

while True:
    clear_buffer()
    #initialize frame
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    grayscale_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    analysis_region = grayscale_frame[AY1:AY2, AX1:AX2]
    print(f"length: {len(prev_frames)}")
    print("scan")
    if avg_frames_ready(prev_frames):
        if current_cooldown < 1:
            if piece_detected(analysis_region, prev_frames):
                record_frame(frame)
                print("captured")
                #create new piece object
                for i in range(2):
                    del prev_frames[len(prev_frames) - 1]
                del prev_frames[0]
                current_cooldown = cooldown
                #prev_frames = [blank_analysis_region()]
            prev_frames.append(analysis_region)
        else:
            current_cooldown -= 1
    else:
        prev_frames.append(analysis_region)
    
    #prev_frames = trim_avg_frames(prev_frames)
    if len(prev_frames) > frames_avgd:
        del prev_frames[len(prev_frames) - 1]
    display_w_rect(frame)

    if cv.waitKey(1) == ord('q'):
        break

cap.release()
cv.destroyAllWindows()
