import time
import threading
from typing import Optional
from ultralytics import YOLO
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.our_types import CameraType


class VisionSystem:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager=None,
    ):
        self.global_config = global_config
        self.irl_interface = irl_interface
        self.logger = global_config["logger"]
        self.websocket_manager = websocket_manager

        self.main_camera = irl_interface["main_camera"]
        self.feeder_camera = irl_interface["feeder_camera"]

        self.model_path = (
            global_config["yolo_weights_path"]
            if global_config["yolo_weights_path"]
            else global_config["yolo_model"]
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
        if self.websocket_manager:
            self.websocket_manager.broadcast_frame(camera_type, frame)

    def get_main_camera_results(self):
        with self.results_lock:
            return self.latest_main_results

    def get_feeder_camera_results(self):
        with self.results_lock:
            return self.latest_feeder_results
