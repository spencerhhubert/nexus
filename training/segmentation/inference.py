import torch
from torchvision import transforms, io, utils
from model import DeepLabV3SegNet
import random
import os
import cv2

def predictMask(img, model):
    img = transforms.Resize((256,256))(img)
    img = img.float()
    img = img.unsqueeze(0)
    with torch.no_grad():
        mask = model(img)
    threshold = 0.5
    mask = torch.where(mask > threshold, torch.ones_like(mask), torch.zeros_like(mask))
    return mask

def findBoundingBox(img: torch.Tensor, mask: torch.Tensor, new_size=(256,256), padding=250):
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

def crop(bounding_box: tuple, img: torch.Tensor, padding=250):
    x,y,w,h = bounding_box
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img.shape[2], w + 2*padding)
    h = min(img.shape[1], h + 2*padding)
    img = img[:,y:y+h,x:x+w]
    return img

def maskImage(img, mask):
    mask = mask.squeeze(0)
    mask = transforms.Resize((img.shape[1], img.shape[2]))(mask)
    mask = mask.repeat(3,1,1)
    img = torch.where(mask > 0, img, torch.zeros_like(img))
    return img

def saveImage(img: torch.Tensor, path: str):
    img = img.float()
    img = img / 255
    utils.save_image(img, path)

if __name__ == "__main__":
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = DeepLabV3SegNet().to(device)
    model_name = "model_1678064497.7959268.pt"
    model.load_state_dict(torch.load(os.path.join("models", model_name)))
    model.eval()

    root_path = "data"
    images_path = os.path.join(root_path, "source")
    output_path = os.path.join(root_path, "output")

    test_images = random.sample(os.listdir(images_path), 100)

    for img_name in test_images:
        img = io.read_image(os.path.join(images_path, img_name))
        img = img.to(device)
        mask = predictMask(img.float(), model)
        box = findBoundingBox(img, mask)
        if box is None:
            continue
        else:
            cropped = crop(box, img, padding=50)
            saveImage(cropped, os.path.join(output_path, img_name))
