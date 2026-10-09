"""Contextual (Transformer) model wrapper for CrisisLens.

Reads the nested metadata.json schema (deployment_model + analysis_model +
canonical_label_order) that the repo already uses.

Public surface agreed with M4 (frozen contract — matches repo README):

    from models.transformer import load_model
    clf = load_model(model_dir="models/transformer/")
    out = clf.classify(text)
    # out = {
    #   "predicted_label":  str,
    #   "probabilities":    dict[str, float],   # all labels, keyed by name
    #   "confidence":       float,              # max calibrated probability
    #   "model_version":    str,
    #   "needs_review":     bool,               # confidence < frozen tau
    # }

The wrapper is predict-only. It never touches a database or shared state.
Temperature scaling and the review threshold come from
deployment_model.temperature_T and deployment_model.review_threshold_tau.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Union

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class ContextualClassifier:
    """Fine-tuned transformer + temperature scaling + frozen review threshold."""

    def __init__(
        self,
        model,
        tokenizer,
        label_order: List[str],
        temperature: float,
        review_threshold: float,
        model_version: str,
        max_length: int = 128,
        device: str = None,
    ):
        if temperature <= 0:
            raise ValueError(f"temperature must be > 0, got {temperature}")
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError(
                f"review_threshold must be in [0, 1], got {review_threshold}"
            )
        if len(label_order) != len(set(label_order)):
            raise ValueError("label_order contains duplicates")

        self.model = model
        self.tokenizer = tokenizer
        self.label_order = list(label_order)
        self.temperature = float(temperature)
        self.review_threshold = float(review_threshold)
        self.model_version = str(model_version)
        self.max_length = int(max_length)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def _probs_to_dict(self, probs: List[float]) -> Dict[str, float]:
        if len(probs) != len(self.label_order):
            raise RuntimeError(
                f"Model output size {len(probs)} does not match "
                f"label_order length {len(self.label_order)}. "
                f"Check that metadata.canonical_label_order matches the "
                f"trained classification head."
            )
        return {label: float(p) for label, p in zip(self.label_order, probs)}

    @torch.no_grad()
    def classify(self, text: str) -> Dict:
        """Classify one text. Returns the frozen contract dict."""
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")

        enc = self.tokenizer(
            text,
            truncation=True,
            padding=False,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)
        logits = self.model(**enc).logits.squeeze(0)
        probs = F.softmax(logits / self.temperature, dim=-1).cpu().tolist()

        prob_dict = self._probs_to_dict(probs)
        predicted_label = max(prob_dict, key=prob_dict.get)
        confidence = float(prob_dict[predicted_label])
        return {
            "predicted_label": predicted_label,
            "probabilities": prob_dict,
            "confidence": confidence,
            "model_version": self.model_version,
            "needs_review": bool(confidence < self.review_threshold),
        }

    @torch.no_grad()
    def classify_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict]:
        """Batch convenience; same contract per element."""
        if not texts:
            return []
        results: List[Dict] = []
        for start in range(0, len(texts), batch_size):
            chunk = texts[start : start + batch_size]
            enc = self.tokenizer(
                chunk,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            batch_probs = F.softmax(
                self.model(**enc).logits / self.temperature, dim=-1
            ).cpu().tolist()
            for probs in batch_probs:
                prob_dict = self._probs_to_dict(probs)
                predicted_label = max(prob_dict, key=prob_dict.get)
                confidence = float(prob_dict[predicted_label])
                results.append(
                    {
                        "predicted_label": predicted_label,
                        "probabilities": prob_dict,
                        "confidence": confidence,
                        "model_version": self.model_version,
                        "needs_review": bool(confidence < self.review_threshold),
                    }
                )
        return results


def _compose_version(meta: dict) -> str:
    """Build a readable model_version string from the nested metadata."""
    top = meta.get("model_version", "unknown")
    dep = meta.get("deployment_model", {})
    enc = dep.get("encoder_id", "model").split("/")[-1]
    rid = dep.get("run_id", "")
    seed = dep.get("seed", "")
    parts = [top, enc]
    if rid:
        parts.append(str(rid))
    if seed != "":
        parts.append(f"s{seed}")
    return "_".join(parts)


def load_model(
    model_dir: Union[str, Path] = "models/transformer/",
    device: str = None,
) -> ContextualClassifier:
    """Load the packaged contextual (deployment) model.

    `model_dir` must contain the HuggingFace save_pretrained files
    (config.json, model.safetensors, tokenizer files) plus a nested
    metadata.json with:

      - canonical_label_order (list[str])
      - deployment_model.temperature_T (float, > 0)
      - deployment_model.review_threshold_tau (float, in [0, 1])
      - training_config.max_seq_length (int, optional, default 128)
      - model_version (str, top level)
    """
    model_dir = Path(model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"model_dir does not exist: {model_dir}")

    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.json not found in {model_dir}")
    with meta_path.open() as f:
        meta = json.load(f)

    try:
        label_order = meta["canonical_label_order"]
        dep = meta["deployment_model"]
        temperature = dep["temperature_T"]
        review_threshold = dep["review_threshold_tau"]
    except KeyError as e:
        raise KeyError(
            f"metadata.json missing required field: {e}. Expected nested "
            f"schema with canonical_label_order and deployment_model.* keys."
        )

    max_length = int(
        meta.get("training_config", {}).get("max_seq_length", 128)
    )

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))

    return ContextualClassifier(
        model=model,
        tokenizer=tokenizer,
        label_order=label_order,
        temperature=temperature,
        review_threshold=review_threshold,
        model_version=_compose_version(meta),
        max_length=max_length,
        device=device,
    )


__all__ = ["load_model", "ContextualClassifier"]
