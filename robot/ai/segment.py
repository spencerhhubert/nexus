import numpy as np
import torch
from typing import List, NamedTuple
from robot.global_config import GlobalConfig
from robot.ai.fast_segment_anything import _segmentFrame


class Segment(NamedTuple):
    bbox: tuple[int, int, int, int]
    mask: torch.Tensor


def segmentFrame(frame: np.ndarray, global_config: GlobalConfig) -> List[Segment]:
    processed_groups = _segmentFrame(frame, global_config)

    segments = []
    for group in processed_groups:
        y_min, y_max, x_min, x_max = group["bbox"]
        segments.append(Segment(bbox=(y_min, y_max, x_min, x_max), mask=group["mask"]))

    return segments
