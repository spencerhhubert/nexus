import cv2
import numpy as np
import torch
from torchvision import transforms

class Camera():
    def __init__(self, dev_path:str, width:int, height:int):
        self.dev_path = dev_path
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(self.dev_path)

    def getFrame(self) -> torch.Tensor:
        _, frame = self.cap.read()
        frame = torch.from_numpy(frame)
        frame = frame.permute(2, 0, 1)
        return frame
