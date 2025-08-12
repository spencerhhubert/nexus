from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import json
import base64
import cv2
import time
from robot.server.types import (
    SystemStatus,
    MotorInfo,
    SetMotorSpeedRequest,
    StartSystemRequest,
    StopSystemRequest,
    WebSocketEvent,
    CameraFrameEvent,
    StatusUpdateEvent,
    LogEvent,
    SystemLifecycleStage,
    SortingState,
)
from robot.global_config import GlobalConfig


class RobotAPI:
    def __init__(self, global_config: GlobalConfig, controller):
        self.global_config = global_config
        self.controller = controller
        self.app = FastAPI()
        self.active_websockets: List[WebSocket] = []

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/status")
        async def get_status() -> SystemStatus:
            return self._get_current_status()

        @self.app.post("/api/motors/set_speed")
        async def set_motor_speed(request: SetMotorSpeedRequest) -> JSONResponse:
            try:
                self._set_motor_speed(request["motor_id"], request["speed"])
                return JSONResponse({"success": True})
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/api/system/start")
        async def start_system(request: StartSystemRequest) -> JSONResponse:
            try:
                self._start_system()
                return JSONResponse({"success": True})
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/api/system/stop")
        async def stop_system(request: StopSystemRequest) -> JSONResponse:
            try:
                self._stop_system()
                return JSONResponse({"success": True})
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_websockets.append(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except:
                pass
            finally:
                if websocket in self.active_websockets:
                    self.active_websockets.remove(websocket)

    def _get_current_status(self) -> SystemStatus:
        motors = [
            MotorInfo(
                motor_id="main_conveyor_dc_motor",
                display_name="Main Conveyor",
                current_speed=0,
                min_speed=-255,
                max_speed=255,
            ),
            MotorInfo(
                motor_id="feeder_conveyor_dc_motor",
                display_name="Feeder Conveyor",
                current_speed=0,
                min_speed=-255,
                max_speed=255,
            ),
            MotorInfo(
                motor_id="vibration_hopper_dc_motor",
                display_name="Vibration Hopper",
                current_speed=0,
                min_speed=-255,
                max_speed=255,
            ),
        ]

        return SystemStatus(
            lifecycle_stage=self.controller.system_lifecycle_stage.value,
            sorting_state=self.controller.sorting_state.value,
            objects_in_frame=self.controller.scene_tracker.objects_in_frame,
            conveyor_speed=self.controller.scene_tracker.conveyor_velocity_cm_per_ms,
            motors=motors,
        )

    def _set_motor_speed(self, motor_id: str, speed: int):
        if motor_id == "main_conveyor_dc_motor":
            self.controller.irl_system["main_conveyor_dc_motor"].setSpeed(speed)
        elif motor_id == "feeder_conveyor_dc_motor":
            self.controller.irl_system["feeder_conveyor_dc_motor"].setSpeed(speed)
        elif motor_id == "vibration_hopper_dc_motor":
            self.controller.irl_system["vibration_hopper_dc_motor"].setSpeed(speed)
        else:
            raise ValueError(f"Unknown motor_id: {motor_id}")

    def _start_system(self):
        if (
            self.controller.system_lifecycle_stage
            == SystemLifecycleStage.PAUSED_BY_USER
        ):
            self.controller.system_lifecycle_stage = SystemLifecycleStage.RUNNING

    def _stop_system(self):
        if self.controller.system_lifecycle_stage == SystemLifecycleStage.RUNNING:
            self.controller.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_USER

    async def broadcast_camera_frame(self, frame):
        if not self.active_websockets:
            return

        _, buffer = cv2.imencode(".jpg", frame)
        frame_data = base64.b64encode(buffer.tobytes()).decode("utf-8")

        event: CameraFrameEvent = {"type": "camera_frame", "frame_data": frame_data}

        await self._broadcast_event(event)

    async def broadcast_status_update(self):
        if not self.active_websockets:
            return

        status = self._get_current_status()
        event: StatusUpdateEvent = {"type": "status_update", "status": status}

        await self._broadcast_event(event)

    async def broadcast_log(self, level: str, message: str):
        if not self.active_websockets:
            return

        event: LogEvent = {
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": int(time.time() * 1000),
        }

        await self._broadcast_event(event)

    async def _broadcast_event(self, event: WebSocketEvent):
        disconnected = []
        for websocket in self.active_websockets:
            try:
                await websocket.send_text(json.dumps(event))
            except:
                disconnected.append(websocket)

        for ws in disconnected:
            self.active_websockets.remove(ws)
