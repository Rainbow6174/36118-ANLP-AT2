"""Pytest fixtures for the CrisisLens backend integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient wired to an isolated temp SQLite DB.

    Each test gets a fresh DB file via tmp_path; the lifespan handler on
    `with TestClient(app)` runs db.bootstrap() against it.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("CRISISLENS_DB_PATH", str(db_path))

    from app.backend.main import app

    with TestClient(app) as c:
        yield c
