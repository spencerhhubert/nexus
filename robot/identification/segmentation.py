import torch
import torch.nn as nn
import torchvision
import torchvision.models.segmentation
from torchvision import transforms
from torchvision.models.segmentation.deeplabv3 import DeepLabHead, DeepLabV3_MobileNet_V3_Large_Weights
import cv2

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

def croppedImage(img:torch.Tensor, segnet:torch.nn.Module, threshold=0.5, padding=250, new_size=(224,224)) -> torch.Tensor:
    mask = predictMask(img, segnet, threshold=threshold)
    bounding_box = findBoundingBox(img, mask, padding=padding)
    img = crop(bounding_box, img, padding=padding)
    img = transforms.Resize(new_size)(img)
    return img

def predictMask(img:torch.Tensor, model:torch.nn.Module, threshold:0.5) -> torch.Tensor:
    img = transforms.Resize((256,256))(img)
    img = img.float()
    img = img.unsqueeze(0)
    with torch.no_grad():
        mask = model(img)
    mask = torch.where(mask > threshold, torch.ones_like(mask), torch.zeros_like(mask))
    return mask

def findBoundingBox(img:torch.Tensor, mask:torch.Tensor, new_size=(256,256), padding=250) -> tuple:
    masked_img = maskImage(img, mask)
    #cv2 will glitch if you pass an empty image, also waste of compute
    if torch.sum(masked_img) < 10:
        masked_img = transforms.Resize(new_size)(masked_img)
        return None
    masked_img = masked_img.permute(1,2,0)
    masked_img = masked_img.cpu().numpy()
    grayscale = cv2.cvtColor(masked_img, cv2.COLOR_BGR2GRAY)
    grayscale = cv2.convertScaleAbs(grayscale)
    thresh = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    x,y,w,h = cv2.boundingRect(contours[0])
    return (x,y,w,h)

def crop(bounding_box:tuple, img:torch.Tensor, padding=250) -> torch.Tensor:
    print(bounding_box)
    x,y,w,h = bounding_box
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img.shape[2], w + 2*padding)
    h = min(img.shape[1], h + 2*padding)
    img = img[:,y:y+h,x:x+w]
    return img

def maskImage(img:torch.Tensor, mask:torch.Tensor) -> torch.Tensor:
    mask = mask.squeeze(0)
    mask = transforms.Resize((img.shape[1], img.shape[2]))(mask)
    mask = mask.repeat(3,1,1)
    img = torch.where(mask > 0, img, torch.zeros_like(img))
    return img

def saveImage(img:torch.Tensor, path:str):
    img = img.float()
    img = img / 255
    utils.save_image(img, path)

def area(bounding_box:tuple) -> int:
    x,y,w,h = bounding_box
    return w*h

def isPiecePresent(bounding_box:tuple, threshold:float) -> bool:
    if area(bounding_box) > threshold:
        return True
    else:
        return False

