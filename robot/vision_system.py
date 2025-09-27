import time
import threading
import numpy as np
import cv2
from typing import Optional, Dict, List, Tuple, Any
from ultralytics import YOLO
import logging

logging.getLogger("ultralytics").setLevel(logging.WARNING)
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.our_types import CameraType
from robot.our_types.vision_system import (
    FeederState,
    MainCameraState,
    CameraPerformanceMetrics,
    FeederRegion,
    RegionReading,
    ObjectDetection,
)
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
SECOND_FEEDER_DISTANCE_THRESHOLD = 20
MAIN_CONVEYOR_THRESHOLD = 0.7
OBJECT_CENTER_THRESHOLD = 0.4
RIGHT_SIDE_THRESHOLD = 0.3
MARGIN_FOR_MAIN_CONVEYOR_BOUNDING_BOX_PX = -40


class SegmentationModelManager:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
    ) -> None:
        self.global_config = global_config
        self.irl_interface = irl_interface
        self.logger = global_config["logger"].ctx(system="vision_system")
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

        # Frame tracking for classification
        self.main_camera_frames: List[Tuple[np.ndarray, Any]] = []
        self.frame_history_lock = threading.Lock()
        self.max_frame_history = 30

        self.running = False
        self.main_thread = None
        self.feeder_thread = None

        # Performance tracking
        self.main_frame_times = []
        self.feeder_frame_times = []
        self.main_processing_times = []
        self.feeder_processing_times = []
        self.performance_lock = threading.Lock()

        # Object detection tracking
        self.object_detections: List[ObjectDetection] = []
        self.detection_lock = threading.Lock()

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
        if self.global_config.get("tensor_device"):
            model.to(self.global_config["tensor_device"])
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.main_camera.captureFrame()

                if frame is not None:
                    start_time = time.time()
                    results = model.track(frame, persist=True, tracker="bytetrack.yaml")
                    # results = model(frame)
                    processing_time = time.time() - start_time

                    self._trackPerformance(CameraType.MAIN_CAMERA, processing_time)

                    with self.results_lock:
                        self.latest_main_results = results

                    # Store frame and results for classification
                    with self.frame_history_lock:
                        self.main_camera_frames.append((frame.copy(), results))
                        if len(self.main_camera_frames) > self.max_frame_history:
                            self.main_camera_frames.pop(0)

                    if results and len(results) > 0:
                        annotated_frame = results[0].plot()
                    else:
                        annotated_frame = frame

                    self._broadcastFrame(CameraType.MAIN_CAMERA, annotated_frame)

                    # Broadcast performance metrics every 30 frames
                    if frame_count % 30 == 0:
                        metrics = self._calculatePerformanceMetrics(
                            CameraType.MAIN_CAMERA
                        )
                        self.websocket_manager.broadcast_camera_performance(
                            CameraType.MAIN_CAMERA, metrics
                        )

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in main camera tracking: {e}")

    def _trackFeederCamera(self) -> None:
        model = YOLO(self.model_path)
        if self.global_config.get("tensor_device"):
            model.to(self.global_config["tensor_device"])
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.feeder_camera.captureFrame()

                if frame is not None:
                    start_time = time.time()
                    results = model.track(frame, persist=True, tracker="bytetrack.yaml")
                    processing_time = time.time() - start_time

                    self._trackPerformance(CameraType.FEEDER_CAMERA, processing_time)

                    with self.results_lock:
                        self.latest_feeder_results = results

                    # Update object detections tracking
                    self._updateObjectDetections()

                    if results and len(results) > 0:
                        annotated_frame = results[0].plot()
                    else:
                        annotated_frame = frame

                    self._broadcastFrame(CameraType.FEEDER_CAMERA, annotated_frame)

                    # Broadcast performance metrics every 30 frames
                    if frame_count % 30 == 0:
                        metrics = self._calculatePerformanceMetrics(
                            CameraType.FEEDER_CAMERA
                        )
                        self.websocket_manager.broadcast_camera_performance(
                            CameraType.FEEDER_CAMERA, metrics
                        )

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in feeder camera tracking: {e}")

    def _broadcastFrame(self, camera_type: CameraType, frame: np.ndarray) -> None:
        self.websocket_manager.broadcast_frame(camera_type, frame)

    def _trackPerformance(
        self, camera_type: CameraType, processing_time: float
    ) -> None:
        current_time = time.time()

        with self.performance_lock:
            if camera_type == CameraType.MAIN_CAMERA:
                self.main_frame_times.append(current_time)
                self.main_processing_times.append(processing_time)

                # Keep only last 5 seconds of data
                cutoff_time = current_time - 5.0
                while self.main_frame_times and self.main_frame_times[0] < cutoff_time:
                    self.main_frame_times.pop(0)
                    self.main_processing_times.pop(0)

            else:  # FEEDER_CAMERA
                self.feeder_frame_times.append(current_time)
                self.feeder_processing_times.append(processing_time)

                # Keep only last 5 seconds of data
                cutoff_time = current_time - 5.0
                while (
                    self.feeder_frame_times and self.feeder_frame_times[0] < cutoff_time
                ):
                    self.feeder_frame_times.pop(0)
                    self.feeder_processing_times.pop(0)

    def _calculatePerformanceMetrics(
        self, camera_type: CameraType
    ) -> CameraPerformanceMetrics:
        current_time = time.time()

        with self.performance_lock:
            if camera_type == CameraType.MAIN_CAMERA:
                frame_times = self.main_frame_times
                processing_times = self.main_processing_times
            else:
                frame_times = self.feeder_frame_times
                processing_times = self.feeder_processing_times

            if len(frame_times) < 2:
                return CameraPerformanceMetrics(
                    fps_1s=0.0, fps_5s=0.0, latency_1s=0.0, latency_5s=0.0
                )

            # Calculate FPS for 1s and 5s windows
            cutoff_1s = current_time - 1.0
            cutoff_5s = current_time - 5.0

            frames_1s = sum(1 for t in frame_times if t >= cutoff_1s)
            frames_5s = len(frame_times)

            fps_1s = frames_1s / 1.0 if frames_1s > 0 else 0.0
            fps_5s = frames_5s / 5.0 if frames_5s > 0 else 0.0

            # Calculate average latency for 1s and 5s windows
            processing_1s = [
                p for i, p in enumerate(processing_times) if frame_times[i] >= cutoff_1s
            ]
            processing_5s = processing_times

            latency_1s = (
                sum(processing_1s) / len(processing_1s) * 1000 if processing_1s else 0.0
            )
            latency_5s = (
                sum(processing_5s) / len(processing_5s) * 1000 if processing_5s else 0.0
            )

            return CameraPerformanceMetrics(
                fps_1s=fps_1s,
                fps_5s=fps_5s,
                latency_1s=latency_1s,
                latency_5s=latency_5s,
            )

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
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return None

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        return (cmin, rmin, cmax, rmax)

    def _applyMarginToBoundingBox(
        self,
        bbox: Tuple[int, int, int, int],
        margin_px: int,
        frame_shape: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox

        if margin_px >= 0:
            new_x1 = x1 - margin_px
            new_y1 = y1 - margin_px
            new_x2 = x2 + margin_px
            new_y2 = y2 + margin_px
        else:
            new_x1 = x1 - margin_px
            new_y1 = y1 - margin_px
            new_x2 = x2 + margin_px
            new_y2 = y2 + margin_px

        if frame_shape:
            frame_height, frame_width = frame_shape
            new_x1 = max(0, min(new_x1, frame_width - 1))
            new_y1 = max(0, min(new_y1, frame_height - 1))
            new_x2 = max(0, min(new_x2, frame_width - 1))
            new_y2 = max(0, min(new_y2, frame_height - 1))

        return (new_x1, new_y1, new_x2, new_y2)

    def _calculateBoundingBoxOverlap(
        self,
        bbox1: Optional[Tuple[int, int, int, int]],
        bbox2: Optional[Tuple[int, int, int, int]],
    ) -> float:
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

    def _calculateMaskEdgeProximity(
        self, object_mask: np.ndarray, target_mask: np.ndarray, proximity_px: int = 3
    ) -> float:
        if object_mask.shape != target_mask.shape:
            return 0.0

        # Create a dilated version of the target mask (expand edges by proximity_px)
        kernel = np.ones((proximity_px * 2 + 1, proximity_px * 2 + 1), np.uint8)
        dilated_target = cv2.dilate(target_mask.astype(np.uint8), kernel, iterations=1)

        # Count object pixels within the dilated target area
        object_pixels_near_target = np.logical_and(object_mask, dilated_target)

        # Calculate percentage
        total_object_pixels = np.sum(object_mask)
        if total_object_pixels == 0:
            return 0.0

        near_target_pixels = np.sum(object_pixels_near_target)
        return near_target_pixels / total_object_pixels

    def _analyzeObjectRegions(
        self, obj_mask: np.ndarray, masks_by_class: Dict[str, List[np.ndarray]]
    ) -> FeederRegion:
        obj_bbox = self._getBoundingBoxFromMask(obj_mask)
        if obj_bbox is None:
            return FeederRegion.UNKNOWN

        # Check main conveyor first
        main_conveyor_masks = masks_by_class.get("main_conveyor", [])
        if main_conveyor_masks:
            total_main_conveyor_proximity = 0.0
            for main_conveyor_mask in main_conveyor_masks:
                main_conveyor_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, main_conveyor_mask
                )
                total_main_conveyor_proximity += main_conveyor_proximity

            if total_main_conveyor_proximity > MAIN_CONVEYOR_THRESHOLD:
                return FeederRegion.MAIN_CONVEYOR

        # Check second feeder masks
        second_feeder_masks = masks_by_class.get("second_feeder", [])
        if second_feeder_masks:
            total_second_proximity = 0.0
            for second_feeder_mask in second_feeder_masks:
                second_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, second_feeder_mask
                )
                total_second_proximity += second_proximity

            if total_second_proximity > 0.5:
                # Check if at exit of second feeder
                main_conveyor_masks = masks_by_class.get("main_conveyor", [])
                if main_conveyor_masks:
                    total_bbox_overlap = 0.0
                    for main_conveyor_mask in main_conveyor_masks:
                        main_conveyor_bbox = self._getBoundingBoxFromMask(
                            main_conveyor_mask
                        )
                        if main_conveyor_bbox:
                            main_conveyor_bbox_with_margin = (
                                self._applyMarginToBoundingBox(
                                    main_conveyor_bbox,
                                    MARGIN_FOR_MAIN_CONVEYOR_BOUNDING_BOX_PX,
                                    (
                                        main_conveyor_mask.shape[0],
                                        main_conveyor_mask.shape[1],
                                    ),
                                )
                            )
                            bbox_overlap = self._calculateBoundingBoxOverlap(
                                obj_bbox, main_conveyor_bbox_with_margin
                            )
                            total_bbox_overlap += bbox_overlap

                    if total_bbox_overlap > MAIN_CONVEYOR_THRESHOLD:
                        return FeederRegion.EXIT_OF_SECOND_FEEDER

                return FeederRegion.SECOND_FEEDER_MASK

        # Check first feeder masks
        first_feeder_masks = masks_by_class.get("first_feeder", [])
        if first_feeder_masks:
            total_first_proximity = 0.0
            for first_feeder_mask in first_feeder_masks:
                first_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, first_feeder_mask
                )
                total_first_proximity += first_proximity

            if total_first_proximity > 0.5:
                # Check if under exit of second feeder (near first feeder)
                if second_feeder_masks:
                    min_distance_to_first = float("inf")
                    for first_feeder_mask in first_feeder_masks:
                        distance_to_first = self._calculateMinDistanceToMask(
                            obj_bbox, first_feeder_mask
                        )
                        min_distance_to_first = min(
                            min_distance_to_first, distance_to_first
                        )

                    if min_distance_to_first < SECOND_FEEDER_DISTANCE_THRESHOLD:
                        return FeederRegion.UNDER_EXIT_OF_SECOND_FEEDER

                return FeederRegion.FIRST_FEEDER_MASK

        return FeederRegion.UNKNOWN

    def _updateObjectDetections(self) -> None:
        # note: _updateObjectDetections is called by both the main and feeder camera loop, but it only looks at masks in the feeder camera
        masks_by_class = self._getDetectedMasksByClass()
        object_masks = masks_by_class.get("object", [])

        if not object_masks:
            return

        current_time = time.time()

        with self.detection_lock:
            # For now, just add new detections for each object
            # Future enhancement: match with existing tracked objects
            for obj_mask in object_masks:
                region = self._analyzeObjectRegions(obj_mask, masks_by_class)
                region_reading = RegionReading(timestamp=current_time, region=region)

                # Simple approach: create new detection for each object
                # In future, this should match with tracked objects by ID
                detection = ObjectDetection()
                detection.region_readings.append(region_reading)
                self.object_detections.append(detection)

            # Cleanup old detections (keep only last 5 seconds)
            cutoff_time = current_time - 5.0
            self.object_detections = [
                detection
                for detection in self.object_detections
                if detection.region_readings
                and detection.region_readings[-1].timestamp >= cutoff_time
            ]

    def _checkForObjectTransitions(self, window_ms: float = 500.0) -> bool:
        window_seconds = window_ms / 1000.0
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        with self.detection_lock:
            for detection in self.object_detections:
                recent_readings = [
                    reading
                    for reading in detection.region_readings
                    if reading.timestamp >= cutoff_time
                ]

                if not recent_readings:
                    continue

                # Check if object went to main conveyor
                for reading in recent_readings:
                    if reading.region == FeederRegion.MAIN_CONVEYOR:
                        return True

                # Check if object went MIA from exit of second feeder
                exit_readings = [
                    reading
                    for reading in recent_readings
                    if reading.region == FeederRegion.EXIT_OF_SECOND_FEEDER
                ]

                if exit_readings:
                    # Check if there are subsequent readings showing the object disappeared
                    last_exit_time = max(reading.timestamp for reading in exit_readings)
                    post_exit_readings = [
                        reading
                        for reading in recent_readings
                        if reading.timestamp > last_exit_time
                    ]

                    # If no readings after being at exit, object went MIA
                    if not post_exit_readings:
                        return True

        return False

    def determineFeederState(self) -> Optional[FeederState]:
        # Future enhancement: use object transition detection
        # object_transition_detected = self._checkForObjectTransitions(window_ms=500.0)
        # if object_transition_detected:
        #     return FeederState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA

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

        # If no objects detected anywhere, return None (can't determine state)
        if not object_masks:
            self.logger.info("No objects detected anywhere")
            return None

        # PHASE 1: Classify all objects by their primary location
        objects_on_main_conveyor = []
        objects_on_second_feeder = []
        objects_on_first_feeder = []
        objects_at_end_of_second_feeder = []

        for i, obj_mask in enumerate(object_masks):
            obj_bbox = self._getBoundingBoxFromMask(obj_mask)
            if obj_bbox is None:
                continue

            # Check for objects at end of second feeder (bbox >50% in main conveyor BUT not touching conveyor surface)
            main_conveyor_masks = masks_by_class.get("main_conveyor", [])
            if main_conveyor_masks:
                total_bbox_overlap = 0.0
                total_main_conveyor_proximity = 0.0

                for main_conveyor_mask in main_conveyor_masks:
                    main_conveyor_bbox = self._getBoundingBoxFromMask(
                        main_conveyor_mask
                    )
                    if main_conveyor_bbox:
                        main_conveyor_bbox_with_margin = self._applyMarginToBoundingBox(
                            main_conveyor_bbox,
                            MARGIN_FOR_MAIN_CONVEYOR_BOUNDING_BOX_PX,
                            (main_conveyor_mask.shape[0], main_conveyor_mask.shape[1]),
                        )
                        bbox_overlap = self._calculateBoundingBoxOverlap(
                            obj_bbox, main_conveyor_bbox_with_margin
                        )
                        total_bbox_overlap += bbox_overlap

                    main_conveyor_proximity = self._calculateMaskEdgeProximity(
                        obj_mask, main_conveyor_mask
                    )
                    total_main_conveyor_proximity += main_conveyor_proximity

                if (
                    total_bbox_overlap > MAIN_CONVEYOR_THRESHOLD
                    and total_main_conveyor_proximity <= MAIN_CONVEYOR_THRESHOLD
                ):
                    objects_at_end_of_second_feeder.append(i)
                    self.logger.info(
                        f"Object {i}: at end of second feeder (bbox_overlap={total_bbox_overlap:.3f}, proximity={total_main_conveyor_proximity:.3f})"
                    )
                    continue
                elif total_main_conveyor_proximity > MAIN_CONVEYOR_THRESHOLD:
                    objects_on_main_conveyor.append(i)
                    self.logger.info(
                        f"Object {i}: on main conveyor (proximity={total_main_conveyor_proximity:.3f})"
                    )
                    continue

            # Check second feeder (>50% surrounded)
            if second_feeder_masks:
                total_second_proximity = 0.0
                for second_feeder_mask in second_feeder_masks:
                    second_proximity = self._calculateMaskEdgeProximity(
                        obj_mask, second_feeder_mask
                    )
                    total_second_proximity += second_proximity

                if total_second_proximity > 0.5:
                    objects_on_second_feeder.append(
                        (i, obj_bbox, total_second_proximity)
                    )
                    self.logger.info(
                        f"Object {i}: on second feeder (surrounded={total_second_proximity:.3f})"
                    )
                    continue

            # Check first feeder (>50% proximity)
            if first_feeder_masks:
                total_first_proximity = 0.0
                for first_feeder_mask in first_feeder_masks:
                    first_proximity = self._calculateMaskEdgeProximity(
                        obj_mask, first_feeder_mask
                    )
                    total_first_proximity += first_proximity

                if total_first_proximity > 0.5:
                    objects_on_first_feeder.append(i)
                    self.logger.info(
                        f"Object {i}: on first feeder (proximity={total_first_proximity:.3f})"
                    )

        if objects_on_main_conveyor:
            self.logger.info(
                f"Objects detected on main conveyor: {len(objects_on_main_conveyor)}"
            )
            return FeederState.OBJECT_ON_MAIN_CONVEYOR

        if objects_at_end_of_second_feeder:
            self.logger.info(
                f"Objects detected at end of second feeder: {len(objects_at_end_of_second_feeder)}"
            )
            return FeederState.OBJECT_AT_END_OF_SECOND_FEEDER

        if not objects_on_first_feeder:
            self.logger.info("First feeder empty")
            return FeederState.FIRST_FEEDER_EMPTY

        dropzone_clear = True
        if objects_on_second_feeder and first_feeder_masks:
            for i, obj_bbox, proximity in objects_on_second_feeder:
                min_distance_to_first = float("inf")
                for first_feeder_mask in first_feeder_masks:
                    distance_to_first = self._calculateMinDistanceToMask(
                        obj_bbox, first_feeder_mask
                    )
                    min_distance_to_first = min(
                        min_distance_to_first, distance_to_first
                    )

                if min_distance_to_first < SECOND_FEEDER_DISTANCE_THRESHOLD:
                    dropzone_clear = False
                    self.logger.info(
                        f"Object {i} in dropzone: {min_distance_to_first:.1f}px from first feeder mask"
                    )
                    break

        if dropzone_clear:
            self.logger.info("Dropzone clear - running first feeder")
            return FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        else:
            self.logger.info("Dropzone blocked - running second feeder")
            return FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER

    def _getMainCameraMasksByClass(self) -> Dict[str, List[np.ndarray]]:
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
        masks_by_class = self._getMainCameraMasksByClass()
        object_masks = masks_by_class.get("object", [])
        main_conveyor_masks = masks_by_class.get("main_conveyor", [])

        if not object_masks or not main_conveyor_masks:
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

            # Check if object is >50% on main conveyor (sum across all conveyor masks)
            total_conveyor_overlap = 0.0
            for main_conveyor_mask in main_conveyor_masks:
                main_conveyor_bbox = self._getBoundingBoxFromMask(main_conveyor_mask)
                if main_conveyor_bbox:
                    main_conveyor_bbox_with_margin = self._applyMarginToBoundingBox(
                        main_conveyor_bbox,
                        MARGIN_FOR_MAIN_CONVEYOR_BOUNDING_BOX_PX,
                        (main_conveyor_mask.shape[0], main_conveyor_mask.shape[1]),
                    )
                    conveyor_overlap = self._calculateBoundingBoxOverlap(
                        obj_bbox, main_conveyor_bbox_with_margin
                    )
                    total_conveyor_overlap += conveyor_overlap

            if total_conveyor_overlap > MAIN_CONVEYOR_THRESHOLD:
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
        feeder_masks = self._getDetectedMasksByClass()
        object_masks = feeder_masks.get("object", [])
        main_conveyor_masks = feeder_masks.get("main_conveyor", [])

        if not object_masks or not main_conveyor_masks:
            return False

        for obj_mask in object_masks:
            total_edge_proximity = 0.0
            for main_conveyor_mask in main_conveyor_masks:
                edge_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, main_conveyor_mask
                )
                total_edge_proximity += edge_proximity

            if total_edge_proximity > MAIN_CONVEYOR_THRESHOLD:
                return True

        return False

    def getFramesForClassification(self) -> List[np.ndarray]:
        with self.frame_history_lock:
            if not self.main_camera_frames:
                return []

            selected_frames = []

            # Add most recent frame
            recent_frame, _ = self.main_camera_frames[-1]
            selected_frames.append(recent_frame)

            # Find frames where object mask doesn't touch frame edges
            for frame, results in reversed(self.main_camera_frames[:-1]):
                if len(selected_frames) >= 6:
                    break

                if not results or len(results) == 0:
                    continue

                # Check if any object mask touches frame edges
                frame_touches_edge = False
                for result in results:
                    if result.masks is not None:
                        for mask in result.masks:
                            mask_data = mask.data[0].cpu().numpy()

                            # Check if mask touches any edge
                            if (
                                mask_data[0, :].any()  # Top edge
                                or mask_data[-1, :].any()  # Bottom edge
                                or mask_data[:, 0].any()  # Left edge
                                or mask_data[:, -1].any()
                            ):  # Right edge
                                frame_touches_edge = True
                                break
                    if frame_touches_edge:
                        break

                if not frame_touches_edge:
                    selected_frames.append(frame)

            self.logger.info(
                f"Selected {len(selected_frames)} frames for classification"
            )
            return selected_frames

    def getFramesForTrackId(self, track_id: str) -> List[np.ndarray]:
        with self.frame_history_lock:
            selected_frames = []

            for frame, results in self.main_camera_frames:
                if not results or len(results) == 0:
                    continue

                for result in results:
                    if (
                        result.masks is not None
                        and hasattr(result, "boxes")
                        and result.boxes.id is not None
                    ):
                        for i, mask in enumerate(result.masks):
                            if i < len(result.boxes.id):
                                current_track_id = str(int(result.boxes.id[i].item()))
                                class_id = int(result.boxes[i].cls.item())

                                if (
                                    current_track_id == track_id and class_id == 0
                                ):  # "object" class
                                    mask_data = mask.data[0].cpu().numpy()

                                    # Check if mask is completely in frame (not touching edges)
                                    if not (
                                        mask_data[0, :].any()
                                        or mask_data[-1, :].any()
                                        or mask_data[:, 0].any()
                                        or mask_data[:, -1].any()
                                    ):
                                        selected_frames.append(frame)
                                        break

            self.logger.info(
                f"Found {len(selected_frames)} complete frames for track ID {track_id}"
            )
            return selected_frames

    def getCurrentCenteredObjectId(self) -> Optional[str]:
        results = self._getMainCameraResults()
        if not results or len(results) == 0:
            return None

        masks_by_class = self._getMainCameraMasksByClass()
        object_masks = masks_by_class.get("object", [])
        main_conveyor_masks = masks_by_class.get("main_conveyor", [])

        if not object_masks or not main_conveyor_masks:
            return None

        main_conveyor_bbox = self._getBoundingBoxFromMask(main_conveyor_masks[0])
        if not main_conveyor_bbox:
            return None

        frame_height, frame_width = object_masks[0].shape

        for result in results:
            if (
                result.masks is not None
                and hasattr(result, "boxes")
                and result.boxes.id is not None
            ):
                for i, mask in enumerate(result.masks):
                    if i < len(result.boxes.id):
                        class_id = int(result.boxes[i].cls.item())
                        if class_id == 0:  # "object" class
                            track_id = str(int(result.boxes.id[i].item()))
                            mask_data = mask.data[0].cpu().numpy()
                            obj_bbox = self._getBoundingBoxFromMask(mask_data)

                            if obj_bbox:
                                conveyor_overlap = self._calculateBoundingBoxOverlap(
                                    obj_bbox, main_conveyor_bbox
                                )
                                if conveyor_overlap > MAIN_CONVEYOR_THRESHOLD:
                                    obj_center_x = (obj_bbox[0] + obj_bbox[2]) / 2
                                    frame_center_x = frame_width / 2
                                    center_threshold = (
                                        frame_width * OBJECT_CENTER_THRESHOLD / 2
                                    )

                                    if (
                                        abs(obj_center_x - frame_center_x)
                                        <= center_threshold
                                    ):
                                        return track_id
        return None
