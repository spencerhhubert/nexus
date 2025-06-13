import sqlite3
import time
from typing import List, Optional
from robot.piece.bricklink.generate_piece_config import PieceGenerationConfig
from robot.piece.bricklink.types import (
    BricklinkPartData,
    BricklinkCategoryData,
    BricklinkColorData,
    GENERATE_PIECE_KIND_FAILED_REASON,
)


def _getCurrentTimestampMs() -> int:
    return int(time.time() * 1000)


def _getDatabaseConnection(piece_config: PieceGenerationConfig) -> sqlite3.Connection:
    return sqlite3.connect(piece_config["database_path"])


def saveCategory(
    piece_config: PieceGenerationConfig, logger, category: BricklinkCategoryData
) -> None:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        current_time = _getCurrentTimestampMs()
        cursor.execute(
            "INSERT OR IGNORE INTO bricklink_category (category_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (
                str(category["category_id"]),
                category["category_name"],
                current_time,
                current_time,
            ),
        )
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(
                f"Saved category: {category['category_name']} (ID: {category['category_id']})"
            )

    except Exception as e:
        logger.error(f"Failed to save category {category['category_id']}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def saveColor(
    piece_config: PieceGenerationConfig, logger, color: BricklinkColorData
) -> None:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        current_time = _getCurrentTimestampMs()
        cursor.execute(
            "INSERT OR IGNORE INTO bricklink_color (color_id, name, hex_color_code, type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(color["color_id"]),
                color["color_name"],
                color["color_code"],
                color["color_type"],
                current_time,
                current_time,
            ),
        )
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Saved color: {color['color_name']} (ID: {color['color_id']})")

    except Exception as e:
        logger.error(f"Failed to save color {color['color_id']}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def saveKind(
    piece_config: PieceGenerationConfig, logger, part: BricklinkPartData
) -> None:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        image_url = (
            f"https:{part['image_url']}"
            if part["image_url"].startswith("//")
            else part["image_url"]
        )

        current_time = _getCurrentTimestampMs()
        cursor.execute(
            "INSERT OR REPLACE INTO piece_kinds (primary_id, bricklink_category_id, name, bricklink_image_url, created_at, updated_at, failed_reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                part["no"],
                str(part["category_id"]),
                part["name"],
                image_url,
                current_time,
                current_time,
                None,
            ),
        )
        conn.commit()

    except Exception as e:
        logger.error(f"Failed to save kind {part['no']}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def saveKindAlternateIds(
    piece_config: PieceGenerationConfig,
    logger,
    primary_id: str,
    alternate_ids: List[str],
) -> None:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM piece_kind_alternate_ids WHERE kind_primary_id = ?",
            (primary_id,),
        )

        current_time = _getCurrentTimestampMs()
        for alternate_id in alternate_ids:
            if alternate_id.strip():
                cursor.execute(
                    "INSERT INTO piece_kind_alternate_ids (kind_primary_id, alternate_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (primary_id, alternate_id.strip(), current_time, current_time),
                )

        conn.commit()

    except Exception as e:
        logger.error(f"Failed to save alternate IDs for kind {primary_id}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def getExistingKind(piece_config: PieceGenerationConfig, primary_id: str) -> bool:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT 1 FROM piece_kinds WHERE primary_id = ? AND failed_reason IS NULL",
            (primary_id,),
        )
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def saveFailedKind(
    piece_config: PieceGenerationConfig,
    logger,
    ldraw_id: str,
    failed_reason: GENERATE_PIECE_KIND_FAILED_REASON,
) -> None:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        current_time = _getCurrentTimestampMs()
        cursor.execute(
            "INSERT OR REPLACE INTO piece_kinds (primary_id, failed_reason, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (ldraw_id, failed_reason.value, current_time, current_time),
        )
        conn.commit()

    except Exception as e:
        logger.error(f"Failed to save failed kind {ldraw_id}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def getFailedKind(piece_config: PieceGenerationConfig, ldraw_id: str) -> bool:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT 1 FROM piece_kinds WHERE primary_id = ? AND failed_reason IS NOT NULL",
            (ldraw_id,),
        )
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getExistingCategory(piece_config: PieceGenerationConfig, category_id: str) -> bool:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT 1 FROM bricklink_category WHERE category_id = ?", (category_id,)
        )
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getExistingColor(piece_config: PieceGenerationConfig, color_id: str) -> bool:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM bricklink_color WHERE color_id = ?", (color_id,))
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getKindCount(piece_config: PieceGenerationConfig) -> int:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM piece_kinds")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()


def getCategoryCount(piece_config: PieceGenerationConfig) -> int:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM bricklink_category")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()


def getColorCount(piece_config: PieceGenerationConfig) -> int:
    conn = _getDatabaseConnection(piece_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM bricklink_color")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()
