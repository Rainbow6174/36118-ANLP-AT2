"""Pydantic request and response models for the CrisisLens API.

Field names, order and shape match README.md. Do not rename without team sign-off.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .labels import LABELS, LABEL_SET

SourceType = Literal["user", "humaid_history"]
Status = Literal["unverified", "needs_review", "resolved"]


class Location(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Prediction(BaseModel):
    predicted_label: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    needs_review: bool

    @field_validator("predicted_label")
    @classmethod
    def _label_known(cls, v: str) -> str:
        if v not in LABEL_SET:
            raise ValueError(f"unknown label: {v}")
        return v

    @field_validator("probabilities")
    @classmethod
    def _probs_valid(cls, v: dict[str, float]) -> dict[str, float]:
        missing = LABEL_SET - v.keys()
        extra = v.keys() - LABEL_SET
        if missing or extra:
            raise ValueError(
                f"probabilities must contain the 10 labels exactly; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for label, p in v.items():
            if not (0.0 <= p <= 1.0):
                raise ValueError(
                    f"probability for {label!r} out of range: {p}"
                )
        total = sum(v.values())
        if abs(total - 1.0) > 1e-3:
            raise ValueError(
                f"probabilities must sum to 1.0 (got {total:.6f})"
            )
        return {k: v[k] for k in LABELS}


class RelatedReport(BaseModel):
    id: str
    similarity: float
    board_label: str
    text_preview: str
    source_type: SourceType


class AnalyseRequest(BaseModel):
    text: str = Field(min_length=1)
    location: Optional[Location] = None


class AnalyseResponse(BaseModel):
    prediction: Prediction
    related_reports: list[RelatedReport] = Field(default_factory=list)
    extraction: Optional[dict] = None


class ReportCreate(BaseModel):
    text: str = Field(min_length=1)
    predicted_label: str
    board_label: Optional[str] = None
    source_type: SourceType = "user"
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    needs_review: bool = False
    location: Optional[Location] = None

    @field_validator("predicted_label")
    @classmethod
    def _label_known(cls, v: str) -> str:
        if v not in LABEL_SET:
            raise ValueError(f"unknown label: {v}")
        return v

    @field_validator("board_label")
    @classmethod
    def _board_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in LABEL_SET:
            raise ValueError(f"unknown board_label: {v}")
        return v


class ReportRecord(BaseModel):
    message_id: str
    text: str
    predicted_label: str
    board_label: str
    source_type: SourceType
    confidence: float
    model_version: str
    needs_review: bool
    created_at: str
    user_correction: Optional[str] = None
    status: Status
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ReportListResponse(BaseModel):
    items: list[ReportRecord]
    page: int
    k: int
    total: int


class ReportDetailResponse(BaseModel):
    report: ReportRecord
    related_reports: list[RelatedReport] = Field(default_factory=list)


class ReportPatch(BaseModel):
    user_correction: Optional[str] = None
    status: Optional[Status] = None

    @field_validator("user_correction")
    @classmethod
    def _correction_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in LABEL_SET:
            raise ValueError(f"unknown user_correction label: {v}")
        return v


class SearchResponse(BaseModel):
    items: list[RelatedReport]
    q: str
    k: int
