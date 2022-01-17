import numpy as np
import cv2
import os
import math
import time
from datetime import datetime
import torch
import inference

def square_crop(img):
	size = min([img.shape[0], img.shape[1]]);
	w_prime = int((img.shape[1]-size)/2);
	h_prime = int((img.shape[0]-size)/2);
	return img[h_prime:(img.shape[0]-h_prime), w_prime:(img.shape[1]-w_prime)]

def cur_part_path():
	if primed:
		#num = len(os.listdir(outpath))+1;
		#num += 1;
		if len(os.listdir(outpath)) > 0:
			num = int( sorted( map( int, os.listdir(outpath) ) )[len(os.listdir(outpath))-1] ) + 1;
		else:
			num = 0;
		os.mkdir(os.path.join(outpath, str(num)))
	else:
		#num = len(os.listdir(outpath));
		num = int( sorted( map( int, os.listdir(outpath) ) )[len(os.listdir(outpath))-1] );
	return os.path.join(outpath, str(num), f"part-{num}-{i}");

def all_in_frame(img, box):
	threshold = 10
	if box[1] <  threshold or box[3] > img.shape[1] - threshold:
		return False
	else:
		return True

rate = 60 # how long to wait between frames, in milliseconds, 60 should be about 15fps

cam = cv2.VideoCapture(0);
res = [cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT)];

os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0');
os.system('v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50');

# let exposure and white balance adjust
stop = time.time() + 5;
while time.time() < stop:
	ret, frame = cam.read();

primed = False;

outpath = 'part_photos';
if len(os.listdir(outpath)) > 0:
	num = int( sorted( map( int, os.listdir(outpath) ) )[len(os.listdir(outpath))-1] ) + 1;
else:
	num = 0;
#os.mkdir(os.path.join(outpath, str(num)));

model = torch.load('trained_model6.pth')
model.eval()

# check frame 15 times a second
# every check, if piece present, check where it goes
# if piece present, check if prime_time was over a second ago. if it was, set primed to true.
# it goes to existing folder if primed false
# make new folder if primed true
prime_time = inference.cur_time()
i=0
while True:
	for j in range(4):
		cam.grab();
	ret, frame = cam.read();
	frame = square_crop(frame);
	#frame = cv2.resize(frame, None, fx=1.5, fy=1.5)
	img = frame	
	img = inference.resize(img);
	mask, box, prediction, score = inference.evaluate(model, inference.prep_img(img));
	timeout = 3000 # in ms
	if inference.cur_time() > prime_time+timeout:
		primed = True;
	else:
		primed = False;
	if score > 0.9:
		print(f"piece found, score = {score}")
		#cv2.imwrite(cur_part_path()+"-not-cropped.jpg", img)
		cur_part_path() # need a little rewrite so this doesn't need to be called. it needs to be called because if a piece isn't in the frame entirely, primed gets changed before a new directory can be made
		if all_in_frame(img, box):
			cropped = inference.crop(img, mask, box);
			cv2.imwrite(cur_part_path()+".jpg", cropped);
			i += 1;
		if primed:
			prime_time = inference.cur_time();
			i = 0
	#time.sleep(rate/1000);
