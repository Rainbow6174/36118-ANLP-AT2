"""Integration tests for the CrisisLens backend (Member 4, step 2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.backend import db
from app.backend.labels import LABELS

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "app" / "schema.sql"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["runtime"]["active_runtime"] == "mock"


def test_analyse_shape(client):
    r = client.post("/api/analyse", json={"text": "water is urgently needed"})
    assert r.status_code == 200
    body = r.json()
    assert "prediction" in body
    assert "related_reports" in body

    p = body["prediction"]
    assert p["predicted_label"] in LABELS
    assert set(p["probabilities"].keys()) == set(LABELS)
    assert len(p["probabilities"]) == 10
    assert abs(sum(p["probabilities"].values()) - 1.0) < 1e-6
    assert 0.0 <= p["confidence"] <= 1.0
    assert isinstance(p["needs_review"], bool)
    assert "model_version" in p


def test_golden_path_analyse_save_browse_search(client):
    analyse = client.post(
        "/api/analyse",
        json={"text": "families need drinking water near the community hall"},
    ).json()
    pred = analyse["prediction"]

    create_body = {
        "text": "families need drinking water near the community hall",
        "predicted_label": pred["predicted_label"],
        "confidence": pred["confidence"],
        "model_version": pred["model_version"],
        "needs_review": pred["needs_review"],
        "location": {"country": "Australia"},
    }
    r = client.post("/api/reports", json=create_body)
    assert r.status_code == 201
    rec = r.json()
    assert rec["board_label"] == pred["predicted_label"]
    assert rec["predicted_label"] == pred["predicted_label"]
    assert rec["source_type"] == "user"
    assert rec["country"] == "Australia"
    mid = rec["message_id"]

    r = client.get(f"/api/reports?board_label={pred['predicted_label']}")
    assert r.status_code == 200
    lst = r.json()
    assert lst["total"] >= 1
    assert any(item["message_id"] == mid for item in lst["items"])

    r = client.get(f"/api/reports/{mid}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["report"]["message_id"] == mid
    assert isinstance(detail["related_reports"], list)

    r = client.get("/api/search?q=water&k=3")
    assert r.status_code == 200
    search = r.json()
    assert len(search["items"]) == 3


def test_empty_search_rejected(client):
    r = client.get("/api/search", params={"q": "", "k": 3})
    assert r.status_code == 422


def test_filtered_search_returns_matching_items(client):
    r = client.get(
        "/api/search",
        params={
            "q": "caution",
            "source_type": "humaid_history",
            "board_label": "caution_and_advice",
            "k": 3,
        },
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(item["board_label"] == "caution_and_advice" for item in items)


def test_analyse_filters_related_items_to_predicted_board(client):
    response = client.post(
        "/api/analyse", json={"text": "families need drinking water"}
    )
    assert response.status_code == 200
    body = response.json()
    predicted = body["prediction"]["predicted_label"]
    assert all(
        item["board_label"] == predicted for item in body["related_reports"]
    )


def test_post_defaults_board_to_predicted(client):
    body = {
        "text": "x",
        "predicted_label": "not_humanitarian",
        "confidence": 0.9,
        "model_version": "mock-v0",
        "needs_review": False,
    }
    r = client.post("/api/reports", json=body)
    assert r.status_code == 201
    assert r.json()["board_label"] == "not_humanitarian"


def test_post_rejects_historical_source_type(client):
    """HumAID history is read-only and is loaded through the retrieval index."""

    body = {
        "text": "historical text supplied through the public endpoint",
        "predicted_label": "not_humanitarian",
        "source_type": "humaid_history",
        "confidence": 0.9,
        "model_version": "external",
        "needs_review": False,
    }
    response = client.post("/api/reports", json=body)
    assert response.status_code == 422


def test_patch_correction_preserves_predicted_label(client):
    body = {
        "text": "x",
        "predicted_label": "requests_or_urgent_needs",
        "confidence": 0.9,
        "model_version": "mock-v0",
        "needs_review": False,
    }
    rec = client.post("/api/reports", json=body).json()
    mid = rec["message_id"]

    r = client.patch(
        f"/api/reports/{mid}",
        json={
            "user_correction": "infrastructure_and_utility_damage",
            "status": "resolved",
        },
    )
    assert r.status_code == 200
    upd = r.json()
    assert upd["predicted_label"] == "requests_or_urgent_needs"
    assert upd["board_label"] == "infrastructure_and_utility_damage"
    assert upd["user_correction"] == "infrastructure_and_utility_damage"
    assert upd["status"] == "resolved"


def test_patch_rejects_unknown_label(client):
    body = {
        "text": "x",
        "predicted_label": "not_humanitarian",
        "confidence": 0.9,
        "model_version": "mock-v0",
        "needs_review": False,
    }
    mid = client.post("/api/reports", json=body).json()["message_id"]
    r = client.patch(f"/api/reports/{mid}", json={"user_correction": "nonsense"})
    assert r.status_code == 422


def test_patch_not_found(client):
    r = client.patch("/api/reports/does-not-exist", json={"status": "resolved"})
    assert r.status_code == 404


def test_delete_removes_report_from_store_and_live_index(client, monkeypatch):
    from app.backend import services

    class TrackingRetriever:
        def __init__(self):
            self.ids: set[str] = set()
            self.removed: list[str] = []

        def add_to_index(self, report):
            self.ids.add(report.message_id)

        def remove_from_index(self, message_id: str) -> bool:
            self.removed.append(message_id)
            was_present = message_id in self.ids
            self.ids.discard(message_id)
            return was_present

    retriever = TrackingRetriever()
    monkeypatch.setattr(services, "_retriever", retriever)

    body = {
        "text": "repeated community report",
        "predicted_label": "requests_or_urgent_needs",
        "confidence": 0.9,
        "model_version": "mock-v0",
        "needs_review": False,
    }
    message_id = client.post("/api/reports", json=body).json()["message_id"]
    assert message_id in retriever.ids

    response = client.delete(f"/api/reports/{message_id}")

    assert response.status_code == 204
    assert client.get(f"/api/reports/{message_id}").status_code == 404
    assert message_id not in retriever.ids
    assert retriever.removed == [message_id]


def test_historical_row_is_readonly(client):
    conn = db.connect()
    try:
        conn.execute(
            """
            INSERT INTO reports (
                message_id, text, predicted_label, board_label, source_type,
                confidence, model_version, needs_review, created_at,
                user_correction, status
            ) VALUES (
                'hist-1', 'historical text', 'not_humanitarian', 'not_humanitarian',
                'humaid_history', 0.9, 'humaid-seed', 0, '2024-01-01T00:00:00+00:00',
                NULL, 'resolved'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    r = client.patch(
        "/api/reports/hist-1",
        json={"user_correction": "requests_or_urgent_needs"},
    )
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"]


def test_needs_review_transition(client):
    low_conf_body = {
        "text": "x",
        "predicted_label": "not_humanitarian",
        "confidence": 0.30,
        "model_version": "mock-v0",
        "needs_review": True,
    }
    rec = client.post("/api/reports", json=low_conf_body).json()
    assert rec["needs_review"] is True
    assert rec["status"] == "needs_review"

    r = client.get("/api/reports?needs_review=true")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.patch(
        f"/api/reports/{rec['message_id']}", json={"status": "resolved"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_list_filter_and_pagination(client):
    for i in range(5):
        client.post(
            "/api/reports",
            json={
                "text": f"msg {i}",
                "predicted_label": "caution_and_advice",
                "confidence": 0.8,
                "model_version": "mock-v0",
                "needs_review": False,
            },
        )
    for i in range(2):
        client.post(
            "/api/reports",
            json={
                "text": f"other {i}",
                "predicted_label": "sympathy_and_support",
                "confidence": 0.8,
                "model_version": "mock-v0",
                "needs_review": False,
            },
        )

    r = client.get("/api/reports?board_label=caution_and_advice&k=3&page=1")
    assert r.json()["total"] == 5
    assert len(r.json()["items"]) == 3

    r = client.get("/api/reports?board_label=caution_and_advice&k=3&page=2")
    assert r.json()["total"] == 5
    assert len(r.json()["items"]) == 2

    r = client.get("/api/reports?board_label=injured_or_dead_people")
    assert r.json()["total"] == 0


def test_prediction_rejects_out_of_range_probability():
    """H2: Prediction validator rejects probs outside [0, 1]."""
    from pydantic import ValidationError

    from app.backend.labels import LABELS
    from app.backend.schemas import Prediction

    bad = {label: 0.1 for label in LABELS}
    bad[LABELS[0]] = 1.5  # out of range; others still "valid" shape
    import pytest as _pt

    with _pt.raises(ValidationError, match="out of range"):
        Prediction(
            predicted_label=LABELS[0],
            probabilities=bad,
            confidence=0.5,
            model_version="x",
            needs_review=False,
        )


def test_prediction_rejects_probs_not_summing_to_one():
    """H2: Prediction validator rejects probability distributions that
    don't sum to ~1.0 within tolerance."""
    from pydantic import ValidationError

    from app.backend.labels import LABELS
    from app.backend.schemas import Prediction

    bad = {label: 0.5 for label in LABELS}  # sums to 5.0
    import pytest as _pt

    with _pt.raises(ValidationError, match="sum to 1.0"):
        Prediction(
            predicted_label=LABELS[0],
            probabilities=bad,
            confidence=0.5,
            model_version="x",
            needs_review=False,
        )


def test_schema_has_required_fields(tmp_path):
    db_file = tmp_path / "schema_check.db"
    conn = sqlite3.connect(db_file)
    try:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        cols = {row[1] for row in conn.execute("PRAGMA table_info(reports)")}
    finally:
        conn.close()

    required = {
        "message_id", "text", "predicted_label", "board_label", "source_type",
        "confidence", "model_version", "needs_review", "created_at",
        "user_correction", "status",
    }
    assert required.issubset(cols), f"missing: {required - cols}"
