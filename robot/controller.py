import time
import threading
from typing import List
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface
from robot.storage.sqlite3.migrations import initializeDatabase
from robot.storage.blob import ensureBlobStorageExists
from robot.bin_state_tracker import BinStateTracker
from robot.sorting.bricklink_categories_sorting_profile import (
    mkBricklinkCategoriesSortingProfile,
)
from robot.our_types import SystemLifecycleStage
from robot.vision_system import SegmentationModelManager
from robot.sorting_state_machine import SortingStateMachine
from robot.websocket_manager import WebSocketManager
from robot.encoder_manager import EncoderManager
from robot.our_types import MotorStatus


class Controller:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
    ):
        self.global_config = global_config
        self.lifecycle_stage = SystemLifecycleStage.INITIALIZING
        self.irl_interface = irl_interface

        self.sorting_profile = mkBricklinkCategoriesSortingProfile(global_config)
        self.bin_state_tracker = BinStateTracker(
            global_config, irl_interface["distribution_modules"], self.sorting_profile
        )

        self.vision_system = SegmentationModelManager(
            global_config, irl_interface, websocket_manager
        )

        self.encoder_manager = EncoderManager(
            global_config, irl_interface["conveyor_encoder"]
        )

        self.sorting_state_machine = SortingStateMachine(
            self.vision_system,
            irl_interface,
            websocket_manager,
            self.encoder_manager,
            self.bin_state_tracker,
        )

        self.running = False
        self.controller_thread = None
        self.websocket_manager = websocket_manager

    def start(self):
        self.running = True
        self.vision_system.start()
        self.controller_thread = threading.Thread(target=self._loop)
        self.controller_thread.start()

    def stop(self):
        self.running = False
        self.lifecycle_stage = SystemLifecycleStage.STOPPING

        # Stop all motors
        self.irl_interface["main_conveyor_dc_motor"].setSpeed(0)
        self.irl_interface["feeder_conveyor_dc_motor"].setSpeed(0)
        self.irl_interface["first_vibration_hopper_motor"].setSpeed(0)
        self.irl_interface["second_vibration_hopper_motor"].setSpeed(0)

        self.vision_system.stop()
        self.encoder_manager.stop()
        if self.controller_thread:
            self.controller_thread.join()

        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN

    def _loop(self):
        self.lifecycle_stage = SystemLifecycleStage.STARTING_HARDWARE

        # Initialize storage
        initializeDatabase(self.global_config)
        ensureBlobStorageExists(self.global_config)

        self.lifecycle_stage = SystemLifecycleStage.RUNNING

        # Main loop - run sorting state machine when running
        last_status_broadcast = 0
        while self.running and self.lifecycle_stage in [
            SystemLifecycleStage.RUNNING,
            SystemLifecycleStage.PAUSED,
        ]:
            if self.lifecycle_stage == SystemLifecycleStage.RUNNING:
                self.sorting_state_machine.step()

            # Broadcast system status every 500ms
            current_time = time.time() * 1000
            if current_time - last_status_broadcast >= 500:
                self._broadcast_system_status()
                last_status_broadcast = current_time

            time.sleep(0.1)

        self.lifecycle_stage = SystemLifecycleStage.STOPPING

        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN

    def _broadcast_system_status(self):
        # Get current motor speeds (we don't track these currently, so use 0 for now)
        motors = {
            "main_conveyor": MotorStatus(speed=0),
            "feeder_conveyor": MotorStatus(speed=0),
            "first_vibration_hopper": MotorStatus(speed=0),
            "second_vibration_hopper": MotorStatus(speed=0),
        }

        encoder_status = self.encoder_manager.getStatus()

        self.websocket_manager.broadcast_system_status(
            self.lifecycle_stage,
            self.sorting_state_machine.current_state,
            motors,
            encoder_status,
        )

    def set_motor_speed(self, motor_id: str, speed: int):
        # Set motor speed via IRL interface
        if motor_id == "main_conveyor_dc_motor":
            self.irl_interface["main_conveyor_dc_motor"].setSpeed(speed)
        elif motor_id == "feeder_conveyor_dc_motor":
            self.irl_interface["feeder_conveyor_dc_motor"].setSpeed(speed)
        elif motor_id == "first_vibration_hopper_motor":
            self.irl_interface["first_vibration_hopper_motor"].setSpeed(speed)
        elif motor_id == "second_vibration_hopper_motor":
            self.irl_interface["second_vibration_hopper_motor"].setSpeed(speed)
        else:
            raise ValueError(f"Unknown motor_id: {motor_id}")

    def pause(self):
        if self.lifecycle_stage == SystemLifecycleStage.RUNNING:
            self.lifecycle_stage = SystemLifecycleStage.PAUSED
            # Stop all motors when pausing
            self.irl_interface["main_conveyor_dc_motor"].setSpeed(0)
            self.irl_interface["feeder_conveyor_dc_motor"].setSpeed(0)
            self.irl_interface["first_vibration_hopper_motor"].setSpeed(0)
            self.irl_interface["second_vibration_hopper_motor"].setSpeed(0)

    def resume(self):
        if self.lifecycle_stage == SystemLifecycleStage.PAUSED:
            self.lifecycle_stage = SystemLifecycleStage.RUNNING
