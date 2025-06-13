import numpy as np
from typing import List, Tuple, Union, Callable, TypedDict
from robot.global_config import GlobalConfig


class CameraCalibrationMeasurement(TypedDict):
    distance_down_from_top_of_frame_percent: float
    physical_distance_on_floor_across_frame_cm: float


class CameraCalibration:
    def __init__(
        self,
        global_config: GlobalConfig,
        frame_width: int,
        frame_height: int,
        calibration_measurements: List[CameraCalibrationMeasurement],
    ):
        self.global_config = global_config
        self.frame_width = frame_width
        self.frame_height = frame_height

        assert (
            len(calibration_measurements) > 0
        ), "Must provide at least one calibration measurement"
        self.pixels_per_cm_interpolator = self._buildPixelsPerCmInterpolator(
            calibration_measurements
        )

    def _buildPixelsPerCmInterpolator(
        self, measurements: List[CameraCalibrationMeasurement]
    ) -> Union[Callable[[float], float], np.poly1d]:
        y_positions = []
        pixels_per_cm_values = []

        for measurement in measurements:
            y_position = measurement["distance_down_from_top_of_frame_percent"]
            physical_distance_cm = measurement[
                "physical_distance_on_floor_across_frame_cm"
            ]
            pixels_per_cm = self.frame_width / physical_distance_cm

            y_positions.append(y_position)
            pixels_per_cm_values.append(pixels_per_cm)

        if len(measurements) == 1:
            constant_value = pixels_per_cm_values[0]
            return lambda y_percent: constant_value

        sorted_data = sorted(zip(y_positions, pixels_per_cm_values))
        y_positions, pixels_per_cm_values = zip(*sorted_data)

        degree = min(len(measurements) - 1, 3)
        return np.poly1d(np.polyfit(y_positions, pixels_per_cm_values, degree))

    def getPixelsPerCmAtPosition(self, y_position_percent: float) -> float:
        y_position_percent = max(0.0, min(1.0, y_position_percent))
        return float(self.pixels_per_cm_interpolator(y_position_percent))

    def convertPixelDistanceToCm(
        self, pixel_distance: float, y_position_percent: float
    ) -> float:
        pixels_per_cm = self.getPixelsPerCmAtPosition(y_position_percent)
        return pixel_distance / pixels_per_cm

    def convertCmDistanceToPixels(
        self, cm_distance: float, y_position_percent: float
    ) -> float:
        pixels_per_cm = self.getPixelsPerCmAtPosition(y_position_percent)
        return cm_distance * pixels_per_cm

    def getPhysicalDistanceBetweenPoints(
        self,
        x1_px: float,
        y1_px: float,
        x2_px: float,
        y2_px: float,
    ) -> float:
        # Convert pixel coordinates to percentages
        y1_percent = y1_px / self.frame_height
        y2_percent = y2_px / self.frame_height
        avg_y_percent = (y1_percent + y2_percent) / 2.0

        # Calculate pixel distance
        dx_px = x2_px - x1_px
        dy_px = y2_px - y1_px
        pixel_distance = (dx_px * dx_px + dy_px * dy_px) ** 0.5

        # Convert to physical distance using calibration at average y position
        return self.convertPixelDistanceToCm(pixel_distance, avg_y_percent)

    def getPhysicalVelocity(
        self,
        x1_px: float,
        y1_px: float,
        timestamp1_ms: int,
        x2_px: float,
        y2_px: float,
        timestamp2_ms: int,
    ) -> Tuple[float, float]:
        time_delta_ms = timestamp2_ms - timestamp1_ms
        if time_delta_ms <= 0:
            return (0.0, 0.0)

        # Calculate physical distances in x and y directions
        y1_percent = y1_px / self.frame_height
        y2_percent = y2_px / self.frame_height
        avg_y_percent = (y1_percent + y2_percent) / 2.0

        dx_px = x2_px - x1_px
        dy_px = y2_px - y1_px

        dx_cm = self.convertPixelDistanceToCm(abs(dx_px), avg_y_percent)
        dy_cm = self.convertPixelDistanceToCm(abs(dy_px), avg_y_percent)

        # Preserve direction
        if dx_px < 0:
            dx_cm = -dx_cm
        if dy_px < 0:
            dy_cm = -dy_cm

        velocity_x_cm_per_ms = dx_cm / time_delta_ms
        velocity_y_cm_per_ms = dy_cm / time_delta_ms

        return (velocity_x_cm_per_ms, velocity_y_cm_per_ms)
