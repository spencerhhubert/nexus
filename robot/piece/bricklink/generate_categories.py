from requests_oauthlib import OAuth1
from robot.global_config import GlobalConfig
from robot.piece.bricklink.api import getCategories
from robot.piece.bricklink.db_operations import (
    saveCategory,
    getExistingCategory,
    getCategoryCount,
)


def generateCategories(global_config: GlobalConfig, auth: OAuth1) -> None:
    logger = global_config["logger"]

    logger.info("Starting BrickLink categories generation...")

    initial_count = getCategoryCount(global_config)
    logger.info(f"Database currently has {initial_count} categories")

    categories = getCategories(global_config, auth)

    if not categories:
        logger.error("Failed to retrieve categories from BrickLink API")
        return

    saved_count = 0
    skipped_count = 0

    for category in categories:
        category_id = str(category["category_id"])

        if getExistingCategory(global_config, category_id):
            logger.info(f"Category {category_id} already exists, skipping")
            skipped_count += 1
            continue

        try:
            saveCategory(global_config, category)
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save category {category_id}: {e}")

    final_count = getCategoryCount(global_config)

    logger.info(f"Categories generation completed:")
    logger.info(f"  Retrieved: {len(categories)} categories")
    logger.info(f"  Saved: {saved_count} new categories")
    logger.info(f"  Skipped: {skipped_count} existing categories")
    logger.info(f"  Total in database: {final_count} categories")
