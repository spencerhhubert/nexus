import os
import numpy as np
import cv2
from PIL import Image
import time
import json
from typing import Dict, Any, Tuple
from robot.global_config import GlobalConfig
from robot.ai.brickognize_types import BrickognizeClassificationResult


def ensureBlobStorageExists(global_config: GlobalConfig) -> None:
    run_blob_dir = global_config["run_blob_dir"]
    os.makedirs(run_blob_dir, exist_ok=True)


def saveObservationBlob(
    global_config: GlobalConfig,
    full_frame: np.ndarray,
    masked_image: np.ndarray,
    classification_result: BrickognizeClassificationResult,
) -> Tuple[str, str, str]:
    ensureBlobStorageExists(global_config)

    timestamp = int(time.time() * 1000)
    observation_dir = os.path.join(global_config["run_blob_dir"], str(timestamp))
    os.makedirs(observation_dir, exist_ok=True)

    # Save full frame
    full_path = os.path.join(observation_dir, "full.jpg")
    rgb_full = cv2.cvtColor(full_frame, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb_full).save(full_path)

    # Save masked image
    masked_path = os.path.join(observation_dir, "masked.jpg")
    rgb_masked = cv2.cvtColor(masked_image, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb_masked).save(masked_path)

    # Save classification result
    classification_path = os.path.join(observation_dir, "classification.json")
    with open(classification_path, "w") as f:
        json.dump(classification_result, f, indent=2)

    return full_path, masked_path, classification_path


def loadBlobImage(global_config: GlobalConfig, file_path: str) -> np.ndarray:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Blob image not found: {file_path}")

    img = Image.open(file_path)
    rgb_array = np.array(img)
    # Convert RGB back to BGR to maintain consistency with OpenCV format
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_array
