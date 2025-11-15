import asyncio
import base64
import json
import threading
from typing import Set, Dict, Optional, Any
import cv2
import numpy as np
from fastapi import WebSocket
from robot.our_types import (
    CameraType,
    SystemLifecycleStage,
    SortingState,
    MotorStatus,
    CameraFrameMessage,
    SystemStatusMessage,
    KnownObjectUpdateMessage,
    BinStateUpdateMessage,
    CameraPerformanceMessage,
    FeederStatusMessage,
    SortingStatsMessage,
)
from robot.our_types.bin import BinCoordinates
from robot.our_types.bin_state import BinState
from robot.our_types.vision_system import CameraPerformanceMetrics
from robot.our_types.feeder_state import FeederState
from robot.global_config import GlobalConfig
from robot.logger import Logger


class WebSocketManager:
    def __init__(self, gc: GlobalConfig):
        self.active_connections: Set[WebSocket] = set()
        self.loop = None
        self.loop_thread = None
        self.logger: Logger = gc["logger"].ctx(component="websocket_manager")

    def set_event_loop(self, loop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    def broadcast_frame(self, camera_type: CameraType, frame):
        if not self.active_connections or not self.loop:
            return

        try:
            _, buffer = cv2.imencode(".jpg", frame)
            frame_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

            message: CameraFrameMessage = {
                "type": "camera_frame",
                "camera": camera_type.value,
                "data": frame_base64,
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting frame: {e}")

    def broadcast_system_status(
        self,
        lifecycle_stage: SystemLifecycleStage,
        sorting_state: SortingState,
        motors: Dict[str, MotorStatus],
        encoder_status: Optional[Dict[str, Any]] = None,
    ):
        if not self.active_connections or not self.loop:
            return

        try:
            message: SystemStatusMessage = {
                "type": "system_status",
                "lifecycle_stage": lifecycle_stage.value,
                "sorting_state": sorting_state.value,
                "motors": motors,
                "encoder": encoder_status,
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting system status: {e}")

    def broadcastKnownObject(
        self,
        uuid: str,
        main_camera_id: Optional[str] = None,
        image: Optional[np.ndarray] = None,
        classification_id: Optional[str] = None,
        bin_coordinates: Optional[BinCoordinates] = None,
    ):
        self.logger.info(
            f"broadcastKnownObject called with UUID={uuid}, connections={len(self.active_connections)}, loop={self.loop is not None}"
        )

        if not self.active_connections or not self.loop:
            self.logger.info(
                f"Early return - connections={len(self.active_connections) if self.active_connections else 0}, loop={self.loop is not None}"
            )
            return

        try:
            message: KnownObjectUpdateMessage = {
                "type": "known_object_update",
                "uuid": uuid,
            }

            if main_camera_id is not None:
                message["main_camera_id"] = main_camera_id

            if image is not None:
                _, buffer = cv2.imencode(".jpg", image)
                image_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                message["image"] = image_base64

            if classification_id is not None:
                message["classification_id"] = classification_id

            if bin_coordinates is not None:
                message["bin_coordinates"] = {
                    "distribution_module_idx": bin_coordinates[
                        "distribution_module_idx"
                    ],
                    "bin_idx": bin_coordinates["bin_idx"],
                }

            message_json = json.dumps(message)
            self.logger.info(f"Broadcasting message: {message_json}")

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting known object: {e}")

    def broadcast_bin_state(self, bin_state: BinState):
        if not self.active_connections or not self.loop:
            return

        try:
            message: BinStateUpdateMessage = {
                "type": "bin_state_update",
                "bin_contents": bin_state["bin_contents"],
                "timestamp": bin_state["timestamp"],
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting bin state: {e}")

    def broadcast_camera_performance(
        self, camera_type: CameraType, metrics: CameraPerformanceMetrics
    ):
        if not self.active_connections or not self.loop:
            return

        try:
            message: CameraPerformanceMessage = {
                "type": "camera_performance",
                "camera": camera_type.value,
                "fps_1s": metrics.fps_1s,
                "fps_5s": metrics.fps_5s,
                "latency_1s": metrics.latency_1s,
                "latency_5s": metrics.latency_5s,
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting camera performance: {e}")

    def broadcast_feeder_status(self, feeder_state: Optional[FeederState]):
        if not self.active_connections or not self.loop:
            return

        try:
            message: FeederStatusMessage = {
                "type": "feeder_status",
                "feeder_state": feeder_state.value if feeder_state else None,
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting feeder status: {e}")

    def broadcast_sorting_stats(
        self,
        total_known_objects: int,
        average_time_between_known_objects_seconds: Optional[float],
    ):
        if not self.active_connections or not self.loop:
            return

        try:
            message: SortingStatsMessage = {
                "type": "sorting_stats",
                "total_known_objects": total_known_objects,
                "average_time_between_known_objects_seconds": average_time_between_known_objects_seconds,
            }

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            self.logger.error(f"Error broadcasting sorting stats: {e}")

    async def _send_safe(self, websocket: WebSocket, message: str):
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)

    async def _broadcast_to_all(self, message: str):
        if not self.active_connections:
            return

        tasks = []
        for connection in self.active_connections.copy():
            tasks.append(self._send_safe(connection, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
