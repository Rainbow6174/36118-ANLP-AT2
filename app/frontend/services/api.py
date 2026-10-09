"""The only place the pages talk to the backend: the real REST API, or the demo backend when CRISISLENS_API_URL is not set."""

import asyncio
import os
from dataclasses import replace

import httpx
from constants.labels import LABELS
from schemas.api import (
    AnalyseResponse,
    ClassificationResponse,
    CrisisReport,
    LocationInput,
    RelatedReport,
    ReportListResponse,
    approximate,
    join_place_name,
)

from services.mock_backend import backend

API_URL = os.environ.get("CRISISLENS_API_URL", "").strip().rstrip("/")
USING_MOCK_BACKEND = not API_URL

_HTTP_TIMEOUT_SECONDS = 8.0
# Analysis and search can take several seconds while the server loads its model.
_SLOW_TIMEOUT_SECONDS = 20.0
_CONNECT_TIMEOUT_SECONDS = 2.0
_MOCK_LATENCY_SECONDS = 0.45
# Reports seeded for demos have a model_version starting with this.
_DEMO_MODEL_PREFIX = "demo"


class BackendError(Exception):
    """The backend could not be reached or rejected the request; the only error pages catch."""


def is_mock_model(model_version: str) -> bool:
    return model_version.startswith("mock")


async def _call(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    allow_not_found: bool = False,
    read_timeout: float = _HTTP_TIMEOUT_SECONDS,
) -> dict | None:
    """Send one request and return the JSON body, or None for an allowed 404."""
    query = {
        key: ("true" if value is True else "false" if value is False else value)
        for key, value in (params or {}).items()
        if value is not None
    }
    try:
        async with httpx.AsyncClient(
            base_url=API_URL,
            timeout=httpx.Timeout(read_timeout, connect=_CONNECT_TIMEOUT_SECONDS),
        ) as client:
            response = await client.request(method, path, params=query, json=json)
    except httpx.HTTPError as exc:
        raise BackendError("The server could not be reached.") from exc

    if allow_not_found and response.status_code == 404:
        return None
    if response.is_error:
        raise BackendError(f"The server answered with error {response.status_code}.")
    try:
        return response.json()
    except ValueError as exc:
        raise BackendError("The server sent an unreadable answer.") from exc


def _parse(build, what: str):
    """Run build(); a missing or mistyped field becomes a BackendError."""
    try:
        return build()
    except (KeyError, TypeError) as exc:
        raise BackendError(f"The {what} was not in the expected format.") from exc


def _known_label(label: str) -> str:
    """Reject an API contract error instead of silently changing model output."""
    if label in LABELS:
        return label
    raise BackendError(f"The backend returned an unsupported category: {label!r}.")


def _prediction_from_json(data: dict) -> ClassificationResponse:
    data = {**data, "predicted_label": _known_label(data["predicted_label"])}
    return ClassificationResponse(**data)


def _location_payload(location: LocationInput | None) -> dict | None:
    if location is None:
        return None
    return {
        "country": location.country,
        "region": location.region,
        "city": location.city,
        "latitude": approximate(location.latitude),
        "longitude": approximate(location.longitude),
    }


def _location_from_record(data: dict) -> LocationInput | None:
    fields = {
        key: data.get(key)
        for key in ("country", "region", "city", "latitude", "longitude")
    }
    if all(value is None for value in fields.values()):
        return None
    fields["latitude"] = approximate(fields["latitude"])
    fields["longitude"] = approximate(fields["longitude"])
    name = join_place_name(fields["city"], fields["region"], fields["country"])
    return LocationInput(location_name=name or None, **fields)


def _report_from_record(data: dict) -> CrisisReport:
    return CrisisReport(
        message_id=data["message_id"],
        text=data["text"],
        predicted_label=_known_label(data["predicted_label"]),
        board_label=_known_label(data["board_label"]),
        source_type=data["source_type"],
        confidence=data["confidence"],
        model_version=data["model_version"],
        needs_review=data["needs_review"],
        created_at=data["created_at"],
        status=data["status"],
        user_correction=data.get("user_correction"),
        location=_location_from_record(data),
        is_demo=data["model_version"].startswith(_DEMO_MODEL_PREFIX),
    )


def _related_from_json(item: dict) -> RelatedReport:
    return RelatedReport(
        id=item["id"],
        similarity=item.get("similarity"),
        board_label=_known_label(item["board_label"]),
        text_preview=item["text_preview"],
        source_type=item["source_type"],
        created_at=item.get("created_at"),
        status=item.get("status"),
        # The place may be nested under "location" or flat, like in a report.
        location=_location_from_record(item.get("location") or item),
        duplicate_count=item.get("duplicate_count") or 0,
    )


async def analyse(text: str, location: LocationInput | None = None) -> AnalyseResponse:
    """Classify a draft report and find related reports."""
    if USING_MOCK_BACKEND:
        await asyncio.sleep(_MOCK_LATENCY_SECONDS)
        return AnalyseResponse(
            prediction=backend.classify(text),
            related_reports=backend.retrieve(text, k=3),
        )

    data = await _call(
        "POST",
        "/api/analyse",
        json={"text": text, "location": _location_payload(location)},
        read_timeout=_SLOW_TIMEOUT_SECONDS,
    )
    return _parse(
        lambda: AnalyseResponse(
            prediction=_prediction_from_json(data["prediction"]),
            related_reports=[
                _related_from_json(item) for item in data.get("related_reports", [])
            ],
        ),
        "analysis answer",
    )


async def create_report(
    text: str,
    prediction: ClassificationResponse,
    board_label: str,
    location: LocationInput | None = None,
) -> CrisisReport:
    """Save a report; the backend sets its status from needs_review."""
    if USING_MOCK_BACKEND:
        try:
            return backend.create_report(text, prediction, board_label, location)
        except ValueError as exc:
            raise BackendError(str(exc)) from exc

    data = await _call(
        "POST",
        "/api/reports",
        json={
            "text": text,
            "predicted_label": prediction.predicted_label,
            "board_label": board_label,
            "confidence": prediction.confidence,
            "model_version": prediction.model_version,
            "needs_review": prediction.needs_review,
            "location": _location_payload(location),
        },
    )
    return _parse(lambda: _report_from_record(data), "saved report")


async def list_reports(
    *,
    board_label: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
    needs_review: bool | None = None,
    page: int = 1,
    page_size: int = 6,
) -> ReportListResponse:
    """One page of full reports, newest first."""
    if USING_MOCK_BACKEND:
        return backend.list_reports(
            board_label=board_label,
            source_type=source_type,
            status=status,
            needs_review=needs_review,
            page=page,
            page_size=page_size,
        )

    data = await _call(
        "GET",
        "/api/reports",
        params={
            "board_label": board_label,
            "source_type": source_type,
            "status": status,
            "needs_review": needs_review,
            "page": page,
            "k": page_size,
        },
    )
    return _parse(
        lambda: ReportListResponse(
            items=[_report_from_record(item) for item in data["items"]],
            page=data["page"],
            page_size=data["k"],
            total=data["total"],
        ),
        "report list",
    )


async def search_reports(
    q: str,
    *,
    board_label: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
    k: int = 60,
) -> list[RelatedReport]:
    """Compact results, best match first (no total, so the page paginates them)."""
    if USING_MOCK_BACKEND:
        return backend.search(
            q, board_label=board_label, source_type=source_type, status=status, k=k
        )

    data = await _call(
        "GET",
        "/api/search",
        params={
            "q": q,
            "k": k,
            "board_label": board_label,
            "source_type": source_type,
            "status": status,
        },
        read_timeout=_SLOW_TIMEOUT_SECONDS,
    )
    found = _parse(
        lambda: [_related_from_json(i) for i in data["items"]], "search answer"
    )
    # Some retrievers ignore the source filter, so it is applied here too.
    return [
        item for item in found if source_type is None or item.source_type == source_type
    ]


async def fill_details(items: list[RelatedReport]) -> list[RelatedReport]:
    """Add time, place and status to saved reports that a search result left without them."""

    async def fill(item: RelatedReport) -> RelatedReport:
        if item.source_type != "user" or item.created_at is not None:
            return item
        try:
            report = await get_report(item.id)
        except BackendError:
            return item  # The short card still works.
        if report is None:
            return item
        return replace(
            item,
            created_at=report.created_at,
            status=report.status,
            location=report.location,
        )

    return list(await asyncio.gather(*(fill(item) for item in items)))


async def get_report_detail(
    message_id: str,
) -> tuple[CrisisReport, list[RelatedReport]] | None:
    """A report and its related reports, or None when it does not exist."""
    if USING_MOCK_BACKEND:
        report = backend.get_report(message_id)
        if report is None:
            return None
        return report, backend.retrieve(report.text, k=4, exclude_id=message_id)

    data = await _call("GET", f"/api/reports/{message_id}", allow_not_found=True)
    if data is None:
        return None
    return _parse(
        lambda: (
            _report_from_record(data["report"]),
            [_related_from_json(item) for item in data.get("related_reports", [])],
        ),
        "report",
    )


async def get_report(message_id: str) -> CrisisReport | None:
    detail = await get_report_detail(message_id)
    return detail[0] if detail else None


async def update_report(
    message_id: str,
    *,
    board_label: str | None = None,
    status: str | None = None,
) -> CrisisReport:
    """Change the category and/or status; pass board_label only when it really changes."""
    if USING_MOCK_BACKEND:
        try:
            return backend.update_report(
                message_id, board_label=board_label, status=status
            )
        except (KeyError, ValueError, PermissionError) as exc:
            raise BackendError(str(exc)) from exc

    body = {}
    if board_label is not None:
        body["user_correction"] = board_label
    if status is not None:
        body["status"] = status
    data = await _call("PATCH", f"/api/reports/{message_id}", json=body)
    return _parse(lambda: _report_from_record(data), "updated report")
