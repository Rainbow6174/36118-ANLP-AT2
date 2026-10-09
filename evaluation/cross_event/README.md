# Cross-Event Evaluation Harness

Owner: Member 4. Consumers: Members 2 and 3.

This folder provides reusable loading, metric and output functions for
event-based evaluation. The command-line example runs the mock classifier over
all event test files. The final Member 2 and Member 3 experiments use their own
training code because the held-out event must be removed before training.

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

The generic evaluator calls a classifier **as-is** and does not train it. It is
useful for checking a packaged model on a set of event files, but a model that
has already seen an event during training is not evidence of unseen-event
performance.

## Running against the mock model

```
python -m evaluation.cross_event \
    --model mock \
    --events-dir data/raw/humaid_events \
    --out-dir outputs/results/cross_event/mock
```

`data/raw/humaid_events/` must exist. The EDA notebook
(`notebooks/01_crisis_eda.ipynb`) downloads it.

## Final shared stress test

The final comparison uses the 13-event `events_set1_47K` subset. It removes
`cyclone_idai_2019` from training and validation, trains on the other 12 events
and evaluates on the held-out event's 779 test messages.

- Member 2 runs `models/text_baseline/cross_event.py`. Its saved results are in
  `outputs/results/cross_event/baseline/`.
- Member 3's run is recorded in
  `notebooks/member3/nb3_cross_event_with output.ipynb`. Its saved results are
  in `outputs/results/cross_event/transformer/`.
- Both use the same ten-label metrics and output conventions supplied here.

This is a focused distribution-shift test on one held-out event. It should not
be described as proof that the model is robust to every unseen disaster.

## What the shared `classify(text)` interface requires

```python
from app.backend.schemas import Prediction

class MyClassifier:
    def classify(self, text: str) -> Prediction | dict: ...
```

`Prediction` carries `predicted_label`, `probabilities` (all 10 labels in
alphabetical order), `confidence`, `model_version`, `needs_review`.
The evaluator validates either a `Prediction` object or the documented
JSON-like dictionary. See `app/backend/ports/classifier.py` for a worked
example.

## Smoke test

```
uv run pytest tests/test_cross_event.py -v
```

Uses a synthetic 3-event fixture under `tmp_path`; no HumAID download
required.
