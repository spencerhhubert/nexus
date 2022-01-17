import os
import numpy as np
import torch
import torch.utils.data
from PIL import Image
import cv2
import torchvision.transforms as T

def get_transform(train):
	transforms = []
	# converts the image, a PIL image, into a PyTorch Tensor
	transforms.append(T.ToTensor())
	transforms.append(T.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)))
	if train:
		# during training, randomly flip the training images
		# and ground-truth for data augmentation
		transforms.append(T.RandomHorizontalFlip(0.5))
		transforms.append(T.ColorJitter(brightness=0.3, contrast=0.5, saturation=0.5, hue=0.3))
	return T.Compose(transforms)

def resize(img, des_w):
	w_perc = (des_w/float(img.size[0]))
	h = int((float(img.size[1]) * float(w_perc)))
	img = img.resize((des_w, h), Image.ANTIALIAS)
	return img

def combine_sub_files(path):
	# takes folders inside a directory and combines their contents into a mega list and returns it
	imgs = [];
	labels = [];
	for label in os.listdir(path):
		label_p = os.path.join(path, label)
		for img in os.listdir(label_p):
			img_p = os.path.join(label_p, img)
			if os.path.isdir(img_p):
				for img2 in os.listdir(img_p):
					labels.append(label);
					imgs.append(os.path.join(img_p, img2));
				continue;
			labels.append(label);
			imgs.append(img_p);			
	return imgs, labels


def partNum(filename):
	split = filename.split('-');
	return split[1];


class PartDataset(torch.utils.data.Dataset):
	def __init__(self, root, transforms=None):
		self.root = root;
		self.transforms = transforms;
		self.imgs, self.labels = combine_sub_files(root);

	def __getitem__(self, idx):
		img_p = self.imgs[idx];
		label = self.labels[idx];
		img = Image.open(img_p).convert("RGB");
		sample = {'image': img, 'label': label}
		if self.transforms is not None:
			img = self.transforms(img);
		label = torch.tensor([idx])
		print(img_p)

		return img, label;

	def __len__(self):
		return len(self.imgs)
