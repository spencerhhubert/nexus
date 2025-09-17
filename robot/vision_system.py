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


class VisionSystem:
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

        self.main_thread = threading.Thread(target=self._track_main_camera, daemon=True)

        self.feeder_thread = threading.Thread(
            target=self._track_feeder_camera, daemon=True
        )

        self.main_thread.start()
        self.feeder_thread.start()

    def stop(self):
        self.running = False
        if self.main_thread:
            self.main_thread.join()
        if self.feeder_thread:
            self.feeder_thread.join()

    def _track_main_camera(self):
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

                    self.broadcast_frame(CameraType.MAIN_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in main camera tracking: {e}")

    def _track_feeder_camera(self):
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

                    self.broadcast_frame(CameraType.FEEDER_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in feeder camera tracking: {e}")

    def broadcast_frame(self, camera_type: CameraType, frame):
        self.websocket_manager.broadcast_frame(camera_type, frame)

    def get_main_camera_results(self):
        with self.results_lock:
            return self.latest_main_results

    def get_feeder_camera_results(self):
        with self.results_lock:
            return self.latest_feeder_results

    def _masks_overlap(self, mask1, mask2):
        """Check if two segmentation masks overlap"""
        # Check if there's any pixel overlap between the two masks
        overlap = np.logical_and(mask1, mask2)
        return np.any(overlap)

    def _get_detected_masks_by_class(self):
        """Get all detected masks organized by class from feeder camera"""
        results = self.get_feeder_camera_results()
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

    def has_object_on_first_feeder(self):
        """Check if any object mask overlaps with any first_feeder mask"""
        masks_by_class = self._get_detected_masks_by_class()

        object_masks = masks_by_class.get("object", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])

        if not object_masks or not first_feeder_masks:
            return False

        # Check for overlaps between any object mask and any first feeder mask
        for obj_mask in object_masks:
            for feeder_mask in first_feeder_masks:
                if self._masks_overlap(obj_mask, feeder_mask):
                    return True
        return False

    def has_object_on_second_feeder(self):
        """Check if any object mask overlaps with any second_feeder mask"""
        masks_by_class = self._get_detected_masks_by_class()

        object_masks = masks_by_class.get("object", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])

        if not object_masks or not second_feeder_masks:
            return False

        # Check for overlaps between any object mask and any second feeder mask
        for obj_mask in object_masks:
            for feeder_mask in second_feeder_masks:
                if self._masks_overlap(obj_mask, feeder_mask):
                    return True
        return False
