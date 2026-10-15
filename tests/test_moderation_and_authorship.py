"""Authorship, hide/restore and search filters behave the same in both runtimes.

The API tests use the backend's mock runtime. The last tests exercise the
frontend's demo backend, so demo mode and the real API follow the same rules.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "app" / "frontend"


def _report(**overrides) -> dict:
    body = {
        "text": "families need drinking water at the school",
        "predicted_label": "requests_or_urgent_needs",
        "confidence": 0.9,
        "model_version": "mock-v0",
        "needs_review": False,
    }
    body.update(overrides)
    return body


def test_author_is_saved_and_my_reports_filter_is_server_side(client):
    mine = client.post("/api/reports", json=_report(created_by="user")).json()
    client.post("/api/reports", json=_report(created_by="admin"))
    client.post("/api/reports", json=_report())

    assert mine["created_by"] == "user"
    detail = client.get(f"/api/reports/{mine['message_id']}").json()
    assert detail["report"]["created_by"] == "user"

    listing = client.get("/api/reports", params={"created_by": "user"}).json()
    assert listing["total"] == 1
    assert listing["items"][0]["message_id"] == mine["message_id"]


def test_restore_returns_a_hidden_report_to_its_previous_status(client):
    waiting = client.post("/api/reports", json=_report(needs_review=True)).json()
    reviewed = client.post("/api/reports", json=_report()).json()
    client.patch(f"/api/reports/{reviewed['message_id']}", json={"status": "resolved"})

    for report in (waiting, reviewed):
        r = client.patch(f"/api/reports/{report['message_id']}", json={"hidden": True})
        assert r.json()["status"] == "hidden"

    queue = client.get("/api/reports", params={"status": "needs_review"}).json()
    assert queue["total"] == 0

    restored_waiting = client.patch(
        f"/api/reports/{waiting['message_id']}", json={"hidden": False}
    ).json()
    restored_reviewed = client.patch(
        f"/api/reports/{reviewed['message_id']}", json={"hidden": False}
    ).json()
    assert restored_waiting["status"] == "needs_review"
    assert restored_reviewed["status"] == "resolved"

    queue = client.get("/api/reports", params={"status": "needs_review"}).json()
    assert [item["message_id"] for item in queue["items"]] == [waiting["message_id"]]


def test_hiding_twice_keeps_the_original_status(client):
    report = client.post("/api/reports", json=_report(needs_review=True)).json()
    url = f"/api/reports/{report['message_id']}"
    client.patch(url, json={"hidden": True})
    client.patch(url, json={"status": "hidden"})
    assert client.patch(url, json={"hidden": False}).json()["status"] == "needs_review"


def test_search_accepts_date_filters_and_rejects_bad_dates(client):
    ok = client.get(
        "/api/search",
        params={"q": "water", "created_after": "2019-01-01T00:00:00Z",
                "created_before": "2030-01-01"},
    )
    assert ok.status_code == 200
    bad = client.get("/api/search", params={"q": "water", "created_after": "not-a-date"})
    assert bad.status_code == 422


def test_existing_database_gains_the_new_columns(tmp_path, monkeypatch):
    """A crisislens.db created before created_by existed keeps working."""
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.executescript(
        """
        CREATE TABLE reports (
            message_id TEXT PRIMARY KEY, text TEXT NOT NULL,
            predicted_label TEXT NOT NULL, board_label TEXT NOT NULL,
            source_type TEXT NOT NULL, confidence REAL NOT NULL,
            model_version TEXT NOT NULL, needs_review INTEGER NOT NULL,
            created_at TEXT NOT NULL, user_correction TEXT,
            status TEXT NOT NULL, country TEXT, region TEXT, city TEXT,
            latitude REAL, longitude REAL
        );
        INSERT INTO reports VALUES ('old-1', 'old report', 'not_humanitarian',
            'not_humanitarian', 'user', 0.8, 'v0', 0, '2026-10-01T00:00:00+00:00',
            NULL, 'unverified', NULL, NULL, NULL, NULL, NULL);
        """
    )
    conn.close()
    monkeypatch.setenv("CRISISLENS_DB_PATH", str(old))
    from app.backend import db, store

    db.bootstrap()
    columns = {row[1] for row in sqlite3.connect(old).execute("PRAGMA table_info(reports)")}
    assert {"created_by", "status_before_hidden"} <= columns
    assert store.get("old-1").created_by is None


# ---- frontend demo backend: same rules as the API -------------------------


@pytest.fixture
def demo_backend(monkeypatch):
    monkeypatch.syspath_prepend(str(FRONTEND_DIR))
    from services.mock_backend import MockBackend

    return MockBackend()


def _first_user_report(backend, status):
    return next(r for r in backend._reports if r.source_type == "user" and r.status == status)


def test_demo_restore_returns_previous_status(demo_backend):
    report = _first_user_report(demo_backend, "needs_review")
    demo_backend.update_report(report.message_id, hidden=True)
    assert demo_backend.get_report(report.message_id).status == "hidden"
    demo_backend.update_report(report.message_id, hidden=False)
    assert demo_backend.get_report(report.message_id).status == "needs_review"


def test_demo_hidden_reports_leave_search_and_related_results(demo_backend):
    report = _first_user_report(demo_backend, "unverified")
    words = report.text.split()[0]
    demo_backend.update_report(report.message_id, hidden=True)
    found = demo_backend.search(report.text, k=50)
    assert report.message_id not in {item.id for item in found}
    related = demo_backend.retrieve(report.text, k=50)
    assert report.message_id not in {item.id for item in related}
    assert words  # the query was not empty


def test_demo_related_reports_come_from_the_current_event(demo_backend):
    """Like the real backend: community reports in any category, no past disasters."""
    related = demo_backend.retrieve("families need water and shelter", k=50)
    assert related
    assert all(item.source_type == "user" for item in related)


def test_demo_my_reports_filter(demo_backend):
    from services.mock_backend import classify

    text = "Water is needed at the shelter tonight."
    saved = demo_backend.create_report(
        text, classify(text), "requests_or_urgent_needs", None, created_by="user"
    )
    listing = demo_backend.list_reports(created_by="user", page_size=50)
    assert [r.message_id for r in listing.items] == [saved.message_id]
