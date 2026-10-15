# CrisisLens

CrisisLens sorts short English disaster messages into ten HumAID categories. It shows the suggested category, calibrated confidence and similar reports already saved for the current event before the user confirms or changes the category. Saved reports appear on category boards and can be searched later. Low-confidence results also appear in a review queue.

CrisisLens organises information. It does not verify reports or make emergency decisions.

- [Technical report](report/tech_report.pdf)
- [Report source](report/tech_report.md)
- [Project poster](poster/ANLP_AT2_PartA_Group2_CrisisLens.pdf)

## How it works

```text
NiceGUI frontend -> FastAPI API
                    ├── DistilBERT classifier
                    ├── MiniLM similarity and TF-IDF search
                    │     └── read-only HumAID history (historical search only)
                    └── SQLite reports for the current event
```

Each deployment serves one event. `POST /api/analyse` cleans the text as in Transformer training, returns a prediction and lists earlier reports from the current event whose MiniLM similarity is at least 0.45, in any category. `POST /api/reports` saves the confirmed category and opens its board. Corrections keep the original prediction and update search and retrieval immediately. Hiding or deleting a community report removes it from the live retrieval index. HumAID history is used only by the separate Historical dataset search and as marked examples on empty boards.

## Results

The official HumAID split contains 53,531 training, 7,793 validation and 15,160 test messages. Macro-F1 is the main classification metric because the ten labels are uneven.

| Component | Selected result |
| --- | --- |
| Word + character TF-IDF baseline | 0.7262 test macro-F1 |
| DistilBERT deployment model | 0.7547 test macro-F1; calibrated ECE 0.0257 |
| Twitter-RoBERTa analysis model | 0.7621 test macro-F1; not loaded by the application |
| Semantic related-message retrieval | Precision@5 0.800 |
| TF-IDF keyword search | Precision@5 0.756 |
| Similar-report display threshold | 0.45 MiniLM similarity; 75.8% of shown candidates relevant on held-out judgements |
| System evaluation | 48 automated tests and 14 failure scenarios passed |

The application uses the DistilBERT model trained on the official HumAID split. The unseen-event experiment retrains separate models on 12 events and tests them on 779 `cyclone_idai_2019` messages; those checkpoints are only used for shift analysis.

## Repository layout

```text
app/          FastAPI backend, SQLite schema and NiceGUI frontend
evaluation/   Reusable cross-event evaluation code
models/       Baseline, Transformer loader, retrieval and index-building code
notebooks/    EDA, training, calibration, cross-event and retrieval experiments
outputs/      Recorded EDA, predictions, metrics and figures
poster/       Final poster
report/       Final report, screenshots and six member sections
scripts/      Demo data, real-mode checks, benchmarks, failure checks and result reproduction
tests/        API, retrieval, moderation, cross-event, accessibility and frontend tests
```

Git contains the code, notebooks, recorded results, TF-IDF baseline, report and poster. It does not contain:

- raw HumAID and CrisisMMD downloads under `data/`;
- the DistilBERT weights `models/transformer/model.safetensors` (about 270 MB, published as a release asset);
- the generated retrieval index under `models/retrieval/index/`;
- the local SQLite database, environments or caches.

## Requirements

- Python 3.11 or later
- Internet access during the first setup for datasets, model files and Python packages
- [uv](https://docs.astral.sh/uv/) is recommended; `pip` is also supported

Run every command from the repository root.

## Install the environment

Clone the repository and enter it:

```bash
git clone https://github.com/Rainbow6174/36118-ANLP-AT2.git
cd 36118-ANLP-AT2
```

With uv:

```bash
uv sync
```

With pip:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then install the same project dependencies:

```bash
python -m pip install -r requirements.txt
```

The uv commands do not require manual activation.

## Quick interface preview

The frontend can run without the large model or retrieval index:

```bash
uv run python app/frontend/main.py
```

For a pip environment:

```bash
python app/frontend/main.py
```

Open <http://localhost:8080>. A visible **Demo mode** notice means the frontend is using its built-in sample data and keyword classifier. This mode is useful for viewing the interface, but it is not the evaluated NLP stack.

## Run the complete application

### 1. Download and prepare the datasets

Start JupyterLab:

```bash
uv run jupyter lab
```

Open `notebooks/01_crisis_eda.ipynb` and run all cells. The notebook downloads the required public files when they are missing and writes them under `data/raw/`. It also recreates the EDA tables and figures under `outputs/eda/`.

The application index uses the event-wise HumAID files expected at:

```text
data/raw/humaid_events/*.json
```

The data sources are [HumAID-all](https://huggingface.co/datasets/QCRI/HumAID-all), [HumAID-events](https://huggingface.co/datasets/QCRI/HumAID-events) and the text annotation files from [CrisisMMD](https://crisisnlp.qcri.org/crisismmd/).

### 2. Add the deployment model

The loader, metadata, configuration and tokenizer files are already tracked in `models/transformer/`. Download `model.safetensors` from the [m3-transformer-v1 release](https://github.com/Rainbow6174/36118-ANLP-AT2/releases/tag/m3-transformer-v1) and save it as:

```text
models/transformer/model.safetensors
```

With the GitHub CLI:

```bash
gh release download m3-transformer-v1 -R Rainbow6174/36118-ANLP-AT2 -p model.safetensors -D models/transformer
```

No archive is extracted, so the tracked loader and metadata are never replaced. The folder should then contain:

```text
models/transformer/
├── __init__.py              # tracked
├── metadata.json            # tracked
├── README.md                # tracked
├── config.json              # tracked
├── tokenizer.json           # tracked
├── tokenizer_config.json    # tracked
└── model.safetensors        # downloaded from the release
```

### 3. Build the retrieval index

After the EDA notebook has prepared `data/raw/humaid_events/`, run:

```bash
uv run python models/retrieval/build_index.py
```

For a pip environment:

```bash
python models/retrieval/build_index.py
```

This creates `models/retrieval/index/` with the historical messages, TF-IDF search files and MiniLM embeddings. The first run also downloads `all-MiniLM-L6-v2`. The generated index is about 150 MB and is ignored by Git.

### 4. Start the backend in real mode

On macOS or Linux:

```bash
CRISISLENS_RUNTIME=real uv run uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
```

On Windows PowerShell:

```powershell
$env:CRISISLENS_RUNTIME = "real"
uv run uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
```

Use `python -m uvicorn` instead of `uv run uvicorn` in a pip environment. Real mode stops with a clear error if the Transformer files or retrieval index are missing.

Check the runtime in another terminal:

```bash
curl http://localhost:8000/api/health
```

On PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

The response should contain `"active_runtime": "real"`. The backend creates `app/backend/crisislens.db` on first use.

### 5. Start the frontend against the API

On macOS or Linux:

```bash
CRISISLENS_API_URL=http://localhost:8000 uv run python app/frontend/main.py
```

On Windows PowerShell:

```powershell
$env:CRISISLENS_API_URL = "http://localhost:8000"
uv run python app/frontend/main.py
```

Use `python app/frontend/main.py` after setting the same variable in a pip environment. Open <http://localhost:8080>. The **Demo mode** notice should no longer be present. Use `user` / `user` for the standard demo account or `admin` / `admin` for the administrator page. The administrator can correct categories and hide, restore or delete community reports.

### 6. Prepare a demonstration event

Each deployment serves one event, and a new database has no community reports. While the backend is running, choose one starting point:

```bash
uv run python scripts/demo_data.py empty --yes
uv run python scripts/demo_data.py nepal --replace
uv run python scripts/demo_data.py event kerala_floods_2018 --limit 40 --replace
```

`empty` removes every community report. `nepal` loads the nine labelled Nepal flood and landslide reports also used by demo mode. `event` samples one event's HumAID test split, classifies each message with the running model and marks the saved records as demo data; `uv run python scripts/demo_data.py event --list` shows the events downloaded by the EDA notebook. Without `--replace`, loading stops if the database already has reports, so two events are never mixed.

## Runtime settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `CRISISLENS_RUNTIME` | Backend component mode: `real`, `mock` or `auto` | Value in `app/app_models.json` (`auto`) |
| `CRISISLENS_API_URL` | REST API used by the frontend | Empty; frontend uses demo mode |
| `CRISISLENS_DB_PATH` | SQLite database path | `app/backend/crisislens.db` |
| `PORT` | NiceGUI frontend port | `8080` |

`auto` loads the real classifier and retrieval index when both are present and otherwise uses mock components. Use `real` for an assessed or deployed run so missing artefacts cannot be hidden by fallback behaviour.

## Verify the repository

The suite contains 48 tests. Most use mock model components and a temporary database. Two retrieval tests use the local index and MiniLM model and are skipped when these are not available:

```bash
uv run pytest
```

Static checks:

```bash
uv run ruff check .
```

With the real backend running, these scripts check the application and repeat the recorded measurements:

```bash
uv run python scripts/real_mode_check.py
uv run python scripts/benchmark_endpoints.py
uv run python scripts/test_failure_scenarios.py
```

`real_mode_check.py` exercises analysis, similar reports, publishing, moderation, search filters and deletion, then removes its own reports. The other two scripts save results in `outputs/results/system/` and add local test records, so use a disposable database if the existing reports matter.

The similar-report threshold and the deployed DistilBERT validation curve can be reproduced with:

```bash
uv run python scripts/calibrate_related_threshold.py
uv run python scripts/distilbert_validation_curve.py
```

## API overview

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Show API and model runtime status |
| `POST /api/analyse` | Classify text and return similar reports from the current event |
| `POST /api/reports` | Save a user-confirmed report |
| `GET /api/reports` | List and filter saved reports; `exclude_hidden=true` omits hidden reports and `created_by` lists one account's reports |
| `GET /api/reports/{message_id}` | Show one report and similar reports from the current event |
| `GET /api/search` | Keyword search; the interface searches either the current event or the Historical dataset, never both |
| `PATCH /api/reports/{message_id}` | Confirm or correct a category, or hide and restore a report |
| `DELETE /api/reports/{message_id}` | Delete a community report and remove it from the live index |

FastAPI also exposes interactive API documentation at <http://localhost:8000/docs> while the backend is running.

## Reproduce the experiments

The repository keeps the experiment code and the recorded outputs used in the report:

| Work | Code or notebook | Recorded evidence |
| --- | --- | --- |
| Data preparation and EDA | `notebooks/01_crisis_eda.ipynb` | `outputs/eda/` |
| TF-IDF baseline | `models/text_baseline/` | `outputs/results/baseline/`, `outputs/predictions/baseline/` |
| Transformer training | `notebooks/member3/nb1-transformer-training_with output.ipynb` | `outputs/results/transformer/` |
| Calibration and selective prediction | `notebooks/member3/nb2_calibration_selective_with output.ipynb`, `scripts/distilbert_validation_curve.py` | calibration tables, coverage-risk files, `distilbert_validation_curve.json` |
| Unseen-event evaluation | `notebooks/member3/nb3_cross_event_with output.ipynb`, `evaluation/cross_event/` | `outputs/results/cross_event/` |
| Retrieval and search | `notebooks/member5/retrieval_experiments.ipynb`, `scripts/calibrate_related_threshold.py` | `outputs/results/retrieval/`, including `related_threshold.csv` |
| Integrated system | `tests/`, `scripts/` | `outputs/results/system/` |

The official benchmark and the unseen-event experiment use different training sets. Their results should not be treated as measurements from one checkpoint. Full methods, limitations and references are in the [technical report](report/tech_report.pdf).

## Team and limits

Detailed contributions are kept under `report/sections/`. `LATER_PLAN.md` records the work split used during development.

| Member | Main contribution |
| --- | --- |
| Jiayu Hao | Data preparation, EDA and the shared data contract |
| Kamali Siddharthan | TF-IDF baseline and baseline cross-event evaluation |
| Xin Yiing Loo | Transformer training, calibration and selective prediction |
| Kunal Mistry | Backend, SQLite integration and system evaluation |
| Sze Xuan Yap | Retrieval, search and duplicate grouping |
| Lujia Ouyang | Frontend, interaction design and responsible-use analysis |

A public version would need moderator accounts, rate limits, abuse reporting, audit logs and data-removal rules. The current SQLite version is for project demonstration.
