-- Rename timestamp_ms to observation_created_at to avoid conflict with existing created_at column
-- SQLite doesn't support renaming columns directly, so we need to recreate the table

-- Create new table with updated schema
CREATE TABLE observations_new (
    observation_id TEXT PRIMARY KEY,
    trajectory_id TEXT,
    observation_created_at INTEGER,
    captured_at_ms INTEGER,
    center_x_percent REAL,
    center_y_percent REAL,
    bbox_width_percent REAL,
    bbox_height_percent REAL,
    leading_edge_x_percent REAL,
    center_x_px INTEGER,
    center_y_px INTEGER,
    bbox_width_px INTEGER,
    bbox_height_px INTEGER,
    leading_edge_x_px INTEGER,
    full_image_path TEXT,
    masked_image_path TEXT,
    classification_file_path TEXT,
    classification_result TEXT,
    created_at INTEGER
);

-- Copy existing data to new table, renaming timestamp_ms to observation_created_at
INSERT INTO observations_new (
    observation_id, trajectory_id, observation_created_at, captured_at_ms,
    center_x_percent, center_y_percent, bbox_width_percent, bbox_height_percent,
    leading_edge_x_percent, center_x_px, center_y_px, bbox_width_px, bbox_height_px,
    leading_edge_x_px, full_image_path, masked_image_path, classification_file_path,
    classification_result, created_at
)
SELECT
    observation_id, trajectory_id, timestamp_ms, captured_at_ms,
    center_x_percent, center_y_percent, bbox_width_percent, bbox_height_percent,
    leading_edge_x_percent, center_x_px, center_y_px, bbox_width_px, bbox_height_px,
    leading_edge_x_px, full_image_path, masked_image_path, classification_file_path,
    classification_result, created_at
FROM observations;

-- Drop old table
DROP TABLE observations;

-- Rename new table to original name
ALTER TABLE observations_new RENAME TO observations;
