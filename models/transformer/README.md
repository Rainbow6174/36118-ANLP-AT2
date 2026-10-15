# Contextual classification model

Deployment model is DistilBERT (run A1, seed 42, plain), with its own fitted
temperature T and frozen review threshold tau. The RoBERTa (A4) analysis
model lives in metadata only; it is the report's analysis model, not shipped
in this package. The loader, metadata, config and tokenizer files are tracked
in Git. Download `model.safetensors` from the
[m3-transformer-v2 release](https://github.com/Rainbow6174/36118-ANLP-AT2/releases/tag/m3-transformer-v2)
and place it directly in this folder; no archive needs to be extracted.

## Contents

```
models/transformer/
  __init__.py                    # load_model + ContextualClassifier
  metadata.json                  # nested: deployment_model, analysis_model, canonical_label_order, ...
  config.json                    # HF: model config (DistilBERT, 10-class head)
  model.safetensors              # HF: deployment weights (A1_best), from the release
  tokenizer.json                 # HF: tokenizer
  tokenizer_config.json
```

## Dependencies

```
torch
transformers
```

Pin to whatever the API side already uses to avoid version drift.

## Public contract (matches repo README)

```python
from models.transformer import load_model

clf = load_model(model_dir="models/transformer/")
out = clf.classify("A bridge collapsed near the river, people trapped.")

# out = {
#   "predicted_label":  str,
#   "probabilities":    dict[str, float],   # all 10 labels, keyed by label name
#   "confidence":       float,              # max calibrated probability
#   "model_version":    str,
#   "needs_review":     bool,               # confidence < deployment_model.review_threshold_tau
# }
```

Notes:

- `probabilities` is a dict keyed by label name. The canonical label set is
  `metadata.canonical_label_order` (also exposed as `clf.label_order`); read
  from there rather than hard-coding.
- `confidence` is after temperature scaling (`logits / T` then softmax),
  with `T = deployment_model.temperature_T` from metadata (currently
  1.1017 at seed 42).
- `needs_review` is computed inside the wrapper from the frozen
  `review_threshold_tau` (currently 0.8866, target_risk 0.05); callers do
  not pass a threshold.
- `model_version` is composed from top-level `model_version` + the
  deployment encoder + run id + seed, e.g. `1.1.0_distilbert-base-uncased_A1_s42`.
- Predict-only. The wrapper never touches a database or shared state.
- `classify_batch(texts, batch_size=32)` is available as a convenience,
  same contract per element.

## metadata.json fields the wrapper reads

| Field                                       | Required | Purpose                            |
| ------------------------------------------- | -------- | ---------------------------------- |
| `canonical_label_order`                     | yes      | Index → label name                 |
| `deployment_model.temperature_T`            | yes      | Softmax temperature (> 0)          |
| `deployment_model.review_threshold_tau`     | yes      | Review threshold (in [0, 1])       |
| `training_config.max_seq_length`            | no       | Tokenizer max length (default 128) |
| `model_version` (top level)                 | no       | Prefix of the composed version     |
| `deployment_model.encoder_id` / `run_id` / `seed` | no | Suffix of the composed version     |

Other fields (`analysis_model`, `cross_event`, `training_config.epochs`, ...) are informational — the wrapper does not read them.

## Smoke test

```python
from models.transformer import load_model
clf = load_model()
out = clf.classify("Water levels rising in the valley, evacuation underway.")
assert set(out) == {
    "predicted_label", "probabilities",
    "confidence", "model_version", "needs_review",
}
assert isinstance(out["probabilities"], dict)
assert set(out["probabilities"]) == set(clf.label_order)
assert out["predicted_label"] in clf.label_order
print(out)
```
