"""Validate the prepared BESSTIE contract and leakage safeguards."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from .data_contract import LABELS, REQUIRED_COLUMNS, SOURCES, SPLITS, VARIETIES, duplicate_key
except ImportError:
    from data_contract import LABELS, REQUIRED_COLUMNS, SOURCES, SPLITS, VARIETIES, duplicate_key


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise AssertionError(f"Column contract mismatch: {reader.fieldnames}")
        return list(reader)


def validate(dataset_path: Path, report_path: Path | None = None) -> dict:
    rows = read_rows(dataset_path)
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    ids = [row["id"] for row in rows]
    keys = [duplicate_key(row["text"]) for row in rows]
    check("dataset_not_empty", bool(rows), f"{len(rows)} rows")
    check("unique_ids", len(ids) == len(set(ids)), f"{len(ids) - len(set(ids))} duplicate IDs")
    check("no_exact_text_duplicates", len(keys) == len(set(keys)), f"{len(keys) - len(set(keys))} duplicate normalized texts")
    check("nonempty_text", all(row["text"].strip() for row in rows), "all text fields are non-empty")
    check("valid_varieties", {row["variety"] for row in rows} == set(VARIETIES), str(sorted({row["variety"] for row in rows})))
    check("valid_sources", {row["source"] for row in rows} == set(SOURCES), str(sorted({row["source"] for row in rows})))
    check("valid_splits", {row["split"] for row in rows} == set(SPLITS), str(sorted({row["split"] for row in rows})))
    check("binary_sentiment", {int(row["sentiment"]) for row in rows} == set(LABELS), str(sorted({row["sentiment"] for row in rows})))
    check("binary_sarcasm", {int(row["sarcasm"]) for row in rows} == set(LABELS), str(sorted({row["sarcasm"] for row in rows})))
    check(
        "test_is_official_validation_only",
        all((row["split"] == "test") == (row["official_split"] == "validation") for row in rows),
        "project test maps exactly to the official public validation split after QC",
    )

    split_keys = {split: {duplicate_key(row["text"]) for row in rows if row["split"] == split} for split in SPLITS}
    overlaps = {
        "train_validation": len(split_keys["train"] & split_keys["validation"]),
        "train_test": len(split_keys["train"] & split_keys["test"]),
        "validation_test": len(split_keys["validation"] & split_keys["test"]),
    }
    check("no_cross_split_text_leakage", not any(overlaps.values()), str(overlaps))

    strata = Counter((row["split"], row["variety"], row["source"]) for row in rows)
    missing_strata = [
        (split, variety, source)
        for split in SPLITS
        for variety in VARIETIES
        for source in SOURCES
        if strata[(split, variety, source)] == 0
    ]
    check("all_split_variety_source_cells_present", not missing_strata, f"missing={missing_strata}")

    display_path = dataset_path.as_posix()
    parts = list(dataset_path.parts)
    if "data" in parts:
        display_path = "/".join(parts[parts.index("data"):])
    report = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": display_path,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    if not report["passed"]:
        failures = [item for item in checks if not item["passed"]]
        raise AssertionError(json.dumps(failures, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=project_root / "data" / "processed" / "dataset_v1.csv")
    parser.add_argument("--report", type=Path, default=project_root / "data" / "processed" / "validation_report.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate(args.dataset, args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
