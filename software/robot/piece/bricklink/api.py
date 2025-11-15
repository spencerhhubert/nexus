import requests
import time
from typing import List, Optional, cast
from requests_oauthlib import OAuth1
from robot.piece.bricklink.consts import BRICKLINK_API_RATE_LIMIT_DELAY_MS
from robot.piece.bricklink.types import (
    BricklinkPartResponse,
    BricklinkPartData,
    BricklinkCategoriesResponse,
    BricklinkCategoryResponse,
    BricklinkCategoryData,
    BricklinkColorsResponse,
    BricklinkColorData,
)


BASE_URL = "https://api.bricklink.com/api/store/v1"


def _makeApiRequest(endpoint: str, auth: OAuth1) -> Optional[dict]:
    url = BASE_URL + endpoint

    try:
        response = requests.get(url, auth=auth)

        if response.status_code != 200:
            return None

        data = response.json()

        if "data" not in data:
            return None

        # Rate limiting
        time.sleep(BRICKLINK_API_RATE_LIMIT_DELAY_MS / 1000.0)

        return data

    except Exception as e:
        return None


def getPartInfo(part_id: str, auth: OAuth1) -> Optional[BricklinkPartData]:
    endpoint = f"/items/part/{part_id}"
    response_data = _makeApiRequest(endpoint, auth)

    if not response_data:
        return None

    try:
        typed_response = cast(BricklinkPartResponse, response_data)
        return typed_response["data"]
    except Exception as e:
        return None


def getCategories(auth: OAuth1) -> List[BricklinkCategoryData]:
    endpoint = "/categories"
    response_data = _makeApiRequest(endpoint, auth)

    if not response_data:
        return []

    try:
        typed_response = cast(BricklinkCategoriesResponse, response_data)
        return typed_response["data"]
    except Exception as e:
        return []


def getCategoryInfo(category_id: int, auth: OAuth1) -> Optional[BricklinkCategoryData]:
    endpoint = f"/categories/{category_id}"
    response_data = _makeApiRequest(endpoint, auth)

    if not response_data:
        return None

    try:
        typed_response = cast(BricklinkCategoryResponse, response_data)
        return typed_response["data"]
    except Exception as e:
        return None


def getColors(auth: OAuth1) -> List[BricklinkColorData]:
    endpoint = "/colors"
    response_data = _makeApiRequest(endpoint, auth)

    if not response_data:
        return []

    try:
        typed_response = cast(BricklinkColorsResponse, response_data)
        all_colors = typed_response["data"]

        # Filter to only solid colors like the old code did
        solid_colors = [color for color in all_colors if color["color_type"] == "Solid"]

        return solid_colors
    except Exception as e:
        return []
