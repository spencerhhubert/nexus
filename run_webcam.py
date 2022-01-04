import numpy as np
import cv2
import os
import math
import time
from datetime import datetime

def square_crop(img):
	size = min([img.shape[0], img.shape[1]]);
	w_prime = int((img.shape[1]-size)/2);
	h_prime = int((img.shape[0]-size)/2);
	return img[h_prime:(img.shape[0]-h_prime), w_prime:(img.shape[1]-w_prime)]

rate = 100 # how long to wait between frames, in milliseconds

cam = cv2.VideoCapture(0);
res = [cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT)];

os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0');
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=25');

while True:
	input("Press Enter to continue...");
	i = 0
	end = time.time() + 2;
	os.mkdir(f"part_photos/{len(os.listdir('part_photos/'))+1}");
	while time.time() < end:
		ret, frame = cam.read();
		frame = square_crop(frame);
		cur_part = len(os.listdir("part_photos"));
		timestamp = math.floor(datetime.timestamp(datetime.now()));
		outfile = f"part_photos/{cur_part}/part-{cur_part}-{i}.jpg";
		cv2.imwrite(outfile, frame);
		time.sleep(rate/1000);
		i += 1;
