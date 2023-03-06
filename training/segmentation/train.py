import os
import time
import numpy as np
import torch
import torch.nn as nn
from model import DeepLabV3SegNet
from torch.utils.data import  DataLoader
from torchvision import transforms, io
from dataset import MaskedPiecesDataset

device = "cuda"
num_epochs = 2
batch_size = 8
model = DeepLabV3SegNet().to(device)
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.Adam(params, lr=0.001, weight_decay=1e-8)
criterion = nn.BCELoss()

model.to(device)

dataset = MaskedPiecesDataset("data", transforms=None)
torch.manual_seed(1)
indices = torch.randperm(len(dataset)).tolist()
train_dataset = torch.utils.data.Subset(dataset, indices[:-50])
test_dataset = torch.utils.data.Subset(dataset, indices[-50:])

print(f"train dataset size: {len(train_dataset)}")
print(f"test dataset size: {len(test_dataset)}")

def collate_fn(batch):
    return tuple(zip(*batch))

train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=None)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, collate_fn=None)

for epoch in range(num_epochs):
    model.train()
    for i, (images, targets) in enumerate(train_dataloader):
        images = images.to(device)
        targets = targets.to(device)
        output = model(images)
        loss = criterion(output, targets)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        print(f"training loss: {loss.item()}")
    print(f"epoch {epoch} complete")

    model.eval()
    for i, (images, targets) in enumerate(test_dataloader):
        images = images.to(device)
        targets = targets.to(device)
        output = model(images)
        loss = criterion(output, targets)
        print(f"test loss: {loss.item()}")

model_name = f"models/model_{time.time()}.pt"
torch.save(model.state_dict(), model_name)
print(f"model saved to {model_name}")
