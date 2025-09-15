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
    def __init__(self, weights_path: str):
        self.model = YOLO(weights_path)
        self.profiling = Profiling()

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        start_time = time.time()

        results = self.model(frame, task="segment")

        inference_time = time.time() - start_time
        self.profiling.add_inference_time(inference_time)
        self.profiling.add_fps(1.0 / inference_time if inference_time > 0 else 0)

        return {
            "results": results,
            "inference_time": inference_time,
            "frame_shape": frame.shape,
        }

    def visualize_results(self, frame: np.ndarray, results) -> np.ndarray:
        annotated_frame = results[0].plot()
        return annotated_frame
