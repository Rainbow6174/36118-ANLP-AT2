"""Classifier port. Members 2/3 will supply real implementations later.

The Protocol matches the shared classify(text) contract in README.md.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from ..labels import LABELS
from ..schemas import Prediction

MOCK_REVIEW_THRESHOLD = 0.60


class Classifier(Protocol):
    def classify(self, text: str) -> Prediction: ...


class MockClassifier:
    """Deterministic mock. Same text always returns the same label.

    Hash the text, pick a label from the 10-label list. Assign a peaked
    probability distribution around that label so needs_review can trip
    both ways depending on input length.
    """

    model_version = "mock-v0"

    def classify(self, text: str) -> Prediction:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        idx = digest[0] % len(LABELS)
        peak_label = LABELS[idx]

        # Confidence: text length modulates peak between 0.45 and 0.90.
        length_signal = min(len(text), 200) / 200.0
        peak = 0.45 + 0.45 * length_signal

        remaining = 1.0 - peak
        others = remaining / (len(LABELS) - 1)
        probabilities = {label: others for label in LABELS}
        probabilities[peak_label] = peak

        return Prediction(
            predicted_label=peak_label,
            probabilities=probabilities,
            confidence=peak,
            model_version=self.model_version,
            needs_review=peak < MOCK_REVIEW_THRESHOLD,
        )
