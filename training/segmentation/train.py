import os
import numpy as np
import torch
import torch.nn as nn
from model import BinarySegmentationModel
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, io

class BinarySegmentationDataset(Dataset):
    def __init__(self, imgs_path, masks_path, crop_shape=(256, 256)):
        self.imgs = []
        self.masks = []
        for img in os.listdir(imgs_path):
            full_path = os.path.join(imgs_path, img)
            img = io.read_image(full_path)
            img = transforms.Resize(crop_shape)(img)
            img = img.float()
            self.imgs.append(img)
        for mask in os.listdir(masks_path):
            full_path = os.path.join(masks_path, mask)
            mask = np.load(full_path)
            mask = torch.from_numpy(mask)
            mask = mask.unsqueeze(0)
            mask = transforms.Resize(crop_shape)(mask)
            mask = mask.float()
            self.masks.append(mask)

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, idx):
        return (self.imgs[idx], self.masks[idx])

device = "cuda"
num_epochs = 16
batch_size = 16
model = BinarySegmentationModel().to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
criterion = nn.BCEWithLogitsLoss()

model.to(device)
model.train()

train_dataset = BinarySegmentationDataset("data/source", "data/labels")
train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

for epoch in range(num_epochs):
    for i, (img, mask) in enumerate(train_dataloader):
        img = img.to(device)
        mask = mask.to(device)
        optimizer.zero_grad()
        print(img)
        output = model(img)
        loss = criterion(output, mask)
        loss.backward()
        optimizer.step()
