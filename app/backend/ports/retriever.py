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
    ) -> list[RelatedReport]: ...

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        k: int = 20,
    ) -> list[RelatedReport]: ...


class MockRetriever:
    """Deterministic mock. Returns k canned RelatedReport items keyed off
    the input length so the shape is exercised without an index.
    """

    def _fake_items(self, text: str, k: int) -> list[RelatedReport]:
        n = max(0, min(k, 5))
        preview = (text or "")[:80]
        return [
            RelatedReport(
                id=f"history-{i:03d}",
                similarity=round(0.9 - 0.1 * i, 3),
                board_label="requests_or_urgent_needs",
                text_preview=f"[mock #{i}] {preview}",
                source_type="humaid_history",
            )
            for i in range(n)
        ]

    def retrieve(
        self,
        text: str,
        k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[RelatedReport]:
        return self._fake_items(text, k)

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        k: int = 20,
    ) -> list[RelatedReport]:
        return self._fake_items(query, k)
