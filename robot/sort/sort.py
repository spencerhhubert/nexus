#practically the main process. this is where motor controls are called and ML models are ran
import os
import time
import torch
from torchvision import transforms
from torchvision.utils import save_image
from pyfirmata import Arduino
import cv2
import robot.identification as id
import robot.irl as irl
import robot.classification as c

mc_path = "/dev/ttyACM0"
camera_path = "/dev/video0"
ml_dev = "cuda"
seg_model = "seg_model_1678064497.7959268.pt"
root_dir = "/nexus"

feeder_stepper_dir_pin = 2
feeder_stepper_step_pin = 3
main_conveyor_stepper_dir_pin = 4
main_conveyor_stepper_step_pin = 5
dev = Arduino(mc_path)

mask_threshold = 1000 #number of pixels that need to be in the mask for it to be considered a present piece

data_collection_mode = True

def servoTest():
    controller = irl.PCA9685(dev, 0x40)
    servo1 = irl.Servo(15, controller)
    while True:
        servo1.setAngle(0)
        time.sleep(1)
        servo1.setAngle(180)
        time.sleep(1)

def saveBuffer(buffer:list):
    out_dir = os.path.join(root_dir, f"training/classification/data/{time.time()}")
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
    feeder_stepper = irl.motors.Stepper(feeder_stepper_dir_pin, feeder_stepper_step_pin, 200*16, dev)
    main_conveyor_stepper = irl.motors.Stepper(main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, 200*16, dev)
    #feeder_stepper.run(dir=True, rpm=5000)
    #main_conveyor_stepper.run(dir=True, rpm=5000)

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
            #only case we want to use buffer
            pass
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
        
        print("saving buffer")

        if data_collection_mode:
            saveBuffer(buffer)
            buffer = []
            continue

        #maybe wait here for a small buffer of images to build up then send in as batch
        #take avg of predictions for piece prediction?
