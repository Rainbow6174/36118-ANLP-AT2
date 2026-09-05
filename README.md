# VarietyLens - AT2 English Variety Project

This repository contains the shared BESSTIE data pipeline, EDA, modelling folders, evaluation plan and report structure for the project.

## Prepare the data

Python 3.10 or newer is enough for the core pipeline.

```powershell
python src/data/run_data_pipeline.py
python -m unittest discover -s tests -v
```

The first command downloads the six public BESSTIE files, prepares fixed project splits, checks the data, creates task-ready files and refreshes the main EDA summaries.

## Main outputs

- `data/raw/besstie/`: the six source CSV files and provenance details
- `data/processed/dataset_v1.csv`: the full prepared dataset
- `data/processed/train.csv`, `validation.csv`, `test.csv`: shared split files with both labels
- `data/processed/by_task/`: ready-to-use files for sentiment, sarcasm and variety
- `data/processed/quality_report.json`: row counts and removal summary
- `data/processed/validation_report.json`: schema and leakage checks
- `data/processed/audit/removed_rows.csv`: row-level removal record
- `notebooks/eda.ipynb`: the full executable EDA
- `reports/eda/`: the data card, report section, tables and figures
- `docs/EDA_TO_HD_IMPLEMENTATION_PLAN.md`: practical next steps for all six roles
- `reports/MASTER_REPORT_OUTLINE.md`: final report structure

## Use the task files directly

Every file under `data/processed/by_task/` contains:

```text
id,text,variety,source,label
```

Use train to fit a model and validation to choose settings or thresholds. Keep test untouched until the final evaluation. If a model needs its own tokenisation or text transformation, apply it inside that model's code without changing the shared files.

## Run the EDA notebook

```powershell
python -m pip install -r requirements-notebook.txt
python tools/build_eda_notebook.py
python tools/execute_eda_notebook.py
```

The executed notebook saves reusable CSV tables and PNG/SVG figures under `reports/eda/notebook_outputs/`.

## Important data choices

The public BESSTIE validation split is used as the project's held-out test set because the official test data is not public. A stratified 15% part of the official train split becomes project validation.

Cleaning is deliberately light. The pipeline normalises whitespace but keeps spelling, case, punctuation, emoji, hashtags and regional wording. It audits exact duplicates and conflicting labels to prevent leakage.

## Source and citation

- Dataset: <https://huggingface.co/datasets/unswnlporg/BESSTIE>
- Paper: <https://aclanthology.org/2025.findings-acl.441/>

Srirag, D., Joshi, A., Painter, J., and Kanojia, D. (2025). *BESSTIE: A Benchmark for Sentiment and Sarcasm Classification for Varieties of English*. Findings of ACL 2025, 8413-8429.
