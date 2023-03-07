import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_large

class PieceClassifier(nn.Module):
    def __init__(self, num_classes=64):
        super(MobileNetV3, self).__init__()
        self.model = mobilenet_v3_large(pretrained=False)
        self.model.classifier = nn.Linear(1280, num_classes) #mobilenetv3 adds its own activation function

    #accepts 224x224 images
    def forward(self, x):
        x = self.model(x)
        return x


