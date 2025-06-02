import numpy as np
import requests
from PIL import Image
from typing import Dict, Any
import io
from robot.global_config import GlobalConfig


def classifySegment(segment_image: np.ndarray, global_config: GlobalConfig) -> Dict[str, Any]:
    url = "https://api.brickognize.com/predict/"
    
    img = Image.fromarray(segment_image)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {
        'query_image': ('segment.jpg', img_bytes, 'image/jpeg')
    }
    
    headers = {
        'accept': 'application/json'
    }
    
    response = requests.post(url, headers=headers, files=files)
    return response.json()