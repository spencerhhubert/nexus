import cv2
import time
import numpy as np
import threading
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


class CameraBuffer:
    def __init__(self, camera: Camera, global_config: GlobalConfig):
        self.camera = camera
        self.global_config = global_config
        self.latest_frame = None
        self.frame_timestamp = 0.0
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

        global_config["logger"].info("Camera buffer thread started")

    def _capture_loop(self):
        while self.running:
            try:
                frame = self.camera.captureFrame()
                if frame is not None:
                    current_time = time.time() * 1000
                    with self.lock:
                        self.latest_frame = frame
                        self.frame_timestamp = current_time
            except Exception as e:
                self.global_config["logger"].error(f"Camera buffer capture error: {e}")
                time.sleep(0.1)  # Brief pause on error

    def get_latest_frame(self) -> tuple[Optional[np.ndarray], float]:
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy(), self.frame_timestamp
            return None, 0.0

    def stop(self):
        self.global_config["logger"].info("Stopping camera buffer thread")
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)


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


def connectToCamera(
    camera_device_index: int,
    global_config: GlobalConfig,
    width: int,
    height: int,
    fps: int,
) -> Camera:
    debug_level = global_config["debug_level"]
    auto_confirm = global_config["auto_confirm"]
    camera = None

    try:
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

    except Exception as e:
        if debug_level > 0:
            print(f"Failed to connect to camera at index {camera_device_index}: {e}")

        discovered_cameras = discoverCameras()
        if not discovered_cameras:
            print(
                f"Failed to connect to camera at index {camera_device_index} and could not discover any cameras"
            )
            raise e

        discovered_camera = discovered_cameras[0]

        if not auto_confirm:
            response = input(
                f"Failed to use camera from environment at index {camera_device_index}. Would you like to automatically try to use discovered camera at index {discovered_camera}? (y/N): "
            )
            if response.lower() not in ["y", "yes"]:
                print("User declined to use discovered camera")
                raise e

        if debug_level > 0:
            print(
                f"Attempting to connect to discovered camera at index {discovered_camera}"
            )

        try:
            camera = Camera(
                global_config,
                discovered_camera,
                width,
                height,
                fps,
            )
            print(f"Successfully connected to camera at index {discovered_camera}")
        except Exception as discovery_error:
            print(
                f"Failed to connect to discovered camera at index {discovered_camera}: {discovery_error}"
            )
            raise e

    # wait for focus to reset back to manual setting. opencv will automatically set the focus to auto, and it'll need to go back to manual before use
    time.sleep(3)
    return camera
