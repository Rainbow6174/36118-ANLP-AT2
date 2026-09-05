"""One-command runner for the shared data and EDA deliverables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .download_besstie import download_all
    from .generate_eda import generate
    from .prepare_besstie import prepare
    from .validate_besstie import validate
except ImportError:
    from download_besstie import download_all
    from generate_eda import generate
    from prepare_besstie import prepare
    from validate_besstie import validate


def run(project_root: Path, force_download: bool = False) -> dict:
    raw_dir = project_root / "data" / "raw" / "besstie"
    processed_dir = project_root / "data" / "processed"
    config_path = project_root / "config" / "data_config.json"
    download_records = download_all(raw_dir, force=force_download)
    quality = prepare(raw_dir, processed_dir, config_path)
    validation = validate(processed_dir / "dataset_v1.csv", processed_dir / "validation_report.json")
    eda = generate(project_root)
    return {
        "downloaded_or_reused": len(download_records),
        "rows_after_quality_control": quality["rows_after_quality_control"],
        "rows_removed": quality["rows_removed"],
        "validation_passed": validation["passed"],
        "split_counts": eda["split_counts"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(run(args.project_root.resolve(), args.force_download), indent=2))


if __name__ == "__main__":
    main()
