import time
from typing import Dict, List, Any
from dataclasses import dataclass
import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class Profiling:
    inference_times: List[float]
    fps_values: List[float]
    last_print_time: float

    def __init__(self):
        self.inference_times = []
        self.fps_values = []
        self.last_print_time = time.time()

    def add_inference_time(self, inference_time: float):
        self.inference_times.append(inference_time)
        if len(self.inference_times) > 100:
            self.inference_times.pop(0)

    def add_fps(self, fps: float):
        self.fps_values.append(fps)
        if len(self.fps_values) > 100:
            self.fps_values.pop(0)

    def printProfiling(self):
        current_time = time.time()
        if current_time - self.last_print_time >= 2.0:
            if self.inference_times:
                avg_inference = sum(self.inference_times) / len(self.inference_times)
                print(f"Avg inference: {avg_inference * 1000:.1f}ms")

            if self.fps_values:
                avg_fps = sum(self.fps_values) / len(self.fps_values)
                print(f"Avg FPS: {avg_fps:.1f}")

            self.last_print_time = current_time


class YOLOModel:
    def __init__(self, model_name: str, weights_path: str = None):
        if weights_path and weights_path.endswith(".pt"):
            self.model = YOLO(weights_path)
        else:
            self.model = YOLO(model_name)
        self.profiling = Profiling()

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        start_time = time.time()

        results = self.model(frame)

        inference_time = time.time() - start_time
        self.profiling.add_inference_time(inference_time)
        self.profiling.add_fps(1.0 / inference_time if inference_time > 0 else 0)

        return {
            "results": results,
            "inference_time": inference_time,
            "frame_shape": frame.shape,
        }

    def track_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        start_time = time.time()

        results = self.model.track(frame, persist=True)

        inference_time = time.time() - start_time
        self.profiling.add_inference_time(inference_time)
        self.profiling.add_fps(1.0 / inference_time if inference_time > 0 else 0)

        return {
            "results": results,
            "inference_time": inference_time,
            "frame_shape": frame.shape,
        }

    def visualize_results(self, frame: np.ndarray, results, max_tracks: int = None) -> np.ndarray:
        annotated_frame = results[0].plot()

        if hasattr(results[0], 'boxes') and results[0].boxes is not None and hasattr(results[0].boxes, 'id'):
            boxes = results[0].boxes
            if boxes.id is not None:
                tracks_to_show = boxes.id[:max_tracks] if max_tracks else boxes.id
                xyxy = boxes.xyxy[:len(tracks_to_show)] if max_tracks else boxes.xyxy

                for i, track_id in enumerate(tracks_to_show):
                    x1, y1, x2, y2 = xyxy[i].cpu().numpy()
                    cv2.putText(annotated_frame, f'ID:{int(track_id)}',
                               (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                               0.6, (0, 255, 255), 2)

        return annotated_frame
