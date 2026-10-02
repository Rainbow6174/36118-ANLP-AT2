"""POST/GET/GET-by-id/PATCH /api/reports."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import store
from ..ports.retriever import MockRetriever, Retriever
from ..schemas import (
    ReportCreate,
    ReportDetailResponse,
    ReportListResponse,
    ReportPatch,
    ReportRecord,
)

router = APIRouter()

_retriever = MockRetriever()


def get_retriever() -> Retriever:
    return _retriever


@router.post("/reports", response_model=ReportRecord, status_code=201)
def create_report(payload: ReportCreate) -> ReportRecord:
    return store.insert(payload)


@router.get("/reports", response_model=ReportListResponse)
def list_reports(
    board_label: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    needs_review: Optional[bool] = None,
    page: int = Query(1, ge=1),
    k: int = Query(20, ge=1, le=200),
) -> ReportListResponse:
    items, total = store.list_reports(
        board_label=board_label,
        source_type=source_type,
        status=status,
        country=country,
        region=region,
        city=city,
        needs_review=needs_review,
        page=page,
        k=k,
    )
    return ReportListResponse(items=items, page=page, k=k, total=total)


@router.get("/reports/{message_id}", response_model=ReportDetailResponse)
def get_report(
    message_id: str,
    retriever: Retriever = Depends(get_retriever),
) -> ReportDetailResponse:
    record = store.get(message_id)
    if record is None:
        raise HTTPException(status_code=404, detail="report not found")
    related = retriever.retrieve(record.text, k=5)
    return ReportDetailResponse(report=record, related_reports=related)


@router.patch("/reports/{message_id}", response_model=ReportRecord)
def patch_report(message_id: str, patch: ReportPatch) -> ReportRecord:
    try:
        updated = store.patch(
            message_id,
            user_correction=patch.user_correction,
            status=patch.status,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="report not found")
    return updated
