import sqlite3
from typing import Optional
from robot.global_config import GlobalConfig


def initializeDatabase(global_config: GlobalConfig) -> None:
    db_path = global_config['db_path']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            observation_id TEXT PRIMARY KEY,
            trajectory_id TEXT,
            timestamp_ms INTEGER,
            center_x REAL,
            center_y REAL,
            bbox_width REAL,
            bbox_height REAL,
            full_image_path TEXT,
            masked_image_path TEXT,
            classification_result TEXT,
            created_at INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()


def getDatabaseConnection(global_config: GlobalConfig) -> sqlite3.Connection:
    db_path = global_config['db_path']
    return sqlite3.connect(db_path)