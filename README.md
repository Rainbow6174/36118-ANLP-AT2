# CrisisLens

CrisisLens sorts short English disaster messages into ten HumAID categories. It shows the suggested category, calibrated confidence and related historical messages before the user confirms or changes the category. Saved reports appear on category boards and can be searched later. Low-confidence results also appear in a review queue.

CrisisLens organises information. It does not verify reports or make emergency decisions.

- [Technical report](report/tech_report.pdf)
- [Report source](report/tech_report.md)
- [Project poster](poster/ANLP_AT2_PartA_Group2_CrisisLens.pdf)

## How it works

```text
NiceGUI frontend -> FastAPI API
                    ├── DistilBERT classifier
                    ├── semantic retrieval and TF-IDF search
                    └── SQLite user reports
```

`POST /api/analyse` returns a prediction and related messages from the predicted category. `POST /api/reports` saves the confirmed category and opens its board. Corrections keep the original prediction and update search and retrieval immediately. The interface marks community reports, HumAID history and demo records separately.

## Results

The official HumAID split contains 53,531 training, 7,793 validation and 15,160 test messages. Macro-F1 is the main classification metric because the ten labels are uneven.

| Component | Selected result |
| --- | --- |
| Word + character TF-IDF baseline | 0.7262 test macro-F1 |
| DistilBERT deployment model | 0.7547 test macro-F1; calibrated ECE 0.0257 |
| Twitter-RoBERTa analysis model | 0.7621 test macro-F1; not loaded by the application |
| Semantic related-message retrieval | Precision@5 0.800 |
| TF-IDF keyword search | Precision@5 0.756 |
| System evaluation | 28 automated tests and 14 recorded failure scenarios passed |

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
scripts/      Endpoint benchmarks and failure-scenario checks
tests/        API, cross-event and frontend contract tests
```

Git contains the code, notebooks, recorded results, TF-IDF baseline, report and poster. It does not contain:

- raw HumAID and CrisisMMD downloads under `data/`;
- DistilBERT weights and tokenizer files under `models/transformer/`;
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

Download `models_transformer.zip` from the [m3-transformer-v1 release](https://github.com/Rainbow6174/36118-ANLP-AT2/releases/tag/m3-transformer-v1) and extract it at the repository root. The deployment files must end up directly inside `models/transformer/`:

```text
models/transformer/
├── __init__.py
├── metadata.json
├── config.json
├── model.safetensors              # or pytorch_model.bin
├── tokenizer.json                 # or vocab.txt
├── tokenizer_config.json
└── special_tokens_map.json        # included when supplied by the tokenizer
```

The repository already contains the loader and metadata. The release supplies the large Hugging Face model and tokenizer files. If extraction creates another `models_transformer/` folder, move its model files into `models/transformer/` before starting the backend.

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

Use `python app/frontend/main.py` after setting the same variable in a pip environment. Open <http://localhost:8080>. The **Demo mode** notice should no longer be present.

### 6. Optional: add demonstration reports

A new database has no community reports. While the backend is running, add the nine labelled demo records with:

```bash
uv run python app/frontend/scripts/seed_demo_reports.py http://localhost:8000
```

The script does not delete or change existing reports. It stops if the demo records already exist unless `--force` is supplied.

## Runtime settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `CRISISLENS_RUNTIME` | Backend component mode: `real`, `mock` or `auto` | Value in `app/app_models.json` (`auto`) |
| `CRISISLENS_API_URL` | REST API used by the frontend | Empty; frontend uses demo mode |
| `CRISISLENS_DB_PATH` | SQLite database path | `app/backend/crisislens.db` |
| `PORT` | NiceGUI frontend port | `8080` |

`auto` loads the real classifier and retrieval index when both are present and otherwise uses mock components. Use `real` for an assessed or deployed run so missing artefacts cannot be hidden by fallback behaviour.

## Verify the repository

The automated tests use mock model components and a temporary database, so they do not require the large Transformer files or retrieval index:

```bash
uv run pytest
```

Static checks:

```bash
uv run ruff check .
```

With the real backend running, the recorded benchmark and failure scripts can be repeated:

```bash
uv run python scripts/benchmark_endpoints.py
uv run python scripts/test_failure_scenarios.py
```

The saved results are in `outputs/results/system/`. These scripts add local test records, so use a disposable database if the existing reports matter.

## API overview

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Show API and model runtime status |
| `POST /api/analyse` | Classify text and return related historical reports |
| `POST /api/reports` | Save a user-confirmed report |
| `GET /api/reports` | List and filter saved reports |
| `GET /api/reports/{message_id}` | Show one report and its related messages |
| `GET /api/search` | Search historical and user reports |
| `PATCH /api/reports/{message_id}` | Confirm or correct a report category or status |

FastAPI also exposes interactive API documentation at <http://localhost:8000/docs> while the backend is running.

## Reproduce the experiments

The repository keeps the experiment code and the recorded outputs used in the report:

| Work | Code or notebook | Recorded evidence |
| --- | --- | --- |
| Data preparation and EDA | `notebooks/01_crisis_eda.ipynb` | `outputs/eda/` |
| TF-IDF baseline | `models/text_baseline/` | `outputs/results/baseline/`, `outputs/predictions/baseline/` |
| Transformer training | `notebooks/member3/nb1-transformer-training_with output.ipynb` | `outputs/results/transformer/` |
| Calibration and selective prediction | `notebooks/member3/nb2_calibration_selective_with output.ipynb` | calibration tables and coverage-risk files |
| Unseen-event evaluation | `notebooks/member3/nb3_cross_event_with output.ipynb`, `evaluation/cross_event/` | `outputs/results/cross_event/` |
| Retrieval and search | `notebooks/member5/retrieval_experiments.ipynb` | `outputs/results/retrieval/` |
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
