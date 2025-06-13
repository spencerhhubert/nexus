-- Add failed_reason column to piece_kinds table
ALTER TABLE piece_kinds ADD COLUMN failed_reason TEXT;
