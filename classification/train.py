import os
import torch.nn as nn
import numpy as np
import torch
from PIL import Image
import torchvision
from setup_model import *
from torch.optim.lr_scheduler import StepLR
import time

# set parameters for transfer learning
#params = [p for p in model.parameters() if p.requires_grad]
#optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
optimizer = torch.optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
criterion = nn.CrossEntropyLoss()

#lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)
lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)

def train_one_epoch(model, optimizer, data_loader, device, epoch):
	model.train()
	lr_scheduler = None
	if epoch == 0:
		warmup_factor = 1.0 / 1000
		warmup_iters = min(1000, len(data_loader) - 1)

		lr_scheduler = torch.optim.lr_scheduler.LinearLR(
		optimizer, start_factor=warmup_factor, total_iters=warmup_iters
		)

	for imgs, labels in data_loader:
		imgs = imgs.to(device)
		labels = labels.to(device)

		optimizer.zero_grad()
		
		# Forward pass
		with torch.set_grad_enabled(True):
			outputs = model(imgs)
			loss = criterion(outputs, labels)

			# Backward and optimize
			loss.backward()
			optimizer.step()

	if lr_scheduler is not None:
		lr_scheduler.step()

	print(f"epoch {epoch} complete")
	
def evaluate(model, data_loader_test, device):
	size = len(data_loader_test.dataset)
	num_batches = len(data_loader_test)
	test_loss, correct = 0, 0
	model.eval()
	with torch.no_grad():
		for imgs, labels in data_loader_test:
			imgs = imgs.to(device)
			labels = labels.to(device)
			pred = model(imgs)
			test_loss += criterion(pred, labels).item()
			correct += (pred.argmax(1) == labels).type(torch.float).sum().item()
	test_loss /= num_batches
	correct /= size
	print(f"Test Error: \n Accuracy: {(100*correct):>0.1f}%, Avg loss: {test_loss:>8f} \n")

if True:
	num_epochs = 25
	for epoch in range(num_epochs):
		print('beginning new epoch')
		train_one_epoch(model, optimizer, data_loader, device, epoch)
		lr_scheduler.step()
		evaluate(model, data_loader, device)
		evaluate(model, data_loader_test, device)
	torch.save(model, f"trained_model_{time.time()}.pth")
