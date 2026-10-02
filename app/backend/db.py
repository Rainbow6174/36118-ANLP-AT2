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


def bootstrap() -> None:
    """Create the DB file and schema if missing. Idempotent."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
