-- Create bricklink_category table first since kind references it
CREATE TABLE IF NOT EXISTS bricklink_category (
    category_id TEXT PRIMARY KEY,
    name TEXT
);

-- Create bricklink_color table
CREATE TABLE IF NOT EXISTS bricklink_color (
    color_id TEXT PRIMARY KEY,
    name TEXT,
    hex_color_code TEXT,
    type TEXT
);

-- Create kind table
CREATE TABLE IF NOT EXISTS kind (
    primary_id TEXT PRIMARY KEY,
    bricklink_category_id TEXT,
    name TEXT,
    bricklink_image_url TEXT,
    FOREIGN KEY (bricklink_category_id) REFERENCES bricklink_category(category_id)
);

-- Create kind_alternate_ids table
CREATE TABLE IF NOT EXISTS kind_alternate_ids (
    kind_primary_id TEXT,
    alternate_id TEXT,
    FOREIGN KEY (kind_primary_id) REFERENCES kind(primary_id),
    PRIMARY KEY (kind_primary_id, alternate_id)
);
