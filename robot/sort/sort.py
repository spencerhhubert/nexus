#practically the main process. this is where motor controls are called and ML models are ran
import os
import torch
from torchvision import transforms
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

mask_threshold = 1000 #number of pixels that need to be in the mask for it to be considered a present piece

def sort(profile:c.Profile):
    dev = Arduino(mc_path)
    feeder_stepper = irl.motors.Stepper(feeder_stepper_dir_pin, feeder_stepper_step_pin, 200*16, dev)
    main_conveyor_stepper = irl.motors.Stepper(main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, 200*16, dev)
    feeder_stepper.run(dir=True, rpm=5000)
    main_conveyor_stepper.run(dir=True, rpm=5000)

    segnet = id.DeepLabV3SegNet().to(ml_dev)
    segnet.load_state_dict(torch.load(os.path.join(root_dir, "robot/models", seg_model)))
    segnet.eval()

    cam = cv2.VideoCapture(camera_path)
    while True:
        ret, img = cam.read()
        if not ret:
            continue
        img = torch.from_numpy(img).to(ml_dev)
        img = img.permute(2, 0, 1)
        mask = id.predictMask(img, segnet, threshold=0.5)
        if mask.sum() < mask_threshold:
            continue
        bounding_box = id.findBoundingBox(img, mask)
        img = id.crop(bounding_box, img)
        img = transforms.Resize((224, 224))(img)
        print("there's a piece there!")
        #maybe wait here for a small buffer of images to build up then send in as batch
        #take avg of predictions for piece prediction?
