import os
import numpy as np
from PIL import Image
import time
from robot.global_config import GlobalConfig


def ensureBlobStorageExists(global_config: GlobalConfig) -> None:
    blob_path = global_config['blob_storage_path']
    os.makedirs(blob_path, exist_ok=True)


def saveBlobImage(global_config: GlobalConfig, image_data: np.ndarray, file_prefix: str) -> str:
    ensureBlobStorageExists(global_config)
    
    timestamp = int(time.time() * 1000)
    filename = f"{file_prefix}_{timestamp}.jpg"
    file_path = os.path.join(global_config['blob_storage_path'], filename)
    
    img = Image.fromarray(image_data)
    img.save(file_path)
    
    return file_path


def loadBlobImage(global_config: GlobalConfig, file_path: str) -> np.ndarray:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Blob image not found: {file_path}")
    
    img = Image.open(file_path)
    return np.array(img)