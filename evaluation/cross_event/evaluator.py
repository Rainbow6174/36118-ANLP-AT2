"""Cross-event evaluation orchestration.

Loads event-wise HumAID test splits from `data/raw/humaid_events/`,
runs a shared `classify(text)` classifier against each event, and writes
per-event + summary tables to the output directory.

Event file naming convention (set by Member 1's EDA notebook):
    <event>__train.json
    <event>__dev.json         (dev = validation)
    <event>__test.json
Each JSON row has `tweet_text` and `class_label`.

The evaluator only reads the __test.json files.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Protocol

import pandas as pd

from app.backend.labels import LABEL_SET
from app.backend.schemas import Prediction

from .metrics import EventMetrics, compute, summarise


class Classifier(Protocol):
    def classify(self, text: str) -> Prediction | dict: ...


def discover_test_events(events_dir: Path) -> dict[str, Path]:
    """Return {event_name: path} for every __test.json file under events_dir.

    Raises FileNotFoundError if events_dir is missing (points user at the
    EDA notebook which populates it).
    """
    if not events_dir.exists():
        raise FileNotFoundError(
            f"{events_dir} not found. Run notebooks/01_crisis_eda.ipynb "
            "to download the HumAID-events files."
        )
    found: dict[str, Path] = {}
    for p in sorted(events_dir.glob("*__test.json")):
        event = p.name.removesuffix("__test.json")
        found[event] = p
    if not found:
        raise FileNotFoundError(
            f"no *__test.json files in {events_dir}. "
            "Expected format: <event>__test.json"
        )
    return found


def load_event_test(path: Path) -> pd.DataFrame:
    frame = pd.read_json(path)
    for col in ("tweet_text", "class_label"):
        if col not in frame.columns:
            raise ValueError(f"{path.name} missing required column '{col}'")
    frame = frame[["tweet_text", "class_label"]].copy()
    frame["tweet_text"] = frame["tweet_text"].fillna("").astype(str)
    frame["class_label"] = frame["class_label"].astype(str)
    unknown = set(frame["class_label"].unique()) - LABEL_SET
    if unknown:
        raise ValueError(f"{path.name} has unknown labels: {sorted(unknown)}")
    return frame


def evaluate_event(
    classifier: Classifier, event: str, frame: pd.DataFrame
) -> EventMetrics:
    start = time.perf_counter()
    predictions = [
        Prediction.model_validate(classifier.classify(t)).predicted_label
        for t in frame["tweet_text"]
    ]
    elapsed = time.perf_counter() - start
    return compute(
        event=event,
        y_true=frame["class_label"].tolist(),
        y_pred=predictions,
        runtime_seconds=elapsed,
    )


def run(
    classifier: Classifier,
    events_dir: Path,
    out_dir: Path,
    model_name: str,
) -> dict:
    """Evaluate the classifier on every event's test split and persist results.

    Writes:
        out_dir/per_event_metrics.csv
        out_dir/per_label_metrics.csv
        out_dir/confusion_<event>.csv (one per event)
        out_dir/summary.json
        out_dir/run_log.json
    Returns the summary dict.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    event_paths = discover_test_events(events_dir)

    all_metrics: list[EventMetrics] = []
    per_event_rows: list[dict] = []
    per_label_rows: list[dict] = []

    for event, path in event_paths.items():
        frame = load_event_test(path)
        m = evaluate_event(classifier, event, frame)
        all_metrics.append(m)

        per_event_rows.append(
            {
                "event": event,
                "n_examples": m.n_examples,
                "macro_f1": m.macro_f1,
                "balanced_accuracy": m.balanced_accuracy,
                "runtime_seconds": m.runtime_seconds,
            }
        )
        for _, row in m.per_label.iterrows():
            per_label_rows.append(
                {
                    "event": event,
                    "label": row["label"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                    "f1": row["f1"],
                    "support": int(row["support"]),
                }
            )
        m.confusion.to_csv(out_dir / f"confusion_{event}.csv")

    pd.DataFrame(per_event_rows).to_csv(out_dir / "per_event_metrics.csv", index=False)
    pd.DataFrame(per_label_rows).to_csv(out_dir / "per_label_metrics.csv", index=False)

    summary = summarise(all_metrics)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (out_dir / "run_log.json").write_text(
        json.dumps(
            {
                "model_name": model_name,
                "events_dir": str(events_dir),
                "out_dir": str(out_dir),
                "events_evaluated": list(event_paths.keys()),
                "n_events": len(event_paths),
                "total_runtime_seconds": sum(m.runtime_seconds for m in all_metrics),
            },
            indent=2,
        )
    )
    return summary
