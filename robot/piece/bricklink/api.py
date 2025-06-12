import requests
import time
from typing import List, Optional, cast
from requests_oauthlib import OAuth1
from robot.global_config import GlobalConfig
from robot.piece.bricklink.types import (
    BricklinkPartResponse,
    BricklinkPartData,
    BricklinkCategoriesResponse,
    BricklinkCategoryData,
    BricklinkColorsResponse,
    BricklinkColorData,
)


BASE_URL = "https://api.bricklink.com/api/store/v1"


def _makeApiRequest(
    endpoint: str, global_config: GlobalConfig, auth: OAuth1
) -> Optional[dict]:
    logger = global_config["logger"]

    url = BASE_URL + endpoint

    try:
        response = requests.get(url, auth=auth)

        if response.status_code != 200:
            logger.error(
                f"BrickLink API request failed: {response.status_code} - {response.text}"
            )
            return None

        data = response.json()

        if "data" not in data:
            logger.error(f"BrickLink API response missing data field: {data}")
            return None

        # Rate limiting
        rate_limit_ms = global_config["bricklink_rate_limit_wait_ms"]
        time.sleep(rate_limit_ms / 1000.0)

        return data

    except Exception as e:
        logger.error(f"BrickLink API request error for {endpoint}: {e}")
        return None


def getPartInfo(
    part_id: str, global_config: GlobalConfig, auth: OAuth1
) -> Optional[BricklinkPartData]:
    logger = global_config["logger"]

    endpoint = f"/items/part/{part_id}"
    response_data = _makeApiRequest(endpoint, global_config, auth)

    if not response_data:
        return None

    try:
        typed_response = cast(BricklinkPartResponse, response_data)
        return typed_response["data"]
    except Exception as e:
        logger.error(f"Failed to parse part info for {part_id}: {e}")
        return None


def getCategories(
    global_config: GlobalConfig, auth: OAuth1
) -> List[BricklinkCategoryData]:
    logger = global_config["logger"]

    endpoint = "/categories"
    response_data = _makeApiRequest(endpoint, global_config, auth)

    if not response_data:
        return []

    try:
        typed_response = cast(BricklinkCategoriesResponse, response_data)
        logger.info(
            f"Retrieved {len(typed_response['data'])} categories from BrickLink API"
        )
        return typed_response["data"]
    except Exception as e:
        logger.error(f"Failed to parse categories: {e}")
        return []


def getColors(global_config: GlobalConfig, auth: OAuth1) -> List[BricklinkColorData]:
    logger = global_config["logger"]

    endpoint = "/colors"
    response_data = _makeApiRequest(endpoint, global_config, auth)

    if not response_data:
        return []

    try:
        typed_response = cast(BricklinkColorsResponse, response_data)
        all_colors = typed_response["data"]

        # Filter to only solid colors like the old code did
        solid_colors = [color for color in all_colors if color["color_type"] == "Solid"]

        logger.info(
            f"Retrieved {len(solid_colors)} solid colors from BrickLink API (filtered from {len(all_colors)} total)"
        )
        return solid_colors
    except Exception as e:
        logger.error(f"Failed to parse colors: {e}")
        return []
