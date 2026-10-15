"""The frontend must not hide a category outside the shared ten-label contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "app" / "frontend"
_frontend_path = str(FRONTEND_DIR)


@pytest.fixture(autouse=True)
def _frontend_on_path(monkeypatch):
    monkeypatch.syspath_prepend(_frontend_path)


def _import_api():
    from services import api
    return api


def _import_labels():
    from constants.labels import LABELS
    return LABELS


def test_known_label_is_returned_unchanged():
    api = _import_api()
    LABELS = _import_labels()
    for label in LABELS:
        assert api._known_label(label) == label


def test_unknown_label_is_reported_as_backend_error():
    api = _import_api()
    with pytest.raises(api.BackendError, match="unsupported category"):
        api._known_label("made_up_label")


def test_related_item_with_unknown_label_is_not_relabelled():
    api = _import_api()
    item = {
        "id": "history-001",
        "similarity": 0.8,
        "board_label": "made_up_label",
        "text_preview": "example",
        "source_type": "humaid_history",
    }
    with pytest.raises(api.BackendError):
        api._related_from_json(item)


def test_empty_success_response_is_not_an_error(monkeypatch):
    """DELETE answers 204 No Content; the client must treat that as success."""
    import asyncio

    import httpx

    api = _import_api()

    def handler(request):
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(api, "API_URL", "http://backend.test")
    monkeypatch.setattr(api.httpx, "AsyncClient", fake_client)
    assert asyncio.run(api._call("DELETE", "/api/reports/x")) is None
