import sqlite3
import json
import time
from typing import Optional, Any
from robot.global_config import GlobalConfig
from robot.storage.sqlite3.migrations import getDatabaseConnection



def saveObservationToDatabase(
    global_config: GlobalConfig,
    observation_id: str,
    trajectory_id: str,
    timestamp_ms: int,
    center_x: float,
    center_y: float,
    bbox_width: float,
    bbox_height: float,
    full_image_path: str,
    masked_image_path: str,
    classification_file_path: str,
    classification_result: Any,
) -> None:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    created_at = int(time.time() * 1000)
    classification_json = json.dumps(classification_result)

    cursor.execute(
        """
        INSERT INTO observations (
            observation_id, trajectory_id, timestamp_ms, center_x, center_y, 
            bbox_width, bbox_height, full_image_path, masked_image_path,
            classification_file_path, classification_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            observation_id,
            trajectory_id,
            timestamp_ms,
            center_x,
            center_y,
            bbox_width,
            bbox_height,
            full_image_path,
            masked_image_path,
            classification_file_path,
            classification_json,
            created_at,
        ),
    )

    conn.commit()
    conn.close()


def loadObservationFromDatabase(
    global_config: GlobalConfig, observation_id: str
) -> Optional[dict]:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT observation_id, trajectory_id, timestamp_ms, center_x, center_y, 
               bbox_width, bbox_height, full_image_path, masked_image_path,
               classification_file_path, classification_result, created_at
        FROM observations 
        WHERE observation_id = ?
    """,
        (observation_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "observation_id": row[0],
        "trajectory_id": row[1],
        "timestamp_ms": row[2],
        "center_x": row[3],
        "center_y": row[4],
        "bbox_width": row[5],
        "bbox_height": row[6],
        "full_image_path": row[7],
        "masked_image_path": row[8],
        "classification_file_path": row[9],
        "classification_result": json.loads(row[10]),
        "created_at": row[11],
    }


def getObservationsForTrajectory(
    global_config: GlobalConfig, trajectory_id: str
) -> list[dict]:
    conn = getDatabaseConnection(global_config)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT observation_id, trajectory_id, timestamp_ms, center_x, center_y, 
               bbox_width, bbox_height, full_image_path, masked_image_path,
               classification_file_path, classification_result, created_at
        FROM observations 
        WHERE trajectory_id = ?
        ORDER BY timestamp_ms ASC
    """,
        (trajectory_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    observations = []
    for row in rows:
        observations.append(
            {
                "observation_id": row[0],
                "trajectory_id": row[1],
                "timestamp_ms": row[2],
                "center_x": row[3],
                "center_y": row[4],
                "bbox_width": row[5],
                "bbox_height": row[6],
                "full_image_path": row[7],
                "masked_image_path": row[8],
                "classification_file_path": row[9],
                "classification_result": json.loads(row[10]),
                "created_at": row[11],
            }
        )

    return observations
