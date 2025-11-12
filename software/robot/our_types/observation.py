from typing import TypedDict, Tuple
import numpy as np
from robot.our_types.classify import ClassificationResult


class BoundingBox(TypedDict):
    x1: int
    y1: int
    x2: int
    y2: int


class Observation(TypedDict):
    frame: np.ndarray
    bounding_box: BoundingBox
    classification_result: ClassificationResult
