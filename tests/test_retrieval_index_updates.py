"""Tests for live user-report updates in the retrieval index."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

from models.retrieval import retrieval


def test_remove_from_index_keeps_index_rows_aligned(monkeypatch):
    records = pd.DataFrame(
        [
            {
                "id": "history-1",
                "text_display": "historical report",
                "clean_text": "historical report",
                "board_label": "not_humanitarian",
                "source_type": "humaid_history",
                "status": None,
                "needs_review": None,
                "country": None,
                "region": None,
                "city": None,
                "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
            },
            {
                "id": "user-1",
                "text_display": "water needed",
                "clean_text": "water needed",
                "board_label": "requests_or_urgent_needs",
                "source_type": "user",
                "status": "unverified",
                "needs_review": False,
                "country": "Australia",
                "region": None,
                "city": None,
                "created_at": pd.Timestamp("2026-10-14", tz="UTC"),
            },
        ],
        columns=retrieval.RECORD_COLUMNS,
    )
    state = {
        "records": records,
        "vectorizer": object(),
        "matrix": sparse.csr_matrix([[1.0, 0.0], [0.0, 1.0]]),
        "model": object(),
        "embeddings": np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        "search_vectorizer": object(),
        "search_matrix": sparse.csr_matrix([[1.0], [1.0]]),
    }
    monkeypatch.setattr(retrieval, "_state", state)

    assert retrieval.remove_from_index("user-1") is True
    assert state["records"]["id"].tolist() == ["history-1"]
    assert state["matrix"].shape == (1, 2)
    assert state["embeddings"].shape == (1, 2)
    assert state["search_vectorizer"] is None
    assert state["search_matrix"] is None
    assert retrieval.remove_from_index("user-1") is False
