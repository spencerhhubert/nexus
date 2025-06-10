import cv2
import time
import numpy as np
import uuid
from typing import Optional, List, Tuple
from robot.global_config import GlobalConfig
from robot.irl.camera_calibration import CameraCalibration


class Camera:
    def __init__(
        self,
        global_config: GlobalConfig,
        device_index: int,
        width: int,
        height: int,
        fps: int,
        calibration: CameraCalibration,
    ):
        self.global_config = global_config
        self.debug_level = global_config["debug_level"]
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.calibration = calibration

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

    def tempSaveFrameWithCalibrationInfo(self) -> None:
        frame = self.captureFrame()
        if frame is None:
            self.global_config["logger"].error(
                "Failed to capture frame for calibration visualization"
            )
            return

        overlay = frame.copy()

        # Draw horizontal lines at different y positions to show perspective
        for y_percent in [0.1, 0.3, 0.5, 0.7, 0.9]:
            y_px = int(y_percent * self.height)
            pixels_per_cm = self.calibration.getPixelsPerCmAtPosition(y_percent)
            physical_distance_cm = self.width / pixels_per_cm

            # Draw line across frame
            cv2.line(overlay, (0, y_px), (self.width, y_px), (0, 255, 0), 2)

            # Add text showing physical distance
            text = f"y={y_percent:.1f}: {physical_distance_cm:.2f}cm across"
            cv2.putText(
                overlay,
                text,
                (10, y_px - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        # Draw vertical grid lines to show perspective distortion
        for x_percent in [0.2, 0.4, 0.6, 0.8]:
            x_px = int(x_percent * self.width)
            cv2.line(overlay, (x_px, 0), (x_px, self.height), (255, 0, 0), 1)

        # Add title
        cv2.putText(
            overlay,
            "Camera Calibration Visualization",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
        )

        filename = f".tmp/calibration_viz_{str(uuid.uuid4())[:8]}.jpg"
        cv2.imwrite(filename, overlay)
        self.global_config["logger"].info(
            f"Saved calibration visualization to {filename}"
        )


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
    calibration: CameraCalibration,
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
            calibration,
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
                calibration,
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
