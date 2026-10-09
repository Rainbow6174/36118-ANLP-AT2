"""Run the reusable cross-event evaluator with a registered classifier.

Usage:
    python -m evaluation.cross_event \\
        --model mock \\
        --events-dir data/raw/humaid_events \\
        --out-dir outputs/results/cross_event/mock

The lightweight mock entry checks the evaluator without loading a trained
model. Final project experiments use their model-specific training files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluator import Classifier, run


def _mock_classifier() -> Classifier:
    from app.backend.ports.classifier import MockClassifier

    return MockClassifier()


_MODEL_REGISTRY: dict[str, callable] = {
    "mock": _mock_classifier,
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="evaluation.cross_event")
    p.add_argument("--model", required=True, choices=sorted(_MODEL_REGISTRY))
    p.add_argument(
        "--events-dir",
        type=Path,
        default=Path("data/raw/humaid_events"),
    )
    p.add_argument("--out-dir", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    classifier = _MODEL_REGISTRY[args.model]()
    summary = run(
        classifier=classifier,
        events_dir=args.events_dir,
        out_dir=args.out_dir,
        model_name=args.model,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
