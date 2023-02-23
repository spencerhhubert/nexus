import torch
import torch.nn as nn
from model import BinarySegmentationModel

device = "cuda"
batch_size = 27
test = torch.randn((batch_size,3,224,224), device=device)
model = BinarySegmentationModel().to(device)
out = model(test)
print(out.shape)
