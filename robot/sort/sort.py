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

camera_path = "/dev/video3"
ml_dev = "cuda"
seg_model = "seg_model_1678064497.7959268.pt"
root_dir = "/nexus"

#todo: make this percentage of frame
mask_threshold = 1000 #number of pixels that need to be in the mask for it to be considered a present piece

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
    raw_buffer = []
    piece_present = False

    while True:
        ret, img = cam.read()
        if not ret:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) #bgr is so dumb

        #flip img 180 degrees
        img = cv2.flip(img, 0)

        img = torch.from_numpy(img).to(ml_dev)
        img = img.permute(2, 0, 1)

        #crop to square but keep height
        size = img.shape[1]
        img = transforms.functional.crop(img, 0, int(size/2), size, size)

        mask = seg.predictMask(img, segnet, threshold=0.5)
        piece_present = False if mask.sum() < mask_threshold else True

        if not piece_present and len(buffer) > 0:
            pass #only case we want to use buffer
        else:
            if not piece_present:
                continue
            else:
                raw_buffer.append(img)
                bounding_box = seg.findBoundingBox(img, mask, square=True)
                img = seg.crop(bounding_box, img, padding=32)
                img = transforms.Resize((224, 224))(img)
                buffer.append(img)
                if len(buffer) < 25: #temporary hack for brickognize because api needs pic asap
                    continue
       
        #will probably want to scrape a few off the ends where it's not as visible
        img_to_pass = buffer[int(len(buffer)/2)] #going to batch these later to get avg as the angle changes
        img_to_pass = buffer[-1]
        print(f"length of buffer: {len(buffer)}")
        preds = id.brickognize.predictFromTensor(img_to_pass)
        all_pred_ids = id.brickognize.allTopIds(preds)
        pred_id = profile.topExistentKind(all_pred_ids)
        print(f"predicted piece: {pred_id} - {profile.getName(pred_id)}")
        pred_category = profile.belongsTo((pred_id, "n/a"))
        dm, bin, dms = incrementBins(pred_category, dms)

        #make cv func for this, ping say every 30 seconds
        speed = 10 #cm/s

        when_open_doors = (1 / speed*(dm.distance_from_camera)) * 1000 #ms
        when_open_doors = 0 #lol need asap
        irl.openDoors(dm, bin, when_open_doors)

        time.sleep(5)

        if dev_mode:
            dev.runErrorAnalysis(buffer, raw_buffer, preds)
            buffer = []
            raw_buffer = []
            continue
