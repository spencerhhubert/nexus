from requests_oauthlib import OAuth1
from robot.global_config import GlobalConfig
from robot.piece.bricklink.api import getPartInfo
from robot.piece.bricklink.scraping import scrapePrimaryId
from robot.piece.bricklink.db_operations import (
    saveKind,
    saveKindAlternateIds,
    getExistingKind,
    getKindCount,
)


def generateKinds(global_config: GlobalConfig, auth: OAuth1) -> None:
    logger = global_config["logger"]

    logger.info("Starting BrickLink kinds generation...")

    initial_count = getKindCount(global_config)
    logger.info(f"Database currently has {initial_count} kinds")

    ldraw_parts_list_path = global_config["ldraw_parts_list_path"]

    try:
        with open(ldraw_parts_list_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(
            f"Failed to read LDraw parts list from {ldraw_parts_list_path}: {e}"
        )
        return

    logger.info(f"Found {len(lines)} parts in LDraw parts list")

    saved_count = 0
    skipped_count = 0
    failed_count = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or not line.endswith(".dat"):
            continue

        parts = line.split(".dat")
        if len(parts) < 2:
            continue

        ldraw_id = parts[0].strip()
        ldraw_name = parts[1].strip() if len(parts) > 1 else ""

        logger.info(
            f"Processing {i+1}/{len(lines)}: LDraw ID {ldraw_id} ({ldraw_name})"
        )

        try:
            bl_primary_id = scrapePrimaryId(ldraw_id, global_config, auth)
            if not bl_primary_id:
                logger.info(
                    f"Could not find BrickLink primary ID for {ldraw_id}, skipping"
                )
                failed_count += 1
                continue

            if getExistingKind(global_config, bl_primary_id):
                logger.info(f"Kind {bl_primary_id} already exists, skipping")
                skipped_count += 1
                continue

            part_info = getPartInfo(bl_primary_id, global_config, auth)
            if not part_info:
                logger.warning(f"Could not get part info for {bl_primary_id}, skipping")
                failed_count += 1
                continue

            saveKind(global_config, part_info)

            alternate_ids = []
            if part_info.get("alternate_no"):
                alternate_ids = [
                    aid.strip() for aid in part_info["alternate_no"].split(",")
                ]

            alternate_ids.append(ldraw_id)
            alternate_ids.append(bl_primary_id)
            alternate_ids = list(set(alternate_ids))

            saveKindAlternateIds(global_config, bl_primary_id, alternate_ids)

            saved_count += 1

        except Exception as e:
            logger.error(f"Failed to process {ldraw_id}: {e}")
            failed_count += 1

    final_count = getKindCount(global_config)

    logger.info(f"Kinds generation completed:")
    logger.info(f"  Processed: {len(lines)} LDraw parts")
    logger.info(f"  Saved: {saved_count} new kinds")
    logger.info(f"  Skipped: {skipped_count} existing kinds")
    logger.info(f"  Failed: {failed_count} parts")
    logger.info(f"  Total in database: {final_count} kinds")
