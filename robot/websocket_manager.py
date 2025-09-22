import asyncio
import base64
import json
import threading
from typing import Set, Dict, Optional, Any
import cv2
import numpy as np
from fastapi import WebSocket
from robot.our_types import CameraType, SystemLifecycleStage, SortingState, MotorStatus


class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.loop = None
        self.loop_thread = None

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

            message = {
                "type": "camera_frame",
                "camera": camera_type.value,
                "data": frame_base64,
            }

            message_json = json.dumps(message)

            # Schedule the broadcast in the event loop
            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            print(f"Error broadcasting frame: {e}")

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
            message = {
                "type": "system_status",
                "lifecycle_stage": lifecycle_stage.value,
                "sorting_state": sorting_state.value,
                "motors": motors,
            }

            if encoder_status is not None:
                message["encoder"] = encoder_status

            message_json = json.dumps(message)

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            print(f"Error broadcasting system status: {e}")

    def broadcastKnownObject(
        self,
        uuid: str,
        main_camera_id: Optional[str] = None,
        image: Optional[np.ndarray] = None,
        classification_id: Optional[str] = None,
    ):
        print(
            f"WEBSOCKET DEBUG: broadcastKnownObject called with UUID={uuid}, connections={len(self.active_connections)}, loop={self.loop is not None}"
        )

        if not self.active_connections or not self.loop:
            print(
                f"WEBSOCKET DEBUG: Early return - connections={len(self.active_connections) if self.active_connections else 0}, loop={self.loop is not None}"
            )
            return

        try:
            message = {
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

            message_json = json.dumps(message)
            print(f"WEBSOCKET DEBUG: Broadcasting message: {message_json}")

            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_all(message_json), self.loop
            )

        except Exception as e:
            print(f"Error broadcasting known object: {e}")

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
