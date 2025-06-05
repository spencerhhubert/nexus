import sqlite3
import json
import time
from typing import Optional, Any
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
            observation_id, trajectory_id, timestamp_ms, center_x, center_y,
            bbox_width, bbox_height, full_image_path, masked_image_path,
            classification_file_path, classification_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            obs_json["observation_id"],
            obs_json["trajectory_id"],
            obs_json["timestamp_ms"],
            obs_json["center_x"],
            obs_json["center_y"],
            obs_json["bbox_width"],
            obs_json["bbox_height"],
            obs_json["full_image_path"],
            obs_json["masked_image_path"],
            obs_json["classification_file_path"],
            classification_json,
            created_at,
        ),
    )

    conn.commit()
    conn.close()
