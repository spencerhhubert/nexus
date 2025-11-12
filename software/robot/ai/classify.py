import numpy as np
import requests
from PIL import Image
from typing import cast, Optional, Dict, List
import io
from robot.global_config import GlobalConfig
from robot.ai.brickognize_types import BrickognizeClassificationResult
from robot.our_types.classify import ClassificationResult
from robot.piece.bricklink.api import getPartInfo
from robot.piece.bricklink.auth import mkAuth


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


def classifyPiece(
    frames: List[np.ndarray], global_config: GlobalConfig
) -> Optional[ClassificationResult]:
    if not frames:
        global_config["logger"].warning("No frames provided for classification")
        return None

    provider = global_config.get("classification_provider", "brickognize")
    global_config["logger"].info(f"Using classification provider: {provider}")

    if provider == "brickognize":
        return classifyWithBrickognize(frames[0], global_config)
    elif provider == "brickit":
        return classifyWithBrickit(frames[0], global_config)
    else:
        global_config["logger"].error(f"Unknown classification provider: {provider}")
        return None


def classifyWithBrickognize(
    frame: np.ndarray, global_config: GlobalConfig
) -> Optional[ClassificationResult]:
    try:
        result = brickognizeClassifySegment(frame, global_config)
        if result and result.get("items") and len(result["items"]) > 0:
            best_item = result["items"][0]
            item_id = best_item.get("id")

            if item_id:
                auth = mkAuth()
                part_data = getPartInfo(item_id, auth)
                if part_data and part_data.get("category_id"):
                    return ClassificationResult(
                        id=item_id, category_id=str(part_data["category_id"])
                    )

        return None
    except Exception as e:
        global_config["logger"].error(f"Brickognize classification failed: {e}")
        return None


def classifyWithBrickit(
    frame: np.ndarray, global_config: GlobalConfig
) -> Optional[ClassificationResult]:
    raise NotImplementedError("Brickit classification not implemented yet")
