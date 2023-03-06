import os
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset
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
