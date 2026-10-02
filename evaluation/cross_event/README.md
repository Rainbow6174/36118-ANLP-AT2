# Cross-Event Evaluation Harness

Owner: Member 4. Consumers: Members 2 and 3.

Evaluates any classifier that implements the shared `classify(text)`
interface against each of the 19 HumAID event test splits, one at a time.
Produces per-event, per-label and summary tables under the chosen
output directory.

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

The classifier is called **as-is**; the evaluator does not train. If the
classifier was trained on all 18 non-held-out events, pass that one
classifier to the run. If each held-out variant is a different model,
register a different name in `__main__._MODEL_REGISTRY` for each.

## Running against the mock model

```
python -m evaluation.cross_event \
    --model mock \
    --events-dir data/raw/humaid_events \
    --out-dir outputs/results/cross_event/mock
```

`data/raw/humaid_events/` must exist. The EDA notebook
(`notebooks/01_crisis_eda.ipynb`) downloads it.

## Adding your model (Members 2 and 3)

1. Package your trained model inside `models/text_baseline/` or
   `models/transformer/` with a loader that returns an object exposing
   `classify(text) -> app.backend.schemas.Prediction`.
2. In `evaluation/cross_event/__main__.py`, register the loader:

   ```python
   def _load_text_baseline():
       from models.text_baseline.loader import load_classifier
       return load_classifier()

   _MODEL_REGISTRY["baseline"] = _load_text_baseline
   ```

3. Run:

   ```
   python -m evaluation.cross_event \
       --model baseline \
       --out-dir outputs/results/cross_event/baseline
   ```

4. Commit the output directory. Member 4 combines the per-model tables
   into the final cross-event comparison.

## What the shared `classify(text)` interface requires

```python
from app.backend.schemas import Prediction

class MyClassifier:
    def classify(self, text: str) -> Prediction: ...
```

`Prediction` carries `predicted_label`, `probabilities` (all 10 labels in
alphabetical order), `confidence`, `model_version`, `needs_review`.
See `app/backend/ports/classifier.py` for a worked example.

## Smoke test

```
.venv/Scripts/python.exe -m pytest tests/test_cross_event.py -v
```

Uses a synthetic 3-event fixture under `tmp_path`; no HumAID download
required.
