import sqlite3
import json
import time
import uuid
from typing import Optional, Any, Dict, List
from robot.global_config import GlobalConfig
from robot.storage.sqlite3.migrations import getDatabaseConnection


def saveObservationToDatabase(global_config: GlobalConfig, observation) -> None:
    from robot.trajectories.observation import Observation

    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    created_at = int(time.time() * 1000)
    obs_json = observation.toJSON()
    classification_json = json.dumps(obs_json["classification_result"])

    cursor.execute(
        """
        INSERT INTO observations (
            observation_id, trajectory_id, timestamp_ms, captured_at_ms, center_x_percent, center_y_percent,
            bbox_width_percent, bbox_height_percent, leading_edge_x_percent, center_x_px, center_y_px,
            bbox_width_px, bbox_height_px, leading_edge_x_px, full_image_path, masked_image_path,
            classification_file_path, classification_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            obs_json["observation_id"],
            obs_json["trajectory_id"],
            obs_json["timestamp_ms"],
            obs_json["captured_at_ms"],
            obs_json["center_x_percent"],
            obs_json["center_y_percent"],
            obs_json["bbox_width_percent"],
            obs_json["bbox_height_percent"],
            obs_json["leading_edge_x_percent"],
            obs_json["center_x_px"],
            obs_json["center_y_px"],
            obs_json["bbox_width_px"],
            obs_json["bbox_height_px"],
            obs_json["leading_edge_x_px"],
            obs_json["full_image_path"],
            obs_json["masked_image_path"],
            obs_json["classification_file_path"],
            classification_json,
            created_at,
        ),
    )

    conn.commit()
    conn.close()


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
