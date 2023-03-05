import torch
import torch.nn as nn
import torchvision.models.segmentation
from torchvision.models.segmentation.deeplabv3 import DeepLabHead, DeepLabV3_MobileNet_V3_Large_Weights

class BinarySegmentationModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(
                weights=DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT,
                progress=True,
                num_classes=2,
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

import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

class SegNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights="DEFAULT")
        in_features = self.model.roi_heads.box_predictor.cls_score.in_features
        self.model.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)
        in_features_mask = self.model.roi_heads.mask_predictor.conv5_mask.in_channels
        self.model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, 256, 2)
    def forward(self, x: torch.Tensor, targets):
        return self.model(x, targets)
