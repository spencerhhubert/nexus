from requests_oauthlib import OAuth1
from robot.global_config import GlobalConfig
from robot.piece.bricklink.api import getColors
from robot.piece.bricklink.db_operations import (
    saveColor,
    getExistingColor,
    getColorCount,
)


def generateColors(global_config: GlobalConfig, auth: OAuth1) -> None:
    logger = global_config["logger"]

    logger.info("Starting BrickLink colors generation...")

    initial_count = getColorCount(global_config)
    logger.info(f"Database currently has {initial_count} colors")

    colors = getColors(global_config, auth)

    if not colors:
        logger.error("Failed to retrieve colors from BrickLink API")
        return

    saved_count = 0
    skipped_count = 0

    for color in colors:
        color_id = str(color["color_id"])

        if getExistingColor(global_config, color_id):
            logger.info(f"Color {color_id} already exists, skipping")
            skipped_count += 1
            continue

        try:
            saveColor(global_config, color)
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save color {color_id}: {e}")

    final_count = getColorCount(global_config)

    logger.info(f"Colors generation completed:")
    logger.info(f"  Retrieved: {len(colors)} colors")
    logger.info(f"  Saved: {saved_count} new colors")
    logger.info(f"  Skipped: {skipped_count} existing colors")
    logger.info(f"  Total in database: {final_count} colors")
