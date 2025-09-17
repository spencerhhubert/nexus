import asyncio
import base64
import json
import threading
from typing import Set
import cv2
from fastapi import WebSocket
from robot.our_types import CameraType


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
