"""The deployed classifier receives text cleaned as in training and evaluation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backend import services
from app.backend.labels import LABEL_SET

ROOT = Path(__file__).resolve().parents[1]


def _training_clean_text():
    """clean_text copied from notebooks/member3/nb1 into the curve script."""
    spec = importlib.util.spec_from_file_location(
        "curve", ROOT / "scripts" / "distilbert_validation_curve.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.clean_text


SAMPLES = [
    "Bridge down on #BallinaRd, see https://t.co/abc123 and www.example.org @SES_NSW",
    "  Need   help at the #school\n@user1 @user2 ",
    "plain text without anything special",
    "#",
]


def test_cleaning_matches_the_training_notebook():
    training = _training_clean_text()
    for text in SAMPLES:
        assert services.clean_for_classifier(text) == training(text)


class RecordingModel:
    model_version = "test-model"

    def __init__(self):
        self.inputs = []

    def classify(self, text):
        self.inputs.append(text)
        probabilities = {label: 0.0 for label in LABEL_SET}
        probabilities["infrastructure_and_utility_damage"] = 1.0
        return {
            "predicted_label": "infrastructure_and_utility_damage",
            "probabilities": probabilities,
            "confidence": 1.0,
            "model_version": self.model_version,
            "needs_review": False,
        }


def test_model_receives_cleaned_text_and_report_keeps_the_original(client, monkeypatch):
    model = RecordingModel()
    monkeypatch.setattr(
        services, "_classifier", services.TransformerClassifierAdapter(model)
    )
    original = "Bridge down on #BallinaRd https://t.co/abc @SES_NSW"

    analysed = client.post("/api/analyse", json={"text": original})

    assert analysed.status_code == 200
    assert model.inputs == ["Bridge down on BallinaRd @user"]
    prediction = analysed.json()["prediction"]
    saved = client.post(
        "/api/reports",
        json={
            "text": original,
            "predicted_label": prediction["predicted_label"],
            "confidence": prediction["confidence"],
            "model_version": prediction["model_version"],
            "needs_review": prediction["needs_review"],
        },
    ).json()
    assert saved["text"] == original
