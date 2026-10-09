"""The frontend must not hide a category outside the shared ten-label contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "app" / "frontend"
sys.path.insert(0, str(FRONTEND_DIR))

from constants.labels import LABELS
from services import api


def test_known_label_is_returned_unchanged():
    for label in LABELS:
        assert api._known_label(label) == label


def test_unknown_label_is_reported_as_backend_error():
    with pytest.raises(api.BackendError, match="unsupported category"):
        api._known_label("made_up_label")


def test_related_item_with_unknown_label_is_not_relabelled():
    item = {
        "id": "history-001",
        "similarity": 0.8,
        "board_label": "made_up_label",
        "text_preview": "example",
        "source_type": "humaid_history",
    }
    with pytest.raises(api.BackendError):
        api._related_from_json(item)
