import sqlite3
import json
import time
import uuid
from typing import Optional, Any, Dict
from robot.global_config import GlobalConfig
from robot.storage.sqlite3.migrations import getDatabaseConnection


def saveBinStateToDatabase(
    global_config: GlobalConfig, bin_contents: Dict[str, Optional[str]]
) -> str:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    bin_state_id = str(uuid.uuid4())
    current_time = int(time.time() * 1000)
    bin_contents_json = json.dumps(bin_contents)

    cursor.execute(
        """
        INSERT INTO bin_states (id, bin_contents, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (bin_state_id, bin_contents_json, current_time, current_time),
    )

    conn.commit()
    conn.close()
    return bin_state_id


def getBinStateFromDatabase(
    global_config: GlobalConfig, bin_state_id: str
) -> Optional[Dict[str, Any]]:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, bin_contents, created_at, updated_at, deleted_at
        FROM bin_states
        WHERE id = ? AND deleted_at IS NULL
        """,
        (bin_state_id,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "bin_contents": json.loads(result[1]),
            "created_at": result[2],
            "updated_at": result[3],
            "deleted_at": result[4],
        }
    return None


def getMostRecentBinState(global_config: GlobalConfig) -> Optional[Dict[str, Any]]:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, bin_contents, created_at, updated_at, deleted_at
        FROM bin_states
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "bin_contents": json.loads(result[1]),
            "created_at": result[2],
            "updated_at": result[3],
            "deleted_at": result[4],
        }
    return None
