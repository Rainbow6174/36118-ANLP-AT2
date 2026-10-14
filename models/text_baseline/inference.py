"""Inference wrapper for the packaged CrisisLens text baseline."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib

from models.text_baseline.baseline import LABEL_ORDER, clean_text


MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "model.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"


@lru_cache(maxsize=1)
def _load_artifacts():
    """Load and validate the packaged baseline model and metadata once."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Packaged model not found: {MODEL_PATH}")

    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Model metadata not found: {METADATA_PATH}")

    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    metadata_labels = metadata.get("canonical_label_order")
    if metadata_labels != LABEL_ORDER:
        raise ValueError(
            "Metadata label order does not match canonical LABEL_ORDER."
        )

    model_labels = model.named_steps["classifier"].classes_.tolist()
    if model_labels != LABEL_ORDER:
        raise ValueError(
            "Packaged model class order does not match canonical LABEL_ORDER."
        )

    return model, metadata


def classify(text: object) -> dict:
    """Classify one text using the frozen packaged baseline."""
    model, metadata = _load_artifacts()

    cleaned_text = clean_text(text)

    predicted_label = str(model.predict([cleaned_text])[0])
    probability_values = model.predict_proba([cleaned_text])[0]

    probabilities = {
        label: float(probability_values[index])
        for index, label in enumerate(LABEL_ORDER)
    }

    confidence = float(max(probability_values))
    review_threshold = float(
        metadata["review_policy"]["review_threshold"]
    )

    return {
        "predicted_label": predicted_label,
        "probabilities": probabilities,
        "confidence": confidence,
        "model_version": metadata["model_version"],
        "needs_review": confidence < review_threshold,
    }
