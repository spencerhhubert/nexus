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
#import transforms as T
from engine import train_one_epoch, evaluate
#from model_prep_tools import get_instance_segmentation_model, get_transform
from setup_model import * 

# set parameters for transfer learning
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)

lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

from torch.optim.lr_scheduler import StepLR

if True:
	num_epochs = 5
	for epoch in range(num_epochs):
		# train for one epoch, printing every 10 iterations
		train_one_epoch(model, optimizer, data_loader, device, epoch, print_freq=10)
		# update the learning rate
		lr_scheduler.step()
		# evaluate on the test dataset
		evaluate(model, data_loader_test, device=device)
	torch.save(model, "trained_model6.pth")
