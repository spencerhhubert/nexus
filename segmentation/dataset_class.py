import os
import numpy as np
import torch
import torch.utils.data
from PIL import Image
import cv2

def resize(img, des_w):
	w_perc = (des_w/float(img.size[0]))
	h = int((float(img.size[1]) * float(w_perc)))
	img = img.resize((des_w, h), Image.ANTIALIAS)
	return img

def combine_sub_files(path):
	# takes folders inside a directory and combines their contents into a mega list and returns it
	output = [];
	for folder in os.listdir(path):
		folder_p = os.path.join(path, folder);
		for img in os.listdir(folder_p):
			output.append(img);
	return sorted(output);


def partNum(filename):
	split = filename.split('-');
	return split[1];

class PartSegDataset(torch.utils.data.Dataset):
	def __init__(self, root, transforms=None):
		self.root = root;
		self.transforms = transforms;
		self.imgs = list(sorted(combine_sub_files(os.path.join(root, "images"))));
		self.masks = list(sorted(os.listdir(os.path.join(root, "masked"))));

	def __getitem__(self, idx):
		img_p = os.path.join(self.root, "images", partNum(self.imgs[idx]), self.imgs[idx]);
		mask_p = os.path.join(self.root, "masked", self.masks[idx]);
		img = Image.open(img_p).convert("RGB");
		mask = Image.open(mask_p);
		print(np.array(img).shape)
		print(np.array(mask).shape)
		#img = resize(img, 240)
		#mask = resize(mask, 240)
		mask = np.array(mask)
		# for some reason in the writing process when formating the data, a few pixels get switched to 2's, when they should be 1's. so we set everything above a 1 to a 1.
		mask[mask > 1] = 1;
		# find out how many objects are in the label
		obj_ids = np.unique(mask);
		obj_ids = obj_ids[1:];
		masks = mask == obj_ids[:, None, None]

		# bounding box vert cords
		num_objs = len(obj_ids)
		boxes = []
		for i in range(num_objs):
			pos = np.where(masks[i])
			xmin = np.min(pos[1])
			xmax = np.max(pos[1])
			ymin = np.min(pos[0])
			ymax = np.max(pos[0])
			boxes.append([xmin, ymin, xmax, ymax])
		# since we often have zero objects in the scene we do this
		if num_objs == 0:
			empty = True;
			boxes = torch.zeros((0, 4), dtype=torch.float32);
			area = torch.as_tensor(0, dtype=torch.float32);
		else:
			empty = False;
			boxes = torch.as_tensor(boxes, dtype=torch.float32)
			area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0]);
		# there is only one class
		labels = torch.ones((num_objs,), dtype=torch.int64)
		masks = torch.as_tensor(masks, dtype=torch.uint8)

		image_id = torch.tensor([idx])
		#area = torch.tensor([0], dtype=torch.float32);
		# suppose all instances are not crowd
		iscrowd = torch.zeros((num_objs,), dtype=torch.int64)

		target = {}
		target["boxes"] = boxes
		target["labels"] = labels
		target["masks"] = masks
		target["image_id"] = image_id
		target["area"] = area
		target["iscrowd"] = iscrowd

		if self.transforms is not None:
			img, target = self.transforms(img, target)

		return img, target

	def __len__(self):
		return len(self.imgs)
