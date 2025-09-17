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
from robot.vision_system import VisionSystem
from robot.sorting_state_machine import SortingStateMachine


class Controller:
    def __init__(
        self,
        global_config: GlobalConfig,
        irl_interface: IRLSystemInterface,
        websocket_manager=None,
    ):
        self.global_config = global_config
        self.lifecycle_stage = SystemLifecycleStage.INITIALIZING
        self.irl_interface = irl_interface

        self.sorting_profile = mkBricklinkCategoriesSortingProfile(global_config)
        self.bin_state_tracker = BinStateTracker(
            global_config, irl_interface["distribution_modules"], self.sorting_profile
        )

        self.vision_system = VisionSystem(
            global_config, irl_interface, websocket_manager
        )
        self.sorting_state_machine = SortingStateMachine(
            self.vision_system, irl_interface
        )

        self.running = False
        self.controller_thread = None

    def start(self):
        self.running = True
        self.vision_system.start()
        self.controller_thread = threading.Thread(target=self._loop)
        self.controller_thread.start()

    def stop(self):
        self.running = False
        self.vision_system.stop()
        if self.controller_thread:
            self.controller_thread.join()

    def _loop(self):
        self.lifecycle_stage = SystemLifecycleStage.STARTING_HARDWARE

        # Initialize storage
        initializeDatabase(self.global_config)
        ensureBlobStorageExists(self.global_config)

        self.lifecycle_stage = SystemLifecycleStage.RUNNING

        # Main loop - run sorting state machine when running
        while self.running and self.lifecycle_stage in [
            SystemLifecycleStage.RUNNING,
            SystemLifecycleStage.PAUSED,
        ]:
            if self.lifecycle_stage == SystemLifecycleStage.RUNNING:
                self.sorting_state_machine.step()
            time.sleep(0.1)

        self.lifecycle_stage = SystemLifecycleStage.STOPPING

        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN

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

    def resume(self):
        if self.lifecycle_stage == SystemLifecycleStage.PAUSED:
            self.lifecycle_stage = SystemLifecycleStage.RUNNING
