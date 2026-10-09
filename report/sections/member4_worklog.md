# Member 4 — Worklog

**Owner:** Kunal Mistry
**Role:** Member 4 — backend, database, API, shared evaluation harness
**Status:** 20/20 tests green · 3 of 5 planned steps complete · steps 4–5 blocked on teammates

This document is the running record of Member 4's work. It will be
compiled into `member4_backend_and_evaluation.md` for the final report.

---

## 1. What exists now

### 1.1 FastAPI backend

Six REST endpoints + a health check, all returning the JSON shapes
documented in `README.md`:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/analyse` | classify text, return 10-label prediction + related reports |
| `POST` | `/api/reports` | persist a report, assign `message_id`, derive `status` |
| `GET`  | `/api/reports` | paginated, filterable list |
| `GET`  | `/api/reports/{id}` | one report + related reports |
| `GET`  | `/api/search` | ranked search over the retrieval index |
| `PATCH`| `/api/reports/{id}` | user correction and/or status update |
| `GET`  | `/api/health` | liveness check |

Shared-contract invariants enforced in code:

- `probabilities` must contain all 10 labels; each in `[0, 1]`; sum ≈ 1.0 (±1e-3).
- `board_label` defaults to `predicted_label` on insert.
- `PATCH user_correction` updates `board_label` only; `predicted_label` is immutable.
- Historical rows (`source_type=humaid_history`) are read-only; PATCH → 403.
- New user rows start at `status=unverified`; low-confidence predictions enter `status=needs_review`.
- Filter query names honored: `q, k, page, board_label, source_type, status, country, region, city, needs_review`.

### 1.2 SQLite persistence

`app/schema.sql` defines a single `reports` table — 11 required columns
+ 5 nullable location columns + 6 indexes. The database path is
`CRISISLENS_DB_PATH` (defaults to `app/backend/crisislens.db` next to
`db.py`, resolved relative to the module). The schema is auto-applied
on FastAPI startup via a lifespan handler.

### 1.3 Mock classifier + retriever

`app/backend/ports/classifier.py` and `ports/retriever.py` define
`Protocol`s and `MockClassifier` / `MockRetriever` implementations.
Members 2, 3 and 5 drop in real implementations by registering their
loaders in `evaluation/cross_event/__main__._MODEL_REGISTRY` and (for the
API) replacing the module-level singleton in `api/analyse.py`,
`api/reports.py`, `api/search.py`.

### 1.4 Cross-event evaluation harness

`evaluation/cross_event/` runs any `classify(text)`-compatible classifier
against each HumAID event's `__test.json` split and writes:

- `per_event_metrics.csv` — one row per event
- `per_label_metrics.csv` — long format (event × label)
- `confusion_<event>.csv` — one 10×10 matrix per event
- `summary.json` — mean/min/max macro-F1 + low-support flags
- `run_log.json` — model name, events evaluated, total runtime

---

## 2. File map

```
app/
├── schema.sql                                SQLite schema (source of truth)
└── backend/
    ├── main.py                               FastAPI entrypoint + lifespan bootstrap
    ├── db.py                                 connection factory + bootstrap
    ├── store.py                              SQLite-backed CRUD
    ├── schemas.py                            Pydantic request/response models
    ├── labels.py                             10 labels + confidence threshold
    ├── ports/
    │   ├── classifier.py                     Classifier Protocol + MockClassifier
    │   └── retriever.py                      Retriever Protocol + MockRetriever
    └── api/
        ├── analyse.py                        POST /api/analyse
        ├── reports.py                        POST/GET/GET-by-id/PATCH /api/reports
        └── search.py                         GET /api/search

evaluation/
└── cross_event/
    ├── __main__.py                           CLI + model registry
    ├── evaluator.py                          data loading + orchestration + writers
    ├── metrics.py                            per-label PRF, macro-F1, bal. acc, confusion
    └── README.md                             how Members 2 and 3 invoke it

tests/
├── conftest.py                               tmp_path DB fixture + TestClient
├── test_api_integration.py                   13 API + schema-validator tests
└── test_cross_event.py                        7 evaluator tests

report/sections/
└── member4_worklog.md                        this file
```

---

## 3. Verification

```
.venv/Scripts/python.exe -m pytest tests/ -v
======================= 20 passed, 7 warnings in 2.51s ========================
```

### API & schema tests (`tests/test_api_integration.py`)

| # | Test | What it proves |
| --- | --- | --- |
| 1 | `test_health` | `/api/health` returns 200 |
| 2 | `test_analyse_shape` | 10 labels, probs sum to 1.0, bounds, keys present |
| 3 | `test_golden_path_analyse_save_browse_search` | end-to-end flow works |
| 4 | `test_post_defaults_board_to_predicted` | `board_label` defaults correctly |
| 5 | `test_patch_correction_preserves_predicted_label` | `predicted_label` is immutable |
| 6 | `test_patch_rejects_unknown_label` | Pydantic rejects → 422 |
| 7 | `test_patch_not_found` | missing id → 404 |
| 8 | `test_historical_row_is_readonly` | `humaid_history` row → 403 |
| 9 | `test_needs_review_transition` | low-conf POST → `needs_review` → resolved |
| 10 | `test_list_filter_and_pagination` | filters + `page`/`k` work |
| 11 | `test_prediction_rejects_out_of_range_probability` | probs outside `[0,1]` rejected |
| 12 | `test_prediction_rejects_probs_not_summing_to_one` | probs not summing to 1.0 rejected |
| 13 | `test_schema_has_required_fields` | all 11 README fields present |

### Cross-event tests (`tests/test_cross_event.py`)

| # | Test | What it proves |
| --- | --- | --- |
| 1 | `test_discover_test_events_finds_three` | glob + naming convention |
| 2 | `test_discover_raises_when_missing` | clean error on absent dir |
| 3 | `test_discover_raises_when_empty` | clean error on empty dir |
| 4 | `test_load_event_test_rejects_unknown_label` | label-vocab guard at load |
| 5 | `test_compute_perfect_classifier` | perfect predictions → f1=1.0 on supported labels, macro-F1 reflects support |
| 6 | `test_full_run_writes_expected_outputs` | all 5 output artefacts land correctly |
| 7 | `test_summary_flags_low_support_events` | low-support flag populated |

The 7 warnings are two cosmetic sklearn/starlette deprecations with no
behavioural impact; neither triggers on real HumAID event splits.

---

## 4. Design decisions

| Area | Decision | Rationale |
| --- | --- | --- |
| DB path | Env var `CRISISLENS_DB_PATH`, default `app/backend/crisislens.db` resolved relative to `db.py` | Tests isolate via `tmp_path`; CWD-independent in prod |
| DB connections | Open per call inside `store.*` functions | SQLite is a file; shared connections add complexity for no gain at our scale |
| Schema bootstrap | Auto-applied on FastAPI lifespan startup, idempotent | Member 6 can start the backend with one command |
| Model/retrieval wiring | `Protocol` ports + module-level mock singletons | Real swap is a one-line change in `api/*.py` |
| Classifier contract | Member 4 does **not** train; Members 2 and 3 provide trained classifiers via the shared `classify(text)` interface | Keeps evaluation independent of training |
| Cross-event mode | Single classifier evaluated on each event (no per-event retraining in the harness) | Keeps the handoff cheap; factory mode can be added later behind the same registry seam |
| Metrics vocab | sklearn calls always pass `labels=LABELS` | Output shape is `(10,)` / `(10,10)` regardless of what appears in `y_true` or `y_pred`; apples-to-apples across events |
| Location storage | Nullable `country/region/city/latitude/longitude` columns on `reports` | API filter params require storage; one table avoids a join for MVP |
| CORS | `allow_origins=["*"]` | Local-dev convenience; tighten before any shared deployment |
| Confidence threshold | `0.60` placeholder in `labels.py` | Final value depends on Member 3's calibration |

---

## 5. Local run

```
# first-time install (local only, not committed to pyproject.toml yet)
uv pip install --python .venv/Scripts/python.exe fastapi pytest

# backend
.venv/Scripts/python.exe -m uvicorn app.backend.main:app --reload
# interactive docs at http://127.0.0.1:8000/docs

# tests
.venv/Scripts/python.exe -m pytest tests/ -v

# cross-event evaluator (once Member 1's EDA has populated data/raw/humaid_events/)
.venv/Scripts/python.exe -m evaluation.cross_event \
    --model mock \
    --events-dir data/raw/humaid_events \
    --out-dir outputs/results/cross_event/mock
```

---

## 6. Local-only dependencies

Installed into `.venv` for development; **not yet** written to
`pyproject.toml` / `requirements.txt` / `uv.lock`. Batch update once
step 4 settles.

```
fastapi    0.142.0
pydantic   2.13.5
starlette  1.7.0   (fastapi transitive)
pytest     9.1.1   (dev)
httpx              (dev, already present via other deps)
```

---

## 7. Pending — blocked on other members

| # | Item | Blocked on | Trigger to resume |
| --- | --- | --- | --- |
| B1 | `app/app_models.json` — model loader config (path, label order, threshold) | Members 2 + 3 | Packaged model with loader signature exists |
| B2 | Register real models in `evaluation/cross_event/__main__._MODEL_REGISTRY` | Members 2 + 3 | Same as B1 |
| B3 | Real cross-event run → `outputs/results/cross_event/{baseline,transformer}/` | Member 1 (data) + Members 2 + 3 (models) | Member 1 publishes event files; models ready |
| B4 | Replace `MockClassifier` in `api/*.py` with the production model | Members 2 + 3 | Final model chosen |
| B5 | Replace `MockRetriever` in `api/*.py` with Member 5's retrieval backend | Member 5 | Member 5 publishes `models/retrieval/` + loader |
| B6 | `GET /api/search` semantics — DB rows, retrieval index, or union? Filter fields like `status`/`needs_review` live only on DB | Members 5 + 6 | Short alignment meeting |
| B7 | Historical-row seeding script (populates `source_type=humaid_history` rows) | Member 1's EDA output + B6 design | After B6 |
| B8 | End-to-end user-flow test — submit → classify → save → redirect → view → correct | Member 6 (frontend) + B4 + B5 | Frontend wired to real backend |
| B9 | User-study feedback integration (confidence display, review queue) | Member 6 (study) | After B8 |

## 8. Pending — Member 4's own backlog

| # | Item | Notes |
| --- | --- | --- |
| S1 | API response-time instrumentation (p50/p95 per endpoint) → `outputs/results/system/` | Deferred until step 4 so numbers reflect the real stack (task 8 of LATER_PLAN) |
| S2 | Sample-request docs — `curl` examples per endpoint + `app/backend/README.md` | Light; should land before Member 6 wires the frontend |
| S3 | Compile this worklog into `report/sections/member4_backend_and_evaluation.md` | End-of-project |
| S4 | CORS tightening (replace `allow_origins=["*"]`) | No deployment target yet |
| S5 | Tune `CONFIDENCE_REVIEW_THRESHOLD` | Depends on Member 3's calibration |
| S6 | Decide whether `location` columns move to a child table | Fine as-is for MVP |

---

## 9. Change log

### Step 1 — FastAPI skeleton + mock ports

Scaffolded the API with mock classifier and mock retriever behind
`Protocol` ports. Returned fully-shaped JSON matching the README. All 12
endpoint invariants verified live via `TestClient` before step 2 began.

### Step 2 — SQLite persistence + pytest

- Added `db.py` with env-var-driven connection + startup bootstrap.
- Rewrote `store.py` with SQLite backing behind the same public signatures (handlers untouched).
- Added lifespan handler to `main.py` so the DB schema is auto-applied; API version bumped to `0.2.0-sqlite`.
- Added `tests/conftest.py` with per-test tmp DB and `TestClient` fixture.
- Added 11 integration tests, all green.
- Removed the step-1 `_reset_for_tests()` helper from `store.py`; it was
  unused after switching to `tmp_path` and would have been a sharp edge
  (DELETE on the live reports table) if ever called from prod code.

### Step 3 — Cross-event evaluation harness

- Built `evaluation/cross_event/` (metrics + evaluator + CLI + README).
- Confirmed event file format matches the EDA notebook's loader
  (`<event>__test.json`, columns `tweet_text`, `class_label`).
- Added 7 cross-event tests on a synthetic 3-event fixture; smoke-ran the
  full pipeline against `MockClassifier` end-to-end.
- Caught my own assertion bug: I expected macro-F1 = 1.0 for a perfect
  classifier on a 3-label event; correct value is 0.3 because macro-F1
  averages over all 10 labels. Semantics intentional (apples-to-apples
  comparability); assertion fixed to match.

### Post-step audit

Re-read every file I had created and shipped a batch of fixes:

- **H2** Added bounds + sum-to-1 validation to the `Prediction` schema; two new tests cover the failure modes.
- **M1** Removed dead code (`_asdict_metrics`, `_mock_prediction_body`); cleaned imports.
- **M2** Anchored `DEFAULT_DB_PATH` and `SCHEMA_PATH` to `db.py`'s own location so launching from any CWD still works.
- **M3** Dropped a redundant `.gitignore` line.

Deferred by explicit decision: H1 (`/api/search` design) — needs
Members 5 and 6; M4 (unreachable 400 branch in PATCH) — kept as a code-path
safety net.
