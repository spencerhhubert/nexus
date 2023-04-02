import requests
import sys
import os
import io
import base64
import torch
from torchvision import transforms

#in the middle of working on this project, a good LEGO classification API was published called brickognize
#so we're using this to get off the ground quickly

def predictFromPath(img_path:str):
    url = "https://api.brickognize.com"
    path = "/predict/parts/"
    name = os.path.basename(img_path)
    headers={'accept': 'application/json'}
    files={'query_image': (name, open(img_path,'rb'), 'image/jpeg')}
    response = requests.post(url+path, headers=headers, files=files)
    return response.json()

def predictFromTensor(img:torch.Tensor):
    img = transforms.ToPILImage()(img)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    img = buffer
    url = "https://api.brickognize.com"
    path = "/predict/parts/"
    headers={'accept': 'application/json'}
    files={'query_image': ("query_image", buffer, 'image/jpeg')}
    response = requests.post(url+path, headers=headers, files=files)
    return response.json()

def topId(preds):
    return preds["items"][0]["id"]

def topName(preds):
    return preds["items"][0]["name"]

def allTopIds(preds):
    return [p["id"] for p in preds["items"]]
