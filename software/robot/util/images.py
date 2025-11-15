import numpy as np
from robot.our_types.observation import BoundingBox


def cropImageToBbox(image: np.ndarray, bbox: BoundingBox) -> np.ndarray:
    height, width = image.shape[:2]

    x1 = max(0, min(bbox["x1"], width - 1))
    y1 = max(0, min(bbox["y1"], height - 1))
    x2 = max(x1 + 1, min(bbox["x2"], width))
    y2 = max(y1 + 1, min(bbox["y2"], height))

    cropped = image[y1:y2, x1:x2]

    return cropped
