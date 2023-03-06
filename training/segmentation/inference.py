import torch
from torchvision import transforms, io, utils
from model import DeepLabV3SegNet
import random
import os

model = DeepLabV3SegNet()
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
        return model(img)

for img_name in test_images:
    img = io.read_image(os.path.join(images_path, img_name))
    out = predictMask(img)
    utils.save_image(out, os.path.join(output_path, img_name))
