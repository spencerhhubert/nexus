import numpy as np
import torch
from typing import List, NamedTuple, Optional
from robot.global_config import GlobalConfig
from robot.ai.fast_segment_anything import _segmentFrame
from fastsam import FastSAM  # type: ignore
from robot.irl.camera_calibration import CameraCalibration


class Segment(NamedTuple):
    bbox: tuple[int, int, int, int]
    mask: torch.Tensor


def initializeSegmentationModel(global_config: GlobalConfig) -> FastSAM:
    global_config["logger"].info("Loading FastSAM segmentation model...")
    model = FastSAM(global_config["fastsam_weights"])
    global_config["logger"].info("FastSAM model loaded successfully")
    return model


def segmentFrame(
    frame: np.ndarray, model: FastSAM, global_config: GlobalConfig
) -> List[Segment]:
    processed_groups = _segmentFrame(frame, model, global_config)

    segments = []
    for group in processed_groups:
        y_min, y_max, x_min, x_max = group["bbox"]
        segments.append(Segment(bbox=(y_min, y_max, x_min, x_max), mask=group["mask"]))

    return segments


def maskSegment(full_frame: np.ndarray, segment) -> Optional[np.ndarray]:
    y_min, y_max, x_min, x_max = segment.bbox

    if y_min >= y_max or x_min >= x_max:
        return None

    y_min = max(0, y_min)
    y_max = min(full_frame.shape[0] - 1, y_max)
    x_min = max(0, x_min)
    x_max = min(full_frame.shape[1] - 1, x_max)

    cropped_image = full_frame[y_min : y_max + 1, x_min : x_max + 1]

    mask_np = segment.mask.cpu().numpy()
    cropped_mask = mask_np[y_min : y_max + 1, x_min : x_max + 1]
    masked_image = cropped_image.copy()
    masked_image[~cropped_mask] = 0

    return masked_image


def calculateNormalizedBounds(
    full_frame: np.ndarray, segment
) -> tuple[float, float, float, float]:
    y_min, y_max, x_min, x_max = segment.bbox

    center_x = (x_min + x_max) / 2.0 / full_frame.shape[1]
    center_y = (y_min + y_max) / 2.0 / full_frame.shape[0]
    bbox_width = (x_max - x_min) / full_frame.shape[1]
    bbox_height = (y_max - y_min) / full_frame.shape[0]

    return center_x, center_y, bbox_width, bbox_height
