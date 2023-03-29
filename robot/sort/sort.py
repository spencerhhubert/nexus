#practically the main process. this is where motor controls are called and ML models are ran
import os
import time
import json
import torch
from torchvision import transforms
from torchvision.utils import save_image
from pyfirmata import Arduino, util, pyfirmata
import cv2
import robot.identification as id
import robot.irl as irl
import robot.classification as c

camera_path = "/dev/video0"
ml_dev = "cuda"
seg_model = "seg_model_1678064497.7959268.pt"
root_dir = "/nexus"

#todo: make this percentage of frame
mask_threshold = 500 #number of pixels that need to be in the mask for it to be considered a present piece

data_collection_mode = True

def servoTest():
    controller = irl.PCA9685(dev, 0x42)
    servo1 = irl.Servo(15, controller)
    while True:
        servo1.setAngle(0)
        time.sleep(1)
        servo1.setAngle(180)
        time.sleep(1)

def saveBuffer(buffer:list, out_dir:str, preds:dict=None):
    if preds is not None:
        os.makedirs(out_dir, exist_ok=True)
        preds_out_path = os.path.join(out_dir, "preds.json")
        with open(out_path, "w") as f:
            json.dump(preds, f)
    for i,img in enumerate(buffer):
        #save whole buffer to the same folder
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{i}.png")
        img = img.float()
        img = img / 255
        print(img.shape)
        img = img.unsqueeze(0)
        save_image(img, out_path)
    print("saved buffer")

def sort(profile:c.Profile):
    mc, dms, feeder_stepper, main_conveyor_stepper bins_allocated = irl.config.buildConfig()

    feeder_stepper.run(dir=True, sps=100)
    main_conveyor_stepper.run(dir=True, sps=500)

    while True:
        pass

    segnet = id.DeepLabV3SegNet().to(ml_dev)
    segnet.load_state_dict(torch.load(os.path.join(root_dir, "robot/models", seg_model)))
    segnet.eval()

    cam = cv2.VideoCapture(camera_path)
    buffer = [] #hopefully all a single piece, from different angles. send as a batch to classification model
    piece_present = False

    while True:
        ret, img = cam.read()
        if not ret:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) #bgr is so dumb
        img = torch.from_numpy(img).to(ml_dev)
        img = img.permute(2, 0, 1)
        mask = id.predictMask(img, segnet, threshold=0.5)
        piece_present = False if mask.sum() < mask_threshold else True

        if not piece_present and len(buffer) > 0:
            pass #only case we want to use buffer
        else:
            if not piece_present:
                print("no piece detected")
                continue
            else:
                bounding_box = id.findBoundingBox(img, mask)
                img = id.crop(bounding_box, img, padding=32)
                img = transforms.Resize((224, 224))(img)
                buffer.append(img)
                continue
       
        #will probably want to scrape a few off the ends where it's not as visible
        img_to_pass = buffer[len(buffer)/2] #going to batch these later to get avg as the angle changes
        preds = id.predict.predictFromTensor(img_to_pass)
        pred_id = id.predict.topId(preds) #temp, going to move all this here

        where_go = profile.getCategory(pred_id)

        if data_collection_mode:
            out_dir = os.path.join(root_dir, f"training/classification/data/{time.time()}")
            saveBuffer(buffer, out_dir, preds)
            buffer = []
            continue

        #maybe wait here for a small buffer of images to build up then send in as batch
        #take avg of predictions for piece prediction?
