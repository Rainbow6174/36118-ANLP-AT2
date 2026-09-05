# VarietyLens EDA Handoff

This repository is a small handoff package for the team. Start with this README, run the notebook once, then read `LATER_PLAN.md` before choosing or continuing a modelling role.

The starting handoff contains four files:

- `README.md` — where to start and where every output goes
- `requirements.txt` — Python packages needed by the notebook
- `eda.ipynb` — data download, preparation, validation and EDA in one place
- `LATER_PLAN.md` — what the results mean and the next work for each role

## 1. Install the packages

From the repository folder, run:

```bash
python -m pip install -r requirements.txt
```

Python 3.10 or newer is recommended.

## 2. Get the BESSTIE data

The notebook handles downloading automatically. When `eda.ipynb` runs, it first looks for these six local files:

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

The public BESSTIE release provides train and validation files. This project reserves the official validation files as its held-out test set. A fixed 15% stratified part of official train becomes project validation, using seed `36118`. Model and threshold choices come from train and project validation; the held-out test supports one final evaluation.

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

Each modelling role uses its own task folder:

| Work | Read these files |
| --- | --- |
| English-variety modelling | `outputs/processed/by_task/variety/` |
| Sentiment modelling | `outputs/processed/by_task/sentiment/` |
| Sarcasm modelling | `outputs/processed/by_task/sarcasm/` |

Each task folder contains `train.csv`, `validation.csv` and `test.csv`, with the same columns:

```text
id,text,variety,source,label
```

Keep `id` in prediction files so evaluation can join each prediction to its label. Apply model-specific tokenisation or feature extraction inside the model code and keep the shared CSV files unchanged.

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

The sarcasm role uses the following Google-data findings:

- Google has only 88 sarcastic examples in the prepared dataset.
- `en-UK Google` has one positive example in train and none in validation or test.
- `en-IN Google` is also sparse.
- Use one shared sarcasm model across all varieties and sources.
- Compare an ordinary baseline with class weighting, using training data only.
- Choose thresholds on validation only.
- Use `N/A` for positive-class metrics when the subgroup contains zero positive examples.
- Pass limited-evidence information to the application so uncertain cases can go to human review.

The full instructions and reasons are in the **Sarcasm modelling** section of `LATER_PLAN.md`.

## 7. What the team keeps on GitHub

The starting EDA handoff stays small because the notebook can rebuild its data outputs quickly. Keep these generated materials on each person's computer:

- `data/` — downloaded BESSTIE source files
- `outputs/processed/` — cleaned data, fixed splits and task CSV files
- `outputs/eda/` — generated EDA tables and figures
- notebook caches, temporary files and exploratory checkpoints

The data preparation logic remains inside `eda.ipynb`, so every person can recreate the same files by running the notebook from the top.

Later modelling work adds useful, reusable project files to GitHub. Each modelling role uploads:

- training and inference code;
- the final configuration and random seed;
- the selected model artefact needed by evaluation or the application;
- validation and final test predictions with `id` and probabilities;
- validation and test metric tables;
- the chosen threshold, class order and model metadata;
- the short report section explaining the result.

These files let evaluation and application work continue without repeating a long training run. When a final model artefact is too large for ordinary Git, store it with Git LFS or the team's shared model storage and commit a small metadata file containing its location, version and loading instructions.

Member 5 uploads the shared evaluation code, locked result tables and final figures. Member 6 uploads the application, inference wrapper, anonymous user-study summary and poster material. `LATER_PLAN.md` gives the expected paths and contents for each role.
