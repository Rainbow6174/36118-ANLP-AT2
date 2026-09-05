"""Download the six public BESSTIE CSV files from the official repository."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://huggingface.co/datasets/unswnlporg/BESSTIE/resolve/main/data"
REMOTE_VARIETY = {"en-AU": "en_AU", "en-IN": "en_IN", "en-UK": "en_UK"}
OFFICIAL_SPLITS = ("train", "validation")
EXPECTED_HEADER = {"source", "variety", "text", "sentiment", "sarcasm"}


def source_url(variety: str, split: str) -> str:
    return f"{BASE_URL}/{REMOTE_VARIETY[variety]}/{split}.csv?download=true"


def validate_download(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
    if set(header) != EXPECTED_HEADER:
        raise ValueError(f"Unexpected header in {path}: {header}")


def download_all(raw_dir: Path, force: bool = False) -> list[dict[str, str]]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    for variety, remote_name in REMOTE_VARIETY.items():
        target_dir = raw_dir / remote_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for split in OFFICIAL_SPLITS:
            target = target_dir / f"{split}.csv"
            url = source_url(variety, split)
            status = "reused"
            if force or not target.exists():
                temporary = target.with_suffix(".csv.part")
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": "VarietyLens-UTS-36118/1.0"},
                )
                with urllib.request.urlopen(request, timeout=90) as response:
                    with temporary.open("wb") as output:
                        shutil.copyfileobj(response, output)
                validate_download(temporary)
                temporary.replace(target)
                status = "downloaded"
            else:
                validate_download(target)
            records.append(
                {
                    "variety": variety,
                    "official_split": split,
                    "url": url,
                    "relative_path": target.relative_to(raw_dir.parents[2]).as_posix(),
                    "bytes": str(target.stat().st_size),
                    "status": status,
                }
            )

    provenance = {
        "dataset": "BESSTIE",
        "repository": "https://huggingface.co/datasets/unswnlporg/BESSTIE",
        "paper": "https://aclanthology.org/2025.findings-acl.441/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": records,
        "integrity_note": "Files are validated by schema and row-level quality checks; no SHA256/local hash freeze is used.",
    }
    with (raw_dir / "provenance.json").open("w", encoding="utf-8") as stream:
        json.dump(provenance, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return records


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=project_root / "data" / "raw" / "besstie",
    )
    parser.add_argument("--force", action="store_true", help="Redownload existing files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = download_all(args.raw_dir, force=args.force)
    for item in records:
        print(f"{item['status']:10s} {item['variety']:5s} {item['official_split']:10s} {item['relative_path']}")


if __name__ == "__main__":
    main()
