import time
import threading
import numpy as np
from typing import Optional
from ultralytics import YOLO
from scipy import ndimage
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

    def calculateSurroundingScore(self, obj_mask, feeder_mask, threshold=3):
        """Calculate how much of the object's perimeter is surrounded by the feeder mask."""
        if obj_mask.shape != feeder_mask.shape:
            return 0.0

        # Convert masks to boolean arrays
        obj_mask = obj_mask.astype(bool)
        feeder_mask = feeder_mask.astype(bool)

        obj_pixels = np.sum(obj_mask)
        if obj_pixels == 0:
            return 0.0

        # Create a dilated version of the object mask
        structure = np.ones((threshold*2+1, threshold*2+1))
        dilated_obj = ndimage.binary_dilation(obj_mask, structure=structure)

        # Find the "border" area (dilated - original)
        border_area = dilated_obj & ~obj_mask

        # Count how much of this border area overlaps with feeder
        surrounded_border = np.sum(border_area & feeder_mask)
        total_border = np.sum(border_area)

        if total_border == 0:
            return 0.0

        return surrounded_border / total_border

    def determineObjectLocation(self):
        """Determine if objects are on 'first', 'second', or 'none' of the feeders."""
        masks_by_class = self.getDetectedMasksByClass()

        object_masks = masks_by_class.get("object", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])

        self.logger.info(f"Object location check: {len(object_masks)} objects, {len(first_feeder_masks)} first_feeder, {len(second_feeder_masks)} second_feeder masks")

        if not object_masks:
            self.logger.info("No objects detected")
            return 'none'

        if not first_feeder_masks and not second_feeder_masks:
            self.logger.info("No feeder masks detected")
            return 'none'

        # Check each object against both feeders
        max_second_score = 0.0
        max_first_score = 0.0

        for i, obj_mask in enumerate(object_masks):
            # Check against second feeder masks (higher priority)
            for j, second_mask in enumerate(second_feeder_masks):
                score = self.calculateSurroundingScore(obj_mask, second_mask)
                self.logger.info(f"Object {i} vs Second Feeder {j}: surrounding score = {score:.3f}")
                max_second_score = max(max_second_score, score)

            # Check against first feeder masks
            for j, first_mask in enumerate(first_feeder_masks):
                score = self.calculateSurroundingScore(obj_mask, first_mask)
                self.logger.info(f"Object {i} vs First Feeder {j}: surrounding score = {score:.3f}")
                max_first_score = max(max_first_score, score)

        # Decision logic: second feeder takes priority
        if max_second_score > 0.3:  # Threshold for being "on" the feeder
            self.logger.info(f"Objects detected on second feeder (score: {max_second_score:.3f})")
            return 'second'
        elif max_first_score > 0.3:
            self.logger.info(f"Objects detected on first feeder (score: {max_first_score:.3f})")
            return 'first'
        else:
            self.logger.info(f"No objects sufficiently on feeders (second: {max_second_score:.3f}, first: {max_first_score:.3f})")
            return 'none'

