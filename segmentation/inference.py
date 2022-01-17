import os
import numpy as np
import torch
import torch.quantization
import torch.nn as nn
from PIL import Image
# where much of the setup actually occurs
from setup_model import *
from torchvision import transforms
from torch.autograd import Variable
import cv2

def resize(img):
	return cv2.resize(img, dsize=(480,480), interpolation=cv2.INTER_CUBIC)

def prep_img(img):
	# img is cv img
	output = img
	output = np.array(output)
	# shrink to values between zero and one and make floats
	output = output / 255
	# pytorch wants the axis in a different order from opencv so we do this switcharoo a few times
	output = np.moveaxis(output, -1, 0)
	output = torch.tensor(output, dtype=torch.float32)
	return output

def piece_present(frame_tensor):
	if frame_tensor[0]['scores'].size(dim=0) == 0:
		return False
	else:
		return True

def cur_time():
	return round(time.time() * 1000)

def evaluate(model, prepped_tensor):
	begin = cur_time()
	with torch.no_grad():
		prediction = model([prepped_tensor.to(device)])
	print(f"took {cur_time() - begin} ms to evaluate")
	#(Image.fromarray(tensor.mul(255).permute(1, 2, 0).byte().numpy())).show()
	if piece_present(prediction):
		# bring mask to cpu and convert to numpy array
		mask = np.array(prediction[0]['masks'][0].cpu())
		# model returns long floats representing its certainty of a pixel being in the mask and we want those to be 1's or 0's
		mask[np.nonzero(mask)] = 1
		mask = mask.astype(int)
		# switch back
		mask = np.moveaxis(mask, 0, -1)
		
		box = np.array(prediction[0]['boxes'][0].cpu())
		box = box.astype(int)

		score = np.array(prediction[0]['scores'][0].cpu())
		return mask, box, prediction, score
		#(Image.fromarray(prediction[0]['masks'][0, 0].mul(255).byte().cpu().numpy())).show()
	else:
		return None, None, None, 0.0

def crop(orig_img, mask, box):
	# make mask 3 channels
	orig_img = np.array(orig_img)
	mask = np.repeat(mask, 3, axis=2)
	#orig_img[np.where(mask == 0)] = 0
	expand = 20
	x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
	if x1 < expand:
		x1 = 0
	else:
		x1 -= expand
	if y1 < expand:
		y1 = 0
	else:
		y1 -= expand
	if orig_img.shape[1]-x2 < expand:
		x2 = orig_img.shape[1]
	else:
		x2 += expand
	if orig_img.shape[0]-y2 < expand:
		y2 = orig_img.shape[0]
	else:
		y2 += expand
	cropped = orig_img[y1:y2,x1:x2]
	return cropped

if False:
	# import model file
	model = torch.load('trained_model5.pth')
	model.eval()
	#
	#img, _ = dataset_test[30]
	#img2 = prep_img('test_subject.jpg')
	#
	#actual_begin = cur_time()
	#
	data_p = 'data/images/90/'
	cropped_p = 'data/cropped/90/'
	for img in os.listdir(data_p):
		img_p = os.path.join(data_p, img)
		write_p = os.path.join(cropped_p, img)
		img = cv2.imread(img_p)
		#img = resize(img)
		mask, box, prediction = evaluate(model, prep_img(img))
		if mask is not None:
			print(prediction)
			cropped = crop(img, mask, box)
			cv2.imwrite(write_p, cropped)

	cv2.imshow('monkey', cropped)
	cv2.waitKey(0)
	cv2.destroyAllWindows()
	#
	#print(cur_time() - actual_begin)
