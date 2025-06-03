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
);