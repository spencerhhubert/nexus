import time
import threading
import cv2
from queue import Queue
from typing import Optional
from ultralytics import YOLO
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface


class VisionSystem:
    def __init__(self, global_config: GlobalConfig, irl_interface: IRLSystemInterface):
        self.global_config = global_config
        self.irl_interface = irl_interface
        self.logger = global_config["logger"]

        self.main_camera = irl_interface["main_camera"]
        self.feeder_camera = irl_interface["feeder_camera"]

        self.model_path = (
            global_config["yolo_weights_path"]
            if global_config["yolo_weights_path"]
            else global_config["yolo_model"]
        )

        self.main_results_queue = Queue()
        self.feeder_results_queue = Queue()

        self.latest_main_results = None
        self.latest_feeder_results = None
        self.results_lock = threading.Lock()

        self.show_preview = global_config.get("camera_preview", False)

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
        if self.show_preview:
            cv2.destroyAllWindows()
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

                    if self.show_preview:
                        if results and len(results) > 0:
                            annotated_frame = results[0].plot()
                        else:
                            annotated_frame = frame
                        self.main_results_queue.put(
                            ("Main Camera YOLO Tracking", annotated_frame)
                        )

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

                    if self.show_preview:
                        if results and len(results) > 0:
                            annotated_frame = results[0].plot()
                        else:
                            annotated_frame = frame
                        self.feeder_results_queue.put(
                            ("Feeder Camera YOLO Tracking", annotated_frame)
                        )

                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in feeder camera tracking: {e}")

    def update_display(self):
        if not self.show_preview:
            return

        try:
            if not self.main_results_queue.empty():
                window_name, frame = self.main_results_queue.get_nowait()
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 640, 480)
                cv2.imshow(window_name, frame)

            if not self.feeder_results_queue.empty():
                window_name, frame = self.feeder_results_queue.get_nowait()
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 640, 480)
                cv2.imshow(window_name, frame)

            cv2.waitKey(1)
        except:
            pass

    def get_main_camera_results(self):
        with self.results_lock:
            return self.latest_main_results

    def get_feeder_camera_results(self):
        with self.results_lock:
            return self.latest_feeder_results
