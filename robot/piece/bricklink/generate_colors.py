from requests_oauthlib import OAuth1
from tqdm import tqdm
from robot.piece.bricklink.generate_piece_config import PieceGenerationConfig
from robot.piece.bricklink.api import getColors
from robot.piece.bricklink.db_operations import (
    saveColor,
    getExistingColor,
    getColorCount,
)


def generateColors(piece_config: PieceGenerationConfig, auth: OAuth1) -> None:
    logger = piece_config["logger"]

    logger.info("Starting BrickLink colors generation...")

    initial_count = getColorCount(piece_config)
    logger.info(f"Database currently has {initial_count} colors")

    colors = getColors(auth)

    if not colors:
        logger.error("Failed to retrieve colors from BrickLink API")
        return

    saved_count = 0
    skipped_count = 0

    with tqdm(colors, desc="Generating colors", unit="color") as pbar:
        for color in pbar:
            color_id = str(color["color_id"])

            if getExistingColor(piece_config, color_id):
                tqdm.write(f"Color {color_id} already exists, skipping")
                skipped_count += 1
                pbar.set_postfix(saved=saved_count, skipped=skipped_count)
                continue

            try:
                saveColor(piece_config, logger, color)
                saved_count += 1
                pbar.set_postfix(saved=saved_count, skipped=skipped_count)
            except Exception as e:
                tqdm.write(f"Failed to save color {color_id}: {e}")

    final_count = getColorCount(piece_config)

    logger.info(f"Colors generation completed:")
    logger.info(f"  Retrieved: {len(colors)} colors")
    logger.info(f"  Saved: {saved_count} new colors")
    logger.info(f"  Skipped: {skipped_count} existing colors")
    logger.info(f"  Total in database: {final_count} colors")
