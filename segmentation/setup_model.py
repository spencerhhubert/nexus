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
from engine import train_one_epoch, evaluate
from model_prep_tools import get_instance_segmentation_model, get_transform
import time

dataset = PartSegDataset('data', get_transform(train=True))
dataset_test = PartSegDataset('data', get_transform(train=False))

torch.manual_seed(1)
indices = torch.randperm(len(dataset)).tolist()
dataset = torch.utils.data.Subset(dataset, indices[:-50])
dataset_test = torch.utils.data.Subset(dataset_test, indices[-50:])

data_loader = torch.utils.data.DataLoader(
	dataset, batch_size=2, shuffle=True, num_workers=4,
	collate_fn=utils.collate_fn)

data_loader_test = torch.utils.data.DataLoader(
	dataset_test, batch_size=1, shuffle=False, num_workers=4,
	collate_fn=utils.collate_fn)

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

num_classes = 2
model = get_instance_segmentation_model(num_classes)
model.to(device)

