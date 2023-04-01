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
import robot.identification.segmentation as seg
import robot.irl as irl
import robot.classification as c
from robot.classification.profile import Profile
from robot.sort.helpers import incrementBins
import robot.utils.dev as dev

camera_path = "/dev/video0"
ml_dev = "cuda"
seg_model = "seg_model_1678064497.7959268.pt"
root_dir = "/nexus"

#todo: make this percentage of frame
mask_threshold = 500 #number of pixels that need to be in the mask for it to be considered a present piece

dev_mode = True

def servoTest():
    controller = irl.PCA9685(dev, 0x42)
    servo1 = irl.Servo(15, controller)
    while True:
        servo1.setAngle(0)
        time.sleep(1)
        servo1.setAngle(180)
        time.sleep(1)

def sort(profile:Profile):
    mc, dms, feeder_stepper, main_conveyor_stepper = irl.buildConfig()

    #feeder_stepper.run(dir=True, sps=100)
    #main_conveyor_stepper.run(dir=True, sps=100)

    segnet = seg.DeepLabV3SegNet().to(ml_dev)
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
        mask = seg.predictMask(img, segnet, threshold=0.5)
        piece_present = False if mask.sum() < mask_threshold else True

        if not piece_present and len(buffer) > 0:
            pass #only case we want to use buffer
        else:
            if not piece_present:
                continue
            else:
                bounding_box = seg.findBoundingBox(img, mask)
                img = seg.crop(bounding_box, img, padding=32)
                img = transforms.Resize((224, 224))(img)
                buffer.append(img)
                continue
       
        #will probably want to scrape a few off the ends where it's not as visible
        img_to_pass = buffer[int(len(buffer)/2)] #going to batch these later to get avg as the angle changes
        preds = id.brickognize.predictFromTensor(img_to_pass)
        pred_id = id.brickognize.topId(preds) #temp, going to move all this here
        print(f"predicted {pred_id} - {id.brickognize.topName(preds)}")
    
        pred_category = profile.belongsTo((pred_id, "n/a"))
        dm, bin, dms = incrementBins(pred_category, dms)

        #make cv func for this, ping say every 30 seconds
        speed = 10 #cm/s

        when_open_doors = (1 / speed*(dm.distance_from_camera)) * 1000 #ms
        when_open_doors = 0 #lol need asap
        irl.openDoors(dm, bin, when_open_doors)

        if dev_mode:
            dev.runErrorAnalysis(buffer, preds)
            buffer = []
            continue
