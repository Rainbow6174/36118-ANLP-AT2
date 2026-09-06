# VarietyLens

VarietyLens is a group NLP project that investigates sentiment and
sarcasm classification across Australian, Indian and British English.
This repository contains the shared dataset, EDA, modelling notebooks,
trained models, evaluation outputs, web application, report and poster.

```text
notebooks/    Data preparation, modelling and evaluation ipynb notebooks
data/         Raw BESSTIE files and frozen processed datasets
models/       Selected trained models
outputs/      EDA, predictions, evaluation results and figures
app/          Web application
report/       Group report
poster/       Group poster
```

Start with this README, run the EDA notebook once, then read `LATER_PLAN.md` before choosing or continuing a modelling role.

## 1. Install the packages

From the repository folder, run:

```bash
uv sync
```

This command creates the project environment from the two files below, so every team member ends up with the same package versions:

```text
pyproject.toml
uv.lock
```

Python 3.11 is used for this project.

## 2. Get the BESSTIE data

When `notebooks/01_data_eda.ipynb` runs, it first checks for the six local files below.

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

If any file is missing, the notebook downloads the corresponding public split from the official [BESSTIE Hugging Face repository](https://huggingface.co/datasets/unswnlporg/BESSTIE). Existing files are retained, so the download is skipped when all six files are available.

The raw files are included in the repository so that all members use the same data. The automatic download step restores any missing files when required.

## 3. Run the notebook

Start Jupyter from the repository root, since the notebook uses the project root to resolve its folders:

```bash
uv run jupyter lab
```

Open `notebooks/01_data_eda.ipynb` and choose **Run All Cells**. Run the whole notebook from top to bottom; later cells use the fixed splits and tables created near the beginning.

The notebook does all shared data work:

1. finds or downloads the six source files;
2. checks their columns and labels;
3. keeps wording, spelling, case, punctuation and emoji while cleaning whitespace;
4. removes exact/case-only duplicates and records every removal;
5. creates fixed train, validation and held-out test splits;
6. validates IDs, labels and split separation;
7. writes task-ready CSV files;
8. creates the EDA tables and figures.

The public BESSTIE release provides train and validation files. This project reserves the official validation files as its held-out test set. A fixed 15% stratified part of official train becomes project validation set, using seed `36118`. Model and threshold choices come from train and project validation; the held-out test supports one final evaluation.

## 4. Find the prepared data

After the notebook finishes, shared data is under:

```text
data/processed/
```

The main files are:

```text
data/processed/dataset_v1.csv
data/processed/train.csv
data/processed/validation.csv
data/processed/test.csv
data/processed/quality_report.json
data/processed/validation_report.json
data/processed/audit/removed_rows.csv
```

Each modelling role uses its own task folder:

| Work | Read these files |
| --- | --- |
| English-variety modelling | `data/processed/by_task/variety/` |
| Sentiment modelling | `data/processed/by_task/sentiment/` |
| Sarcasm modelling | `data/processed/by_task/sarcasm/` |

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
- `figures/` — PNG and SVG versions of the figures

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

The project repository shares the code, approved EDA outputs, modelling results, evaluation materials, application, report and poster through GitHub. The raw and processed datasets are excluded from Git, but they can be downloaded and regenerated locally by running notebooks/01_data_eda.ipynb. 

### Stored in GitHub

```text
data/raw/                 Original BESSTIE files
data/processed/           Frozen project data and task splits
notebooks/                EDA, modelling and evaluation notebooks
outputs/eda/              Approved EDA tables and figures
outputs/predictions/      Standard model predictions
outputs/results/          Verified evaluation results
outputs/figures/          Final report and poster figures
models/                   Small trained models or model metadata
app/                      Application code
report/                   Group report
poster/                   Poster material
pyproject.toml            Project dependencies
uv.lock                   Reproducible environment lock
```

### Excluded from GitHub

```text
.venv/
.ipynb_checkpoints/
__pycache__/
temporary checkpoints
experiment caches
secrets and environment files
large intermediate model files
```

The data preparation logic remains inside `notebooks/01_data_eda.ipynb`, so every person can recreate the same files by running the notebook from the top if anything needs to be rebuilt.

Later modelling work adds useful, reusable project files to GitHub. Each modelling role uploads:

- modelling notebooks and any reusable inference code;
- the final configuration and random seed;
- the selected trained model or model metadata;
- validation and final test predictions with `id` and probabilities;
- validation and test metric tables;
- the chosen threshold, class order and model metadata;
- the short report section explaining the result.

These files let evaluation and application work continue without repeating a long training run. When a final trained model is too large for ordinary Git, store it with Git LFS or the team's shared model storage and commit a small metadata file containing its location, version and loading instructions.

Member 5 uploads the shared evaluation code, locked result tables and final figures. Member 6 uploads the application, inference wrapper, anonymous user-study summary and poster material. `LATER_PLAN.md` gives the expected paths and contents for each role.

## 8. Project workflow at a glance

| Workstream | Primary location |
| --- | --- |
| Data preparation and EDA | `notebooks/01_data_eda.ipynb` |
| Sentiment modelling | `notebooks/02_sentiment_modelling.ipynb` |
| Sarcasm modelling | `notebooks/03_sarcasm_modelling.ipynb` |
| Variety modelling | `notebooks/04_variety_modelling.ipynb` |
| Model evaluation | `notebooks/05_model_evaluation.ipynb` |
| Trained models | `models/` |
| Predictions and results | `outputs/` |
| Application | `app/` |
| Report | `report/` |
| Poster | `poster/` |

## 9. Dataset attribution

This project uses the BESSTIE dataset released by Srirag et al. (2025) under the CC BY 4.0 licence. The downloaded data is stored without project-level preprocessing under `data/raw/besstie/`.

- Dataset: [BESSTIE on Hugging Face](https://huggingface.co/datasets/unswnlporg/BESSTIE)
- Paper: [BESSTIE: A Benchmark for Sentiment and Sarcasm Classification for Varieties of English](https://aclanthology.org/2025.findings-acl.441/)