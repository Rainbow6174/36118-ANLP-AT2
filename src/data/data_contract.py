"""Shared dataset contract used by every modelling and application stream."""

from __future__ import annotations

import re
import unicodedata


VARIETIES = ("en-AU", "en-IN", "en-UK")
SOURCES = ("google", "reddit")
LABELS = (0, 1)
SPLITS = ("train", "validation", "test")

REQUIRED_COLUMNS = (
    "id",
    "text",
    "variety",
    "source",
    "sentiment",
    "sarcasm",
    "official_split",
    "split",
    "char_count",
    "word_count",
)

TASK_COLUMNS = ("id", "text", "variety", "source", "label")


def clean_text(value: str) -> str:
    """Apply deliberately minimal cleaning while retaining linguistic cues."""

    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def duplicate_key(value: str) -> str:
    """Canonical key for exact/case-only duplicate detection, not file hashing."""

    normalized = unicodedata.normalize("NFKC", clean_text(value))
    return normalized.casefold()


def parse_binary_label(value: object, field: str) -> int:
    """Parse 0/1 labels while accepting CSV representations such as 1.0."""

    try:
        parsed = int(float(str(value).strip()))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not numeric: {value!r}") from exc
    if parsed not in LABELS:
        raise ValueError(f"{field} must be 0 or 1, received {value!r}")
    return parsed


def slug_variety(variety: str) -> str:
    return variety.lower().replace("-", "_")
