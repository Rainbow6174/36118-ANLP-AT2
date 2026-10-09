"""Package the frozen CrisisLens Member 2 text baseline."""

from __future__ import annotations

import json
from pathlib import Path

import joblib

from models.text_baseline.baseline import LABEL_ORDER, clean_text
from models.text_baseline.final_test import (
    EXPECTED_TRAIN_ROWS,
    FINAL_TEST_RESULT_PATH,
    TRAIN_PATH,
    build_frozen_model,
    load_frozen_validation_record,
    load_split,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "text_baseline" / "model.joblib"


def verify_final_test_record(frozen_record: dict) -> dict:
    """Verify the committed final-test record matches the frozen model."""
    if not FINAL_TEST_RESULT_PATH.exists():
        raise FileNotFoundError(
            "Final-test result is missing: "
            f"{FINAL_TEST_RESULT_PATH}"
        )

    final_result = json.loads(
        FINAL_TEST_RESULT_PATH.read_text(encoding="utf-8")
    )

    if final_result.get("experiment_stage") != "final_official_test":
        raise ValueError("Final-test result has an unexpected stage.")

    if final_result.get("evaluation_split") != "test":
        raise ValueError("Final-test result must come from the test split.")

    if final_result.get("configuration") != frozen_record["configuration"]:
        raise ValueError(
            "Final-test configuration does not match frozen validation config."
        )

    if (
        final_result.get("review_threshold")
        != frozen_record["review_threshold"]
    ):
        raise ValueError(
            "Final-test review threshold does not match frozen validation."
        )

    if (
        final_result.get("probability_method")
        != frozen_record["probability_method"]
    ):
        raise ValueError(
            "Final-test probability method does not match frozen validation."
        )

    return final_result


def main() -> None:
    """Fit and save the exact frozen train-only baseline pipeline."""
    if MODEL_PATH.exists():
        raise FileExistsError(
            "Packaged model already exists. Refusing to overwrite it: "
            f"{MODEL_PATH}"
        )

    frozen_record = load_frozen_validation_record()
    final_result = verify_final_test_record(frozen_record)

    train_frame = load_split(
        TRAIN_PATH,
        EXPECTED_TRAIN_ROWS,
        "train",
    )

    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    model = build_frozen_model()
    model.fit(x_train, y_train)

    model_class_order = model.named_steps[
        "classifier"
    ].classes_.tolist()

    if model_class_order != LABEL_ORDER:
        raise ValueError(
            "Fitted model class order does not match canonical LABEL_ORDER."
        )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("Frozen baseline package created.")
    print(f"Model:               {MODEL_PATH}")
    print(f"Train rows:          {len(train_frame):,}")
    print(
        "Validation macro-F1: "
        f"{frozen_record['macro_f1']:.4f}"
    )
    print(
        "Final test macro-F1: "
        f"{final_result['macro_f1']:.4f}"
    )
    print(
        "Review threshold:    "
        f"{frozen_record['review_threshold']:.6f}"
    )
    print(
        "Class order matches: "
        f"{model_class_order == LABEL_ORDER}"
    )


if __name__ == "__main__":
    main()
