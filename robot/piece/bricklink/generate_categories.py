from requests_oauthlib import OAuth1
from tqdm import tqdm
from robot.piece.bricklink.generate_piece_config import PieceGenerationConfig
from robot.piece.bricklink.api import getCategories
from robot.piece.bricklink.db_operations import (
    saveCategory,
    getExistingCategory,
    getCategoryCount,
)


def generateCategories(piece_config: PieceGenerationConfig, auth: OAuth1) -> None:
    logger = piece_config["logger"]

    logger.info("Starting BrickLink categories generation...")

    initial_count = getCategoryCount(piece_config)
    logger.info(f"Database currently has {initial_count} categories")

    categories = getCategories(auth)

    if not categories:
        logger.error("Failed to retrieve categories from BrickLink API")
        return

    saved_count = 0
    skipped_count = 0

    with tqdm(categories, desc="Generating categories", unit="category") as pbar:
        for category in pbar:
            category_id = str(category["category_id"])

            if getExistingCategory(piece_config, category_id):
                tqdm.write(f"Category {category_id} already exists, skipping")
                skipped_count += 1
                pbar.set_postfix(saved=saved_count, skipped=skipped_count)
                continue

            try:
                saveCategory(piece_config, logger, category)
                saved_count += 1
                pbar.set_postfix(saved=saved_count, skipped=skipped_count)
            except Exception as e:
                tqdm.write(f"Failed to save category {category_id}: {e}")

    final_count = getCategoryCount(piece_config)

    logger.info(f"Categories generation completed:")
    logger.info(f"  Retrieved: {len(categories)} categories")
    logger.info(f"  Saved: {saved_count} new categories")
    logger.info(f"  Skipped: {skipped_count} existing categories")
    logger.info(f"  Total in database: {final_count} categories")
