"""One-shot official HumAID test evaluation for the frozen Member 2 baseline."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
)
from sklearn.pipeline import FeatureUnion, Pipeline

from models.text_baseline.baseline import LABEL_ORDER, clean_text
from models.text_baseline.train import compute_expected_calibration_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAID_DIR = PROJECT_ROOT / "data" / "raw" / "humaid"

RESULTS_DIR = PROJECT_ROOT / "outputs" / "results" / "baseline"
PREDICTIONS_DIR = PROJECT_ROOT / "outputs" / "predictions" / "baseline"

FROZEN_VALIDATION_PATH = RESULTS_DIR / "selected_validation.json"
FINAL_TEST_RESULT_PATH = RESULTS_DIR / "final_test.json"
FINAL_TEST_PREDICTIONS_PATH = (
    PREDICTIONS_DIR / "test_predictions.csv"
)

TRAIN_PATH = HUMAID_DIR / "train-00000-of-00001.parquet"
TEST_PATH = HUMAID_DIR / "test-00000-of-00001.parquet"

EXPECTED_TRAIN_ROWS = 53_531
EXPECTED_TEST_ROWS = 15_160

REQUIRED_COLUMNS = {
    "tweet_text",
    "class_label",
}

EXPECTED_MODEL_NAME = "word_char_tfidf_logistic_regression"
EXPECTED_C = 1.0
EXPECTED_CLASS_WEIGHT = None
EXPECTED_SOLVER = "lbfgs"
EXPECTED_MAX_ITER = 1000
EXPECTED_RANDOM_STATE = 42

EXPECTED_WORD_CONFIG = {
    "analyzer": "word",
    "ngram_range": [1, 2],
    "min_df": 5,
    "max_features": 12_000,
    "sublinear_tf": True,
}

EXPECTED_CHAR_CONFIG = {
    "analyzer": "char",
    "ngram_range": [3, 5],
    "min_df": 10,
    "max_features": 16_000,
    "sublinear_tf": True,
}


def load_frozen_validation_record() -> dict:
    """Load and verify the committed pre-test freeze record."""
    if not FROZEN_VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "Frozen validation record is missing: "
            f"{FROZEN_VALIDATION_PATH}"
        )

    record = json.loads(
        FROZEN_VALIDATION_PATH.read_text(encoding="utf-8")
    )

    if record.get("model") != EXPECTED_MODEL_NAME:
        raise ValueError(
            "Frozen model name does not match the final-test runner."
        )

    if record.get("evaluation_split") != "validation":
        raise ValueError(
            "Frozen selection record must come from validation."
        )

    config = record.get("configuration", {})

    if config.get("word_tfidf") != EXPECTED_WORD_CONFIG:
        raise ValueError("Frozen word TF-IDF configuration mismatch.")

    if config.get("char_tfidf") != EXPECTED_CHAR_CONFIG:
        raise ValueError("Frozen character TF-IDF configuration mismatch.")

    if config.get("classifier") != "LogisticRegression":
        raise ValueError("Frozen classifier mismatch.")

    if config.get("C") != EXPECTED_C:
        raise ValueError("Frozen Logistic Regression C mismatch.")

    if config.get("class_weight") is not EXPECTED_CLASS_WEIGHT:
        raise ValueError("Frozen class_weight mismatch.")

    if config.get("solver") != EXPECTED_SOLVER:
        raise ValueError("Frozen solver mismatch.")

    if config.get("max_iter") != EXPECTED_MAX_ITER:
        raise ValueError("Frozen max_iter mismatch.")

    if config.get("random_state") != EXPECTED_RANDOM_STATE:
        raise ValueError("Frozen random_state mismatch.")

    if record.get("additional_calibration_applied") is not False:
        raise ValueError(
            "Frozen probability decision mismatch: "
            "expected native Logistic Regression probabilities."
        )

    if (
        record.get("probability_method")
        != "native_logistic_regression_predict_proba"
    ):
        raise ValueError("Frozen probability method mismatch.")

    if record.get("confidence_definition") != "max_predict_proba":
        raise ValueError("Frozen confidence definition mismatch.")

    review_threshold = record.get("review_threshold")
    if not isinstance(review_threshold, (int, float)):
        raise ValueError("Frozen review threshold is missing.")

    return record


def load_split(path: Path, expected_rows: int, split_name: str) -> pd.DataFrame:
    """Load one official HumAID split and validate its data contract."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing HumAID {split_name} split: {path}"
        )

    frame = pd.read_parquet(path)

    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"{split_name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if len(frame) != expected_rows:
        raise ValueError(
            f"Unexpected {split_name} row count: "
            f"expected {expected_rows:,}, got {len(frame):,}"
        )

    observed_labels = set(frame["class_label"].dropna().unique())
    expected_labels = set(LABEL_ORDER)

    if observed_labels != expected_labels:
        missing_labels = sorted(expected_labels - observed_labels)
        unexpected_labels = sorted(observed_labels - expected_labels)
        raise ValueError(
            f"Label mismatch in {split_name}. "
            f"Missing={missing_labels}; unexpected={unexpected_labels}"
        )

    if frame["tweet_text"].isna().any():
        raise ValueError(
            f"{split_name} contains missing tweet_text values."
        )

    if frame["class_label"].isna().any():
        raise ValueError(
            f"{split_name} contains missing class_label values."
        )

    return frame


def build_frozen_model() -> Pipeline:
    """Build the exact model frozen before official test access."""
    features = FeatureUnion(
        transformer_list=[
            (
                "word_tfidf",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=5,
                    max_features=12_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "char_tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(3, 5),
                    min_df=10,
                    max_features=16_000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )

    return Pipeline(
        steps=[
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    C=EXPECTED_C,
                    class_weight=EXPECTED_CLASS_WEIGHT,
                    solver=EXPECTED_SOLVER,
                    max_iter=EXPECTED_MAX_ITER,
                    random_state=EXPECTED_RANDOM_STATE,
                ),
            ),
        ]
    )


def build_prediction_frame(
    test_frame: pd.DataFrame,
    predictions,
    probabilities,
    confidence,
    needs_review,
) -> pd.DataFrame:
    """Assemble official-test predictions in canonical label order."""
    prediction_frame = pd.DataFrame(
        {
            "row_index": test_frame.index.to_numpy(),
            "true_label": test_frame["class_label"].to_numpy(),
            "predicted_label": predictions,
        }
    )

    for index, label in enumerate(LABEL_ORDER):
        prediction_frame[f"prob_{label}"] = probabilities[:, index]

    prediction_frame["confidence"] = confidence
    prediction_frame["needs_review"] = needs_review

    return prediction_frame


def main() -> None:
    """Run the frozen baseline on the official test split exactly once."""
    if FINAL_TEST_RESULT_PATH.exists():
        raise FileExistsError(
            "Official-test result already exists. "
            "Refusing to overwrite or rerun the frozen test evaluation: "
            f"{FINAL_TEST_RESULT_PATH}"
        )

    if FINAL_TEST_PREDICTIONS_PATH.exists():
        raise FileExistsError(
            "Official-test predictions already exist. "
            "Refusing to overwrite or rerun the frozen test evaluation: "
            f"{FINAL_TEST_PREDICTIONS_PATH}"
        )

    frozen_record = load_frozen_validation_record()
    review_threshold = float(frozen_record["review_threshold"])

    train_frame = load_split(
        TRAIN_PATH,
        EXPECTED_TRAIN_ROWS,
        "train",
    )
    test_frame = load_split(
        TEST_PATH,
        EXPECTED_TEST_ROWS,
        "test",
    )

    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    x_test = test_frame["tweet_text"].map(clean_text)
    y_test = test_frame["class_label"]

    model = build_frozen_model()

    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_runtime = perf_counter() - training_start

    model_class_order = model.named_steps[
        "classifier"
    ].classes_.tolist()

    if model_class_order != LABEL_ORDER:
        raise ValueError(
            "Fitted model class order does not match canonical LABEL_ORDER."
        )

    inference_start = perf_counter()
    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)
    inference_runtime = perf_counter() - inference_start

    evaluation_start = perf_counter()

    accuracy = float(
        (y_test.to_numpy() == predictions).mean()
    )

    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_test,
        predictions,
    )

    report = classification_report(
        y_test,
        predictions,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=LABEL_ORDER,
    )

    test_log_loss = log_loss(
        y_test,
        probabilities,
        labels=LABEL_ORDER,
    )

    test_ece, ece_bin_data = compute_expected_calibration_error(
        probabilities,
        y_test,
        predictions,
        n_bins=int(frozen_record["ece_bins"]),
    )

    confidence = probabilities.max(axis=1)
    correct_mask = predictions == y_test.to_numpy()

    accepted_mask = confidence >= review_threshold
    test_coverage = float(accepted_mask.mean())

    if accepted_mask.any():
        test_risk = float(
            1.0 - correct_mask[accepted_mask].mean()
        )
    else:
        test_risk = 0.0

    test_review_rate = float(1.0 - test_coverage)
    needs_review = confidence < review_threshold

    probability_row_sums = probabilities.sum(axis=1)

    evaluation_runtime = perf_counter() - evaluation_start

    result = {
        "model": EXPECTED_MODEL_NAME,
        "experiment_stage": "final_official_test",
        "evaluation_split": "test",
        "train_rows": int(len(train_frame)),
        "test_rows": int(len(test_frame)),
        "frozen_from": str(
            FROZEN_VALIDATION_PATH.relative_to(PROJECT_ROOT)
        ),
        "configuration": frozen_record["configuration"],
        "probability_calibration_assessed": True,
        "additional_calibration_applied": False,
        "probability_method": (
            "native_logistic_regression_predict_proba"
        ),
        "confidence_definition": "max_predict_proba",
        "review_threshold": review_threshold,
        "target_risk": float(frozen_record["target_risk"]),
        "accuracy": accuracy,
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "log_loss": float(test_log_loss),
        "expected_calibration_error": float(test_ece),
        "ece_bins": int(frozen_record["ece_bins"]),
        "ece_method": frozen_record["ece_method"],
        "ece_bin_data": ece_bin_data,
        "test_coverage": test_coverage,
        "test_risk": test_risk,
        "test_review_rate": test_review_rate,
        "auto_accepted": int(accepted_mask.sum()),
        "needs_review": int(needs_review.sum()),
        "training_runtime_seconds": float(training_runtime),
        "inference_runtime_seconds": float(inference_runtime),
        "evaluation_runtime_seconds": float(evaluation_runtime),
        "probability_row_sum_min": float(
            probability_row_sums.min()
        ),
        "probability_row_sum_max": float(
            probability_row_sums.max()
        ),
        "label_order": LABEL_ORDER,
        "model_class_order": model_class_order,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    prediction_frame = build_prediction_frame(
        test_frame,
        predictions,
        probabilities,
        confidence,
        needs_review,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    FINAL_TEST_RESULT_PATH.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    prediction_frame.to_csv(
        FINAL_TEST_PREDICTIONS_PATH,
        index=False,
    )

    print("Official test evaluation complete.")
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Macro-F1:            {macro_f1:.4f}")
    print(f"Balanced accuracy:   {balanced_accuracy:.4f}")
    print(f"Log loss:            {test_log_loss:.4f}")
    print(f"ECE:                 {test_ece:.4f}")
    print(f"Review threshold:    {review_threshold:.6f}")
    print(f"Test coverage:       {test_coverage:.2%}")
    print(f"Test risk:           {test_risk:.4f}")
    print(f"Test review rate:    {test_review_rate:.2%}")
    print(f"Auto-accepted:       {int(accepted_mask.sum()):,}")
    print(f"Needs review:        {int(needs_review.sum()):,}")
    print(f"Saved result:        {FINAL_TEST_RESULT_PATH}")
    print(
        "Saved predictions:   "
        f"{FINAL_TEST_PREDICTIONS_PATH}"
    )


if __name__ == "__main__":
    main()
