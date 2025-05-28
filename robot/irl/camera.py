import cv2
import time
import numpy as np
from typing import Optional, List, Tuple
from robot.global_config import GlobalConfig


class Camera:
    def __init__(self, global_config: GlobalConfig, device_index: int, width: int = 1920, height: int = 1080, fps: int = 30):
        self.global_config = global_config
        self.debug_level = global_config["debug_level"]
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps

        if self.debug_level > 0:
            print(f"Initializing camera with device index: {device_index}")

        self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera at index {device_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        if self.debug_level > 0:
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")

    def captureFrame(self) -> Optional[np.ndarray]:
        ret, frame = self.cap.read()
        if not ret:
            if self.debug_level > 0:
                print("Failed to capture frame")
            return None
        return frame

    def release(self) -> None:
        if self.debug_level > 0:
            print("Releasing camera")
        self.cap.release()

    def isOpened(self) -> bool:
        return self.cap.isOpened()


def discoverCameras() -> List[int]:
    available_cameras = []

    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available_cameras.append(i)
        cap.release()

    return available_cameras


def connectToCamera(camera_device_index: int, global_config: GlobalConfig, width: int = 1920, height: int = 1080, fps: int = 30) -> Camera:
    debug_level = global_config["debug_level"]
    auto_confirm = global_config["auto_confirm"]
    camera = None

    try:
        if debug_level > 0:
            print(f"Attempting to connect to camera at index {camera_device_index}")
        camera = Camera(global_config, camera_device_index, width, height, fps)

    except Exception as e:
        if debug_level > 0:
            print(f"Failed to connect to camera at index {camera_device_index}: {e}")

        discovered_cameras = discoverCameras()
        if not discovered_cameras:
            print(f"Failed to connect to camera at index {camera_device_index} and could not discover any cameras")
            raise e

        discovered_camera = discovered_cameras[0]

        if not auto_confirm:
            response = input(f"Failed to use camera from environment at index {camera_device_index}. Would you like to automatically try to use discovered camera at index {discovered_camera}? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("User declined to use discovered camera")
                raise e

        if debug_level > 0:
            print(f"Attempting to connect to discovered camera at index {discovered_camera}")

        try:
            camera = Camera(global_config, discovered_camera, width, height, fps)
            print(f"Successfully connected to camera at index {discovered_camera}")
        except Exception as discovery_error:
            print(f"Failed to connect to discovered camera at index {discovered_camera}: {discovery_error}")
            raise e

    # wait for focus to reset back to manual setting. opencv will automatically set the focus to auto, and it'll need to go back to manual before use
    time.sleep(3)
    return camera
