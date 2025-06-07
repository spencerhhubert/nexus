from typing import List
from robot.irl.motors import Servo
from robot.global_config import GlobalConfig


class Bin:
    def __init__(
        self, global_config: GlobalConfig, servo: Servo, category: str, bin_idx: int
    ):
        self.global_config = global_config
        self.servo = servo
        self.category = category
        self.bin_idx = bin_idx


class DistributionModule:
    def __init__(
        self,
        global_config: GlobalConfig,
        servo: Servo,
        distance_from_camera_cm: int,
        bins: List[Bin],
        distribution_module_idx: int,
    ):
        self.global_config = global_config
        self.servo = servo
        self.distance_from_camera_cm = distance_from_camera_cm
        self.bins = bins
        self.distribution_module_idx = distribution_module_idx
