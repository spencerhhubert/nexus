import cv2
import time
import numpy as np
import os
from typing import Optional, List, Tuple, TypedDict
from robot.global_config import GlobalConfig

COLOR_1_RGB = (175, 1, 0)
MARKER_HEIGHT_FROM_CONVEYOR_MM = 8.0
SQUARE_SIZE_MM = 8.0
COLOR_TOLERANCE = 50
CALIBRATION_DISTANCE_TOLERANCE_PERCENT = 10
NUM_CALIBRATION_SQUARES = 2


class CalibrationData(TypedDict):
    pixels_per_cm_at_y: List[Tuple[int, float]]


class Camera:
    def __init__(
        self,
        global_config: GlobalConfig,
        device_index: int,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        distance_across_frame_cm: float = 120.0,
    ):
        self.global_config = global_config
        self.debug_level = global_config["debug_level"]
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.distance_across_frame_cm = distance_across_frame_cm
        self.calibration_data: Optional[CalibrationData] = None

        if self.debug_level > 0:
            print(f"Initializing camera with device index: {device_index}")

        self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera at index {device_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        if self.debug_level > 0:
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(
                f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS"
            )

    def captureFrame(self) -> Optional[np.ndarray]:
        ret, frame = self.cap.read()
        if not ret:
            if self.debug_level > 0:
                print("Failed to capture frame")
            return None
        return frame

    def release(self) -> None:
        if self.debug_level > 0:
            print("Releasing camera")
        self.cap.release()

    def isOpened(self) -> bool:
        return self.cap.isOpened()

    def calibrateFromPerpendicularColoredSquares(self, frame: np.ndarray, expected_frame_width_cm: float) -> bool:
        squares = self._detectColoredSquares(frame)

        if len(squares) != NUM_CALIBRATION_SQUARES:
            self.global_config["logger"].warning(
                f"Expected {NUM_CALIBRATION_SQUARES} red squares, found {len(squares)}"
            )
            return False

        # Sort squares by center Y, then center X
        squares.sort(key=lambda s: (np.mean(s[:, 1]), np.mean(s[:, 0])))

        # Calculate global perspective using all squares together
        self.global_config["logger"].info(f"Calculating perspective from {len(squares)} squares")

        # Collect all corner points and their real-world positions
        all_image_points = []
        all_world_points = []

        for i, square_corners in enumerate(squares):
            center_x = int(np.mean(square_corners[:, 0]))
            center_y = int(np.mean(square_corners[:, 1]))

            self.global_config["logger"].info(f"Square {i+1}: center at ({center_x}, {center_y})")

            # Add all 4 corners of this square to our point collections
            for j, corner in enumerate(square_corners):
                all_image_points.append(corner)
                # Real world coordinates relative to first square's top-left corner
                world_x = i * SQUARE_SIZE_MM * 2  # Assume squares are spaced 2 square-widths apart
                world_y = 0
                if j == 0:  # top-left
                    all_world_points.append([world_x, world_y])
                elif j == 1:  # top-right
                    all_world_points.append([world_x + SQUARE_SIZE_MM, world_y])
                elif j == 2:  # bottom-right
                    all_world_points.append([world_x + SQUARE_SIZE_MM, world_y + SQUARE_SIZE_MM])
                elif j == 3:  # bottom-left
                    all_world_points.append([world_x, world_y + SQUARE_SIZE_MM])

        if len(all_image_points) < 8:  # Need at least 8 points for good homography
            self.global_config["logger"].error(f"Not enough points for perspective calculation: {len(all_image_points)}")
            return False

        # Calculate global homography from image to world coordinates
        image_points = np.array(all_image_points, dtype=np.float32)
        world_points = np.array(all_world_points, dtype=np.float32)

        try:
            homography, _ = cv2.findHomography(image_points, world_points, cv2.RANSAC)
            if homography is None:
                self.global_config["logger"].error("Failed to calculate homography")
                return False
        except Exception as e:
            self.global_config["logger"].error(f"Homography calculation failed: {e}")
            return False

        self.global_config["logger"].info("Global homography calculated successfully")

        # Now calculate pixels per cm at different Y positions using the global transformation
        calibration_points = []
        for y in range(0, self.height, 100):  # Sample every 100 pixels
            # Test how a 1cm horizontal distance transforms at this Y position
            test_points_img = np.array([
                [[self.width // 2, y]],
                [[self.width // 2 + 10, y]]  # 10 pixels to the right
            ], dtype=np.float32)

            # Transform to world coordinates
            world_points = cv2.perspectiveTransform(test_points_img, homography)

            # Calculate real-world distance
            world_dist_mm = np.linalg.norm(world_points[1] - world_points[0])

            if world_dist_mm > 0:
                # Calculate pixels per mm, then convert to pixels per cm
                pixels_per_mm = 10.0 / world_dist_mm  # 10 pixels / world_dist_mm
                pixels_per_cm_at_y = pixels_per_mm * 10
                calibration_points.append((y, pixels_per_cm_at_y))

                self.global_config["logger"].info(f"Y={y}: {pixels_per_cm_at_y:.1f} px/cm")

        calibration_points.sort()
        unique_points = []
        for y, ppcm in calibration_points:
            if not unique_points or abs(unique_points[-1][0] - y) > 10:
                unique_points.append((y, ppcm))

        self.calibration_data = CalibrationData(pixels_per_cm_at_y=unique_points)
        self.global_config["logger"].info(f"Camera calibrated with {len(unique_points)} reference points")

        middle_y = self.height // 2
        pixels_per_cm_at_middle = self.getPixelsPerCmAtY(middle_y)
        if pixels_per_cm_at_middle is not None:
            frame_width_cm = self.width / pixels_per_cm_at_middle
            self.global_config["logger"].info(f"Predicted frame width at center: {frame_width_cm:.2f} cm")

            tolerance = expected_frame_width_cm * CALIBRATION_DISTANCE_TOLERANCE_PERCENT / 100.0
            difference = abs(frame_width_cm - expected_frame_width_cm)

            if difference > tolerance:
                self.global_config["logger"].error(
                    f"Calibration validation failed: predicted width {frame_width_cm:.2f} cm differs from expected "
                    f"{expected_frame_width_cm:.2f} cm by {difference:.2f} cm (tolerance: ±{tolerance:.2f} cm)"
                )
                return False

            self.global_config["logger"].info(
                f"Calibration validation successful: predicted width within tolerance "
                f"(difference: {difference:.2f} cm, tolerance: ±{tolerance:.2f} cm)"
            )

        return True

    def _detectColoredSquares(self, frame: np.ndarray) -> List[np.ndarray]:
        return self._detectColoredSquaresForColor(frame, COLOR_1_RGB)

    def _detectColoredSquaresForColor(self, frame: np.ndarray, target_color: Tuple[int, int, int]) -> List[np.ndarray]:
        squares = []
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mask = self._createColorMask(frame_rgb, target_color)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:
                continue

            # Approximate contour to get quadrilateral
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Check if we have roughly a quadrilateral
            if len(approx) >= 4:
                # Get the 4 corners of the perspective-distorted square
                hull = cv2.convexHull(approx)
                if len(hull) >= 4:
                    # Sort corners to consistent order (top-left, top-right, bottom-right, bottom-left)
                    corners = hull[:4].reshape(4, 2)
                    # Sort by y coordinate first, then by x within each row
                    sorted_corners = corners[np.lexsort((corners[:, 0], corners[:, 1]))]

                    # Reorder to clockwise from top-left
                    if len(sorted_corners) >= 4:
                        top_two = sorted_corners[:2]
                        bottom_two = sorted_corners[2:]

                        # Sort top two by x (left to right)
                        top_left, top_right = top_two[np.argsort(top_two[:, 0])]
                        # Sort bottom two by x (left to right)
                        bottom_left, bottom_right = bottom_two[np.argsort(bottom_two[:, 0])]

                        ordered_corners = np.array([top_left, top_right, bottom_right, bottom_left])
                        squares.append(ordered_corners)

        return squares

    def _createColorMask(self, frame_rgb: np.ndarray, target_color: Tuple[int, int, int]) -> np.ndarray:
        lower = np.array([max(0, c - COLOR_TOLERANCE) for c in target_color])
        upper = np.array([min(255, c + COLOR_TOLERANCE) for c in target_color])
        return cv2.inRange(frame_rgb, lower, upper)

    def getPixelsPerCmAtY(self, y: int) -> Optional[float]:
        if self.calibration_data is None:
            return None

        points = self.calibration_data["pixels_per_cm_at_y"]
        if not points:
            return None

        if len(points) == 1:
            return points[0][1]

        points_sorted = sorted(points, key=lambda p: p[0])

        if y <= points_sorted[0][0]:
            return points_sorted[0][1]

        if y >= points_sorted[-1][0]:
            return points_sorted[-1][1]

        for i in range(len(points_sorted) - 1):
            y1, ppcm1 = points_sorted[i]
            y2, ppcm2 = points_sorted[i + 1]

            if y1 <= y <= y2:
                ratio = (y - y1) / (y2 - y1)
                return ppcm1 + ratio * (ppcm2 - ppcm1)

        return points_sorted[0][1]

    def saveDebugCalibrationImage(self, frame: np.ndarray, debug_path: str = "calibration_debug.jpg") -> None:
        debug_frame = frame.copy()
        squares = self._detectColoredSquares(frame)

        for i, square_corners in enumerate(squares):
            # Draw the actual perspective-distorted quadrilateral
            pts = square_corners.reshape((-1, 1, 2)).astype(np.int32)
            cv2.polylines(debug_frame, [pts], True, (0, 255, 0), 3)

            # Calculate and draw center point
            center_x = int(np.mean(square_corners[:, 0]))
            center_y = int(np.mean(square_corners[:, 1]))
            cv2.circle(debug_frame, (center_x, center_y), 5, (0, 255, 0), -1)

            # Draw corner points
            for j, corner in enumerate(square_corners):
                cv2.circle(debug_frame, tuple(corner.astype(int)), 3, (255, 0, 0), -1)
                cv2.putText(debug_frame, f"{j}", tuple(corner.astype(int) + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

            cv2.putText(debug_frame, f"S{i+1}", (center_x - 20, center_y - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if self.calibration_data is not None:
                ppcm = self.getPixelsPerCmAtY(center_y)
                if ppcm is not None:
                    cv2.putText(debug_frame, f"{ppcm:.1f}px/cm", (center_x + 20, center_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        if self.calibration_data is not None:
            self._drawCalibrationGrid(debug_frame)

        if self.calibration_data is not None:
            middle_y = self.height // 2
            ppcm_middle = self.getPixelsPerCmAtY(middle_y)
            if ppcm_middle is not None:
                frame_width_cm = self.width / ppcm_middle
                cv2.putText(debug_frame, f"Frame width: {frame_width_cm:.1f}cm",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(debug_frame, f"Expected: {self.distance_across_frame_cm:.1f}cm",
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.putText(debug_frame, f"Squares found: {len(squares)}",
                   (10, self.height - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imwrite(debug_path, debug_frame)
        self.global_config["logger"].info(f"Debug calibration image saved to {debug_path}")

    def _drawCalibrationGrid(self, debug_frame: np.ndarray) -> None:
        grid_spacing_cm = 5.0

        for y in range(0, self.height, 100):
            ppcm = self.getPixelsPerCmAtY(y)
            if ppcm is None:
                continue

            x_step = int(ppcm * grid_spacing_cm)
            if x_step > 0:
                for x in range(0, self.width, x_step):
                    cv2.line(debug_frame, (x, y), (x, min(y + 100, self.height)), (0, 100, 255), 2)

        for y in range(0, self.height, 200):
            cv2.line(debug_frame, (0, y), (self.width, y), (0, 150, 255), 2)

            ppcm = self.getPixelsPerCmAtY(y)
            if ppcm is not None:
                cv2.putText(debug_frame, f"y={y}, {ppcm:.1f}px/cm",
                           (self.width - 300, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 255), 3)


def discoverCameras() -> List[int]:
    available_cameras = []

    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available_cameras.append(i)
        cap.release()

    return available_cameras


def connectToCamera(
    camera_device_index: int,
    global_config: GlobalConfig,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    distance_across_frame_cm: float = 120.0,
) -> Camera:
    debug_level = global_config["debug_level"]
    auto_confirm = global_config["auto_confirm"]
    camera = None

    try:
        if debug_level > 0:
            print(f"Attempting to connect to camera at index {camera_device_index}")
        camera = Camera(
            global_config,
            camera_device_index,
            width,
            height,
            fps,
            distance_across_frame_cm,
        )

    except Exception as e:
        if debug_level > 0:
            print(f"Failed to connect to camera at index {camera_device_index}: {e}")

        discovered_cameras = discoverCameras()
        if not discovered_cameras:
            print(
                f"Failed to connect to camera at index {camera_device_index} and could not discover any cameras"
            )
            raise e

        discovered_camera = discovered_cameras[0]

        if not auto_confirm:
            response = input(
                f"Failed to use camera from environment at index {camera_device_index}. Would you like to automatically try to use discovered camera at index {discovered_camera}? (y/N): "
            )
            if response.lower() not in ["y", "yes"]:
                print("User declined to use discovered camera")
                raise e

        if debug_level > 0:
            print(
                f"Attempting to connect to discovered camera at index {discovered_camera}"
            )

        try:
            camera = Camera(
                global_config,
                discovered_camera,
                width,
                height,
                fps,
                distance_across_frame_cm,
            )
            print(f"Successfully connected to camera at index {discovered_camera}")
        except Exception as discovery_error:
            print(
                f"Failed to connect to discovered camera at index {discovered_camera}: {discovery_error}"
            )
            raise e

    time.sleep(3)
    return camera
