"""Similar reports and search work within the current event.

The first tests check the backend rule with stand-in retrievers. The last two use
the real MiniLM retrieval module and are skipped when its index or model files
are not available locally.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.backend import services
from app.backend.schemas import RelatedReport

INDEX_DIR = Path(__file__).resolve().parents[1] / "models" / "retrieval" / "index"


def _item(item_id: str, similarity: float | None) -> RelatedReport:
    return RelatedReport(
        id=item_id,
        similarity=similarity,
        board_label="infrastructure_and_utility_damage",
        text_preview="bridge collapsed",
        source_type="user",
    )


class RecordingRetriever:
    """Returns fixed results and records how it was asked."""

    def __init__(self, items):
        self.items = items
        self.calls = []

    def retrieve(self, text, k=5, filters=None, exclude_ids=None):
        self.calls.append({"k": k, "filters": filters, "exclude_ids": exclude_ids})
        return list(self.items)


def test_related_reports_use_the_current_event_in_any_category():
    retriever = RecordingRetriever([])
    services.find_related(retriever, "bridge collapsed", k=5)
    # Only community reports, and no category filter.
    assert retriever.calls[0]["filters"] == {"source_type": "user"}


def test_weak_matches_are_not_shown_as_similar():
    threshold = services.RELATED_MIN_SIMILARITY
    retriever = RecordingRetriever(
        [
            _item("same-bridge", 0.80),
            _item("at-threshold", threshold),
            _item("other-topic", threshold - 0.01),
        ]
    )
    found = services.find_related(retriever, "bridge collapsed")
    assert [item.id for item in found] == ["same-bridge", "at-threshold"]


def test_report_detail_excludes_the_report_itself(client, monkeypatch):
    saved = client.post(
        "/api/reports",
        json={
            "text": "The bridge on Ballina Road has collapsed",
            "predicted_label": "infrastructure_and_utility_damage",
            "confidence": 0.9,
            "model_version": "mock-v0",
            "needs_review": False,
        },
    ).json()
    retriever = RecordingRetriever([])
    monkeypatch.setattr(services, "_retriever", retriever)

    response = client.get(f"/api/reports/{saved['message_id']}")

    assert response.status_code == 200
    call = retriever.calls[0]
    assert call["filters"] == {"source_type": "user"}
    assert call["exclude_ids"] == [saved["message_id"]]


# --- Real retrieval module (MiniLM) -------------------------------------------

EVENT = [
    ("The Ballina Road bridge in Lismore has collapsed into the river.",
     "infrastructure_and_utility_damage"),
    ("Ballina Rd bridge is gone, part of it fell into the Wilsons River, do not drive there.",
     "caution_and_advice"),
    ("Just saw the bridge on Ballina Road in Lismore collapse, cars stuck on both sides.",
     "infrastructure_and_utility_damage"),
    ("Lismore: the Ballina Road bridge has broken apart after the flood.",
     "infrastructure_and_utility_damage"),
    ("We need help at 12 Union Street South Lismore, water is up to the second floor.",
     "requests_or_urgent_needs"),
    ("Please send a boat to Union Street, South Lismore, three families trapped and need help.",
     "requests_or_urgent_needs"),
    ("Need help urgently in South Lismore near Union Street, elderly man cannot get out.",
     "requests_or_urgent_needs"),
    ("Evacuation centre at Southern Cross University is open.",
     "displaced_people_and_evacuations"),
    ("Power is out across North Lismore.", "infrastructure_and_utility_damage"),
    ("Thinking of everyone in Lismore tonight, stay safe.", "sympathy_and_support"),
]


@pytest.fixture
def event_index():
    """The real index with one simulated event added; restored afterwards."""
    if not (INDEX_DIR / "semantic_embeddings.npy").exists():
        pytest.skip("retrieval index not built (models/retrieval/index)")
    from models.retrieval import retrieval

    retrieval.reset_index()
    ids = {}
    try:
        for text, label in EVENT:
            message_id = str(uuid.uuid4())
            ids[text] = message_id
            retrieval.add_to_index(
                {
                    "message_id": message_id,
                    "text": text,
                    "board_label": label,
                    "source_type": "user",
                    "status": "unverified",
                    "needs_review": False,
                }
            )
        # Loads the sentence model; skip if it is not available offline.
        retrieval.retrieve("warm-up", 1, filters={"source_type": "user"})
    except OSError as exc:
        retrieval.reset_index()
        pytest.skip(f"sentence model not available: {exc}")
    yield retrieval, ids
    retrieval.reset_index()


def test_reports_about_the_same_bridge_find_each_other(event_index):
    retrieval, ids = event_index
    adapter = services.RetrievalAdapter(retrieval)

    found = services.find_related(
        adapter, "The bridge on Ballina Road near Lismore has fallen down.", k=5
    )

    bridge_ids = {ids[text] for text, _ in EVENT[:4]}
    # All four earlier bridge reports, including the one in another category,
    # and nothing else from the event.
    assert {item.id for item in found} == bridge_ids


def test_help_search_returns_this_events_requests(event_index):
    retrieval, ids = event_index

    found = retrieval.search("help", k=10, filters={"source_type": "user"})

    help_ids = {ids[text] for text, _ in EVENT[4:7]}
    assert {item["id"] for item in found} == help_ids
