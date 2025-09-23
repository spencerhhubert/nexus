import cv2
import time
import numpy as np
import uuid
from typing import Optional, List, Tuple
from robot.global_config import GlobalConfig


class Camera:
    def __init__(
        self,
        global_config: GlobalConfig,
        device_index: int,
        width: int,
        height: int,
        fps: int,
    ):
        self.global_config = global_config
        self.debug_level = global_config["debug_level"]
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps

        self.global_config["logger"].info(
            f"Initializing camera with device index: {device_index}"
        )

        self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera at index {device_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.global_config["logger"].info(
            f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS"
        )

    def captureFrame(self) -> Optional[np.ndarray]:
        ret, frame = self.cap.read()
        if not ret:
            self.global_config["logger"].info("Failed to capture frame")
            return None
        return frame

    def release(self) -> None:
        self.global_config["logger"].info("Releasing camera")
        self.cap.release()

    def isOpened(self) -> bool:
        return self.cap.isOpened()


def connectToCamera(
    camera_device_index: int,
    global_config: GlobalConfig,
    width: int,
    height: int,
    fps: int,
) -> Camera:
    global_config["logger"].info(
        f"Attempting to connect to camera at index {camera_device_index}"
    )

    camera = Camera(
        global_config,
        camera_device_index,
        width,
        height,
        fps,
    )

    # wait for focus to reset back to manual setting. opencv will automatically set the focus to auto, and it'll need to go back to manual before use
    time.sleep(3)
    return camera
