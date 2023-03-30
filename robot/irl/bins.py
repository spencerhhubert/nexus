class DistributionModule:
    def __init__(self, servo, distance_from_camera, bins=[]):
        self.servo = servo
        self.distance_from_camera = distance_from_camera
        self.bins = bins

class Bin:
    def __init__(self, servo, category=None):
        self.servo = servo
        self.category = category
