-- Create bin_states table to store versioned bin state snapshots
CREATE TABLE IF NOT EXISTS bin_states (
    id TEXT PRIMARY KEY,
    bin_contents TEXT NOT NULL, -- JSON representation of bin contents
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    deleted_at INTEGER
);
