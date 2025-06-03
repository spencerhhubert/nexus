import numpy as np
import torch
from typing import List, NamedTuple
from robot.global_config import GlobalConfig
from robot.ai.fast_segment_anything import _segmentFrame
from fastsam import FastSAM  # type: ignore


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
