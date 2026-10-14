-- CrisisLens SQLite schema (Member 4).
-- Source of truth for the reports table. Recreate the DB with:
--     sqlite3 app/backend/crisislens.db < app/schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS reports (
    message_id       TEXT PRIMARY KEY,
    text             TEXT NOT NULL,
    predicted_label  TEXT NOT NULL,
    board_label      TEXT NOT NULL,
    source_type      TEXT NOT NULL CHECK (source_type IN ('user', 'humaid_history')),
    confidence       REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    model_version    TEXT NOT NULL,
    needs_review     INTEGER NOT NULL CHECK (needs_review IN (0, 1)),
    created_at       TEXT NOT NULL,
    user_correction  TEXT,
    status           TEXT NOT NULL CHECK (status IN ('unverified', 'needs_review', 'resolved', 'hidden')),
    country          TEXT,
    region           TEXT,
    city             TEXT,
    latitude         REAL,
    longitude        REAL
);

CREATE INDEX IF NOT EXISTS idx_reports_board_label   ON reports(board_label);
CREATE INDEX IF NOT EXISTS idx_reports_source_type   ON reports(source_type);
CREATE INDEX IF NOT EXISTS idx_reports_status        ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_needs_review  ON reports(needs_review);
CREATE INDEX IF NOT EXISTS idx_reports_created_at    ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_country       ON reports(country);
