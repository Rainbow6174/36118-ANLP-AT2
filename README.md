# CrisisLens

CrisisLens is an NLP tool for sorting new disaster messages. A user submits a message. The system chooses a humanitarian board, saves the message, opens that board, shows related messages and sends uncertain cases to a review queue.

It helps users organise and browse information. It is not an emergency-response system. It does not verify reports or make safety-critical decisions.

## Project layout

```text
notebooks/    Data preparation, EDA, modelling and evaluation notebooks
data/         Local raw files and generated data (not committed)
models/       Selected models and their settings
outputs/      Shared EDA, predictions, evaluation results and figures
app/          Web app, data storage and model connection
report/       Group report and user-study material
poster/       Group poster source files
LATER_PLAN.md Detailed English work plan and shared file rules
```

The old VarietyLens experiment is kept for reference in:

```text
notebooks/legacy/
outputs/legacy_varietylens_eda/
models/legacy_varietylens/
outputs/legacy_varietylens_predictions/
```

Do not use those files for current CrisisLens results.

## Quick start

Run these commands from the repository root.

### Recommended setup with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not available.

```bash
uv sync
uv run jupyter lab
```

Open `notebooks/01_crisis_eda.ipynb` and run all cells.

### Pip alternative

```bash
python -m pip install -r requirements.txt
python -m jupyter lab
```

Use Python 3.11 or later. The EDA notebook downloads and prepares its own data. No prepared local dataset is needed before it runs.

## Data sources and notebook outputs

The notebook downloads missing public files into `data/raw/`:

```text
data/raw/
├── humaid/
│   ├── train-00000-of-00001.parquet
│   ├── validation-00000-of-00001.parquet
│   └── test-00000-of-00001.parquet
├── humaid_events/       19 event-wise HumAID JSON groups
└── crisismmd/           CrisisMMD label and split files
```

The sources are:

- [HumAID-all](https://huggingface.co/datasets/QCRI/HumAID-all), the main ten-label text-classification dataset;
- [HumAID-events](https://huggingface.co/datasets/QCRI/HumAID-events), which supplies event names for unseen-event testing;
- [CrisisMMD](https://crisisnlp.qcri.org/crisismmd), used as a separate supporting label benchmark.

The notebook downloads the small CrisisMMD label archive, not the large image archive. Keep the original licence and terms for each dataset. Check the source pages before sharing raw data, tweet text or trained models.

The notebook writes shared results to:

```text
outputs/eda/
├── eda_summary.json
├── humaid_split_summary.csv
├── humaid_label_distribution.csv
├── humaid_event_distribution.csv
├── humaid_event_label_counts.csv
├── humaid_event_holdout_plan.csv
├── humaid_text_statistics.csv
├── humaid_duplicate_summary.csv
├── humaid_label_top_word_features.csv
├── humaid_label_top_char_ngrams.csv
├── crisismmd_task_summary.csv
├── crisismmd_label_distribution.csv
├── crisismmd_annotation_agreement.csv
└── figures/
```

All data-processing steps are inside the notebook. `tools/build_crisis_eda_notebook.py` only rebuilds the notebook. Most users should open the notebook directly.

## What the EDA found

HumAID contains 76,484 posts from 19 disaster events. The downloaded files contain ten labels:

```text
caution_and_advice
displaced_people_and_evacuations
infrastructure_and_utility_damage
injured_or_dead_people
missing_or_found_people
not_humanitarian
other_relevant_information
requests_or_urgent_needs
rescue_volunteering_or_donation_effort
sympathy_and_support
```

The official split sizes are 53,531 train, 7,793 validation and 15,160 test rows. The largest class is `rescue_volunteering_or_donation_effort` with 21,278 rows; `missing_or_found_people` has 358 rows. Use macro-F1 and show support for each label. Do not use accuracy alone.

Hurricanes account for 41,320 posts. The event-held-out table shows that some small events have very little test support for particular labels, so those results must be reported with support and interpreted carefully.

The duplicate check found 12 exact duplicate rows and four normalised duplicate groups crossing official splits. The baseline and Transformer work should use the same text cleaning and mention these groups when interpreting scores.

CrisisMMD has informative, humanitarian and damage-severity tasks. Its label files contain image-text rows, so one tweet can occur with several images. Later experiments must split or remove duplicates by `tweet_id`, not by raw row.

## Product flow

The classifier is only one part. The app also saves messages, shows boards and finds related messages:

```text
user submits a message
    -> model returns label, probabilities and confidence
    -> application saves the message and prediction
    -> application redirects to /boards/<predicted_label>
    -> board page shows the new message and related historical messages
    -> user browses boards, searches/filter messages, or corrects the board
    -> low-confidence items remain visible in a review queue
```

Historical HumAID examples are saved as read-only records with `source_type=humaid_history`. New messages use `source_type=user`. The app must not present a model guess as an official fact.

## Shared interfaces

Every classification model must accept one text string and return:

```json
{
  "predicted_label": "requests_or_urgent_needs",
  "probabilities": {"requests_or_urgent_needs": 0.82},
  "confidence": 0.82,
  "model_version": "baseline-v1",
  "needs_review": false
}
```

The retrieval component accepts `search(query, board_label, k)` and returns records in this shape:

```json
{
  "id": "history-123",
  "similarity": 0.74,
  "text_preview": "...",
  "source_type": "humaid_history"
}
```

The stored message record contains `message_id`, `text`, `board_label`, `source_type`, `confidence`, `model_version`, `needs_review`, `created_at` and an optional `user_correction`.

## Work areas

| Work | Main location | Responsibility |
| --- | --- | --- |
| Data and EDA | `notebooks/01_crisis_eda.ipynb`, `outputs/eda/` | Download, prepare and explain the common data contract |
| Text baseline | `models/text_baseline/`, `outputs/results/baseline/` | Majority, TF-IDF word/character and linear models |
| Contextual model | `models/transformer/`, `outputs/results/transformer/` | Compact Transformer and imbalance treatment |
| New-event evaluation | `evaluation/cross_event/`, `outputs/results/cross_event/` | Test on one unseen event at a time |
| Retrieval | `models/retrieval/`, `outputs/results/retrieval/` | Related historical messages and duplicate grouping |
| Application and user study | `app/`, `report/user_study/`, `poster/` | Storage, boards, routing, review flow and user evidence |

Read `LATER_PLAN.md` for each member's tasks, goal, expected files and shared rules.

## Evaluation agreement

The main classification metric is macro-F1. Each serious run reports precision, recall, F1 and support for every label, plus balanced accuracy, a confusion matrix and run time. The final app model also reports how well its confidence scores match its results.

The main test uses the official HumAID train, validation and test split. The new-event test trains on 18 events and tests on one unseen event at a time. Use the official test set only after settings and thresholds are fixed.

Retrieval reports precision@k or recall@k on a small checked set and records search time. The user study reports task completion, time, board choice, confidence understanding and corrections.

## What belongs in Git

Commit files that another member needs or would take a long time to recreate:

- notebooks and reusable code;
- approved EDA tables and figures;
- model metadata, loading instructions and selected checkpoints when needed;
- validation and final predictions;
- evaluation tables, reviewed errors and final figures;
- anonymous user-study results, report sections and poster sources.

Keep raw downloads, generated local datasets, virtual environments, temporary checkpoints and caches out of Git. `data/` is ignored and is rebuilt by the notebook. Large model files may use Git LFS or shared storage, but the repository must contain the version, location and loading instructions.
