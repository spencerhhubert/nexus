import os
import requests
import time
import json
from typing import Optional, Dict, Any
from requests_oauthlib import OAuth1
from robot.global_config import GlobalConfig
from robot.piece.bricklink.types import BricklinkSearchResponse


def getScrapingConfig() -> Dict[str, Any]:
    cookies_json = os.environ.get("BL_SCRAPING_COOKIES")
    if not cookies_json:
        raise ValueError("Missing required environment variable: BL_SCRAPING_COOKIES")

    try:
        cookies = json.loads(cookies_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in BL_SCRAPING_COOKIES: {e}")

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    return {"cookies": cookies, "headers": headers}


def scrapePrimaryId(
    ldraw_id: str, global_config: GlobalConfig, auth: OAuth1
) -> Optional[str]:
    logger = global_config["logger"]

    try:
        scraping_config = getScrapingConfig()

        base_url = "https://www.bricklink.com"
        search_path = f"/ajax/clone/search/searchproduct.ajax?q={ldraw_id}&st=0&cond=&type=&cat=&yf=0&yt=0&loc=&reg=0&ca=0&ss=&pmt=&nmp=0&color=-1&min=0&max=0&minqty=0&nosuperlot=1&incomplete=0&showempty=1&rpp=25&pi=1&ci=0"

        # Add referer to headers
        headers = scraping_config["headers"].copy()
        headers["referer"] = f"https://www.bricklink.com/v2/search.page?q={ldraw_id}"

        logger.info(f"Scraping BrickLink search for ID: {ldraw_id}")
        response = requests.get(
            base_url + search_path, cookies=scraping_config["cookies"], headers=headers
        )

        if response.status_code != 200:
            logger.warning(
                f"Scraping failed for {ldraw_id}, status: {response.status_code}"
            )
            return None

        search_data = response.json()

        if "result" not in search_data:
            logger.info(f"No search results found for {ldraw_id}")
            return None

        if len(search_data["result"]["typeList"]) == 0:
            logger.info(f"No search results in typeList for {ldraw_id}")
            return None

        search_results = search_data["result"]["typeList"][0]["items"]

        # Try to find primary ID by checking alternate IDs via API
        for result in search_results:
            bl_primary_id = result["strItemNo"]

            # Use API to get part info and check alternate IDs
            try:
                from robot.piece.bricklink.api import getPartInfo

                part_info = getPartInfo(bl_primary_id, global_config, auth)

                if part_info and "alternate_no" in part_info:
                    alternate_ids = part_info["alternate_no"].split(",")
                    alternate_ids = [aid.strip() for aid in alternate_ids]

                    if ldraw_id in alternate_ids:
                        logger.info(f"Found primary ID {bl_primary_id} for {ldraw_id}")
                        return bl_primary_id

            except Exception as e:
                logger.warning(f"Failed to check alternates for {bl_primary_id}: {e}")
                continue

        # If only one result and no alternates found, might be the primary ID itself
        if len(search_results) == 1:
            bl_primary_id = search_results[0]["strItemNo"]
            logger.info(f"Single result found, using {bl_primary_id} for {ldraw_id}")
            return bl_primary_id

        logger.info(f"Could not determine primary ID for {ldraw_id}")
        return None

    except Exception as e:
        logger.error(f"Error scraping primary ID for {ldraw_id}: {e}")
        return None
