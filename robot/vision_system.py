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

    def getBoundingBoxFromMask(self, mask):
        """Extract bounding box coordinates from a mask."""
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return None

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        return (cmin, rmin, cmax, rmax)  # (x1, y1, x2, y2)

    def calculateBoundingBoxOverlap(self, bbox1, bbox2):
        """Calculate what percentage of bbox1 is within bbox2."""
        if bbox1 is None or bbox2 is None:
            return 0.0

        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calculate intersection
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)

        if x1_inter >= x2_inter or y1_inter >= y2_inter:
            return 0.0

        # Calculate areas
        intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)

        if bbox1_area == 0:
            return 0.0

        return intersection_area / bbox1_area

    def calculateMinDistanceToMask(self, obj_bbox, mask):
        """Calculate minimum distance from object bounding box to any pixel in the mask."""
        if obj_bbox is None or mask is None:
            return float("inf")

        # Get object bounding box coordinates
        x1_obj, y1_obj, x2_obj, y2_obj = obj_bbox

        # Find all pixels in the mask
        mask_pixels = np.where(mask)
        if len(mask_pixels[0]) == 0:
            return float("inf")

        # Convert to (y, x) coordinates
        mask_y, mask_x = mask_pixels

        # Calculate minimum distance from bounding box to any mask pixel
        min_distance = float("inf")

        for my, mx in zip(mask_y, mask_x):
            # Distance from point to rectangle
            dx = max(x1_obj - mx, 0, mx - x2_obj)
            dy = max(y1_obj - my, 0, my - y2_obj)
            distance = np.sqrt(dx * dx + dy * dy)
            min_distance = min(min_distance, distance)

        return min_distance

    def determineObjectLocation(self):
        """Determine if objects are on 'first', 'second', or 'none' of the feeders using bounding box overlap."""
        masks_by_class = self.getDetectedMasksByClass()

        object_masks = masks_by_class.get("object", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])

        self.logger.info(
            f"Object location check: {len(object_masks)} objects, {len(first_feeder_masks)} first_feeder, {len(second_feeder_masks)} second_feeder masks"
        )

        if not object_masks:
            self.logger.info("No objects detected")
            return "none"

        if not first_feeder_masks and not second_feeder_masks:
            self.logger.info("No feeder masks detected")
            return "none"

        # Get bounding boxes for feeders
        first_feeder_bbox = None
        second_feeder_bbox = None

        if first_feeder_masks:
            first_feeder_bbox = self.getBoundingBoxFromMask(first_feeder_masks[0])

        if second_feeder_masks:
            second_feeder_bbox = self.getBoundingBoxFromMask(second_feeder_masks[0])

        # First pass: Check if ANY object needs second feeder cleared (priority)
        for i, obj_mask in enumerate(object_masks):
            obj_bbox = self.getBoundingBoxFromMask(obj_mask)
            if obj_bbox is None:
                continue

            # Calculate overlaps
            first_overlap = (
                self.calculateBoundingBoxOverlap(obj_bbox, first_feeder_bbox)
                if first_feeder_bbox
                else 0.0
            )
            second_overlap = (
                self.calculateBoundingBoxOverlap(obj_bbox, second_feeder_bbox)
                if second_feeder_bbox
                else 0.0
            )

            # Calculate distance to first feeder mask
            distance_to_first = (
                self.calculateMinDistanceToMask(obj_bbox, first_feeder_masks[0])
                if first_feeder_masks
                else float("inf")
            )

            self.logger.info(
                f"Object {i}: overlap with first={first_overlap:.3f}, second={second_overlap:.3f}, distance to first feeder={distance_to_first:.1f} pixels"
            )

            # Priority check: >50% within second feeder AND <50% within first feeder AND within distance threshold of first feeder
            if second_overlap > 0.5 and first_overlap < 0.5:
                # Import threshold from state machine (we'll pass it as parameter)
                from robot.sorting_state_machine import SECOND_FEEDER_DISTANCE_THRESHOLD

                if distance_to_first <= SECOND_FEEDER_DISTANCE_THRESHOLD:
                    self.logger.info(
                        f"Object {i} is >50% in second feeder ({second_overlap:.3f}), <50% in first ({first_overlap:.3f}), and within {SECOND_FEEDER_DISTANCE_THRESHOLD}px of first feeder ({distance_to_first:.1f}px) - running second feeder"
                    )
                    return "second"
                else:
                    self.logger.info(
                        f"Object {i} is >50% in second feeder but too far from first feeder ({distance_to_first:.1f}px > {SECOND_FEEDER_DISTANCE_THRESHOLD}px) - ignoring"
                    )

        # Second pass: Only if no objects need second feeder, check for first feeder
        for i, obj_mask in enumerate(object_masks):
            obj_bbox = self.getBoundingBoxFromMask(obj_mask)
            if obj_bbox is None:
                continue

            # Calculate overlaps (only need first overlap for this check)
            first_overlap = (
                self.calculateBoundingBoxOverlap(obj_bbox, first_feeder_bbox)
                if first_feeder_bbox
                else 0.0
            )

            # Check if >50% within first feeder
            if first_overlap > 0.5:
                self.logger.info(
                    f"Object {i} is >50% in first feeder ({first_overlap:.3f}) - running first feeder"
                )
                return "first"

        self.logger.info("No objects meet criteria for feeder action")
        return "none"
