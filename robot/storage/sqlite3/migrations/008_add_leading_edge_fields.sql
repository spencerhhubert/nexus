-- Add leading edge fields to observations table
ALTER TABLE observations ADD COLUMN leading_edge_x_percent REAL;
ALTER TABLE observations ADD COLUMN leading_edge_x_px INTEGER;
