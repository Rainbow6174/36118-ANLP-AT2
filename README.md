# VarietyLens

VarietyLens studies sentiment and sarcasm across Australian, Indian and British English. The project also tests whether English-variety information can make one downstream classifier more reliable.

This repository is organised so that every member can start from the same notebook, rebuild the same data locally and place later work in a clear shared location.

```text
notebooks/    Data preparation, modelling and evaluation notebooks
data/         Local raw BESSTIE files and prepared datasets created by the EDA notebook
models/       Selected trained models or model metadata
outputs/      EDA, predictions, evaluation results and figures
app/          Web application
report/       Group report and user-study material
poster/       Group poster
```

The detailed repository map below shows the exact subfolders used by each workstream.

## Quick start

Run the following commands from the repository root.

### Recommended setup with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first if it is not available on your computer.

```bash
uv sync
uv run jupyter lab
```

Open `notebooks/01_data_eda.ipynb` and choose **Run All Cells**.

### Pip alternative

```bash
python -m pip install -r requirements.txt
python -m jupyter lab
```

Python 3.11 is used for the project. Both setup methods install the packages needed by the EDA notebook, including the Hugging Face `datasets` package.

When later work adds a package, update `pyproject.toml` and `requirements.txt` together and refresh `uv.lock` in the same change.

## Data download and preparation

The EDA notebook checks for these six BESSTIE files:

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

If a file is missing, the notebook downloads the corresponding public split from the official [BESSTIE Hugging Face repository](https://huggingface.co/datasets/unswnlporg/BESSTIE). Existing local files are reused, and only missing files are downloaded. The notebook uses a fixed dataset revision, so every member reads the same source version.

The notebook then:

1. checks the columns, varieties, sources and labels;
2. cleans whitespace while preserving spelling, case, punctuation and emoji;
3. removes duplicate text and records each removal;
4. creates fixed train, validation and held-out test splits;
5. validates IDs, labels and split separation;
6. writes task-ready CSV files;
7. creates the shared EDA tables and figures.

The official BESSTIE validation files become the held-out project test set. A fixed 15% stratified sample from the official training files becomes the project validation set. The split seed is `36118`.

Model choice, threshold choice and routing choice use train and validation data. The held-out test set is used after the final settings have been agreed.

## Notebook inputs and outputs

The notebook uses these paths:

| Purpose | Path | Git policy |
| --- | --- | --- |
| Downloaded BESSTIE files | `data/raw/besstie/` | Local, downloaded when needed |
| Full prepared dataset | `data/processed/dataset_v1.csv` | Local, rebuilt by the notebook |
| Shared train/validation/test files | `data/processed/` | Local, rebuilt by the notebook |
| Task-specific files | `data/processed/by_task/` | Local, rebuilt by the notebook |
| Data-quality records | `data/processed/audit/` | Local, rebuilt by the notebook |
| Approved EDA tables and figures | `outputs/eda/` | Shared through Git |

The main prepared files are:

```text
data/processed/dataset_v1.csv
data/processed/train.csv
data/processed/validation.csv
data/processed/test.csv
data/processed/quality_report.json
data/processed/validation_report.json
data/processed/audit/removed_rows.csv
```

Important EDA outputs include:

- `outputs/eda/label_balance_by_split.csv`
- `outputs/eda/variety_source_sample_counts.csv`
- `outputs/eda/text_length_distribution_summary.csv`
- `outputs/eda/top_keywords_by_variety_source_train_only.csv`
- `outputs/eda/top_character_ngrams_by_variety_train_only.csv`
- `outputs/eda/source_diagnostic_validation_report.csv`
- `outputs/eda/sarcasm_distribution_by_split_variety_source.csv`
- `outputs/eda/sarcasm_segment_support_recommendations.csv`
- `outputs/eda/figures/`

Each task folder contains `train.csv`, `validation.csv` and `test.csv`:

```text
data/processed/by_task/sentiment/
data/processed/by_task/sarcasm/
data/processed/by_task/variety/
```

The task files use the same columns:

```text
id,text,variety,source,label
```

Keep `id` unchanged. Later prediction files use it to join predictions to the correct gold labels. Keep the shared CSV files unchanged and place model-specific tokenisation, feature extraction and scaling inside the modelling code.

## Repository map

```text
notebooks/              Data preparation, modelling and evaluation notebooks
data/                   Local raw and processed data created by the EDA notebook
models/                 Selected models or model metadata needed for inference
outputs/eda/            Approved EDA tables and figures
outputs/predictions/    Validation and final test predictions
outputs/results/        Model and evaluation result tables
outputs/error_analysis/ Reviewed error examples
outputs/figures/        Final report and poster figures
app/                    Web application and inference integration
report/                 Report sections and user-study material
poster/                 Poster source files
```

`LATER_PLAN.md` gives the work package, purpose and exact handoff paths for each member.

## Shared Git files

Git contains the material that the team needs to read directly or would take significant time to recreate:

- notebooks and reusable code;
- the dependency files;
- approved EDA tables and figures;
- selected model artefacts or model-location metadata;
- validation and final test predictions;
- agreed metric tables and final figures;
- routing and threshold settings;
- report sections, anonymous user-study results and poster files.

The `data/` folder stays local. The notebook downloads and rebuilds it from the fixed BESSTIE revision. Local virtual environments, caches, temporary checkpoints and exploratory outputs also stay outside Git.

Large selected model artefacts can use Git LFS or the team's shared model storage. In that case, commit a small metadata file with the model version, location and loading instructions.

## Work areas

| Work | Main notebook | Main output area |
| --- | --- | --- |
| Data preparation and EDA | `notebooks/01_data_eda.ipynb` | `outputs/eda/` |
| Sentiment modelling | `notebooks/02_sentiment_modelling.ipynb` | `models/sentiment/`, `outputs/results/sentiment/` |
| Sarcasm modelling | `notebooks/03_sarcasm_modelling.ipynb` | `models/sarcasm/`, `outputs/results/sarcasm/` |
| Variety modelling and variety-aware experiment | `notebooks/04_variety_modelling.ipynb` | `models/variety/`, `outputs/results/variety/`, `outputs/results/routing/` |
| Shared evaluation | `notebooks/05_model_evaluation.ipynb` | `outputs/results/final/`, `outputs/figures/final/` |
| Application and user study | `app/` | `report/user_study/`, `poster/` |

## Working evaluation agreement

Validation macro-F1 is the shared working primary metric. It gives the three modelling roles a common result to record while Member 5 prepares the final evaluation protocol.

Member 5 will propose the exact secondary metrics, confidence or calibration method and uncertainty method. The team will agree on that protocol before final model selection and before anyone runs the held-out test evaluation. All modelling roles save validation probabilities so threshold or metric decisions can be applied without retraining.

## Sarcasm support note

The prepared data contains 88 sarcastic Google examples. `en-IN Google` is sparse, and `en-UK Google` contains one sarcastic example in train and none in validation or test.

The sarcasm work therefore:

- uses one shared model across varieties and sources;
- compares an ordinary baseline with class weighting based on training data;
- chooses its working threshold on validation data;
- reports positive and total support beside subgroup results;
- writes `N/A` for positive-class metrics when a subgroup has no positive examples;
- passes limited-evidence information to the application review workflow.

## Dataset attribution

This project uses the BESSTIE dataset released by Srirag et al. (2025) under the CC BY 4.0 licence.

- [BESSTIE on Hugging Face](https://huggingface.co/datasets/unswnlporg/BESSTIE)
- [BESSTIE: A Benchmark for Sentiment and Sarcasm Classification for Varieties of English](https://aclanthology.org/2025.findings-acl.441/)
