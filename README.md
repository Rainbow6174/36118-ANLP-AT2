# CrisisLens

CrisisLens is an NLP tool for sorting new disaster messages. A user submits a message. The system chooses a humanitarian board, saves the message, opens that board, shows related messages and sends uncertain cases to a review queue.

It helps users organise and browse information. It is not an emergency-response system. It does not verify reports or make safety-critical decisions.

## Project layout

```text
notebooks/    Data preparation, EDA, modelling and evaluation notebooks
data/         Local raw files and generated data (not committed)
models/       Selected models and their settings
outputs/      Shared EDA, predictions, evaluation results and figures
app/          Backend API, database schema and frontend
report/       Group report and user-study material
poster/       Group poster exports and supporting files
LATER_PLAN.md Detailed English work plan and shared file rules
```

## Current implementation state

The repository now contains the six members' integrated work. Member 3's
DistilBERT package is the selected application classifier, Member 2's
word-and-character TF-IDF model is the transparent comparison, and Member 5's
index provides semantic retrieval and keyword search. The FastAPI backend and
NiceGUI frontend are connected through the shared interfaces below.

Large model and index files are prepared separately, so a fresh clone starts
in `auto` mode and may use the mock components until those files are present.
The remaining project evidence is the verified real-stack walkthrough, system
timing and failure results, user-study results, deployment record, final report
and poster.

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

### Prepare the real application

The code is in Git, while the large generated artefacts stay outside Git.

1. Download `models_transformer.zip` from the [Member 3 model release](https://github.com/Rainbow6174/36118-ANLP-AT2/releases/tag/m3-transformer-v1) and unzip it at the repository root. The weights and tokenizer will be placed in `models/transformer/`.
2. Run the EDA notebook once so `data/raw/humaid_events/` exists.
3. Build the local historical-message index:

```bash
uv run python models/retrieval/build_index.py
```

The index is written to `models/retrieval/index/`. It is generated locally and is not committed.

### Run the backend

The FastAPI entry point remains `app/backend/main.py`:

```bash
CRISISLENS_RUNTIME=real uv run uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
```

On PowerShell:

```powershell
$env:CRISISLENS_RUNTIME="real"
uv run uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
```

`real` requires both the Member 3 model and Member 5 index and stops with a clear message when either is missing. `mock` is available for tests and interface work. The default `auto` mode uses the real components when both artefacts exist and otherwise reports its mock fallback at `GET /api/health`.

### Run the frontend

The web app is in `app/frontend/` (NiceGUI). From the repository root:

```bash
uv sync
uv run python app/frontend/main.py
```

Open http://localhost:8080. Without a backend address it runs in demo mode (built-in sample reports and a keyword classifier, with a "Demo mode" notice). To use the real REST API:

```bash
CRISISLENS_API_URL=http://localhost:8000 uv run python app/frontend/main.py
```

On PowerShell: `$env:CRISISLENS_API_URL="http://localhost:8000"; uv run python app/frontend/main.py`

Restart the app after editing Python or CSS files.

#### Fill the backend with demo reports

A real backend starts with an empty database, so the boards show nothing. To add the 9 demo community reports (marked "Demo data" in the app), run this while the backend is running:

```bash
uv run python app/frontend/scripts/seed_demo_reports.py http://localhost:8000
```

Use the backend's own address, so it also works for a deployed backend. If demo reports are already there, the script stops without adding more; add `--force` to add them again. Run it from this repository after `uv sync`; the frontend does not have to be running. It only adds reports and never changes or deletes existing ones.

### Deploy the frontend

The frontend is one Python process with no database of its own. It needs the backend to be reachable from the machine it runs on.

| Variable | Meaning |
| --- | --- |
| `CRISISLENS_API_URL` | Address of the REST API. If it is not set, the frontend shows built-in demo data. |
| `PORT` | Port to listen on (default 8080). Hosting services set it, and then no browser is opened. |

After starting, check the top of the page: a "Demo mode" notice means `CRISISLENS_API_URL` is not set and the data is built in, not from the backend. The notice is gone when the real backend is connected.

The host must support WebSockets (NiceGUI needs them), so static hosting such as GitHub Pages will not work. The app has no login: anyone with the link can submit reports and change categories, so treat a public site as a demo.

#### Local

Follow "Run the frontend" above. To serve other devices on the same network, run it on the machine that hosts the backend and open `http://<that machine's address>:8080`.

#### Cloud

| Item | Value |
| --- | --- |
| Frontend URL | Not deployed yet |
| Backend API URL | Not deployed yet |
| Hosting service | Not selected yet |

No shared cloud deployment has been verified on this branch. After deployment,
record the service, both URLs and any platform-specific start command here.
First confirm that `/api/health` reports the real runtime and complete the full
submit, save, redirect, search and correction flow.

### Dependency changes

The checked-in environment covers the EDA and shared project code. If your work needs another package, install and test it locally first. After the local test works, update `pyproject.toml`, `requirements.txt` and `uv.lock` together, record the version and tell the team before changing the shared files. A planned package is not added to the repository until it has passed a local test.

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
- [CrisisMMD](https://crisisnlp.qcri.org/crisismmd), used for a separate supporting label profile in the EDA.

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

All data-processing steps are inside the notebook. The notebook is the single source of truth; open it directly when you need to run or inspect the EDA.

The notebook does not create a second modelling dataset. Model work reads the downloaded HumAID files from `data/raw/` and uses the shared labels and split rules in this README and `outputs/eda/`.

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

Historical HumAID examples stay in Member 5's read-only retrieval index with
`source_type=humaid_history`. New messages are saved in SQLite with
`source_type=user`. The public report-creation endpoint accepts user messages
only. The app must not present a model guess as an official fact.

## Shared interfaces

These names and response fields are shared by every member. Do not change them in a private branch without telling the team.

### Classification model

Every classification model must implement `classify(text)` and return:

```json
{
  "predicted_label": "requests_or_urgent_needs",
  "probabilities": {
    "caution_and_advice": 0.03,
    "displaced_people_and_evacuations": 0.02,
    "infrastructure_and_utility_damage": 0.03,
    "injured_or_dead_people": 0.01,
    "missing_or_found_people": 0.01,
    "not_humanitarian": 0.02,
    "other_relevant_information": 0.06,
    "requests_or_urgent_needs": 0.78,
    "rescue_volunteering_or_donation_effort": 0.02,
    "sympathy_and_support": 0.02
  },
  "confidence": 0.78,
  "model_version": "baseline-v1",
  "needs_review": false
}
```

`probabilities` contains all ten labels in a fixed order. `predicted_label` is the original model result. `confidence` is the score used for the review rule. The model wrapper only predicts; it does not write to the database.

### Retrieval and search

The retrieval component implements `retrieve(text, k, filters=None)`. It returns related historical or user reports:

```json
{
  "id": "history-123",
  "similarity": 0.74,
  "board_label": "requests_or_urgent_needs",
  "text_preview": "...",
  "source_type": "humaid_history"
}
```

`search(query, filters=None, k=20)` handles keyword search and filters. Its result items use the same fields as `retrieve()`. Member 5 owns the ranking and index. Member 4 exposes the REST endpoint and database filters.

### Stored message fields

The database keeps:

```text
message_id
text
predicted_label
board_label
source_type
confidence
model_version
needs_review
created_at
user_correction
status
```

`predicted_label` keeps the original model result. `board_label` is the board
shown by the application and defaults to `predicted_label`. A correction
changes `board_label` but does not overwrite `predicted_label`. New user
records use `source_type=user` and `status=unverified`. Historical HumAID
results use `source_type=humaid_history`, come from the read-only retrieval
index and are not created through this database interface.

The MVP status values are `unverified`, `needs_review` and `resolved`. They describe the application's handling of a report, not the truth of its content.

### REST API

Member 4 owns these endpoints. Member 6 calls the API and does not call models or the database directly. The implementation is in `app/backend/`, the SQLite schema is `app/schema.sql`, and `app/app_models.json` keeps the selected model and index paths.

| Method and path | Request | Minimum response |
| --- | --- | --- |
| `POST /api/analyse` | `{"text": "...", "location": {...}}` | `prediction`, `related_reports`, optional `extraction` |
| `POST /api/reports` | new user message, prediction, optional location | `message_id`, `board_label`, `status`, `created_at` |
| `GET /api/reports` | board, source, status and location filters | paginated report list |
| `GET /api/reports/{message_id}` | message ID | one report and related reports |
| `GET /api/search` | `q`, filters and `k` | ranked report list |
| `PATCH /api/reports/{message_id}` | category correction or permitted status update | updated report |

`GET /api/reports` lists the user messages persisted in SQLite.
`GET /api/search` and the `related_reports` fields can also return the
read-only HumAID examples from the retrieval index.

Use these query names for list and search endpoints: `q`, `k`, `page`, `board_label`, `source_type`, `status`, `country`, `region`, `city` and `needs_review`. Members may add a filter only when its stored field and behaviour are documented.

Example analyse request and response:

```json
{
  "text": "Several families need drinking water near the community hall.",
  "location": {
    "country": "Australia",
    "region": null,
    "city": null,
    "latitude": null,
    "longitude": null
  }
}
```

```json
{
  "prediction": {
    "predicted_label": "requests_or_urgent_needs",
    "probabilities": {
      "caution_and_advice": 0.03,
      "displaced_people_and_evacuations": 0.02,
      "infrastructure_and_utility_damage": 0.03,
      "injured_or_dead_people": 0.01,
      "missing_or_found_people": 0.01,
      "not_humanitarian": 0.02,
      "other_relevant_information": 0.06,
      "requests_or_urgent_needs": 0.78,
      "rescue_volunteering_or_donation_effort": 0.02,
      "sympathy_and_support": 0.02
    },
    "confidence": 0.78,
    "model_version": "baseline-v1",
    "needs_review": false
  },
  "related_reports": [],
  "extraction": null
}
```

Example report request:

```json
{
  "text": "Several families need drinking water near the community hall.",
  "predicted_label": "requests_or_urgent_needs",
  "board_label": "requests_or_urgent_needs",
  "source_type": "user",
  "confidence": 0.78,
  "model_version": "baseline-v1",
  "needs_review": false,
  "location": {"country": "Australia"}
}
```

The normal user flow is:

```text
POST /api/analyse
    -> user confirms or corrects the board
    -> POST /api/reports
    -> redirect to /boards/<board_label>
```

The API stores user reports as unverified by default. Similar reports provide context, not fact checking.

### Optional extraction interface

Information extraction is an extension, not a required MVP module. If the team adds it, the function is:

```text
extract(text) -> structured fields
```

The first version should keep the fields small and auditable:

```json
{
  "location_mention": null,
  "need_type": [],
  "urgency": null,
  "quantity": null,
  "field_confidences": {}
}
```

The extension needs its own labelled sample and field-level evaluation. It may add an `extraction` object to `POST /api/analyse`, but it must not change the required classification or stored-message fields.

## Work areas

| Work | Main location | Responsibility |
| --- | --- | --- |
| Data and EDA | `notebooks/01_crisis_eda.ipynb`, `outputs/eda/` | Download, prepare and explain the common data contract |
| Text baseline | `models/text_baseline/`, `outputs/results/baseline/` | Majority, TF-IDF word/character and linear models |
| Contextual model | `models/transformer/`, `outputs/results/transformer/` | Compact Transformer and imbalance treatment |
| Backend and evaluation harness | `app/backend/`, `evaluation/cross_event/`, `outputs/results/cross_event/`, `outputs/results/system/` | REST API, database, integration tests and reusable event-held-out evaluator |
| Retrieval | `models/retrieval/`, `outputs/results/retrieval/` | Related historical messages and duplicate grouping |
| Frontend and user study | `app/frontend/`, `report/user_study/`, `outputs/figures/application/` | Boards, routing, review flow, user evidence and screenshots |

Read `LATER_PLAN.md` for each member's tasks, goal, expected files and shared rules.

### Member handoff map

| Member | Read first | Commit work to |
| --- | --- | --- |
| 1 | `notebooks/01_crisis_eda.ipynb`, `outputs/eda/` | EDA notebook, `outputs/eda/`, `report/sections/member1_data_and_eda.md` |
| 2 | `outputs/eda/eda_summary.json`, `data/raw/humaid/` | `models/text_baseline/`, `outputs/predictions/baseline/`, `outputs/results/baseline/`, `outputs/results/cross_event/baseline/`, `report/sections/member2_text_baseline.md` |
| 3 | `outputs/eda/humaid_label_distribution.csv`, `outputs/eda/humaid_text_statistics.csv`, `data/raw/humaid/` | `models/transformer/`, `outputs/predictions/transformer/`, `outputs/results/transformer/`, `outputs/results/cross_event/transformer/`, `report/sections/member3_contextual_model.md` |
| 4 | `README.md`, `LATER_PLAN.md`, `outputs/eda/eda_summary.json` | `app/backend/`, `app/schema.sql`, `app/app_models.json`, `evaluation/cross_event/`, `outputs/results/cross_event/`, `outputs/results/system/`, `report/sections/member4_worklog.md` |
| 5 | `data/raw/humaid_events/`, `outputs/eda/humaid_duplicate_summary.csv` | `models/retrieval/`, `outputs/results/retrieval/`, `report/sections/member5_retrieval.md` |
| 6 | `app/frontend/`, `outputs/eda/eda_summary.json` and the REST API above | `app/frontend/`, `report/user_study/`, `outputs/figures/application/`, `report/sections/member6_frontend_and_user_study.md` |

Members may read other folders for context, but they should keep their implementation and result files in their own paths. The final report and poster use evidence from all six members.

## Evaluation agreement

The main classification metric is macro-F1. Each serious run reports precision, recall, F1 and support for every label, plus balanced accuracy, a confusion matrix and run time. The final app model also reports how well its confidence scores match its results.

The standard test uses the official HumAID train, validation and test split. The shared unseen-disaster stress test uses the 13-event `events_set1_47K` subset, removes `cyclone_idai_2019` completely from training and validation, and evaluates on its 779 test messages. Member 2 and Member 3 use this same protocol. The full 19-event download remains the source for EDA and the retrieval index.

Retrieval reports precision@k or recall@k on a small checked set and records search time. The user study reports task completion, time, board choice, confidence understanding and corrections.

## Optional extensions

These ideas come from the wider proposal. They are useful only after the core text-only workflow and evaluation are complete.

- Information extraction for location, need type or urgency. This needs a small labelled set and a clear field-level evaluation.
- CrisisMMD image or multimodal modelling. The current project uses its label files only; the image archive and an image model are not part of the MVP.
- Live social-media feeds, notifications, advanced maps, route planning, payment, identity checks, full misinformation detection and production moderation.

An extension must keep the shared interfaces above and have its own data, evaluation and privacy notes. It must not change the core label contract.

## What belongs in Git

Commit files that another member needs or would take a long time to recreate:

- notebooks and reusable code;
- approved EDA tables and figures;
- model metadata, loading instructions and selected checkpoints when needed;
- validation and final predictions;
- evaluation tables, reviewed errors and final figures;
- anonymous user-study results, report sections and poster sources.

Keep raw downloads, generated local datasets, virtual environments, temporary checkpoints and caches out of Git. `data/` is ignored and is rebuilt by the notebook. Large model files may use Git LFS or shared storage, but the repository must contain the version, location and loading instructions.
