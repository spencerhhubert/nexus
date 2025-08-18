import numpy as np
import requests
from PIL import Image
from typing import cast
import io
from robot.global_config import GlobalConfig
from robot.ai.brickognize_types import BrickognizeClassificationResult


def brickognizeClassifySegment(
    segment_image: np.ndarray, global_config: GlobalConfig
) -> BrickognizeClassificationResult:
    url = "https://api.brickognize.com/predict/"

    img = Image.fromarray(segment_image)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    files = {"query_image": ("segment.jpg", img_bytes, "image/jpeg")}

    headers = {"accept": "application/json"}

    response = requests.post(url, headers=headers, files=files)
    out = cast(BrickognizeClassificationResult, response.json())
    filter_category_substrings = ["primo", "duplo"]
    out["items"] = [
        item
        for item in out["items"]
        if not any(
            substring in item["category"].lower()
            for substring in filter_category_substrings
        )
    ]
    global_config["logger"].info(f"Brickognize Filtered Response {out}")
    return out
