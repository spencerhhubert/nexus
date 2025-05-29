import time
import cv2
import os
from datetime import datetime
from robot.irl.config import buildIRLSystemInterface, IRLSystemInterface, buildIRLConfig
from robot.irl.motors import Servo, DCMotor
from robot.global_config import GlobalConfig, buildGlobalConfig


def main() -> None:
    gc = buildGlobalConfig()
    irl_config = buildIRLConfig()
    system: IRLSystemInterface = buildIRLSystemInterface(irl_config, gc)

    arduino = system["arduino"]
    distribution_modules = system["distribution_modules"]
    main_conveyor_motor = system["main_conveyor_dc_motor"]
    feeder_conveyor_motor = system["feeder_conveyor_dc_motor"]
    vibration_hopper_motor = system["vibration_hopper_dc_motor"]
    main_camera = system["main_camera"]

    logger = gc["logger"]
    logger.info(f"Running with debug level: {gc['debug_level']}")
    logger.info("Waiting for Arduino responses...")

    try:
        if False:
            logger.info("Testing camera...")
            frame = main_camera.captureFrame()
            if frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tmp/camera_test_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                logger.info(f"Captured frame saved as {filename}")
            else:
                logger.error("Failed to capture frame")

        logger.info("Setting all motors...")
        main_conveyor_motor.setSpeed(50)
        feeder_conveyor_motor.setSpeed(100)
        vibration_hopper_motor.setSpeed(65)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping motors...")
        main_conveyor_motor.setSpeed(0)
        feeder_conveyor_motor.setSpeed(0)
        vibration_hopper_motor.setSpeed(0)
        arduino.flush()
        arduino.close()
        main_camera.release()


if __name__ == "__main__":
    main()
