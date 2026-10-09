"""Retrieval port. Member 5 will supply the real TF-IDF/embeddings backend.

Matches the retrieve(text, k, filters=None) and search(query, filters, k)
contract from README.md.
"""

from __future__ import annotations

from typing import Optional, Protocol

from ..schemas import RelatedReport


class Retriever(Protocol):
    def retrieve(
        self,
        text: str,
        k: int = 5,
        filters: Optional[dict] = None,
        exclude_ids=None,
    ) -> list[RelatedReport]: ...

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        k: int = 20,
        exclude_ids=None,
    ) -> list[RelatedReport]: ...


class MockRetriever:
    """Deterministic mock. Returns k canned RelatedReport items keyed off
    the input length so the shape is exercised without an index.
    """

    def _fake_items(
        self,
        text: str,
        k: int,
        filters: Optional[dict] = None,
        exclude_ids=None,
    ) -> list[RelatedReport]:
        n = max(0, min(k, 5))
        preview = (text or "")[:80]
        filters = filters or {}
        board_label = filters.get("board_label") or "requests_or_urgent_needs"
        source_type = filters.get("source_type") or "humaid_history"
        prefix = "user" if source_type == "user" else "history"
        excluded = {str(value) for value in (exclude_ids or [])}
        items = [
            RelatedReport(
                id=f"{prefix}-{i:03d}",
                similarity=round(0.9 - 0.1 * i, 3),
                board_label=board_label,
                text_preview=f"[mock #{i}] {preview}",
                source_type=source_type,
            )
            for i in range(n)
        ]
        return [item for item in items if item.id not in excluded]

    def retrieve(
        self,
        text: str,
        k: int = 5,
        filters: Optional[dict] = None,
        exclude_ids=None,
    ) -> list[RelatedReport]:
        return self._fake_items(text, k, filters, exclude_ids)

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        k: int = 20,
        exclude_ids=None,
    ) -> list[RelatedReport]:
        return self._fake_items(query, k, filters, exclude_ids)
