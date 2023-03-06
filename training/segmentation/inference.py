import torch
from torchvision import transforms, io, utils
from model import DeepLabV3SegNet
import random
import os

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = DeepLabV3SegNet().to(device)
model.load_state_dict(torch.load("models/model_1678060418.016126.pt"))
model.eval()

root_path = "data"
images_path = os.path.join(root_path, "source")
output_path = os.path.join(root_path, "output")

test_images = random.sample(os.listdir(images_path), 10)

def predictMask(img):
    img = transforms.Resize((256,256))(img)
    img = img.float()
    img = img.unsqueeze(0)
    with torch.no_grad():
        mask = model(img)
    threshold = 0.5
    mask = torch.where(mask > threshold, torch.ones_like(mask), torch.zeros_like(mask))
    return mask

def maskImage(img, mask):
    mask = mask.squeeze(0)
    mask = transforms.Resize((img.shape[1], img.shape[2]))(mask)
    mask = mask.repeat(3,1,1)
    img = torch.where(mask > 0, img, torch.zeros_like(img))
    return img

for img_name in test_images:
    img = io.read_image(os.path.join(images_path, img_name))
    img = img.to(device)
    out = predictMask(img.float())
    masked = maskImage(img, out)
    masked = masked.float()
    masked = masked / 255
    utils.save_image(masked, os.path.join(output_path, img_name))
