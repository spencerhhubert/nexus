import time
import threading
import numpy as np
from typing import Optional
from ultralytics import YOLO
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.our_types import CameraType
from robot.websocket_manager import WebSocketManager

# YOLO model class definitions
YOLO_CLASSES = {
    0: "object",
    1: "first_feeder",
    2: "second_feeder",
    3: "main_conveyor",
    4: "feeder_conveyor",
}


class SegmentationModelManager:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
    ):
        self.global_config = global_config
        self.irl_interface = irl_interface
        self.logger = global_config["logger"]
        self.websocket_manager = websocket_manager

        self.main_camera = irl_interface["main_camera"]
        self.feeder_camera = irl_interface["feeder_camera"]

        if global_config["yolo_weights_path"]:
            self.model_path = global_config["yolo_weights_path"]
        else:
            self.logger.error(
                "No YOLO model path found: 'yolo_weights_path' is missing or empty in global_config"
            )
            raise ValueError(
                "No YOLO model path found: 'yolo_weights_path' is missing or empty in global_config"
            )

        self.latest_main_results = None
        self.latest_feeder_results = None
        self.results_lock = threading.Lock()

        self.running = False
        self.main_thread = None
        self.feeder_thread = None

    def start(self):
        self.running = True

        self.main_thread = threading.Thread(target=self.trackMainCamera, daemon=True)

        self.feeder_thread = threading.Thread(
            target=self.trackFeederCamera, daemon=True
        )

        self.main_thread.start()
        self.feeder_thread.start()

    def stop(self):
        self.running = False
        if self.main_thread:
            self.main_thread.join()
        if self.feeder_thread:
            self.feeder_thread.join()

    def trackMainCamera(self):
        model = YOLO(self.model_path)
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.main_camera.captureFrame()

                if frame is not None:
                    results = model.track(frame, persist=True)
                    # results = model(frame)

                    with self.results_lock:
                        self.latest_main_results = results

                    if results and len(results) > 0:
                        annotated_frame = results[0].plot()
                    else:
                        annotated_frame = frame

                    self.broadcastFrame(CameraType.MAIN_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in main camera tracking: {e}")

    def trackFeederCamera(self):
        model = YOLO(self.model_path)
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.feeder_camera.captureFrame()

                if frame is not None:
                    results = model.track(frame, persist=True)

                    with self.results_lock:
                        self.latest_feeder_results = results

                    if results and len(results) > 0:
                        annotated_frame = results[0].plot()
                    else:
                        annotated_frame = frame

                    self.broadcastFrame(CameraType.FEEDER_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in feeder camera tracking: {e}")

    def broadcastFrame(self, camera_type: CameraType, frame):
        self.websocket_manager.broadcast_frame(camera_type, frame)

    def getMainCameraResults(self):
        with self.results_lock:
            return self.latest_main_results

    def getFeederCameraResults(self):
        with self.results_lock:
            return self.latest_feeder_results

    def masksOverlap(self, mask1, mask2):
        overlap = np.logical_and(mask1, mask2)
        return np.any(overlap)

    def getDetectedMasksByClass(self):
        results = self.getFeederCameraResults()
        if not results or len(results) == 0:
            return {}

        masks_by_class = {}

        for result in results:
            if result.masks is not None:
                for i, mask in enumerate(result.masks):
                    class_id = int(result.boxes[i].cls.item())
                    class_name = YOLO_CLASSES.get(class_id, f"unknown_{class_id}")
                    mask_data = (
                        mask.data[0].cpu().numpy()
                    )  # Get the mask as numpy array

                    if class_name not in masks_by_class:
                        masks_by_class[class_name] = []
                    masks_by_class[class_name].append(mask_data)

        return masks_by_class

    def hasObjectMostlyOnFirstFeeder(self):
        masks_by_class = self.getDetectedMasksByClass()

        object_masks = masks_by_class.get("object", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])

        if not object_masks or not first_feeder_masks:
            return False

        for obj_mask in object_masks:
            for feeder_mask in first_feeder_masks:
                overlap = np.logical_and(obj_mask, feeder_mask)
                overlap_ratio = np.sum(overlap) / np.sum(obj_mask)
                if overlap_ratio > 0.5:  # Object is mostly on this feeder
                    return True
        return False

    def hasObjectMostlyOnSecondFeeder(self):
        masks_by_class = self.getDetectedMasksByClass()

        object_masks = masks_by_class.get("object", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])

        if not object_masks or not second_feeder_masks:
            return False

        for obj_mask in object_masks:
            for feeder_mask in second_feeder_masks:
                overlap = np.logical_and(obj_mask, feeder_mask)
                overlap_ratio = np.sum(overlap) / np.sum(obj_mask)
                if overlap_ratio > 0.5:  # Object is mostly on this feeder
                    return True
        return False
