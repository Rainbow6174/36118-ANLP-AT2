"""Data shapes of the backend API (see the repo root README.md)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Two decimals is about 1 km: locations are shared as an area, not a point.
COORDINATE_DECIMALS = 2


def approximate(value: float | None) -> float | None:
    """Round a coordinate to the shared precision."""
    return None if value is None else round(value, COORDINATE_DECIMALS)


def join_place_name(*parts: str | None) -> str:
    """Join the non-empty parts with commas, dropping repeats."""
    return ", ".join(dict.fromkeys(part for part in parts if part))


@dataclass
class ClassificationResponse:
    predicted_label: str
    probabilities: dict[str, float]
    confidence: float
    model_version: str
    needs_review: bool


@dataclass
class LocationInput:
    location_name: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass
class RelatedReport:
    id: str
    board_label: str
    text_preview: str
    source_type: str  # "user" | "humaid_history"


@dataclass
class AnalyseResponse:
    prediction: ClassificationResponse
    related_reports: list[RelatedReport] = field(default_factory=list)


@dataclass
class CrisisReport:
    message_id: str
    text: str
    predicted_label: str
    board_label: str
    source_type: str  # "user" | "humaid_history"
    confidence: float
    model_version: str
    needs_review: bool
    created_at: str
    status: str  # "unverified" | "needs_review" | "resolved"
    user_correction: str | None = None
    location: LocationInput | None = None
    is_demo: bool = False  # Set by the adapter for demo records, not sent by the API.


@dataclass
class ReportListResponse:
    items: list[CrisisReport]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        return max(1, -(-self.total // self.page_size))
