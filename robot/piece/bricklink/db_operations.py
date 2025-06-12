import sqlite3
from typing import List, Optional
from robot.global_config import GlobalConfig
from robot.storage.sqlite3.migrations import getDatabaseConnection
from robot.piece.bricklink.types import (
    BricklinkPartData,
    BricklinkCategoryData,
    BricklinkColorData,
)


def saveCategory(global_config: GlobalConfig, category: BricklinkCategoryData) -> None:
    logger = global_config["logger"]
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO bricklink_category (category_id, name) VALUES (?, ?)",
            (str(category["category_id"]), category["category_name"]),
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


def saveColor(global_config: GlobalConfig, color: BricklinkColorData) -> None:
    logger = global_config["logger"]
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO bricklink_color (color_id, name, hex_color_code, type) VALUES (?, ?, ?, ?)",
            (
                str(color["color_id"]),
                color["color_name"],
                color["color_code"],
                color["color_type"],
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


def saveKind(global_config: GlobalConfig, part: BricklinkPartData) -> None:
    logger = global_config["logger"]
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        image_url = (
            f"https:{part['image_url']}"
            if part["image_url"].startswith("//")
            else part["image_url"]
        )

        cursor.execute(
            "INSERT OR REPLACE INTO kind (primary_id, bricklink_category_id, name, bricklink_image_url) VALUES (?, ?, ?, ?)",
            (part["no"], str(part["category_id"]), part["name"], image_url),
        )
        conn.commit()
        logger.info(f"Saved kind: {part['name']} (ID: {part['no']})")

    except Exception as e:
        logger.error(f"Failed to save kind {part['no']}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def saveKindAlternateIds(
    global_config: GlobalConfig, primary_id: str, alternate_ids: List[str]
) -> None:
    logger = global_config["logger"]
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM kind_alternate_ids WHERE kind_primary_id = ?", (primary_id,)
        )

        for alternate_id in alternate_ids:
            if alternate_id.strip():
                cursor.execute(
                    "INSERT INTO kind_alternate_ids (kind_primary_id, alternate_id) VALUES (?, ?)",
                    (primary_id, alternate_id.strip()),
                )

        conn.commit()
        logger.info(f"Saved {len(alternate_ids)} alternate IDs for kind {primary_id}")

    except Exception as e:
        logger.error(f"Failed to save alternate IDs for kind {primary_id}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def getExistingKind(global_config: GlobalConfig, primary_id: str) -> bool:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM kind WHERE primary_id = ?", (primary_id,))
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getExistingCategory(global_config: GlobalConfig, category_id: str) -> bool:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT 1 FROM bricklink_category WHERE category_id = ?", (category_id,)
        )
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getExistingColor(global_config: GlobalConfig, color_id: str) -> bool:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM bricklink_color WHERE color_id = ?", (color_id,))
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()


def getKindCount(global_config: GlobalConfig) -> int:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM kind")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()


def getCategoryCount(global_config: GlobalConfig) -> int:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM bricklink_category")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()


def getColorCount(global_config: GlobalConfig) -> int:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM bricklink_color")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()
