import os
import numpy as np
import torch
import torch.nn as nn
from model import MaskRCNNSegNet
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

        obj_ids = torch.unique(mask)
        obj_ids = obj_ids[1:]
        masks = mask == obj_ids[:, None, None]
        mask[mask > 1] = 1 #idk sometimes the mask has other values in it and we're just doing binary rn

        num_objs = len(obj_ids)
        boxes = []
        for i in range(num_objs):
            pos = torch.where(masks[i])
            xmin = torch.min(pos[1])
            xmax = torch.max(pos[1])
            ymin = torch.min(pos[0])
            ymax = torch.max(pos[0])
            boxes.append([xmin, ymin, xmax, ymax])

		#since we often have zero objects in the scene we do this
        if num_objs == 0:
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            area = torch.as_tensor(0, dtype=torch.float32)
        else:
            boxes = torch.as_tensor(boxes, dtype=torch.float32)
            area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])

        labels = torch.ones((num_objs,), dtype=torch.int64)
        masks = torch.as_tensor(masks, dtype=torch.uint8)

        image_id = torch.tensor([idx])
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])
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
        return len(self.masks)

device = "cuda"
num_epochs = 100
batch_size = 2
model = MaskRCNNSegNet().to(device)
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.Adam(params, lr=0.001, weight_decay=1e-8)
#num_params = sum(p.numel() for p in model.model.classifier.parameters())
criterion = nn.BCELoss()

model.to(device)
model.train()


#dataset = BinarySegmentationDataset("data/source", "data/labels")
dataset = MaskedPiecesDataset("data", transforms=None)
#train_dataset = dataset.getRange(0, 100)
#val_dataset = dataset.getRange(100, 120)
train_dataset = dataset

def collate_fn(batch):
    return tuple(zip(*batch))

train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
model.train()

for epoch in range(num_epochs):
    for i, (images, targets) in enumerate(train_dataloader):
        if batch_size == 1:
            images = [images]
            targets = [targets]
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        print(f"loss: {losses.item()}")
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()
    print(f"epoch {epoch} complete")


