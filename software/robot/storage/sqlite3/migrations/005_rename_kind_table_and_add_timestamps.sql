-- Rename kind table to piece_kinds and add timestamps to all piece tables

-- Create new bricklink_category table with timestamps
CREATE TABLE bricklink_category_new (
    category_id TEXT PRIMARY KEY,
    name TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    deleted_at INTEGER
);

-- Copy existing data to new bricklink_category table
INSERT INTO bricklink_category_new (category_id, name, created_at, updated_at)
SELECT category_id, name,
       strftime('%s', 'now') * 1000,
       strftime('%s', 'now') * 1000
FROM bricklink_category;

-- Drop old table and rename new one
DROP TABLE bricklink_category;
ALTER TABLE bricklink_category_new RENAME TO bricklink_category;

-- Create new bricklink_color table with timestamps
CREATE TABLE bricklink_color_new (
    color_id TEXT PRIMARY KEY,
    name TEXT,
    hex_color_code TEXT,
    type TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    deleted_at INTEGER
);

-- Copy existing data to new bricklink_color table
INSERT INTO bricklink_color_new (color_id, name, hex_color_code, type, created_at, updated_at)
SELECT color_id, name, hex_color_code, type,
       strftime('%s', 'now') * 1000,
       strftime('%s', 'now') * 1000
FROM bricklink_color;

-- Drop old table and rename new one
DROP TABLE bricklink_color;
ALTER TABLE bricklink_color_new RENAME TO bricklink_color;

-- Create new piece_kinds table (renamed from kind) with timestamps
CREATE TABLE piece_kinds (
    primary_id TEXT PRIMARY KEY,
    bricklink_category_id TEXT,
    name TEXT,
    bricklink_image_url TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    deleted_at INTEGER,
    FOREIGN KEY (bricklink_category_id) REFERENCES bricklink_category(category_id)
);

-- Copy existing data from kind table to piece_kinds
INSERT INTO piece_kinds (primary_id, bricklink_category_id, name, bricklink_image_url, created_at, updated_at)
SELECT primary_id, bricklink_category_id, name, bricklink_image_url,
       strftime('%s', 'now') * 1000,
       strftime('%s', 'now') * 1000
FROM kind;

-- Create new piece_kind_alternate_ids table (renamed and updated foreign key) with timestamps
CREATE TABLE piece_kind_alternate_ids (
    kind_primary_id TEXT,
    alternate_id TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    deleted_at INTEGER,
    FOREIGN KEY (kind_primary_id) REFERENCES piece_kinds(primary_id),
    PRIMARY KEY (kind_primary_id, alternate_id)
);

-- Copy existing data from kind_alternate_ids table
INSERT INTO piece_kind_alternate_ids (kind_primary_id, alternate_id, created_at, updated_at)
SELECT kind_primary_id, alternate_id,
       strftime('%s', 'now') * 1000,
       strftime('%s', 'now') * 1000
FROM kind_alternate_ids;

-- Drop old tables
DROP TABLE kind_alternate_ids;
DROP TABLE kind;
