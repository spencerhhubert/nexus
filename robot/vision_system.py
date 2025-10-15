import time
import threading
import numpy as np
import cv2
import os
from typing import Optional, Dict, List, Tuple, Any
from ultralytics import YOLO
import logging

logging.getLogger("ultralytics").setLevel(logging.WARNING)
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.our_types import CameraType
from robot.our_types.vision_system import (
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
SECOND_FEEDER_DISTANCE_THRESHOLD = 40
MAIN_CONVEYOR_BOUNDING_BOX_OVERLAP_THRESHOLD = 0.75
FEEDER_CAMERA_MAIN_CONVEYOR_MASK_PROXIMITY_THRESHOLD = 0.9
MAIN_CAMERA_MAIN_CONVEYOR_MASK_PROXIMITY_THRESHOLD = 0.5
OBJECT_CENTER_THRESHOLD = 0.4
RIGHT_SIDE_THRESHOLD = 0.3
MARGIN_FOR_MAIN_CONVEYOR_BOUNDING_BOX_PX = -20


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

        if global_config["feeder_camera_yolo_weights_path"]:
            self.feeder_model_path = global_config["feeder_camera_yolo_weights_path"]
        else:
            self.logger.error(
                "No YOLO model path found: 'feeder_camera_yolo_weights_path' is missing or empty in global_config"
            )
            raise ValueError(
                "No YOLO model path found: 'feeder_camera_yolo_weights_path' is missing or empty in global_config"
            )

        if global_config["main_camera_yolo_weights_path"]:
            self.main_model_path = global_config["main_camera_yolo_weights_path"]
        else:
            self.logger.error(
                "No YOLO model path found: 'main_camera_yolo_weights_path' is missing or empty in global_config"
            )
            raise ValueError(
                "No YOLO model path found: 'main_camera_yolo_weights_path' is missing or empty in global_config"
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

        # Video recording
        self.main_camera_raw_writer = None
        self.main_camera_annotated_writer = None
        self.feeder_camera_raw_writer = None
        self.feeder_camera_annotated_writer = None

    def start(self) -> None:
        self.running = True

        if self.global_config["recording_enabled"]:
            self._initializeVideoWriters()

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

        if self.global_config["recording_enabled"]:
            self._cleanupVideoWriters()

    def _initializeVideoWriters(self) -> None:
        recordings_dir = os.path.join(self.global_config["run_blob_dir"], "recordings")
        os.makedirs(recordings_dir, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc("M", "J", "P", "G")
        fps = 10.0  # Approximate based on 0.1s sleep
        frame_size = (1920, 1080)  # Full 1080p resolution

        self.main_camera_raw_writer = cv2.VideoWriter(
            os.path.join(recordings_dir, "main_camera_raw.avi"), fourcc, fps, frame_size
        )
        self.main_camera_annotated_writer = cv2.VideoWriter(
            os.path.join(recordings_dir, "main_camera_annotated.avi"),
            fourcc,
            fps,
            frame_size,
        )
        self.feeder_camera_raw_writer = cv2.VideoWriter(
            os.path.join(recordings_dir, "feeder_camera_raw.avi"),
            fourcc,
            fps,
            frame_size,
        )
        self.feeder_camera_annotated_writer = cv2.VideoWriter(
            os.path.join(recordings_dir, "feeder_camera_annotated.avi"),
            fourcc,
            fps,
            frame_size,
        )

    def _cleanupVideoWriters(self) -> None:
        if self.main_camera_raw_writer:
            self.main_camera_raw_writer.release()
        if self.main_camera_annotated_writer:
            self.main_camera_annotated_writer.release()
        if self.feeder_camera_raw_writer:
            self.feeder_camera_raw_writer.release()
        if self.feeder_camera_annotated_writer:
            self.feeder_camera_annotated_writer.release()

    def _trackMainCamera(self) -> None:
        model = YOLO(self.main_model_path)
        if self.global_config.get("tensor_device"):
            model.to(self.global_config["tensor_device"])
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.main_camera.captureFrame()

                if frame is not None:
                    # Record raw frame
                    if (
                        self.global_config["recording_enabled"]
                        and self.main_camera_raw_writer
                    ):
                        if frame.shape[:2] != (1080, 1920):  # height, width
                            frame_resized = cv2.resize(frame, (1920, 1080))
                            self.main_camera_raw_writer.write(frame_resized)
                        else:
                            self.main_camera_raw_writer.write(frame)

                    start_time = time.time()
                    results = model.track(
                        frame,
                        persist=False,  # Persist true is really bad in this situation. if it misses the first few frames of segmentation, it'll never find the object as it crosses the frame
                    )
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

                    # Record annotated frame
                    if (
                        self.global_config["recording_enabled"]
                        and self.main_camera_annotated_writer
                    ):
                        if annotated_frame.shape[:2] != (1080, 1920):  # height, width
                            annotated_resized = cv2.resize(
                                annotated_frame, (1920, 1080)
                            )
                            self.main_camera_annotated_writer.write(annotated_resized)
                        else:
                            self.main_camera_annotated_writer.write(annotated_frame)

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
        model = YOLO(self.feeder_model_path)
        if self.global_config.get("tensor_device"):
            model.to(self.global_config["tensor_device"])
        frame_count = 0
        try:
            while self.running:
                frame_count += 1
                frame = self.feeder_camera.captureFrame()

                if frame is not None:
                    # Record raw frame
                    if (
                        self.global_config["recording_enabled"]
                        and self.feeder_camera_raw_writer
                    ):
                        if frame.shape[:2] != (1080, 1920):  # height, width
                            frame_resized = cv2.resize(frame, (1920, 1080))
                            self.feeder_camera_raw_writer.write(frame_resized)
                        else:
                            self.feeder_camera_raw_writer.write(frame)

                    start_time = time.time()
                    results = model.track(
                        frame,
                        persist=False,
                    )
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

                    # Record annotated frame
                    if (
                        self.global_config["recording_enabled"]
                        and self.feeder_camera_annotated_writer
                    ):
                        if annotated_frame.shape[:2] != (1080, 1920):  # height, width
                            annotated_resized = cv2.resize(
                                annotated_frame, (1920, 1080)
                            )
                            self.feeder_camera_annotated_writer.write(annotated_resized)
                        else:
                            self.feeder_camera_annotated_writer.write(annotated_frame)

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

    def _getDetectedMasks(self) -> Dict[str, List[Tuple[np.ndarray, Optional[str]]]]:
        results = self._getFeederCameraResults()
        if not results or len(results) == 0:
            return {}

        masks_by_class: Dict[str, List[Tuple[np.ndarray, Optional[str]]]] = {}

        for result in results:
            if result.masks is not None:
                for i, mask in enumerate(result.masks):
                    class_id = int(result.boxes[i].cls.item())
                    class_name = YOLO_CLASSES.get(class_id, f"unknown_{class_id}")
                    mask_data = mask.data[0].cpu().numpy()

                    track_id = None
                    if result.boxes.id is not None and i < len(result.boxes.id):
                        track_id = str(int(result.boxes.id[i].item()))

                    if class_name not in masks_by_class:
                        masks_by_class[class_name] = []
                    masks_by_class[class_name].append((mask_data, track_id))

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
        self, object_mask: np.ndarray, target_mask: np.ndarray, proximity_px: int = 6
    ) -> float:
        if object_mask.shape != target_mask.shape:
            self.logger.warning(
                "Can't calculate mask edge proximity, masks are not the same shape"
            )
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
        self,
        obj_mask: np.ndarray,
        masks_by_class: Dict[str, List[np.ndarray]],
        track_id: str,
    ) -> FeederRegion:
        obj_bbox = self._getBoundingBoxFromMask(obj_mask)
        if obj_bbox is None:
            self.logger.info(f"REGION[{track_id}]: UNKNOWN - no bounding box")
            return FeederRegion.UNKNOWN

        # Check main conveyor first
        main_conveyor_masks = masks_by_class.get("main_conveyor", [])
        first_feeder_masks = masks_by_class.get("first_feeder", [])
        second_feeder_masks = masks_by_class.get("second_feeder", [])
        if main_conveyor_masks:
            feeder_masks_negative = first_feeder_masks + second_feeder_masks
            total_main_conveyor_proximity = 0.0
            for main_conveyor_mask in main_conveyor_masks:
                main_conveyor_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, main_conveyor_mask
                )
                total_main_conveyor_proximity += main_conveyor_proximity

            if (
                total_main_conveyor_proximity
                > FEEDER_CAMERA_MAIN_CONVEYOR_MASK_PROXIMITY_THRESHOLD
            ):
                self.logger.info(
                    f"REGION[{track_id}]: MAIN_CONVEYOR - proximity={total_main_conveyor_proximity:.3f} > threshold={FEEDER_CAMERA_MAIN_CONVEYOR_MASK_PROXIMITY_THRESHOLD}"
                )
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
                # Check if under exit of first feeder (object on second feeder but near first)
                first_feeder_masks = masks_by_class.get("first_feeder", [])
                if first_feeder_masks:
                    min_distance_to_first = float("inf")
                    for first_feeder_mask in first_feeder_masks:
                        distance_to_first = self._calculateMinDistanceToMask(
                            obj_bbox, first_feeder_mask
                        )
                        min_distance_to_first = min(
                            min_distance_to_first, distance_to_first
                        )

                    if min_distance_to_first < SECOND_FEEDER_DISTANCE_THRESHOLD:
                        self.logger.info(
                            f"REGION[{track_id}]: UNDER_EXIT_OF_FIRST_FEEDER - distance={min_distance_to_first:.1f}px < threshold={SECOND_FEEDER_DISTANCE_THRESHOLD}px, second_proximity={total_second_proximity:.3f}"
                        )
                        return FeederRegion.UNDER_EXIT_OF_FIRST_FEEDER

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

                    if (
                        total_bbox_overlap
                        > MAIN_CONVEYOR_BOUNDING_BOX_OVERLAP_THRESHOLD
                    ):
                        self.logger.info(
                            f"REGION[{track_id}]: EXIT_OF_SECOND_FEEDER - bbox_overlap={total_bbox_overlap:.3f} > threshold={MAIN_CONVEYOR_BOUNDING_BOX_OVERLAP_THRESHOLD}, second_proximity={total_second_proximity:.3f}"
                        )
                        return FeederRegion.EXIT_OF_SECOND_FEEDER

                self.logger.info(
                    f"REGION[{track_id}]: SECOND_FEEDER_MASK - second_proximity={total_second_proximity:.3f}"
                )
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
                self.logger.info(
                    f"REGION[{track_id}]: FIRST_FEEDER_MASK - first_proximity={total_first_proximity:.3f} > 0.5"
                )
                return FeederRegion.FIRST_FEEDER_MASK

        self.logger.info(f"REGION[{track_id}]: UNKNOWN - no matching region")
        return FeederRegion.UNKNOWN

    def _updateObjectDetections(self) -> None:
        results = self._getFeederCameraResults()
        if not results or len(results) == 0:
            return

        current_time = time.time()
        masks_by_class = self._getDetectedMasksByClass()

        with self.detection_lock:
            # Process each YOLO result to get tracked objects
            for result in results:
                if (
                    result.masks is not None
                    and hasattr(result, "boxes")
                    and result.boxes.id is not None
                ):
                    for i, mask in enumerate(result.masks):
                        if i < len(result.boxes.id):
                            class_id = int(result.boxes[i].cls.item())
                            if class_id == 0:  # Only process "object" class
                                track_id = str(int(result.boxes.id[i].item()))
                                mask_data = mask.data[0].cpu().numpy()

                                # Analyze what region this object is in
                                region = self._analyzeObjectRegions(
                                    mask_data, masks_by_class, track_id
                                )
                                region_reading = RegionReading(
                                    timestamp=current_time,
                                    region=region,
                                    track_id=track_id,
                                )

                                # Find existing detection for this track_id or create new one
                                existing_detection = None
                                for detection in self.object_detections:
                                    if detection.track_id == track_id:
                                        existing_detection = detection
                                        break

                                if existing_detection:
                                    # Add new reading to existing tracked object
                                    existing_detection.region_readings.append(
                                        region_reading
                                    )
                                else:
                                    # Create new tracked object
                                    new_detection = ObjectDetection(
                                        track_id=track_id,
                                        region_readings=[region_reading],
                                    )
                                    self.object_detections.append(new_detection)

            # Cleanup old detections (keep only last 5 seconds)
            cutoff_time = current_time - 5.0
            self.object_detections = [
                detection
                for detection in self.object_detections
                if detection.region_readings
                and detection.region_readings[-1].timestamp >= cutoff_time
            ]

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

            if total_conveyor_overlap > MAIN_CONVEYOR_BOUNDING_BOX_OVERLAP_THRESHOLD:
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
        feeder_masks = self._getDetectedMasks()
        object_masks = feeder_masks.get("object", [])
        main_conveyor_masks = feeder_masks.get("main_conveyor", [])
        first_feeder_masks = feeder_masks.get("first_feeder", [])
        second_feeder_masks = feeder_masks.get("second_feeder", [])

        if not object_masks or not main_conveyor_masks:
            return False

        feeder_masks_negative = [mask for mask, _ in first_feeder_masks] + [
            mask for mask, _ in second_feeder_masks
        ]
        main_conveyor_mask_data = [mask for mask, _ in main_conveyor_masks]

        for obj_mask, track_id in object_masks:
            total_edge_proximity = 0.0
            for main_conveyor_mask in main_conveyor_mask_data:
                edge_proximity = self._calculateMaskEdgeProximity(
                    obj_mask, main_conveyor_mask
                )
                total_edge_proximity += edge_proximity

            if (
                total_edge_proximity
                > FEEDER_CAMERA_MAIN_CONVEYOR_MASK_PROXIMITY_THRESHOLD
            ):
                self.logger.info(
                    f"Object detected on main conveyor in feeder view with proximity: {total_edge_proximity}, track_id: {track_id}"
                )
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

        # Combine all main conveyor masks into one
        combined_main_conveyor_mask = np.zeros_like(main_conveyor_masks[0])
        for mask in main_conveyor_masks:
            combined_main_conveyor_mask = np.logical_or(
                combined_main_conveyor_mask, mask
            )

        main_conveyor_bbox = self._getBoundingBoxFromMask(combined_main_conveyor_mask)
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
                                if (
                                    conveyor_overlap
                                    > MAIN_CONVEYOR_BOUNDING_BOX_OVERLAP_THRESHOLD
                                ):
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
