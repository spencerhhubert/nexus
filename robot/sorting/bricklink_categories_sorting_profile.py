import sqlite3
from typing import Dict
from robot.global_config import GlobalConfig
from robot.sorting.piece_sorting_profile import PieceSortingProfile
from robot.storage.sqlite3.migrations import getDatabaseConnection


def mkBricklinkCategoriesSortingProfile(
    global_config: GlobalConfig,
) -> PieceSortingProfile:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    item_id_to_category_id = {}

    # Get all piece kinds with their categories
    cursor.execute(
        """
        SELECT pk.primary_id, pk.bricklink_category_id
        FROM piece_kinds pk
        WHERE pk.failed_reason IS NULL AND pk.bricklink_category_id IS NOT NULL
    """
    )

    piece_kinds = cursor.fetchall()

    for primary_id, category_id in piece_kinds:
        # Map primary ID to category
        item_id_to_category_id[primary_id] = category_id

        # Get all alternate IDs for this piece
        cursor.execute(
            """
            SELECT alternate_id FROM piece_kind_alternate_ids
            WHERE kind_primary_id = ?
        """,
            (primary_id,),
        )

        alternate_ids = cursor.fetchall()
        for (alternate_id,) in alternate_ids:
            if alternate_id and alternate_id.strip():
                item_id_to_category_id[alternate_id.strip()] = category_id

    conn.close()

    global_config["logger"].info(
        f"Built BrickLink sorting profile with {len(item_id_to_category_id)} item mappings"
    )

    return PieceSortingProfile(
        global_config,
        "BrickLink Categories",
        item_id_to_category_id,
        "Sorting profile based on BrickLink categories",
    )
