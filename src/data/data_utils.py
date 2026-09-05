"""Small shared loader so every team stream reads the same data contract."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

try:
    from .data_contract import REQUIRED_COLUMNS, SPLITS
except ImportError:
    from data_contract import REQUIRED_COLUMNS, SPLITS


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_records(split: str | None = None, root: Path | None = None) -> list[dict]:
    """Return rows as dictionaries with integer labels and length fields."""

    if split is not None and split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, received {split!r}")
    base = root or project_root()
    filename = f"{split}.csv" if split else "dataset_v1.csv"
    path = base / "data" / "processed" / filename
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError(f"Unexpected dataset schema in {path}: {reader.fieldnames}")
        rows = list(reader)
    for row in rows:
        for field in ("sentiment", "sarcasm", "char_count", "word_count"):
            row[field] = int(row[field])
    return rows


def iter_task_records(task: str, split: str, root: Path | None = None) -> Iterator[dict]:
    """Yield the five-column task view used by model owners."""

    if task not in {"sentiment", "sarcasm", "variety"}:
        raise ValueError("task must be sentiment, sarcasm or variety")
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}")
    base = root or project_root()
    path = base / "data" / "processed" / "by_task" / task / f"{split}.csv"
    with path.open("r", encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def load_dataframe(split: str | None = None, root: Path | None = None):
    """Optional pandas adapter for notebooks and modelling code."""

    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("Install pandas to use load_dataframe(); load_records() needs no dependency.") from exc
    return pd.DataFrame(load_records(split=split, root=root))
