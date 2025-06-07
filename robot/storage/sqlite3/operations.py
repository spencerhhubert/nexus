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
            observation_id, trajectory_id, timestamp_ms, center_x_percent, center_y_percent,
            bbox_width_percent, bbox_height_percent, center_x_px, center_y_px,
            bbox_width_px, bbox_height_px, full_image_path, masked_image_path,
            classification_file_path, classification_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            obs_json["observation_id"],
            obs_json["trajectory_id"],
            obs_json["timestamp_ms"],
            obs_json["center_x_percent"],
            obs_json["center_y_percent"],
            obs_json["bbox_width_percent"],
            obs_json["bbox_height_percent"],
            obs_json["center_x_px"],
            obs_json["center_y_px"],
            obs_json["bbox_width_px"],
            obs_json["bbox_height_px"],
            obs_json["full_image_path"],
            obs_json["masked_image_path"],
            obs_json["classification_file_path"],
            classification_json,
            created_at,
        ),
    )

    conn.commit()
    conn.close()
