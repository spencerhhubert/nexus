import time
import threading
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from ultralytics import YOLO
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.our_types import CameraType
from robot.our_types.vision_system import FeederState, MainCameraState
from robot.websocket_manager import WebSocketManager

# YOLO model class definitions
YOLO_CLASSES = {
    0: "object",
    1: "first_feeder",
    2: "second_feeder",
    3: "main_conveyor",
    4: "feeder_conveyor",
}

# Vision analysis constants
SECOND_FEEDER_DISTANCE_THRESHOLD = 30
MAIN_CONVEYOR_THRESHOLD = 0.5  # 50% object coverage for main conveyor detection
OBJECT_CENTER_THRESHOLD = 0.4  # 40% of frame center for object centering
RIGHT_SIDE_THRESHOLD = 0.3  # 30% from right edge for object positioning


class SegmentationModelManager:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
    ) -> None:
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

    def start(self) -> None:
        self.running = True

        self.main_thread = threading.Thread(target=self._trackMainCamera, daemon=True)

        self.feeder_thread = threading.Thread(
            target=self._trackFeederCamera, daemon=True
        )

        self.main_thread.start()
        self.feeder_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.main_thread:
            self.main_thread.join()
        if self.feeder_thread:
            self.feeder_thread.join()

    def _trackMainCamera(self) -> None:
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

                    self._broadcastFrame(CameraType.MAIN_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in main camera tracking: {e}")

    def _trackFeederCamera(self) -> None:
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

                    self._broadcastFrame(CameraType.FEEDER_CAMERA, annotated_frame)

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in feeder camera tracking: {e}")

    def _broadcastFrame(self, camera_type: CameraType, frame: np.ndarray) -> None:
        self.websocket_manager.broadcast_frame(camera_type, frame)

    def _getMainCameraResults(self) -> Any:
        with self.results_lock:
            return self.latest_main_results

    def _getFeederCameraResults(self) -> Any:
        with self.results_lock:
            return self.latest_feeder_results

    def _masksOverlap(self, mask1: np.ndarray, mask2: np.ndarray) -> bool:
        overlap = np.logical_and(mask1, mask2)
        return bool(np.any(overlap))

    def _getDetectedMasksByClass(self) -> Dict[str, List[np.ndarray]]:
        results = self._getFeederCameraResults()
        if not results or len(results) == 0:
            return {}

        masks_by_class: Dict[str, List[np.ndarray]] = {}

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

    def _getBoundingBoxFromMask(
        self, mask: np.ndarray
    ) -> Optional[Tuple[int, int, int, int]]:
        """Extract bounding box coordinates from a mask."""
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return None

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        return (cmin, rmin, cmax, rmax)  # (x1, y1, x2, y2)

    def _calculateBoundingBoxOverlap(
        self,
        bbox1: Optional[Tuple[int, int, int, int]],
        bbox2: Optional[Tuple[int, int, int, int]],
    ) -> float:
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

    def _calculateMinDistanceToMask(
        self, obj_bbox: Optional[Tuple[int, int, int, int]], mask: Optional[np.ndarray]
    ) -> float:
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

    def determineFeederState(self) -> Optional[FeederState]:
        """Determine feeder state based on object locations."""
        masks_by_class = self._getDetectedMasksByClass()

        object_masks = masks_by_class.get("object", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])

        self.logger.info(
            f"Object location check: {len(object_masks)} objects, {len(first_feeder_masks)} first_feeder, {len(second_feeder_masks)} second_feeder masks"
        )

        # Return None only if we can't find feeder masks
        if not first_feeder_masks and not second_feeder_masks:
            self.logger.info("No feeder masks detected")
            return None

        # If no objects detected, determine empty state
        if not object_masks:
            self.logger.info("No objects detected - first feeder empty")
            return FeederState.FIRST_FEEDER_EMPTY

        # Get bounding boxes for feeders
        first_feeder_bbox = None
        second_feeder_bbox = None

        if first_feeder_masks:
            first_feeder_bbox = self._getBoundingBoxFromMask(first_feeder_masks[0])

        if second_feeder_masks:
            second_feeder_bbox = self._getBoundingBoxFromMask(second_feeder_masks[0])

        # First pass: Check if ANY object needs second feeder cleared (priority)
        for i, obj_mask in enumerate(object_masks):
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if obj_bbox is None:
                continue

            # Calculate overlaps
            first_overlap = (
                self._calculateBoundingBoxOverlap(obj_bbox, first_feeder_bbox)
                if first_feeder_bbox
                else 0.0
            )
            second_overlap = (
                self._calculateBoundingBoxOverlap(obj_bbox, second_feeder_bbox)
                if second_feeder_bbox
                else 0.0
            )

            # Calculate distance to first feeder mask
            distance_to_first = (
                self._calculateMinDistanceToMask(obj_bbox, first_feeder_masks[0])
                if first_feeder_masks
                else float("inf")
            )

            self.logger.info(
                f"Object {i}: overlap with first={first_overlap:.3f}, second={second_overlap:.3f}, distance to first feeder={distance_to_first:.1f} pixels"
            )

            # Priority check: >50% within second feeder AND <50% within first feeder AND within distance threshold of first feeder
            if second_overlap > 0.5 and first_overlap < 0.5:
                if distance_to_first <= SECOND_FEEDER_DISTANCE_THRESHOLD:
                    self.logger.info(
                        f"Object {i} is >50% in second feeder ({second_overlap:.3f}), <50% in first ({first_overlap:.3f}), and within {SECOND_FEEDER_DISTANCE_THRESHOLD}px of first feeder ({distance_to_first:.1f}px) - running second feeder"
                    )
                    return FeederState.OBJECT_AT_END_OF_SECOND_FEEDER
                else:
                    self.logger.info(
                        f"Object {i} is >50% in second feeder but too far from first feeder ({distance_to_first:.1f}px > {SECOND_FEEDER_DISTANCE_THRESHOLD}px) - ignoring"
                    )

        # Second pass: Only if no objects need second feeder, check for first feeder
        for i, obj_mask in enumerate(object_masks):
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if obj_bbox is None:
                continue

            # Calculate overlaps (only need first overlap for this check)
            first_overlap = (
                self._calculateBoundingBoxOverlap(obj_bbox, first_feeder_bbox)
                if first_feeder_bbox
                else 0.0
            )

            # Check if >50% within first feeder
            if first_overlap > 0.5:
                self.logger.info(
                    f"Object {i} is >50% in first feeder ({first_overlap:.3f}) - running first feeder"
                )
                return FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

        # If we reach here, there are objects but they don't meet the criteria for feeder action
        # Need to determine if first feeder is empty or just no objects underneath exit
        if not first_feeder_masks:
            return FeederState.FIRST_FEEDER_EMPTY

        # Check if any objects have any overlap with first feeder
        first_feeder_bbox = self._getBoundingBoxFromMask(first_feeder_masks[0])
        for obj_mask in object_masks:
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if obj_bbox and first_feeder_bbox:
                overlap = self._calculateBoundingBoxOverlap(obj_bbox, first_feeder_bbox)
                if overlap > 0:
                    self.logger.info(
                        "Objects detected in first feeder but not underneath exit"
                    )
                    return FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

        self.logger.info("No objects detected in first feeder - feeder empty")
        return FeederState.FIRST_FEEDER_EMPTY

    def _getMainCameraMasksByClass(self) -> Dict[str, List[np.ndarray]]:
        """Get detected masks by class from main camera results."""
        results = self._getMainCameraResults()
        if not results or len(results) == 0:
            return {}

        masks_by_class: Dict[str, List[np.ndarray]] = {}
        for result in results:
            if result.masks is not None:
                for i, mask in enumerate(result.masks):
                    class_id = int(result.boxes[i].cls.item())
                    class_name = YOLO_CLASSES.get(class_id, f"unknown_{class_id}")
                    mask_data = mask.data[0].cpu().numpy()

                    if class_name not in masks_by_class:
                        masks_by_class[class_name] = []
                    masks_by_class[class_name].append(mask_data)

        return masks_by_class

    def determineMainCameraState(self) -> MainCameraState:
        """Determine main camera state based on object positions."""
        masks_by_class = self._getMainCameraMasksByClass()
        object_masks = masks_by_class.get("object", [])
        main_conveyor_masks = masks_by_class.get("main_conveyor", [])

        if not object_masks or not main_conveyor_masks:
            return MainCameraState.NO_OBJECT_UNDER_CAMERA

        main_conveyor_bbox = self._getBoundingBoxFromMask(main_conveyor_masks[0])
        if not main_conveyor_bbox:
            return MainCameraState.NO_OBJECT_UNDER_CAMERA

        # Get frame dimensions from the first object mask
        if object_masks:
            frame_height, frame_width = object_masks[0].shape
        else:
            return MainCameraState.NO_OBJECT_UNDER_CAMERA

        for obj_mask in object_masks:
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if not obj_bbox:
                continue

            # Check if object is >50% on main conveyor
            conveyor_overlap = self._calculateBoundingBoxOverlap(
                obj_bbox, main_conveyor_bbox
            )
            if conveyor_overlap > MAIN_CONVEYOR_THRESHOLD:
                # Object is on main conveyor, determine its position
                obj_center_x = (obj_bbox[0] + obj_bbox[2]) / 2
                frame_center_x = frame_width / 2
                right_edge_threshold = frame_width * (1 - RIGHT_SIDE_THRESHOLD)

                # Check if object is within 30% of right side
                if obj_center_x >= right_edge_threshold:
                    return (
                        MainCameraState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
                    )

                # Check if object is within 40% of center
                center_threshold = frame_width * OBJECT_CENTER_THRESHOLD / 2
                if abs(obj_center_x - frame_center_x) <= center_threshold:
                    return MainCameraState.OBJECT_CENTERED_UNDER_MAIN_CAMERA

        return MainCameraState.NO_OBJECT_UNDER_CAMERA

    def hasObjectOnMainConveyorInFeederView(self) -> bool:
        """Check if there's an object on main conveyor visible in feeder camera view."""
        feeder_masks = self._getDetectedMasksByClass()
        object_masks = feeder_masks.get("object", [])
        main_conveyor_masks = feeder_masks.get("main_conveyor", [])

        if not object_masks or not main_conveyor_masks:
            return False

        main_conveyor_bbox = self._getBoundingBoxFromMask(main_conveyor_masks[0])
        if not main_conveyor_bbox:
            return False

        for obj_mask in object_masks:
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if obj_bbox and main_conveyor_bbox:
                conveyor_overlap = self._calculateBoundingBoxOverlap(
                    obj_bbox, main_conveyor_bbox
                )
                if conveyor_overlap > MAIN_CONVEYOR_THRESHOLD:
                    return True

        return False
