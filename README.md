# VarietyLens EDA Handoff

This repository is a small handoff package for the team. Start with this README, run the notebook once, then read `LATER_PLAN.md` before choosing or continuing a modelling role.

The repository contains only four files:

- `README.md` — where to start and where every output goes
- `requirements.txt` — Python packages needed by the notebook
- `eda.ipynb` — data download, preparation, validation and EDA in one place
- `LATER_PLAN.md` — what the results mean and what each role should do next

## 1. Install the packages

From the repository folder, run:

```bash
python -m pip install -r requirements.txt
```

Python 3.10 or newer is recommended.

## 2. Get the BESSTIE data

You normally do not need to download anything by hand. When `eda.ipynb` runs, it looks for these six files:

```text
data/raw/besstie/
├── en_AU/
│   ├── train.csv
│   └── validation.csv
├── en_IN/
│   ├── train.csv
│   └── validation.csv
└── en_UK/
    ├── train.csv
    └── validation.csv
```

If a file is missing, the notebook downloads it from the official [BESSTIE Hugging Face repository](https://huggingface.co/datasets/unswnlporg/BESSTIE). If you already have the files, place them in the paths above and the notebook will use the local copies.

## 3. Run the notebook

Start Jupyter from the repository folder:

```bash
jupyter lab
```

Open `eda.ipynb` and choose **Run All Cells**. Run the whole notebook from top to bottom; later cells use the fixed splits and tables created near the beginning.

The notebook does all shared data work:

1. finds or downloads the six source files;
2. checks their columns and labels;
3. keeps wording, spelling, case, punctuation and emoji while cleaning whitespace;
4. removes exact/case-only duplicates and records every removal;
5. creates fixed train, validation and held-out test splits;
6. validates IDs, labels and split separation;
7. writes task-ready CSV files;
8. creates the EDA tables and figures.

The official BESSTIE validation files become the project test set because the official test set is not public. The project validation set is a fixed 15% stratified part of official train, using seed `36118`. Do not use the project test set to choose a model, feature or threshold.

## 4. Find the prepared data

After the notebook finishes, shared data is under:

```text
outputs/processed/
```

The main files are:

```text
outputs/processed/dataset_v1.csv
outputs/processed/train.csv
outputs/processed/validation.csv
outputs/processed/test.csv
outputs/processed/quality_report.json
outputs/processed/validation_report.json
outputs/processed/audit/removed_rows.csv
```

Each modelling role should use its own task folder:

| Work | Read these files |
| --- | --- |
| English-variety modelling | `outputs/processed/by_task/variety/` |
| Sentiment modelling | `outputs/processed/by_task/sentiment/` |
| Sarcasm modelling | `outputs/processed/by_task/sarcasm/` |

Each task folder contains `train.csv`, `validation.csv` and `test.csv`, with the same columns:

```text
id,text,variety,source,label
```

Keep `id` in prediction files. Evaluation should join predictions to labels by `id`, not row order. A model may apply its own tokenizer or feature extraction, but it should not rewrite these shared CSV files.

## 5. Find the EDA results

All tables and figures are saved under:

```text
outputs/eda/
```

Important files include:

- `label_balance_by_split.csv`
- `variety_source_sample_counts.csv`
- `text_length_distribution_summary.csv`
- `top_keywords_by_variety_source_train_only.csv`
- `top_character_ngrams_by_variety_train_only.csv`
- `source_diagnostic_validation_report.csv`
- `sarcasm_distribution_by_split_variety_source.csv`
- `sarcasm_segment_support_recommendations.csv`
- `figures/`

## 6. Before starting later work

Read `LATER_PLAN.md`. It explains the six separate work packages, shared prediction format, evaluation rules and user-testing plan.

The sarcasm role should pay particular attention to the Google data:

- Google has only 88 sarcastic examples in the prepared dataset.
- `en-UK Google` has one positive example in train and none in validation or test.
- `en-IN Google` is also sparse.
- Use a shared sarcasm model instead of separate models for these segments.
- Compare an ordinary baseline with class weighting, using training data only.
- Choose thresholds on validation only.
- Report unsupported positive-class metrics as `N/A`, not zero.
- Pass limited-evidence information to the application so uncertain cases can go to human review.

The full instructions and reasons are in the **Sarcasm modelling** section of `LATER_PLAN.md`.

## Local files

The `data/` and `outputs/` folders are created locally and are not part of the four-file handoff. They should not be committed to this repository.
