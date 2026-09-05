# Using the Prepared Data

The files in this folder are ready for modelling. No extra deduplication, split creation or label conversion is needed.

## Which files to use

- Sentiment: `by_task/sentiment/train.csv`, `validation.csv`, `test.csv`
- Sarcasm: `by_task/sarcasm/train.csv`, `validation.csv`, `test.csv`
- English variety: `by_task/variety/train.csv`, `validation.csv`, `test.csv`
- Both labels and all metadata: `train.csv`, `validation.csv`, `test.csv`
- One complete file: `dataset_v1.csv`

Every task file has:

```text
id,text,variety,source,label
```

`label` is the target for that folder. For sentiment and sarcasm it is `0` or `1`; for variety it is `en-AU`, `en-IN` or `en-UK`.

Keep `source` and `variety` for result breakdowns and routing experiments. For the main text-only variety classifier, do not feed `source` in as a feature; otherwise the model may rely on the Google/Reddit shortcut found in the EDA.

## A minimal example

```python
import pandas as pd

train = pd.read_csv("data/processed/by_task/variety/train.csv")
validation = pd.read_csv("data/processed/by_task/variety/validation.csv")

X_train = train["text"]
y_train = train["label"]
```

Use train to fit the model and validation to choose settings. Keep test untouched until the final evaluation.

## Joining predictions later

Keep the `id` column in every prediction file. Evaluation should merge predictions and labels by `id`, not by row order.

## What may still happen inside a model

A model can tokenize text, build TF-IDF features or apply a model-specific truncation length. Keep those steps inside the model code and record them in the report. Do not edit the shared CSV files.

## Useful checks and EDA files

- `validation_report.json`: confirms schema, IDs, label values and split separation
- `quality_report.json`: shows row counts and cleaning outcomes
- `audit/removed_rows.csv`: records every removed row and reason
- `../../reports/eda/notebook_outputs/`: label balance, group support, text length, keyword, character n-gram and sarcasm-support tables

The sarcasm model should read `../../reports/eda/notebook_outputs/sarcasm_segment_support_recommendations.csv`. It records the very small Google-positive groups that need shared modelling and cautious evaluation.
