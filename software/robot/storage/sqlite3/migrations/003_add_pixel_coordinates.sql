-- Add new pixel coordinate columns and rename existing columns to _percent
-- SQLite doesn't support renaming columns directly, so we need to recreate the table

-- Create new table with updated schema
CREATE TABLE observations_new (
    observation_id TEXT PRIMARY KEY,
    trajectory_id TEXT,
    timestamp_ms INTEGER,
    center_x_percent REAL,
    center_y_percent REAL,
    bbox_width_percent REAL,
    bbox_height_percent REAL,
    center_x_px INTEGER,
    center_y_px INTEGER,
    bbox_width_px INTEGER,
    bbox_height_px INTEGER,
    full_image_path TEXT,
    masked_image_path TEXT,
    classification_file_path TEXT,
    classification_result TEXT,
    created_at INTEGER
);

-- Copy existing data to new table (pixel coordinates will be NULL for existing records)
INSERT INTO observations_new (
    observation_id, trajectory_id, timestamp_ms,
    center_x_percent, center_y_percent, bbox_width_percent, bbox_height_percent,
    full_image_path, masked_image_path, classification_file_path,
    classification_result, created_at
)
SELECT
    observation_id, trajectory_id, timestamp_ms,
    center_x, center_y, bbox_width, bbox_height,
    full_image_path, masked_image_path, classification_file_path,
    classification_result, created_at
FROM observations;

-- Drop old table
DROP TABLE observations;

-- Rename new table to original name
ALTER TABLE observations_new RENAME TO observations;
