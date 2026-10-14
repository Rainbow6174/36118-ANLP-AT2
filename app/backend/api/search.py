"""GET /api/search."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import services
from ..ports.retriever import Retriever
from ..schemas import SearchResponse

router = APIRouter()

def get_retriever() -> Retriever:
    return services.get_retriever()


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    k: int = Query(20, ge=1, le=200),
    board_label: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    needs_review: Optional[bool] = None,
    retriever: Retriever = Depends(get_retriever),
) -> SearchResponse:
    filters = {
        key: val
        for key, val in {
            "board_label": board_label,
            "source_type": source_type,
            "status": status,
            "country": country,
            "region": region,
            "city": city,
            "needs_review": needs_review,
        }.items()
        if val is not None
    }
    items = retriever.search(q, filters=filters, k=k)
    return SearchResponse(items=items, q=q, k=k)
