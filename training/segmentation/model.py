import torch
import torch.nn as nn
import torchvision.models.segmentation
from torchvision.models.segmentation.deeplabv3 import DeepLabHead, DeepLabV3_MobileNet_V3_Large_Weights

class BinarySegmentationModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights=DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT)
        self.model.classifier = DeepLabHead(320*3, 1)
        self.sigmoid = nn.Sigmoid() #s/o pytorch for depracating the better functional version of this. a stateless function is totally something that needs an object

    def forward(self, x: torch.Tensor):
        x = self.model(x)['out']
        x = self.sigmoid(x) 
        return x


