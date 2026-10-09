"""Cross-event evaluation for the frozen CrisisLens Member 2 baseline."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import log_loss

from models.text_baseline.baseline import LABEL_ORDER, clean_text
from models.text_baseline.final_test import build_frozen_model
from models.text_baseline.train import compute_expected_calibration_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVENTS_DIR = PROJECT_ROOT / "data" / "raw" / "humaid_events"
OUTPUT_DIR = (
    PROJECT_ROOT / "outputs" / "results" / "cross_event" / "baseline"
)
FROZEN_VALIDATION_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "results"
    / "baseline"
    / "selected_validation.json"
)

HELD_OUT_EVENT = "cyclone_idai_2019"

CROSS_EVENT_EVENTS = [
    "canada_wildfires_2016",
    "cyclone_idai_2019",
    "ecuador_earthquake_2016",
    "greece_wildfires_2018",
    "hurricane_harvey_2017",
    "hurricane_irma_2017",
    "hurricane_maria_2017",
    "hurricane_matthew_2016",
    "italy_earthquake_aug_2016",
    "kaikoura_earthquake_2016",
    "maryland_floods_2018",
    "puebla_mexico_earthquake_2017",
    "srilanka_floods_2017",
]

EXPECTED_FULL_TRAIN_ROWS = 30_381
EXPECTED_FULL_DEV_ROWS = 4_422
EXPECTED_FULL_TEST_ROWS = 8_606

EXPECTED_TRAIN_AFTER_HOLDOUT = 27_628
EXPECTED_DEV_AFTER_HOLDOUT = 4_021
EXPECTED_HELDOUT_TEST_ROWS = 779


def load_event_split(event: str, split: str) -> pd.DataFrame:
    path = EVENTS_DIR / f"{event}__{split}.json"

    if not path.exists():
        raise FileNotFoundError(f"Missing event split: {path}")

    frame = pd.read_json(path)

    required = {"tweet_text", "class_label"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name} missing required columns: {sorted(missing)}"
        )

    frame = frame[["tweet_text", "class_label"]].copy()
    frame["tweet_text"] = frame["tweet_text"].fillna("").astype(str)
    frame["class_label"] = frame["class_label"].astype(str)
    frame["event"] = event

    unknown = set(frame["class_label"].unique()) - set(LABEL_ORDER)
    if unknown:
        raise ValueError(
            f"{path.name} contains unknown labels: {sorted(unknown)}"
        )

    return frame


def load_protocol_data():
    splits = {"train": [], "dev": [], "test": []}

    for event in CROSS_EVENT_EVENTS:
        for split in splits:
            splits[split].append(load_event_split(event, split))

    train_full = pd.concat(splits["train"], ignore_index=True)
    dev_full = pd.concat(splits["dev"], ignore_index=True)
    test_full = pd.concat(splits["test"], ignore_index=True)

    if len(train_full) != EXPECTED_FULL_TRAIN_ROWS:
        raise ValueError(
            f"Unexpected 13-event train rows: {len(train_full)}"
        )
    if len(dev_full) != EXPECTED_FULL_DEV_ROWS:
        raise ValueError(
            f"Unexpected 13-event dev rows: {len(dev_full)}"
        )
    if len(test_full) != EXPECTED_FULL_TEST_ROWS:
        raise ValueError(
            f"Unexpected 13-event test rows: {len(test_full)}"
        )

    train_xev = train_full[
        train_full["event"] != HELD_OUT_EVENT
    ].reset_index(drop=True)

    dev_xev = dev_full[
        dev_full["event"] != HELD_OUT_EVENT
    ].reset_index(drop=True)

    test_held = test_full[
        test_full["event"] == HELD_OUT_EVENT
    ].reset_index(drop=True)

    if len(train_xev) != EXPECTED_TRAIN_AFTER_HOLDOUT:
        raise ValueError(
            f"Unexpected train rows after holdout: {len(train_xev)}"
        )
    if len(dev_xev) != EXPECTED_DEV_AFTER_HOLDOUT:
        raise ValueError(
            f"Unexpected dev rows after holdout: {len(dev_xev)}"
        )
    if len(test_held) != EXPECTED_HELDOUT_TEST_ROWS:
        raise ValueError(
            f"Unexpected held-out test rows: {len(test_held)}"
        )

    if HELD_OUT_EVENT in set(train_xev["event"]):
        raise ValueError("Held-out event leaked into cross-event training.")
    if HELD_OUT_EVENT in set(dev_xev["event"]):
        raise ValueError("Held-out event leaked into cross-event validation.")

    observed_train_labels = set(train_xev["class_label"].unique())
    if observed_train_labels != set(LABEL_ORDER):
        raise ValueError(
            "Cross-event training labels do not match canonical labels."
        )

    return train_full, dev_full, test_full, train_xev, dev_xev, test_held


def load_frozen_policy() -> dict:
    return json.loads(
        FROZEN_VALIDATION_PATH.read_text(encoding="utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluator-root",
        type=Path,
        required=True,
        help="Path to Member 4 backend/evaluation worktree.",
    )
    args = parser.parse_args()

    evaluator_root = args.evaluator_root.resolve()

    if not evaluator_root.exists():
        raise FileNotFoundError(
            f"Member 4 evaluator root not found: {evaluator_root}"
        )

    sys.path.insert(0, str(evaluator_root))

    from app.backend.schemas import Prediction
    from evaluation.cross_event.evaluator import run

    (
        train_full,
        dev_full,
        test_full,
        train_xev,
        dev_xev,
        test_held,
    ) = load_protocol_data()

    frozen = load_frozen_policy()
    review_threshold = float(frozen["review_threshold"])

    x_train = train_xev["tweet_text"].map(clean_text)
    y_train = train_xev["class_label"]

    model = build_frozen_model()

    train_start = time.perf_counter()
    model.fit(x_train, y_train)
    training_runtime = time.perf_counter() - train_start

    model_class_order = model.named_steps[
        "classifier"
    ].classes_.tolist()

    if model_class_order != LABEL_ORDER:
        raise ValueError(
            "Cross-event model class order does not match LABEL_ORDER."
        )

    class BaselineCrossEventClassifier:
        def classify(self, text: str) -> Prediction:
            cleaned = clean_text(text)

            predicted_label = str(
                model.predict([cleaned])[0]
            )

            probability_values = model.predict_proba([cleaned])[0]

            probabilities = {
                label: float(probability_values[index])
                for index, label in enumerate(LABEL_ORDER)
            }

            confidence = float(max(probability_values))

            return Prediction(
                predicted_label=predicted_label,
                probabilities=probabilities,
                confidence=confidence,
                model_version="baseline-v1-cross-event",
                needs_review=confidence < review_threshold,
            )

    classifier = BaselineCrossEventClassifier()

    if OUTPUT_DIR.exists():
        existing = [
            p
            for p in OUTPUT_DIR.iterdir()
            if p.name != ".gitkeep"
        ]
        if existing:
            raise FileExistsError(
                "Cross-event baseline outputs already exist. "
                f"Refusing to overwrite: {existing}"
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    heldout_source = (
        EVENTS_DIR / f"{HELD_OUT_EVENT}__test.json"
    )

    with tempfile.TemporaryDirectory(
        prefix="crisislens_baseline_xev_"
    ) as tmp:
        evaluator_events_dir = Path(tmp)
        shutil.copy2(
            heldout_source,
            evaluator_events_dir / heldout_source.name,
        )

        summary = run(
            classifier=classifier,
            events_dir=evaluator_events_dir,
            out_dir=OUTPUT_DIR,
            model_name="word_char_tfidf_logistic_regression_cross_event",
        )

    # Member 4's evaluator records the temporary input directory and
    # machine-specific absolute output path. Normalise those fields for
    # a reproducible committed Member 2 artifact.
    run_log_path = OUTPUT_DIR / "run_log.json"
    run_log = json.loads(run_log_path.read_text(encoding="utf-8"))
    run_log["events_dir"] = "data/raw/humaid_events"
    run_log["source_test_file"] = (
        f"data/raw/humaid_events/{HELD_OUT_EVENT}__test.json"
    )
    run_log["out_dir"] = "outputs/results/cross_event/baseline"
    run_log_path.write_text(
        json.dumps(run_log, indent=2) + "\n",
        encoding="utf-8",
    )

    x_test = test_held["tweet_text"].map(clean_text)
    y_test = test_held["class_label"]

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)

    confidence = probabilities.max(axis=1)
    correct = predictions == y_test.to_numpy()

    accepted = confidence >= review_threshold
    coverage = float(accepted.mean())

    if accepted.any():
        accepted_risk = float(
            1.0 - correct[accepted].mean()
        )
    else:
        accepted_risk = 0.0

    review_rate = float(1.0 - coverage)

    heldout_log_loss = float(
        log_loss(
            y_test,
            probabilities,
            labels=LABEL_ORDER,
        )
    )

    heldout_ece, ece_bins = compute_expected_calibration_error(
        probabilities,
        y_test,
        predictions,
        n_bins=int(frozen["ece_bins"]),
    )

    prediction_frame = pd.DataFrame(
        {
            "true_label": y_test.to_numpy(),
            "predicted_label": predictions,
            "confidence": confidence,
            "needs_review": confidence < review_threshold,
        }
    )

    for index, label in enumerate(LABEL_ORDER):
        prediction_frame[f"prob_{label}"] = probabilities[:, index]

    prediction_frame.to_csv(
        OUTPUT_DIR / "heldout_predictions.csv",
        index=False,
    )

    protocol_record = {
        "protocol_name": "team_agreed_13_event_single_holdout",
        "held_out_event": HELD_OUT_EVENT,
        "events": CROSS_EVENT_EVENTS,
        "n_events": len(CROSS_EVENT_EVENTS),
        "full_13_event_rows": {
            "train": int(len(train_full)),
            "dev": int(len(dev_full)),
            "test": int(len(test_full)),
        },
        "cross_event_rows": {
            "train_after_holdout": int(len(train_xev)),
            "dev_after_holdout": int(len(dev_xev)),
            "heldout_test": int(len(test_held)),
        },
        "training_policy": {
            "training_data": (
                "train splits from the 12 non-held-out events only"
            ),
            "dev_used_for_tuning": False,
            "configuration": frozen["configuration"],
        },
        "review_policy": {
            "threshold_source": (
                "frozen official-split validation threshold"
            ),
            "review_threshold": review_threshold,
            "target_risk": float(frozen["target_risk"]),
        },
        "heldout_probability_metrics": {
            "log_loss": heldout_log_loss,
            "expected_calibration_error": float(heldout_ece),
            "ece_bins": int(frozen["ece_bins"]),
            "ece_method": frozen["ece_method"],
        },
        "heldout_selective_prediction": {
            "coverage": coverage,
            "risk": accepted_risk,
            "review_rate": review_rate,
            "auto_accepted": int(accepted.sum()),
            "needs_review": int((~accepted).sum()),
        },
        "training_runtime_seconds": float(training_runtime),
        "model_class_order": model_class_order,
        "shared_evaluator_summary": summary,
    }

    (
        OUTPUT_DIR / "cross_event_details.json"
    ).write_text(
        json.dumps(protocol_record, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Member 2 cross-event evaluation complete.")
    print(f"Events in protocol:       {len(CROSS_EVENT_EVENTS)}")
    print(f"Held-out event:           {HELD_OUT_EVENT}")
    print(f"Training rows:            {len(train_xev):,}")
    print(f"Validation rows unused:   {len(dev_xev):,}")
    print(f"Held-out test rows:       {len(test_held):,}")
    print(f"Training runtime:         {training_runtime:.2f}s")
    print(
        "Held-out macro-F1:       "
        f"{summary['macro_f1']['mean']:.4f}"
    )
    print(
        "Held-out balanced acc:   "
        f"{summary['balanced_accuracy']['mean']:.4f}"
    )
    print(f"Held-out log loss:        {heldout_log_loss:.4f}")
    print(f"Held-out ECE:             {heldout_ece:.4f}")
    print(f"Coverage:                 {coverage:.2%}")
    print(f"Accepted risk:            {accepted_risk:.4f}")
    print(f"Review rate:              {review_rate:.2%}")
    print(f"Saved outputs:            {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
