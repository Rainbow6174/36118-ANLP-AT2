"""Smoke tests for the cross-event evaluator.

Uses a synthetic 3-event fixture built inside tmp_path; no HumAID data
download required. Proves the end-to-end pipeline runs and the output
files have the right shape.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: F401 - used in fixture type hints at runtime

import pandas as pd
import pytest

from app.backend.labels import LABELS
from app.backend.ports.classifier import MockClassifier
from app.backend.schemas import Prediction
from evaluation.cross_event import evaluator, metrics


class PerfectClassifier:
    """Always returns the correct label. Used to exercise macro_f1=1.0."""

    model_version = "perfect-v0"

    def __init__(self, truth_map: dict[str, str] | None = None):
        self.truth_map = truth_map or {}

    def classify(self, text: str) -> Prediction:
        label = self.truth_map.get(text, LABELS[0])
        probs = {k: 0.0 for k in LABELS}
        probs[label] = 1.0
        return Prediction(
            predicted_label=label,
            probabilities=probs,
            confidence=1.0,
            model_version=self.model_version,
            needs_review=False,
        )


def _make_event_file(events_dir: Path, event: str, rows: list[tuple[str, str]]) -> None:
    df = pd.DataFrame(rows, columns=["tweet_text", "class_label"])
    df.to_json(events_dir / f"{event}__test.json")


@pytest.fixture
def events_dir(tmp_path):
    d = tmp_path / "events"
    d.mkdir()
    rows_a = [
        ("water needed", "requests_or_urgent_needs"),
        ("evacuating now", "displaced_people_and_evacuations"),
        ("bridge collapsed", "infrastructure_and_utility_damage"),
    ]
    rows_b = [
        ("prayers for all", "sympathy_and_support"),
        ("rescue team arrived", "rescue_volunteering_or_donation_effort"),
    ]
    rows_c = [
        ("stay safe advisory", "caution_and_advice"),
        ("missing child alert", "missing_or_found_people"),
        ("one injured reported", "injured_or_dead_people"),
        ("flood warning", "caution_and_advice"),
    ]
    _make_event_file(d, "event_a", rows_a)
    _make_event_file(d, "event_b", rows_b)
    _make_event_file(d, "event_c", rows_c)
    return d


def test_discover_test_events_finds_three(events_dir):
    found = evaluator.discover_test_events(events_dir)
    assert set(found.keys()) == {"event_a", "event_b", "event_c"}


def test_discover_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        evaluator.discover_test_events(tmp_path / "does_not_exist")


def test_discover_raises_when_empty(tmp_path):
    (tmp_path / "events").mkdir()
    with pytest.raises(FileNotFoundError):
        evaluator.discover_test_events(tmp_path / "events")


def test_load_event_test_rejects_unknown_label(tmp_path):
    d = tmp_path / "events"
    d.mkdir()
    _make_event_file(d, "bad_event", [("x", "nonsense_label")])
    with pytest.raises(ValueError, match="unknown labels"):
        evaluator.load_event_test(d / "bad_event__test.json")


def test_compute_perfect_classifier(events_dir):
    truth = {}
    for p in events_dir.glob("*__test.json"):
        df = pd.read_json(p)
        for _, row in df.iterrows():
            truth[row["tweet_text"]] = row["class_label"]

    clf = PerfectClassifier(truth_map=truth)
    frame = evaluator.load_event_test(events_dir / "event_a__test.json")
    m = evaluator.evaluate_event(clf, "event_a", frame)
    # event_a has support on exactly 3 of the 10 labels; perfect predictions
    # mean those three score f1=1.0 and the other seven score 0 (zero_division=0).
    # Macro-F1 is averaged over all 10 labels, so = 3/10 = 0.3.
    assert m.macro_f1 == pytest.approx(0.3)
    supported = m.per_label[m.per_label["support"] > 0]
    assert supported["f1"].tolist() == pytest.approx([1.0, 1.0, 1.0])
    assert m.n_examples == 3
    assert m.confusion.shape == (10, 10)
    assert m.per_label.shape == (10, 5)
    # Confusion diagonal sums to n_examples when predictions are perfect.
    assert int(m.confusion.values.diagonal().sum()) == 3


def test_full_run_writes_expected_outputs(events_dir, tmp_path):
    out_dir = tmp_path / "out"
    summary = evaluator.run(
        classifier=MockClassifier(),
        events_dir=events_dir,
        out_dir=out_dir,
        model_name="mock",
    )

    for name in ("per_event_metrics.csv", "per_label_metrics.csv", "summary.json", "run_log.json"):
        assert (out_dir / name).exists(), name
    for event in ("event_a", "event_b", "event_c"):
        assert (out_dir / f"confusion_{event}.csv").exists()

    per_event = pd.read_csv(out_dir / "per_event_metrics.csv")
    assert set(per_event["event"]) == {"event_a", "event_b", "event_c"}
    assert set(per_event.columns) == {
        "event",
        "n_examples",
        "macro_f1",
        "balanced_accuracy",
        "runtime_seconds",
    }

    per_label = pd.read_csv(out_dir / "per_label_metrics.csv")
    assert len(per_label) == 3 * 10
    assert set(per_label["label"]) == set(LABELS)

    run_log = json.loads((out_dir / "run_log.json").read_text())
    assert run_log["model_name"] == "mock"
    assert run_log["n_events"] == 3

    assert summary["n_events"] == 3
    assert "macro_f1" in summary
    assert "mean" in summary["macro_f1"]


def test_summary_flags_low_support_events(events_dir):
    results = []
    for event in ("event_a", "event_b", "event_c"):
        frame = evaluator.load_event_test(events_dir / f"{event}__test.json")
        results.append(evaluator.evaluate_event(MockClassifier(), event, frame))
    s = metrics.summarise(results)
    assert set(s["low_support_events"]).issubset({"event_a", "event_b", "event_c"})
