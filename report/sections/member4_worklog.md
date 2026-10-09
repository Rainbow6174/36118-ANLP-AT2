# Member 4 — Worklog

**Owner:** Kunal Mistry
**Role:** Member 4 — backend, database, API, shared evaluation harness
**Status:** backend and evaluation handoff complete; final model and retrieval wiring added on the integration branch

> Integration update: `app/backend/services.py` now loads the selected Member 3 classifier and Member 5 retrieval index through the existing ports. The API entry point, schema, database path and endpoint paths remain unchanged. Mock mode is retained for tests and isolated frontend work.

This document records Member 4's backend and evaluation contribution and is
source material for the final group report.

---

## 1. What exists now

### 1.1 FastAPI backend

Six REST endpoints + a health check, all returning the JSON shapes
documented in `README.md`:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/analyse` | classify text, return 10-label prediction + related reports |
| `POST` | `/api/reports` | persist a report, assign `message_id`, derive `status` |
| `GET`  | `/api/reports` | paginated, filterable list of saved user reports |
| `GET`  | `/api/reports/{id}` | one report + related reports |
| `GET`  | `/api/search` | ranked search over the retrieval index |
| `PATCH`| `/api/reports/{id}` | user correction and/or status update |
| `GET`  | `/api/health` | liveness check |

Shared-contract invariants enforced in code:

- `probabilities` must contain all 10 labels; each in `[0, 1]`; sum ≈ 1.0 (±1e-3).
- `board_label` defaults to `predicted_label` on insert.
- `PATCH user_correction` updates `board_label` only; `predicted_label` is immutable.
- The public POST endpoint accepts `source_type=user` only. If an internal
  database contains a historical row, PATCH rejects it with 403.
- New user rows start at `status=unverified`; low-confidence predictions enter `status=needs_review`.
- Filter query names honored: `q, k, page, board_label, source_type, status, country, region, city, needs_review`.

### 1.2 SQLite persistence

`app/schema.sql` defines a single `reports` table — 11 required columns
+ 5 nullable location columns + 6 indexes. The database path is
`CRISISLENS_DB_PATH` (defaults to `app/backend/crisislens.db` next to
`db.py`, resolved relative to the module). The schema is auto-applied
on FastAPI startup via a lifespan handler.

### 1.3 Classifier and retriever ports

`app/backend/ports/classifier.py` and `ports/retriever.py` define
`Protocol`s and `MockClassifier` / `MockRetriever` implementations.
`app/backend/services.py` now provides the application assembly layer.
It loads the selected real classifier and retrieval index in `real`
mode, or the mock implementations in `mock` mode. API modules ask this
service for the active implementation, so their routes do not need to
know how either model is stored.

### 1.4 Cross-event evaluation harness

`evaluation/cross_event/` provides reusable loaders, metrics and writers for
any `classify(text)`-compatible classifier. Its generic runner evaluates event
`__test.json` files and writes:

- `per_event_metrics.csv` — one row per event
- `per_label_metrics.csv` — long format (event × label)
- `confusion_<event>.csv` — one 10×10 matrix per event
- `summary.json` — mean/min/max macro-F1 + low-support flags
- `run_log.json` — model name, events evaluated, total runtime

The final shared stress test is stricter than the generic runner: Members 2
and 3 remove `cyclone_idai_2019` before training on the other 12 events in the
13-event subset, then evaluate on its 779 test messages. Their model-specific
training code and saved outputs are linked from
`evaluation/cross_event/README.md`.

---

## 2. File map

```
app/
├── app_models.json                           selected model and index paths
├── schema.sql                                SQLite schema (source of truth)
└── backend/
    ├── main.py                               FastAPI entrypoint + lifespan bootstrap
    ├── db.py                                 connection factory + bootstrap
    ├── store.py                              SQLite-backed CRUD
    ├── services.py                           real/mock component assembly
    ├── schemas.py                            Pydantic request/response models
    ├── labels.py                             shared 10-label order
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
├── test_api_integration.py                   16 API + schema-validator tests
└── test_cross_event.py                        8 evaluator tests

report/sections/
└── member4_worklog.md                        this file
```

---

## 3. Verification

```
uv run pytest tests/ -q
24 passed, 7 warnings
```

### API & schema tests (`tests/test_api_integration.py`)

| # | Test | What it proves |
| --- | --- | --- |
| 1 | `test_health` | `/api/health` returns 200 |
| 2 | `test_analyse_shape` | 10 labels, probs sum to 1.0, bounds, keys present |
| 3 | `test_golden_path_analyse_save_browse_search` | end-to-end flow works |
| 4 | `test_empty_search_supports_filtered_history_browsing` | an empty query can browse a filtered board |
| 5 | `test_analyse_filters_related_items_to_predicted_board` | related items stay in the predicted board |
| 6 | `test_post_defaults_board_to_predicted` | `board_label` defaults correctly |
| 7 | `test_post_rejects_historical_source_type` | public POST accepts user reports only |
| 8 | `test_patch_correction_preserves_predicted_label` | `predicted_label` is immutable |
| 9 | `test_patch_rejects_unknown_label` | Pydantic rejects → 422 |
| 10 | `test_patch_not_found` | missing id → 404 |
| 11 | `test_historical_row_is_readonly` | `humaid_history` row → 403 |
| 12 | `test_needs_review_transition` | low-conf POST → `needs_review` → resolved |
| 13 | `test_list_filter_and_pagination` | filters + `page`/`k` work |
| 14 | `test_prediction_rejects_out_of_range_probability` | probs outside `[0,1]` rejected |
| 15 | `test_prediction_rejects_probs_not_summing_to_one` | probs not summing to 1.0 rejected |
| 16 | `test_schema_has_required_fields` | all 11 README fields present |

### Cross-event tests (`tests/test_cross_event.py`)

| # | Test | What it proves |
| --- | --- | --- |
| 1 | `test_discover_test_events_finds_three` | glob + naming convention |
| 2 | `test_discover_raises_when_missing` | clean error on absent dir |
| 3 | `test_discover_raises_when_empty` | clean error on empty dir |
| 4 | `test_load_event_test_rejects_unknown_label` | label-vocab guard at load |
| 5 | `test_compute_perfect_classifier` | perfect predictions → f1=1.0 on supported labels, macro-F1 reflects support |
| 6 | `test_evaluator_accepts_dictionary_predictions` | evaluator accepts the packaged models' dictionary response |
| 7 | `test_full_run_writes_expected_outputs` | all output artefacts land correctly |
| 8 | `test_summary_flags_low_support_events` | low-support flag populated |

The 7 warnings are one Starlette test-client deprecation and six expected
sklearn warnings from the small synthetic event fixtures. They do not change
the test results.

---

## 4. Design decisions

| Area | Decision | Rationale |
| --- | --- | --- |
| DB path | Env var `CRISISLENS_DB_PATH`, default `app/backend/crisislens.db` resolved relative to `db.py` | Tests isolate via `tmp_path`; CWD-independent in prod |
| DB connections | Open per call inside `store.*` functions | SQLite is a file; shared connections add complexity for no gain at our scale |
| Schema bootstrap | Auto-applied on FastAPI lifespan startup, idempotent | Member 6 can start the backend with one command |
| Model/retrieval wiring | `Protocol` ports + `app/backend/services.py` | Keeps API routes stable while real and mock components use the same contract |
| Classifier contract | Member 4 does **not** train; Members 2 and 3 provide trained classifiers via the shared `classify(text)` interface | Keeps evaluation independent of training |
| Cross-event mode | Generic harness evaluates a supplied classifier; the final Member 2/3 stress test retrains after removing Cyclone Idai | Separates reusable metrics from the model-specific no-leakage training protocol |
| Metrics vocab | sklearn calls always pass `labels=LABELS` | Output shape is `(10,)` / `(10,10)` regardless of what appears in `y_true` or `y_pred`; apples-to-apples across events |
| Location storage | Nullable `country/region/city/latitude/longitude` columns on `reports` | API filter params require storage; one table avoids a join for MVP |
| CORS | `allow_origins=["*"]` | Local-dev convenience; tighten before any shared deployment |
| Confidence threshold | Owned by the selected Member 3 model metadata | The deployed DistilBERT uses its calibrated temperature and review threshold |

---

## 5. Local run

Install the shared environment from the repository root:

```bash
uv sync
```

For lightweight API work on PowerShell, start the mock runtime:

```powershell
$env:CRISISLENS_RUNTIME="mock"
uv run uvicorn app.backend.main:app --reload
```

The interactive API documentation is at `http://127.0.0.1:8000/docs`.
Run the tracked backend and evaluator tests with:

```bash
uv run pytest tests/ -q
```

The real runtime needs Member 3's release files and Member 5's locally built
index. `README.md` gives the exact preparation and launch commands. The mock
CLI below remains a quick check of the generic event evaluator:

```bash
uv run python -m evaluation.cross_event \
    --model mock \
    --events-dir data/raw/humaid_events \
    --out-dir outputs/results/cross_event/mock
```

---

## 6. Shared dependencies

The backend, frontend, model and retrieval dependencies are recorded together
in `pyproject.toml`, `requirements.txt` and `uv.lock`. `uv sync` installs the
agreed environment. Important compatibility ranges include
`transformers >=4.40,<5`, `sentence-transformers >=5,<6` and `torch >=2.2,<3`.
Any later dependency change should be tested locally before all three shared
dependency files are updated.

---

## 7. Integration outcome

| Area | Current state |
| --- | --- |
| Selected components | `app/app_models.json` points to Member 3's Transformer and Member 5's retrieval index |
| Runtime wiring | `app/backend/services.py` loads real components or the explicit mock fallback |
| Model results | Baseline and Transformer results are saved under `outputs/results/` and `outputs/results/cross_event/` |
| Search behaviour | The read-only HumAID index and saved user reports share Member 5's search interface |
| Persistence | Only user submissions are created through `POST /api/reports`; historical examples remain in the retrieval index |
| Frontend connection | Member 6's frontend calls the documented REST API without loading models or SQLite directly |
| Automated checks | 16 API/schema tests and 8 evaluator tests pass in the tracked suite |

The historical HumAID rows are not copied into SQLite. They remain in the
read-only retrieval index, while saved and corrected user reports are replayed
from SQLite when the real service starts.

## 8. Remaining final-submission evidence

These items are not implemented results yet and should be added only after the
team has measured or verified them:

1. Run the full frontend and backend with the downloaded Member 3 model and
   locally built Member 5 index. Record the complete submit, save, redirect,
   browse, search and correction flow.
2. Save API latency, failure behaviour and runtime details under
   `outputs/results/system/`.
3. Complete the user study and one evidence-based interface revision.
4. Add verified cloud URLs and hosting instructions if the team deploys the
   application.
5. Tighten CORS and add access control if the application becomes a public
   service rather than a class demonstration.
6. Select final screenshots and combine this worklog with the other report
   sections.

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

The later integration resolved the search design: Member 5's index holds the
read-only HumAID history and replays saved user reports from SQLite. Member 6
uses that interface through the API. Open CORS remains suitable for the class
demo but must be narrowed if a public deployment adds access control.
