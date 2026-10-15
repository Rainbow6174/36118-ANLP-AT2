"""SQLite connection factory and schema bootstrap.

DB path comes from the CRISISLENS_DB_PATH env var; defaults to
app/backend/crisislens.db. The schema is applied on first access
(idempotent CREATE IF NOT EXISTS).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_HERE = Path(__file__).resolve().parent  # app/backend/
_REPO_ROOT = _HERE.parent.parent

DEFAULT_DB_PATH = _HERE / "crisislens.db"
SCHEMA_PATH = _REPO_ROOT / "app" / "schema.sql"


def get_db_path() -> Path:
    raw = os.environ.get("CRISISLENS_DB_PATH")
    return Path(raw) if raw else DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columns added after the first release. bootstrap() adds any that an existing
# database file is missing, so a saved crisislens.db keeps working.
_ADDED_COLUMNS = {
    "created_by": "TEXT",
    "status_before_hidden": "TEXT",
}


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    present = {row[1] for row in conn.execute("PRAGMA table_info(reports)")}
    for name, sql_type in _ADDED_COLUMNS.items():
        if name not in present:
            conn.execute(f"ALTER TABLE reports ADD COLUMN {name} {sql_type}")


def bootstrap() -> None:
    """Create the DB file and schema if missing. Idempotent."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reports'"
        ).fetchone()
        if table_exists:
            _add_missing_columns(conn)
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
