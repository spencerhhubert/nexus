from typing import List
from robot.irl.motors import Servo
from robot.global_config import GlobalConfig


class Bin:
    def __init__(self, global_config: GlobalConfig, servo: Servo, category: str):
        self.global_config = global_config
        self.servo = servo
        self.category = category


class DistributionModule:
    def __init__(self, global_config: GlobalConfig, servo: Servo, distance_from_camera: int, bins: List[Bin]):
        self.global_config = global_config
        self.servo = servo
        self.distance_from_camera = distance_from_camera
        self.bins = bins
