import os
import numpy as np
import torch
import torch.utils.data
from PIL import Image
from dataset_class import PartSegDataset
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
import utils
import transforms as T
from engine import train_one_epoch, evaluate

def get_instance_segmentation_model(num_classes):
	# get pre-trained rcnn model and modify it for transfer learning
	model = torchvision.models.detection.maskrcnn_resnet50_fpn(pretrained=True);
	in_features = model.roi_heads.box_predictor.cls_score.in_features;
	# replace the pre-trained head with a new one
	model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes);
	# now get the number of input features for the mask classifier
	in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels;
	hidden_layer = 256;
	# and replace the mask predictor with a new one
	model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes);
	return model;

def get_transform(train):
	transforms = []
	# converts the image, a PIL image, into a PyTorch Tensor
	transforms.append(T.ToTensor())
	if train:
		# during training, randomly flip the training images
		# and ground-truth for data augmentation
		transforms.append(T.RandomHorizontalFlip(0.5))
	return T.Compose(transforms)

