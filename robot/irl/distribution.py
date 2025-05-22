from typing import List
from robot.irl.motors import Servo


class Bin:
    def __init__(self, servo: Servo, category: str):
        self.servo = servo
        self.category = category


class DistributionModule:
    def __init__(self, servo: Servo, distance_from_camera: int, bins: List[Bin]):
        self.servo = servo
        self.distance_from_camera = distance_from_camera
        self.bins = bins
