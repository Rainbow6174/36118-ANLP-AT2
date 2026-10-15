"""Coverage-risk curve of the deployed DistilBERT on the HumAID validation split.

The released model package contains the weights but not the validation logits, so
this script recomputes them with the same text cleaning as the training notebook
(notebooks/member3/nb1), then repeats the calibration and threshold steps of
notebooks/member3/nb_reconcile_canonical.ipynb:

  * temperature T fitted by negative log-likelihood (bounded search on 0.5-5);
  * tau = first threshold on 1,000 points from 0.5 to 0.999 whose validation
    risk (error rate among accepted messages) is at most 5%.

It checks the results against models/transformer/metadata.json and writes:
  outputs/results/transformer/distilbert_validation_curve.json
  outputs/results/transformer/distilbert_coverage_risk_curve.png

Run from the repository root (CPU takes a few minutes):
    python scripts/distilbert_validation_curve.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.transformer import load_model

VALIDATION = ROOT / "data" / "raw" / "humaid" / "validation-00000-of-00001.parquet"
RESULTS = ROOT / "outputs" / "results" / "transformer"
METADATA = ROOT / "models" / "transformer" / "metadata.json"
TARGET_RISK = 0.05
BATCH_SIZE = 64


def clean_text(text) -> str:
    """Identical to clean_text in notebooks/member3/nb1 (training input)."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "@user", text)
    text = re.sub(r"#", "", text)
    return re.sub(r"\s+", " ", text).strip()


def softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = logits / temperature
    exp = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def nll(temperature: float, logits: np.ndarray, labels: np.ndarray) -> float:
    probs = softmax(logits, temperature)
    return float(-np.log(probs[np.arange(len(labels)), labels] + 1e-12).mean())


@torch.no_grad()
def validation_logits(classifier, texts: list[str]) -> np.ndarray:
    chunks = []
    for start in range(0, len(texts), BATCH_SIZE):
        enc = classifier.tokenizer(
            texts[start : start + BATCH_SIZE],
            truncation=True,
            padding=True,
            max_length=classifier.max_length,
            return_tensors="pt",
        ).to(classifier.device)
        enc.pop("token_type_ids", None)
        chunks.append(classifier.model(**enc).logits.cpu().numpy())
    return np.concatenate(chunks)


def main() -> None:
    meta = json.loads(METADATA.read_text())
    deployed = meta["deployment_model"]
    labels_order = meta["canonical_label_order"]

    data = pd.read_parquet(VALIDATION)
    texts = [clean_text(t) for t in data["tweet_text"]]
    labels = data["class_label"].map({l: i for i, l in enumerate(labels_order)}).to_numpy()

    classifier = load_model()
    started = time.perf_counter()
    logits = validation_logits(classifier, texts)
    seconds = time.perf_counter() - started

    temperature = minimize_scalar(
        lambda t: nll(t, logits, labels), bounds=(0.5, 5), method="bounded"
    ).x
    probs = softmax(logits, temperature)
    confidence = probs.max(axis=1)
    correct = probs.argmax(axis=1) == labels
    tau = next(
        float(t)
        for t in np.linspace(0.5, 0.999, 1000)
        if (confidence >= t).sum() and (1 - correct[confidence >= t]).mean() <= TARGET_RISK
    )
    accepted = confidence >= tau

    grid = np.linspace(0, 1, 200)
    curve = {
        "tau": grid.tolist(),
        "coverage": [float((confidence >= t).mean()) for t in grid],
        "risk": [
            float(1 - correct[confidence >= t].mean()) if (confidence >= t).any() else 0.0
            for t in grid
        ],
    }
    summary = {
        "model_version": classifier.model_version,
        "split": "HumAID official validation",
        "messages": len(labels),
        "validation_macro_f1": None,
        "temperature_T": round(float(temperature), 4),
        "temperature_T_released": deployed["temperature_T"],
        "review_threshold_tau": round(tau, 4),
        "review_threshold_tau_released": deployed["review_threshold_tau"],
        "coverage_at_tau": round(float(accepted.mean()), 4),
        "risk_at_tau": round(float(1 - correct[accepted].mean()), 4),
        "target_risk": TARGET_RISK,
        "inference_seconds_cpu": round(seconds, 1),
    }
    from sklearn.metrics import f1_score

    summary["validation_macro_f1"] = round(
        float(f1_score(labels, probs.argmax(axis=1), average="macro")), 4
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "distilbert_validation_curve.json").write_text(
        json.dumps({"summary": summary, "curve": curve}, indent=2)
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(curve["coverage"], curve["risk"], "b-", linewidth=2)
    ax.axhline(TARGET_RISK, color="red", linestyle="--", alpha=0.7,
               label=f"Target risk = {TARGET_RISK:.0%}")
    ax.axvline(summary["coverage_at_tau"], color="green", linestyle="--", alpha=0.7,
               label=f"Coverage = {summary['coverage_at_tau']:.1%}")
    ax.plot(summary["coverage_at_tau"], summary["risk_at_tau"], "ro", markersize=10,
            label=f"Operating point (tau={summary['review_threshold_tau']:.4f})")
    ax.set_xlabel("Coverage (fraction auto-accepted)")
    ax.set_ylabel("Risk (error rate among accepted)")
    ax.set_title("DistilBERT coverage-risk curve (validation, calibrated)")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, max(curve["risk"]) * 1.1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "distilbert_coverage_risk_curve.png", dpi=180, bbox_inches="tight")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
