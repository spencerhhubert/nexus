import os
import torch
from torch.utils.data import Dataset
from torchvision import transforms, io

class PiecesDataset(Dataset):
    def __init__(self, root_path:str, transforms=None):
        self.root_path = root_path
        self.pieces = os.listdir(root_path)
        self.transforms = transforms

    def __getitem__(self, idx):
        img_path = os.path.join(self.root_path, self.pieces[idx])
        img = io.read_image(img_path)
        kind, color = getLabels(self.pieces[idx])
        return img, (kind, color)

    def __len__(self):
        return len(self.pieces)

def getLabels(img_name:str):
    kind = img_name.split('_')[0]
    color = img_name.split('_')[1]
    return kind, color
