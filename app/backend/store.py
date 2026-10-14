"""SQLite-backed report store.

Public API (insert / get / list_reports / patch) matches the step-1
in-memory store so handlers do not change.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from . import db
from .labels import LABEL_SET
from .schemas import ReportCreate, ReportRecord

_COLUMNS = (
    "message_id, text, predicted_label, board_label, source_type, "
    "confidence, model_version, needs_review, created_at, user_correction, "
    "status, country, region, city, latitude, longitude"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_record(row: sqlite3.Row) -> ReportRecord:
    return ReportRecord(
        message_id=row["message_id"],
        text=row["text"],
        predicted_label=row["predicted_label"],
        board_label=row["board_label"],
        source_type=row["source_type"],
        confidence=row["confidence"],
        model_version=row["model_version"],
        needs_review=bool(row["needs_review"]),
        created_at=row["created_at"],
        user_correction=row["user_correction"],
        status=row["status"],
        country=row["country"],
        region=row["region"],
        city=row["city"],
        latitude=row["latitude"],
        longitude=row["longitude"],
    )


def insert(payload: ReportCreate) -> ReportRecord:
    board = payload.board_label or payload.predicted_label
    status = "needs_review" if payload.needs_review else "unverified"
    loc = payload.location
    record = ReportRecord(
        message_id=str(uuid.uuid4()),
        text=payload.text,
        predicted_label=payload.predicted_label,
        board_label=board,
        source_type=payload.source_type,
        confidence=payload.confidence,
        model_version=payload.model_version,
        needs_review=payload.needs_review,
        created_at=_now_iso(),
        user_correction=None,
        status=status,
        country=loc.country if loc else None,
        region=loc.region if loc else None,
        city=loc.city if loc else None,
        latitude=loc.latitude if loc else None,
        longitude=loc.longitude if loc else None,
    )
    conn = db.connect()
    try:
        conn.execute(
            f"INSERT INTO reports ({_COLUMNS}) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.message_id,
                record.text,
                record.predicted_label,
                record.board_label,
                record.source_type,
                record.confidence,
                record.model_version,
                int(record.needs_review),
                record.created_at,
                record.user_correction,
                record.status,
                record.country,
                record.region,
                record.city,
                record.latitude,
                record.longitude,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return record


def get(message_id: str) -> Optional[ReportRecord]:
    conn = db.connect()
    try:
        cur = conn.execute(
            "SELECT * FROM reports WHERE message_id = ?", (message_id,)
        )
        row = cur.fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()

def list_reports(
    *,
    board_label: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    needs_review: Optional[bool] = None,
    page: int = 1,
    k: int = 20,
) -> tuple[list[ReportRecord], int]:
    conditions: list[str] = ["1=1"]
    params: list = []
    if board_label is not None:
        conditions.append("board_label = ?")
        params.append(board_label)
    if source_type is not None:
        conditions.append("source_type = ?")
        params.append(source_type)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if country is not None:
        conditions.append("country = ?")
        params.append(country)
    if region is not None:
        conditions.append("region = ?")
        params.append(region)
    if city is not None:
        conditions.append("city = ?")
        params.append(city)
    if needs_review is not None:
        conditions.append("needs_review = ?")
        params.append(int(needs_review))

    where_sql = " AND ".join(conditions)
    page = max(1, page)
    k = max(1, k)
    offset = (page - 1) * k

    conn = db.connect()
    try:
        conn.execute("BEGIN")
        cur = conn.execute(
            f"SELECT COUNT(*) AS c FROM reports WHERE {where_sql}", params
        )
        total = cur.fetchone()["c"]
        cur = conn.execute(
            f"SELECT * FROM reports WHERE {where_sql} "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, k, offset],
        )
        rows = cur.fetchall()
        conn.execute("COMMIT")
    finally:
        conn.close()
    return [_row_to_record(r) for r in rows], total


def patch(
    message_id: str,
    *,
    user_correction: Optional[str],
    status: Optional[str],
) -> Optional[ReportRecord]:
    """Apply a correction and/or status update.

    - user_correction updates board_label; predicted_label is never overwritten.
    - Historical rows (source_type=humaid_history) raise PermissionError.
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "SELECT * FROM reports WHERE message_id = ?", (message_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        if row["source_type"] == "humaid_history":
            raise PermissionError("historical records are read-only")

        new_correction = row["user_correction"]
        new_board = row["board_label"]
        new_status = row["status"]
        new_needs_review = row["needs_review"]

        if user_correction is not None:
            if user_correction not in LABEL_SET:
                raise ValueError(f"unknown correction label: {user_correction}")
            new_correction = user_correction
            new_board = user_correction
            new_needs_review = False
        if status is not None:
            new_status = status
            if status == "resolved":
                new_needs_review = False

        conn.execute(
            "UPDATE reports SET user_correction = ?, board_label = ?, "
            "status = ?, needs_review = ? WHERE message_id = ?",
            (new_correction, new_board, new_status, new_needs_review, message_id),
        )
        conn.commit()
        cur = conn.execute(
            "SELECT * FROM reports WHERE message_id = ?", (message_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_record(row)
    finally:
        conn.close()
