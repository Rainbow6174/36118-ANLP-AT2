"""Metric functions used by the cross-event evaluator.

Fixed label order matches app.backend.labels.LABELS. The functions here
compute per-label precision/recall/F1/support, macro-F1, balanced
accuracy and a confusion matrix, all against a known label vocabulary so
labels with zero support in a given event still appear as rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from app.backend.labels import LABELS


@dataclass
class EventMetrics:
    event: str
    n_examples: int
    macro_f1: float
    balanced_accuracy: float
    per_label: pd.DataFrame  # columns: label, precision, recall, f1, support
    confusion: pd.DataFrame  # 10x10, rows=true, cols=pred, in LABELS order
    runtime_seconds: float = 0.0
    extras: dict = field(default_factory=dict)


def compute(
    event: str,
    y_true: Sequence[str],
    y_pred: Sequence[str],
    runtime_seconds: float = 0.0,
) -> EventMetrics:
    """Compute per-label PRF, macro-F1, balanced accuracy, confusion matrix.

    labels=LABELS is passed to every sklearn call so output shape is
    always (10,) / (10,10) regardless of whether a label is absent from
    y_true or y_pred.
    """
    y_true_arr = np.asarray(list(y_true))
    y_pred_arr = np.asarray(list(y_pred))

    if y_true_arr.shape != y_pred_arr.shape:
        raise ValueError(
            f"shape mismatch: y_true={y_true_arr.shape}, "
            f"y_pred={y_pred_arr.shape}"
        )
    if y_true_arr.size == 0:
        raise ValueError(f"event {event!r} has no examples")

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true_arr,
        y_pred_arr,
        labels=list(LABELS),
        zero_division=0,
    )
    macro_f1 = float(
        f1_score(
            y_true_arr,
            y_pred_arr,
            labels=list(LABELS),
            average="macro",
            zero_division=0,
        )
    )
    bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))

    per_label = pd.DataFrame(
        {
            "label": list(LABELS),
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    )

    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=list(LABELS))
    confusion = pd.DataFrame(cm, index=list(LABELS), columns=list(LABELS))
    confusion.index.name = "true"
    confusion.columns.name = "pred"

    return EventMetrics(
        event=event,
        n_examples=int(y_true_arr.size),
        macro_f1=macro_f1,
        balanced_accuracy=bal_acc,
        per_label=per_label,
        confusion=confusion,
        runtime_seconds=runtime_seconds,
    )


def summarise(event_metrics: list[EventMetrics]) -> dict:
    """Mean/min/max of macro-F1 and balanced accuracy across events.

    Also flags events whose minimum per-label support is below 5 as
    low-support warnings.
    """
    if not event_metrics:
        return {
            "n_events": 0,
            "macro_f1": {},
            "balanced_accuracy": {},
            "low_support_events": [],
        }

    f1s = [m.macro_f1 for m in event_metrics]
    bals = [m.balanced_accuracy for m in event_metrics]
    low_support = [
        m.event
        for m in event_metrics
        if int(m.per_label["support"].min()) < 5
    ]
    return {
        "n_events": len(event_metrics),
        "macro_f1": {
            "mean": float(np.mean(f1s)),
            "min": float(np.min(f1s)),
            "max": float(np.max(f1s)),
        },
        "balanced_accuracy": {
            "mean": float(np.mean(bals)),
            "min": float(np.min(bals)),
            "max": float(np.max(bals)),
        },
        "low_support_events": sorted(low_support),
    }
