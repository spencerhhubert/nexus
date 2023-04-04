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
from robot.sort.helpers import incrementBins, speed
import robot.utils.dev as dev

camera_path = "/dev/video3"
ml_dev = "cuda"
seg_model = "seg_model_1678064497.7959268.pt"
root_dir = "/nexus"

#todo: make this percentage of frame
mask_threshold = 1000 #number of pixels that need to be in the mask for it to be considered a present piece

dev_mode = True

def sort(profile:Profile):
    mc, dms, feeder_stepper, main_conveyor_stepper = irl.buildConfig()
    irl.motors.runSteppers(mc)

    segnet = seg.DeepLabV3SegNet().to(ml_dev)
    segnet.load_state_dict(torch.load(os.path.join(root_dir, "robot/models", seg_model)))
    segnet.eval()

    cam = cv2.VideoCapture(camera_path)
    buffer = [] #hopefully all a single piece, from different angles. send as a batch to classification model
    raw_buffer = []
    piece_present = False
    
    print("beginning sort")
    while True:
        ret, img = cam.read()
        if not ret:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) #bgr is so dumb

        #flip img 180 degrees
        img = cv2.flip(img, 0)

        img = torch.from_numpy(img).to(ml_dev)
        img = img.permute(2, 0, 1)

        #crop to square but keep height. need to get more segmentation training data, environment changes mess it up too much
        #size = img.shape[1]
        #img = transforms.functional.crop(img, 0, int(size/2), size, size)

        mask = seg.predictMask(img, segnet, threshold=0.5)
        piece_present = False if mask.sum() < mask_threshold else True

        if not piece_present and len(buffer) > 0:
            pass #only case we want to use buffer
        else:
            if not piece_present:
                continue
            else:
                raw_buffer.append(img)
                bounding_box = seg.findBoundingBox(img, mask)
                img = seg.crop(bounding_box, img, padding=32, square=True)
                img = transforms.Resize((224, 224))(img)
                buffer.append(img)

                if len(buffer) < 15: #temporary hack for brickognize because api needs pic asap
                    continue
       
        preds = id.brickognize.predictFromTensor(buffer[-1])
        all_pred_ids = id.brickognize.allTopIds(preds)
        pred_id = profile.topExistentKind(all_pred_ids)
        print(f"predicted piece: {pred_id} - {profile.getName(pred_id)}")
        pred_category = profile.belongsTo((pred_id, "n/a"))
        dm, bin, dms = incrementBins(pred_category, dms)

        #TODO make cv func for speed, ping say every 30 seconds
        delay_constant = -1000 #from api taking long time
        when_open_doors = (1 / speed(200, 1/2, 600, (30.88/10))*(dm.distance_from_camera)) * 1000 + delay_constant
        print(f"opening doors in {when_open_doors}ms")
        irl.openDoors(dm, bin, when_open_doors)

        if dev_mode:
            dev.runErrorAnalysis(buffer, raw_buffer, preds)
            buffer = []
            raw_buffer = []
            continue
