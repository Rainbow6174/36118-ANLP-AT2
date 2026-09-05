"""Prepare leakage-safe, minimally cleaned BESSTIE project splits."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from .data_contract import (
        REQUIRED_COLUMNS,
        SOURCES,
        TASK_COLUMNS,
        VARIETIES,
        clean_text,
        duplicate_key,
        parse_binary_label,
        slug_variety,
    )
except ImportError:  # Allows direct execution from the repository root.
    from data_contract import (
        REQUIRED_COLUMNS,
        SOURCES,
        TASK_COLUMNS,
        VARIETIES,
        clean_text,
        duplicate_key,
        parse_binary_label,
        slug_variety,
    )


REMOTE_VARIETY = {"en-AU": "en_AU", "en-IN": "en_IN", "en-UK": "en_UK"}
RAW_COLUMNS = {"source", "variety", "text", "sentiment", "sarcasm"}


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_raw_rows(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    removed: list[dict] = []
    for variety in VARIETIES:
        for official_split in ("train", "validation"):
            path = raw_dir / REMOTE_VARIETY[variety] / f"{official_split}.csv"
            if not path.exists():
                raise FileNotFoundError(f"Missing raw file: {path}. Run download_besstie.py first.")
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if set(reader.fieldnames or []) != RAW_COLUMNS:
                    raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
                for row_number, raw in enumerate(reader, start=1):
                    row_id = (
                        f"besstie-{slug_variety(variety)}-{official_split}-"
                        f"{str(raw.get('source', '')).strip().lower()}-{row_number:06d}"
                    )
                    text = clean_text(raw.get("text", ""))
                    try:
                        source = str(raw.get("source", "")).strip().lower()
                        if raw.get("variety") != variety:
                            raise ValueError(
                                f"file variety {variety!r} disagrees with row value {raw.get('variety')!r}"
                            )
                        if source not in SOURCES:
                            raise ValueError(f"unknown source {source!r}")
                        if not text:
                            raise ValueError("empty text")
                        sentiment = parse_binary_label(raw.get("sentiment"), "sentiment")
                        sarcasm = parse_binary_label(raw.get("sarcasm"), "sarcasm")
                    except ValueError as exc:
                        removed.append(
                            {
                                "id": row_id,
                                "reason": "invalid_row",
                                "detail": str(exc),
                                "duplicate_of": "",
                                "variety": variety,
                                "source": str(raw.get("source", "")),
                                "official_split": official_split,
                            }
                        )
                        continue
                    rows.append(
                        {
                            "id": row_id,
                            "text": text,
                            "variety": variety,
                            "source": source,
                            "sentiment": sentiment,
                            "sarcasm": sarcasm,
                            "official_split": official_split,
                            "_duplicate_key": duplicate_key(text),
                            "_raw_row": row_number,
                        }
                    )
    return rows, removed


def deduplicate(rows: list[dict], removed: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["_duplicate_key"]].append(row)

    kept: list[dict] = []
    for key in sorted(groups):
        group = groups[key]
        label_pairs = {(item["sentiment"], item["sarcasm"]) for item in group}
        if len(label_pairs) > 1:
            for item in group:
                removed.append(
                    {
                        "id": item["id"],
                        "reason": "conflicting_duplicate_labels",
                        "detail": f"duplicate group has label pairs {sorted(label_pairs)}",
                        "duplicate_of": "",
                        "variety": item["variety"],
                        "source": item["source"],
                        "official_split": item["official_split"],
                    }
                )
            continue

        ordered = sorted(
            group,
            key=lambda item: (
                0 if item["official_split"] == "validation" else 1,
                item["variety"],
                item["source"],
                item["_raw_row"],
            ),
        )
        canonical = ordered[0]
        kept.append(canonical)
        for item in ordered[1:]:
            removed.append(
                {
                    "id": item["id"],
                    "reason": "duplicate_text",
                    "detail": "same text after NFKC, case-folding and whitespace collapse",
                    "duplicate_of": canonical["id"],
                    "variety": item["variety"],
                    "source": item["source"],
                    "official_split": item["official_split"],
                }
            )
    return kept


def assign_project_splits(rows: list[dict], validation_fraction: float, seed: int) -> list[dict]:
    if not 0 < validation_fraction < 0.5:
        raise ValueError("validation_fraction must be between 0 and 0.5")
    official_train = [row for row in rows if row["official_split"] == "train"]
    official_validation = [row for row in rows if row["official_split"] == "validation"]

    strata: dict[tuple, list[dict]] = defaultdict(list)
    for row in official_train:
        key = (row["variety"], row["source"], row["sentiment"], row["sarcasm"])
        strata[key].append(row)

    rng = random.Random(seed)
    for key in sorted(strata):
        group = sorted(strata[key], key=lambda item: item["id"])
        rng.shuffle(group)
        if len(group) <= 1:
            validation_count = 0
        else:
            validation_count = max(1, round(len(group) * validation_fraction))
            validation_count = min(validation_count, len(group) - 1)
        validation_ids = {item["id"] for item in group[:validation_count]}
        for item in group:
            item["split"] = "validation" if item["id"] in validation_ids else "train"

    for row in official_validation:
        row["split"] = "test"

    output: list[dict] = []
    for row in official_train + official_validation:
        clean = {key: row[key] for key in REQUIRED_COLUMNS if key in row}
        clean["char_count"] = len(row["text"])
        clean["word_count"] = len(row["text"].split())
        clean = {key: clean[key] for key in REQUIRED_COLUMNS}
        output.append(clean)

    split_order = {"train": 0, "validation": 1, "test": 2}
    return sorted(output, key=lambda item: (split_order[item["split"]], item["variety"], item["source"], item["id"]))


def write_csv(path: Path, rows: Iterable[dict], columns: tuple[str, ...] | list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_task_views(processed_dir: Path, rows: list[dict]) -> None:
    for task in ("sentiment", "sarcasm", "variety"):
        for split in ("train", "validation", "test"):
            task_rows = []
            for row in rows:
                if row["split"] != split:
                    continue
                label = row[task] if task != "variety" else row["variety"]
                task_rows.append(
                    {
                        "id": row["id"],
                        "text": row["text"],
                        "variety": row["variety"],
                        "source": row["source"],
                        "label": label,
                    }
                )
            write_csv(processed_dir / "by_task" / task / f"{split}.csv", task_rows, TASK_COLUMNS)


def summarize(rows: list[dict], removed: list[dict], config: dict) -> dict:
    def nested_counts(fields: tuple[str, ...]) -> list[dict]:
        counts = Counter(tuple(str(row[field]) for field in fields) for row in rows)
        return [
            {**{field: key[index] for index, field in enumerate(fields)}, "count": count}
            for key, count in sorted(counts.items())
        ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": config,
        "rows_after_quality_control": len(rows),
        "rows_removed": len(removed),
        "removal_reasons": dict(sorted(Counter(item["reason"] for item in removed).items())),
        "counts_by_split": nested_counts(("split",)),
        "counts_by_split_variety_source": nested_counts(("split", "variety", "source")),
        "counts_by_variety_source_labels": nested_counts(("variety", "source", "sentiment", "sarcasm")),
    }


def prepare(raw_dir: Path, processed_dir: Path, config_path: Path) -> dict:
    config = load_config(config_path)
    rows, removed = load_raw_rows(raw_dir)
    rows = deduplicate(rows, removed)
    rows = assign_project_splits(
        rows,
        validation_fraction=float(config["validation_fraction_from_official_train"]),
        seed=int(config["random_seed"]),
    )

    write_csv(processed_dir / "dataset_v1.csv", rows, REQUIRED_COLUMNS)
    for split in ("train", "validation", "test"):
        write_csv(processed_dir / f"{split}.csv", [row for row in rows if row["split"] == split], REQUIRED_COLUMNS)
    write_task_views(processed_dir, rows)

    removed_columns = ("id", "reason", "detail", "duplicate_of", "variety", "source", "official_split")
    write_csv(processed_dir / "audit" / "removed_rows.csv", removed, removed_columns)

    quality_report = summarize(rows, removed, config)
    with (processed_dir / "quality_report.json").open("w", encoding="utf-8") as stream:
        json.dump(quality_report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return quality_report


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=project_root / "data" / "raw" / "besstie")
    parser.add_argument("--processed-dir", type=Path, default=project_root / "data" / "processed")
    parser.add_argument("--config", type=Path, default=project_root / "config" / "data_config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = prepare(args.raw_dir, args.processed_dir, args.config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
