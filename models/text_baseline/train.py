"""Training and evaluation entry point for the CrisisLens text baseline."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

from models.text_baseline.baseline import LABEL_ORDER, clean_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAID_DIR = PROJECT_ROOT / "data" / "raw" / "humaid"
RESULTS_DIR = PROJECT_ROOT / "outputs" / "results" / "baseline"

EXPECTED_SPLIT_SIZES = {
    "train": 53_531,
    "validation": 7_793,
}

FINAL_TEST_SIZE = 15_160

REQUIRED_COLUMNS = {
    "tweet_text",
    "class_label",
}


def load_humaid_splits() -> dict[str, pd.DataFrame]:
    """Load and validate the official HumAID train/validation/test splits."""
    splits: dict[str, pd.DataFrame] = {}

    for split_name, expected_rows in EXPECTED_SPLIT_SIZES.items():
        path = HUMAID_DIR / f"{split_name}-00000-of-00001.parquet"

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
                f"Missing={missing_labels}; "
                f"unexpected={unexpected_labels}"
            )

        if frame["tweet_text"].isna().any():
            raise ValueError(
                f"{split_name} contains missing tweet_text values."
            )

        if frame["class_label"].isna().any():
            raise ValueError(
                f"{split_name} contains missing class_label values."
            )

        splits[split_name] = frame

    return splits


def evaluate_majority_baseline(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
) -> dict:
    """Evaluate a training-derived majority-class predictor on validation."""
    majority_label = train_frame["class_label"].value_counts().idxmax()

    y_true = validation_frame["class_label"]
    y_pred = [majority_label] * len(validation_frame)

    start = perf_counter()

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(y_true, y_pred)

    report = classification_report(
        y_true,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=LABEL_ORDER,
    )

    elapsed = perf_counter() - start

    accuracy = float((y_true.to_numpy() == majority_label).mean())

    result = {
        "model": "majority_baseline",
        "evaluation_split": "validation",
        "majority_label": majority_label,
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "evaluation_runtime_seconds": float(elapsed),
        "label_order": LABEL_ORDER,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    return result


def evaluate_word_tfidf_linearsvc_screening(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    class_weight: str | None = None,
    C: float = 1.0,
) -> dict:
    """Run an uncalibrated word TF-IDF + LinearSVC validation screen."""
    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    x_validation = validation_frame["tweet_text"].map(clean_text)
    y_validation = validation_frame["class_label"]

    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=5,
                    max_features=12_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LinearSVC(
                    C=C,
                    class_weight=class_weight,
                    dual="auto",
                    random_state=42,
                ),
            ),
        ]
    )

    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_runtime = perf_counter() - training_start

    inference_start = perf_counter()
    y_pred = model.predict(x_validation)
    inference_runtime = perf_counter() - inference_start

    evaluation_start = perf_counter()

    macro_f1 = f1_score(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_validation,
        y_pred,
    )

    report = classification_report(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
    )

    evaluation_runtime = perf_counter() - evaluation_start

    accuracy = float(
        (y_validation.to_numpy() == y_pred).mean()
    )

    result = {
        "model": "word_tfidf_linearsvc",
        "experiment_stage": "validation_screening",
        "calibrated": False,
        "probabilities_available": False,
        "evaluation_split": "validation",
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "configuration": {
            "preprocessing": "models.text_baseline.baseline.clean_text",
            "analyzer": "word",
            "ngram_range": [1, 2],
            "min_df": 5,
            "max_features": 12_000,
            "sublinear_tf": True,
            "classifier": "LinearSVC",
            "C": C,
            "class_weight": class_weight,
            "dual": "auto",
            "random_state": 42,
        },
        "accuracy": accuracy,
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "training_runtime_seconds": float(training_runtime),
        "inference_runtime_seconds": float(inference_runtime),
        "evaluation_runtime_seconds": float(evaluation_runtime),
        "label_order": LABEL_ORDER,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    return result


def evaluate_char_tfidf_linearsvc_screening(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    class_weight: str | None = None,
    C: float = 1.0,
) -> dict:
    """Run an uncalibrated character TF-IDF + LinearSVC validation screen."""
    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    x_validation = validation_frame["tweet_text"].map(clean_text)
    y_validation = validation_frame["class_label"]

    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(3, 5),
                    min_df=10,
                    max_features=16_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LinearSVC(
                    C=C,
                    class_weight=class_weight,
                    dual="auto",
                    random_state=42,
                ),
            ),
        ]
    )

    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_runtime = perf_counter() - training_start

    inference_start = perf_counter()
    y_pred = model.predict(x_validation)
    inference_runtime = perf_counter() - inference_start

    evaluation_start = perf_counter()

    macro_f1 = f1_score(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_validation,
        y_pred,
    )

    report = classification_report(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
    )

    evaluation_runtime = perf_counter() - evaluation_start

    accuracy = float(
        (y_validation.to_numpy() == y_pred).mean()
    )

    result = {
        "model": "char_tfidf_linearsvc",
        "experiment_stage": "validation_screening",
        "calibrated": False,
        "probabilities_available": False,
        "evaluation_split": "validation",
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "configuration": {
            "preprocessing": "models.text_baseline.baseline.clean_text",
            "analyzer": "char",
            "ngram_range": [3, 5],
            "min_df": 10,
            "max_features": 16_000,
            "sublinear_tf": True,
            "classifier": "LinearSVC",
            "C": C,
            "class_weight": class_weight,
            "dual": "auto",
            "random_state": 42,
        },
        "accuracy": accuracy,
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "training_runtime_seconds": float(training_runtime),
        "inference_runtime_seconds": float(inference_runtime),
        "evaluation_runtime_seconds": float(evaluation_runtime),
        "label_order": LABEL_ORDER,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    return result

def evaluate_combined_tfidf_linearsvc_screening(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    class_weight: str | None = None,
    C: float = 0.25,
) -> dict:
    """Run an uncalibrated word+character TF-IDF LinearSVC validation screen."""
    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    x_validation = validation_frame["tweet_text"].map(clean_text)
    y_validation = validation_frame["class_label"]

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

    model = Pipeline(
        steps=[
            ("features", features),
            (
                "classifier",
                LinearSVC(
                    C=C,
                    class_weight=class_weight,
                    dual="auto",
                    random_state=42,
                ),
            ),
        ]
    )

    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_runtime = perf_counter() - training_start

    inference_start = perf_counter()
    y_pred = model.predict(x_validation)
    inference_runtime = perf_counter() - inference_start

    evaluation_start = perf_counter()

    macro_f1 = f1_score(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_validation,
        y_pred,
    )

    report = classification_report(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
    )

    evaluation_runtime = perf_counter() - evaluation_start

    accuracy = float(
        (y_validation.to_numpy() == y_pred).mean()
    )

    result = {
        "model": "word_char_tfidf_linearsvc",
        "experiment_stage": "validation_screening",
        "calibrated": False,
        "probabilities_available": False,
        "evaluation_split": "validation",
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "configuration": {
            "preprocessing": "models.text_baseline.baseline.clean_text",
            "word_tfidf": {
                "analyzer": "word",
                "ngram_range": [1, 2],
                "min_df": 5,
                "max_features": 12_000,
                "sublinear_tf": True,
            },
            "char_tfidf": {
                "analyzer": "char",
                "ngram_range": [3, 5],
                "min_df": 10,
                "max_features": 16_000,
                "sublinear_tf": True,
            },
            "classifier": "LinearSVC",
            "C": C,
            "class_weight": class_weight,
            "dual": "auto",
            "random_state": 42,
        },
        "accuracy": accuracy,
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "training_runtime_seconds": float(training_runtime),
        "inference_runtime_seconds": float(inference_runtime),
        "evaluation_runtime_seconds": float(evaluation_runtime),
        "label_order": LABEL_ORDER,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    return result

def evaluate_combined_tfidf_logreg_screening(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    class_weight: str | None = None,
    C: float = 1.0,
) -> dict:
    """Run a word+character TF-IDF Logistic Regression validation screen."""
    x_train = train_frame["tweet_text"].map(clean_text)
    y_train = train_frame["class_label"]

    x_validation = validation_frame["tweet_text"].map(clean_text)
    y_validation = validation_frame["class_label"]

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

    model = Pipeline(
        steps=[
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    C=C,
                    class_weight=class_weight,
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )

    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_runtime = perf_counter() - training_start

    inference_start = perf_counter()
    y_pred = model.predict(x_validation)
    probabilities = model.predict_proba(x_validation)
    inference_runtime = perf_counter() - inference_start

    evaluation_start = perf_counter()

    macro_f1 = f1_score(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_validation,
        y_pred,
    )

    report = classification_report(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_validation,
        y_pred,
        labels=LABEL_ORDER,
    )

    evaluation_runtime = perf_counter() - evaluation_start

    accuracy = float(
        (y_validation.to_numpy() == y_pred).mean()
    )

    probability_row_sums = probabilities.sum(axis=1)

    result = {
        "model": "word_char_tfidf_logistic_regression",
        "experiment_stage": "validation_screening",
        "calibrated": False,
        "probabilities_available": True,
        "evaluation_split": "validation",
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "configuration": {
            "preprocessing": "models.text_baseline.baseline.clean_text",
            "word_tfidf": {
                "analyzer": "word",
                "ngram_range": [1, 2],
                "min_df": 5,
                "max_features": 12_000,
                "sublinear_tf": True,
            },
            "char_tfidf": {
                "analyzer": "char",
                "ngram_range": [3, 5],
                "min_df": 10,
                "max_features": 16_000,
                "sublinear_tf": True,
            },
            "classifier": "LogisticRegression",
            "C": C,
            "class_weight": class_weight,
            "solver": "lbfgs",
            "max_iter": 1000,
            "random_state": 42,
        },
        "accuracy": accuracy,
        "macro_f1": float(macro_f1),
        "balanced_accuracy": float(balanced_accuracy),
        "training_runtime_seconds": float(training_runtime),
        "inference_runtime_seconds": float(inference_runtime),
        "evaluation_runtime_seconds": float(evaluation_runtime),
        "probability_row_sum_min": float(probability_row_sums.min()),
        "probability_row_sum_max": float(probability_row_sums.max()),
        "label_order": LABEL_ORDER,
        "model_class_order": model.named_steps[
            "classifier"
        ].classes_.tolist(),
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }

    return result

def save_majority_result(result: dict) -> Path:
    """Save the majority validation result as reproducible JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RESULTS_DIR / "majority_validation.json"

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    """Validate HumAID and evaluate the majority reference baseline."""
    splits = load_humaid_splits()

    print(f"Project root: {PROJECT_ROOT}")
    print(f"HumAID directory: {HUMAID_DIR}")
    print()

    for split_name in ("train", "validation"):
        frame = splits[split_name]
        print(
            f"{split_name:<10} "
            f"rows={len(frame):>6,} "
            f"labels={frame['class_label'].nunique()}"
        )

    print()
    print("Canonical label order:")
    for index, label in enumerate(LABEL_ORDER, start=1):
        print(f"{index:>2}. {label}")

    print()
    print("HumAID training/validation data contract validated successfully.")

    majority_result = evaluate_majority_baseline(
        splits["train"],
        splits["validation"],
    )
    result_path = save_majority_result(majority_result)

    print()
    print("Majority baseline — validation")
    print(f"Majority label:      {majority_result['majority_label']}")
    print(f"Accuracy:            {majority_result['accuracy']:.4f}")
    print(f"Macro-F1:            {majority_result['macro_f1']:.4f}")
    print(
        "Balanced accuracy:   "
        f"{majority_result['balanced_accuracy']:.4f}"
    )
    print(f"Saved result:        {result_path}")


if __name__ == "__main__":
    main()