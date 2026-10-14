# Cross-Event Evaluation Harness

Owner: Member 4. Consumers: Members 2 and 3.

This folder provides shared data loading, metrics and output formats for
event-based evaluation. The command-line entry point uses the mock classifier
for a quick check that does not require a trained model.

## What the evaluator does

For each `<event>__test.json` under `--events-dir`:

1. Loads the file into a DataFrame of `(tweet_text, class_label)`.
2. Calls the classifier on every row's text, collects `predicted_label`.
3. Computes per-label precision/recall/F1/support, macro-F1, balanced
   accuracy and a 10x10 confusion matrix.

Then it writes:

```
<out-dir>/
├── per_event_metrics.csv      event, n_examples, macro_f1, balanced_accuracy, runtime_seconds
├── per_label_metrics.csv      event, label, precision, recall, f1, support (long format)
├── confusion_<event>.csv      one 10x10 matrix per event (rows=true, cols=pred)
├── summary.json               mean/min/max across events + low-support flags
└── run_log.json               model_name, events_evaluated, total_runtime_seconds
```

The evaluator calls a supplied classifier as-is and does not train it.

## Quick smoke run

```bash
uv run python -m evaluation.cross_event \
    --model mock \
    --events-dir data/raw/humaid_events \
    --out-dir outputs/results/cross_event/mock
```

`data/raw/humaid_events/` must exist. The EDA notebook
(`notebooks/01_crisis_eda.ipynb`) downloads it.

## Final shared stress test

The final experiment uses the 13-event `events_set1_47K` subset. Cyclone Idai
is removed before training, the models train on the other 12 events, and the
779 `cyclone_idai_2019` test messages form the unseen-event test set.

- Member 2: `models/text_baseline/cross_event.py`
- Member 3: `notebooks/member3/nb3_cross_event_with output.ipynb`
- Saved results: `outputs/results/cross_event/baseline/` and
  `outputs/results/cross_event/transformer/`

This is a focused stress test on one held-out event.

## What the shared `classify(text)` interface requires

```python
from app.backend.schemas import Prediction

class MyClassifier:
    def classify(self, text: str) -> Prediction | dict: ...
```

`Prediction` carries `predicted_label`, `probabilities` (all 10 labels in
alphabetical order), `confidence`, `model_version`, `needs_review`.
The dictionary form uses the same fields. See
`app/backend/ports/classifier.py` for an example.

## Smoke test

```bash
uv run pytest tests/test_cross_event.py -v
```

Uses a synthetic 3-event fixture under `tmp_path`; no HumAID download
required.
