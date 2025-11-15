from requests_oauthlib import OAuth1
from tqdm import tqdm
from robot.piece.bricklink.generate_piece_config import PieceGenerationConfig
from robot.piece.bricklink.api import getPartInfo
from robot.piece.bricklink.scraping import scrapePrimaryId
from robot.piece.bricklink.db_operations import (
    saveKind,
    saveKindAlternateIds,
    getExistingKind,
    getKindCount,
    saveFailedKind,
    getFailedKind,
)
from robot.piece.bricklink.types import GENERATE_PIECE_KIND_FAILED_REASON


def generateKinds(piece_config: PieceGenerationConfig, auth: OAuth1) -> None:
    logger = piece_config["logger"]

    logger.info("Starting BrickLink kinds generation...")

    initial_count = getKindCount(piece_config)
    logger.info(f"Database currently has {initial_count} kinds")

    ldraw_parts_list_path = piece_config["ldraw_parts_list_path"]

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

    # Parse all valid lines first to get accurate progress bar
    valid_lines = []
    for line in lines:
        line = line.strip()
        if not line or ".dat" not in line:
            continue

        parts = line.split(".dat")
        if len(parts) < 2:
            continue

        ldraw_id = parts[0].strip()
        ldraw_name = parts[1].strip() if len(parts) > 1 else ""
        valid_lines.append((ldraw_id, ldraw_name))

    logger.info(f"Found {len(valid_lines)} valid parts to process")

    with tqdm(valid_lines, desc="Generating kinds", unit="part") as pbar:
        for ldraw_id, ldraw_name in pbar:
            pbar.set_description(f"Processing {ldraw_id}")

            # Check if this piece already failed in the past
            if getFailedKind(piece_config, ldraw_id):
                tqdm.write(f"LDraw ID {ldraw_id} previously failed, skipping")
                skipped_count += 1
                pbar.set_postfix(
                    saved=saved_count, skipped=skipped_count, failed=failed_count
                )
                continue

            try:
                bl_primary_id = scrapePrimaryId(ldraw_id, auth)
                if not bl_primary_id:
                    tqdm.write(
                        f"Could not find BrickLink primary ID for {ldraw_id}, skipping"
                    )
                    saveFailedKind(
                        piece_config,
                        logger,
                        ldraw_id,
                        GENERATE_PIECE_KIND_FAILED_REASON.COULD_NOT_FIND_PRIMARY_ID,
                    )
                    failed_count += 1
                    pbar.set_postfix(
                        saved=saved_count, skipped=skipped_count, failed=failed_count
                    )
                    continue

                if getExistingKind(piece_config, bl_primary_id):
                    tqdm.write(f"Kind {bl_primary_id} already exists, skipping")
                    skipped_count += 1
                    pbar.set_postfix(
                        saved=saved_count, skipped=skipped_count, failed=failed_count
                    )
                    continue

                part_info = getPartInfo(bl_primary_id, auth)
                if not part_info:
                    tqdm.write(f"Could not get part info for {bl_primary_id}, skipping")
                    saveFailedKind(
                        piece_config,
                        logger,
                        ldraw_id,
                        GENERATE_PIECE_KIND_FAILED_REASON.COULD_NOT_GET_PART_INFO,
                    )
                    failed_count += 1
                    pbar.set_postfix(
                        saved=saved_count, skipped=skipped_count, failed=failed_count
                    )
                    continue

                saveKind(piece_config, logger, part_info)

                alternate_ids = []
                if part_info.get("alternate_no"):
                    alternate_ids = [
                        aid.strip() for aid in part_info["alternate_no"].split(",")
                    ]

                alternate_ids.append(ldraw_id)
                alternate_ids.append(bl_primary_id)
                alternate_ids = list(set(alternate_ids))

                saveKindAlternateIds(piece_config, logger, bl_primary_id, alternate_ids)

                saved_count += 1
                pbar.set_postfix(
                    saved=saved_count, skipped=skipped_count, failed=failed_count
                )

            except Exception as e:
                tqdm.write(f"Failed to process {ldraw_id}: {e}")
                saveFailedKind(
                    piece_config,
                    logger,
                    ldraw_id,
                    GENERATE_PIECE_KIND_FAILED_REASON.API_ERROR,
                )
                failed_count += 1
                pbar.set_postfix(
                    saved=saved_count, skipped=skipped_count, failed=failed_count
                )

    final_count = getKindCount(piece_config)

    logger.info(f"Kinds generation completed:")
    logger.info(f"  Processed: {len(valid_lines)} LDraw parts")
    logger.info(f"  Saved: {saved_count} new kinds")
    logger.info(f"  Skipped: {skipped_count} existing kinds")
    logger.info(f"  Failed: {failed_count} parts")
    logger.info(f"  Total in database: {final_count} kinds")
