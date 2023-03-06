import os
import time
import numpy as np
import torch
import torch.nn as nn
from model import DeepLabV3SegNet
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, io

class MaskedPiecesDataset(Dataset):
    def __init__(self, root, transforms=None, crop_shape=(256, 256)):
        self.root = root
        self.transforms = transforms
        self.crop_shape = crop_shape
        self.masks = list(sorted(os.listdir(os.path.join(root, "labels"))))

        self.imgs = []
        #might be less masks than images
        for mask in self.masks:
            img = os.path.basename(mask)[:-4] + ".jpg"
            self.imgs.append(img)

    def __getitem__(self, idx):
        img_path = os.path.join(self.root, "source", self.imgs[idx])
        mask_path = os.path.join(self.root, "labels", self.masks[idx])
        img = io.read_image(img_path)
        img = img.float()
        #img = img / 255.0 #normalize to (0,1)
        
        mask = np.load(mask_path)
        mask = torch.from_numpy(mask)
        mask = mask.unsqueeze(0)

        img = transforms.Resize(self.crop_shape)(img)
        mask = transforms.Resize(self.crop_shape, interpolation=transforms.InterpolationMode.NEAREST)(mask)

        mask[mask > 1] = 1 #idk sometimes the mask has other values in it and we're just doing binary rn

        mask = torch.as_tensor(mask, dtype=torch.float32)

        if self.transforms is not None:
            img, mask = self.transforms(img, mask)

        return img, mask

    def __len__(self):
        return len(self.masks)

device = "cuda"
num_epochs = 8
batch_size = 16
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


torch.save(model.state_dict(), f"models/model_{time.time()}.pt")
