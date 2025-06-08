import time
import threading
from typing import List
from robot.global_config import GlobalConfig
from robot.bin_state_tracker import BinCoordinates
from robot.irl.distribution import DistributionModule
from robot.irl.motors import Servo


class DoorScheduler:
    def __init__(
        self,
        global_config: GlobalConfig,
        distribution_modules: List[DistributionModule],
    ):
        self.global_config = global_config
        self.distribution_modules = distribution_modules

    def _getServosForBin(self, bin_coordinates: BinCoordinates) -> tuple[Servo, Servo]:
        dm_idx = bin_coordinates["distribution_module_idx"]
        bin_idx = bin_coordinates["bin_idx"]

        assert (
            dm_idx < len(self.distribution_modules)
        ), f"Distribution module index {dm_idx} out of range (have {len(self.distribution_modules)} modules)"

        dm = self.distribution_modules[dm_idx]
        assert (
            bin_idx < len(dm.bins)
        ), f"Bin index {bin_idx} out of range for distribution module {dm_idx} (has {len(dm.bins)} bins)"

        return dm.servo, dm.bins[bin_idx].servo

    def scheduleDoorAction(
        self, bin_coordinates: BinCoordinates, delay_ms: int = 0
    ) -> None:
        def executeDoorAction(delay: int, coords: BinCoordinates):
            # offset due to lag?? debt to be paid back. that, or something is wrong with the code estimating the speed of the conveyor
            delay += self.global_config["door_delay_offset_ms"]
            if delay < 0:
                delay = 0
            if delay > 0:
                time.sleep(delay / 1000.0)

            dm_servo, bin_servo = self._getServosForBin(coords)
            assert (
                dm_servo is not None
            ), f"Distribution module servo is None for bin {coords}"
            assert bin_servo is not None, f"Bin servo is None for bin {coords}"

            conveyor_door_open_angle = self.global_config["conveyor_door_open_angle"]
            bin_door_open_angle = self.global_config["bin_door_open_angle"]
            door_closed_angle = self.global_config["door_closed_angle"]
            door_open_duration_ms = self.global_config["door_open_duration_ms"]

            self.global_config["logger"].info(
                f"Opening doors for bin {coords} - conveyor: {conveyor_door_open_angle}°, bin: {bin_door_open_angle}°"
            )
            dm_servo.setAngle(conveyor_door_open_angle)
            bin_servo.setAngle(bin_door_open_angle)

            time.sleep(door_open_duration_ms / 1000.0)

            self.global_config["logger"].info(
                f"Closing doors for bin {coords} to {door_closed_angle} degrees"
            )
            dm_servo.setAngle(door_closed_angle, duration=500)
            bin_servo.setAngle(door_closed_angle)

        thread = threading.Thread(
            target=executeDoorAction, args=(delay_ms, bin_coordinates), daemon=True
        )
        thread.start()
