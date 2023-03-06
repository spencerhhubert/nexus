import torch
import torch.nn as nn
import torchvision
import torchvision.models.segmentation
from torchvision.models.segmentation.deeplabv3 import DeepLabHead, DeepLabV3_MobileNet_V3_Large_Weights

class DeepLabV3SegNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(
                weights=DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT,
                progress=True,
        )
        for param in self.model.parameters():
            param.requires_grad = False
        self.model.classifier = DeepLabHead(320*3, 1)
        for param in self.model.classifier.parameters():
            param.requires_grad = True
        self.act = nn.Sigmoid()

    def forward(self, x: torch.Tensor):
        x = self.model(x)['out']
        x = self.act(x) 
        return x
