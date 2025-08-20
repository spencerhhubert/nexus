from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, TYPE_CHECKING
import asyncio
import json
import base64
import cv2
import time
from robot.server.thread_safe_state import ThreadSafeState
from robot.server.types import (
    SystemStatus,
    MotorInfo,
    SetMotorSpeedRequest,
    StartSystemRequest,
    StopSystemRequest,
    WebSocketEvent,
    CameraFrameEvent,
    StatusUpdateEvent,
    SystemLifecycleStage,
    SortingState,
)
from robot.global_config import GlobalConfig

if TYPE_CHECKING:
    from robot.controller import SortingController

class RobotAPI:
    def __init__(self, global_config: GlobalConfig, controller: "SortingController"):
        self.global_config = global_config
        self.controller = controller
        self.app = FastAPI()
        self.active_websockets: List[WebSocket] = []
        self.last_camera_frame_timestamp = 0.0

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._setup_routes()
        self._setup_startup_events()

    def _setup_routes(self):
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

        @self.app.websocket("/api/ws")
        async def websocket_endpoint(websocket: WebSocket):
            client_host = websocket.client.host if websocket.client else "unknown"
            self.global_config["logger"].info(
                f"WebSocket connection attempt from {client_host}"
            )

            try:
                await websocket.accept()
                self.global_config["logger"].info(
                    f"WebSocket connection accepted from {client_host}"
                )

                self.active_websockets.append(websocket)
                self.global_config["logger"].info(
                    f"Added WebSocket to active list. Total active: {len(self.active_websockets)}"
                )

                try:
                    while True:
                        message = await websocket.receive_text()
                        self.global_config["logger"].info(
                            f"Received WebSocket message from {client_host}: {message[:100]}"
                        )
                except Exception as e:
                    self.global_config["logger"].info(
                        f"WebSocket receive loop ended for {client_host}: {e}"
                    )

            except Exception as e:
                self.global_config["logger"].error(
                    f"WebSocket connection failed for {client_host}: {e}"
                )
            finally:
                if websocket in self.active_websockets:
                    self.active_websockets.remove(websocket)
                    self.global_config["logger"].info(
                        f"Removed WebSocket from active list. Total active: {len(self.active_websockets)}"
                    )

    def _set_motor_speed(self, motor_id: str, speed: int):
        if motor_id == "main_conveyor_dc_motor":
            self.controller.irl_system["main_conveyor_dc_motor"].setSpeed(speed)
            self.controller.main_conveyor_speed = speed
        elif motor_id == "feeder_conveyor_dc_motor":
            self.controller.irl_system["feeder_conveyor_dc_motor"].setSpeed(speed)
            self.controller.feeder_conveyor_speed = speed
        elif motor_id == "first_vibration_hopper_motor":
            self.controller.irl_system["first_vibration_hopper_motor"].setSpeed(speed)
            self.controller.first_vibration_hopper_motor_speed = speed
        elif motor_id == "second_vibration_hopper_motor":
            self.controller.irl_system["second_vibration_hopper_motor"].setSpeed(speed)
            self.controller.second_vibration_hopper_motor_speed = speed
        elif motor_id == "vibration_hopper_dc_motor":
            # Backward compatibility - set both motors to same speed
            self.controller.irl_system["first_vibration_hopper_motor"].setSpeed(speed)
            self.controller.irl_system["second_vibration_hopper_motor"].setSpeed(speed)
            self.controller.first_vibration_hopper_motor_speed = speed
            self.controller.second_vibration_hopper_motor_speed = speed
        else:
            raise ValueError(f"Unknown motor_id: {motor_id}")

    def _start_system(self):
        if self.controller.system_lifecycle_stage in [
            SystemLifecycleStage.PAUSED_BY_USER,
            SystemLifecycleStage.PAUSED_BY_SYSTEM,
        ]:
            self.controller.system_lifecycle_stage = SystemLifecycleStage.RUNNING
            self.controller.sorting_state = SortingState.GETTING_NEW_OBJECT
            self.controller.timestamps["getting_new_object_start_time"] = None

    def _stop_system(self):
        if self.controller.system_lifecycle_stage == SystemLifecycleStage.RUNNING:
            self.controller.system_lifecycle_stage = SystemLifecycleStage.PAUSED_BY_USER
            self.controller.irl_system["main_conveyor_dc_motor"].setSpeed(0)
            self.controller.irl_system["feeder_conveyor_dc_motor"].setSpeed(0)
            self.controller.irl_system["first_vibration_hopper_motor"].setSpeed(0)
            self.controller.irl_system["second_vibration_hopper_motor"].setSpeed(0)
            self.controller.main_conveyor_speed = 0
            self.controller.feeder_conveyor_speed = 0
            self.controller.first_vibration_hopper_motor_speed = 0
            self.controller.second_vibration_hopper_motor_speed = 0

    async def _checkAndBroadcastCameraFrame(self):
        if not self.active_websockets:
            return

        frame, timestamp = self.controller.thread_safe_state.getWithTimestamp(
            "latest_camera_frame"
        )
        if frame is None or timestamp is None:
            return

        if timestamp <= self.last_camera_frame_timestamp:
            return

        try:
            _, buffer = cv2.imencode(".jpg", frame)
            frame_data = base64.b64encode(buffer.tobytes()).decode("utf-8")

            event: CameraFrameEvent = {"type": "camera_frame", "frame_data": frame_data}
            await self._broadcastEvent(event)

            self.last_camera_frame_timestamp = timestamp
        except Exception as e:
            self.global_config["logger"].error(f"Error broadcasting camera frame: {e}")

    async def broadcastStatusUpdate(self):
        if not self.active_websockets:
            return

        motors = [
            MotorInfo(
                motor_id="main_conveyor_dc_motor",
                display_name="Main Conveyor",
                current_speed=self.controller.main_conveyor_speed,
                min_speed=-255,
                max_speed=255,
            ),
            MotorInfo(
                motor_id="feeder_conveyor_dc_motor",
                display_name="Feeder Conveyor",
                current_speed=self.controller.feeder_conveyor_speed,
                min_speed=-255,
                max_speed=255,
            ),
            MotorInfo(
                motor_id="first_vibration_hopper_motor",
                display_name="First Vibration Hopper",
                current_speed=self.controller.first_vibration_hopper_motor_speed,
                min_speed=-255,
                max_speed=255,
            ),
            MotorInfo(
                motor_id="second_vibration_hopper_motor",
                display_name="Second Vibration Hopper",
                current_speed=self.controller.second_vibration_hopper_motor_speed,
                min_speed=-255,
                max_speed=255,
            ),
        ]

        average_speed_1s = self.controller.scene_tracker.getAverageSpeed(1000)
        average_speed_5s = self.controller.scene_tracker.getAverageSpeed(5000)

        status = SystemStatus(
            lifecycle_stage=self.controller.system_lifecycle_stage.value,
            sorting_state=self.controller.sorting_state.value,
            objects_in_frame=self.controller.scene_tracker.objects_in_frame,
            conveyor_speed=average_speed_1s,
            average_speed_1s=average_speed_1s,
            average_speed_5s=average_speed_5s,
            motors=motors,
        )

        event: StatusUpdateEvent = {"type": "status_update", "status": status}

        await self._broadcastEvent(event)

    async def _broadcastEvent(self, event: WebSocketEvent):
        disconnected = []
        for websocket in self.active_websockets:
            try:
                await websocket.send_text(json.dumps(event))
            except:
                disconnected.append(websocket)

        for ws in disconnected:
            self.active_websockets.remove(ws)

    def _setup_startup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            self.global_config["logger"].info("Starting periodic broadcast task")
            asyncio.create_task(self._periodicBroadcast())

    async def _periodicBroadcast(self):
        while True:
            try:
                await asyncio.sleep(1 / 30)
                if self.active_websockets:
                    await self._checkAndBroadcastCameraFrame()

                    if int(time.time() * 5) % 1 == 0:
                        await self.broadcastStatusUpdate()
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                self.global_config["logger"].error(f"Error in periodic broadcast: {e}")
                await asyncio.sleep(5)
