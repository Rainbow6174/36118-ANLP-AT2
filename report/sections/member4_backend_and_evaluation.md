# Member 4: Backend, API and Cross-event Evaluation

## 5.4 Backend Architecture

### 5.4.1 Design goals

CrisisLens requires a backend that (a) serves a DistilBERT classifier and a semantic retrieval index through a REST API, (b) persists user-submitted crisis reports, and (c) supports the human review workflow where low-confidence predictions are flagged for manual checking. The design uses a ports-and-adapters architecture so that the classifier and retriever can be swapped between mock implementations (for offline testing and frontend development) and real implementations (Member 3's DistilBERT and Member 5's retrieval index) without changing any handler code.

### 5.4.2 API surface

The backend exposes six REST endpoints and a health check through FastAPI:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /api/analyse | Classify text, return 10-label prediction and related reports |
| POST | /api/reports | Persist a report with auto-assigned ID, derive status from confidence |
| GET | /api/reports | Paginated, filterable list of reports |
| GET | /api/reports/{id} | Single report with related reports from the retrieval index |
| GET | /api/search | Ranked keyword and semantic search over the retrieval index |
| PATCH | /api/reports/{id} | User correction (updates board_label) and/or status change |
| GET | /api/health | Liveness check reporting runtime mode and loaded components |

Every response conforms to Pydantic schemas enforcing the 10-label contract: probabilities must contain all 10 labels, each in [0, 1], summing to 1.0 within 1e-3 tolerance. The `predicted_label` field is immutable after creation; user corrections update `board_label` only, preserving the original model output for evaluation.

### 5.4.3 Persistence

SQLite stores user-submitted reports in a single `reports` table with 11 required columns, 5 nullable location columns, and 6 indexes. The schema is auto-applied on startup via a lifespan handler. Historical HumAID messages (76,484 records) live in the read-only retrieval index rather than SQLite, keeping the database small and the write path simple.

### 5.4.4 Runtime modes

The backend supports three modes controlled by the `CRISISLENS_RUNTIME` environment variable:

- **real**: loads Member 3's DistilBERT classifier and Member 5's retrieval index. Fails fast if model files or index are missing.
- **mock**: uses MockClassifier and MockRetriever for frontend development without model dependencies.
- **auto** (default): attempts real, falls back to mock with a warning.

A `TransformerClassifierAdapter` bridges Member 3's `classify()` return dictionary to the Pydantic `Prediction` schema. A `RetrievalAdapter` wraps Member 5's `retrieve()`, `search()`, `add_to_index()`, `warm_up()`, and `reset()` functions behind the `Retriever` protocol. On startup in real mode, any existing user reports from SQLite are loaded into the retrieval index so that search covers both historical and user-submitted messages.

### 5.4.5 Integration fixes

Two bugs were discovered and fixed during integration:

1. **DistilBERT token_type_ids error.** The HuggingFace tokenizer returns `token_type_ids` by default, but DistilBERT's architecture does not accept them. Fix: `enc.pop("token_type_ids", None)` before the forward pass in both `classify()` and `classify_batch()`.

2. **Whitespace and empty query validation.** The analyse endpoint accepted whitespace-only text (e.g. `"   "`), and the search endpoint accepted empty queries, both producing meaningless results. Fix: added a `field_validator` to `AnalyseRequest` rejecting blank-only text, and changed the search query parameter to `Query(..., min_length=1)`.

### 5.4.6 Test suite

The final test suite contains 28 tests across three files:

| File | Tests | Coverage |
| --- | --- | --- |
| test_api_integration.py | 16 | Endpoint contracts, golden path, validation, pagination, corrections |
| test_cross_event.py | 9 | Evaluator data loading, metric computation, output file generation |
| test_frontend_labels.py | 3 | Frontend strict label handling for unknown labels |

All 28 tests pass. The 7 warnings are cosmetic sklearn/starlette deprecations with no behavioural impact.

## 5.5 Cross-event Evaluation Harness

### 5.5.1 Purpose

The cross-event harness evaluates any `classify(text)`-compatible model against held-out HumAID disaster events. This tests generalisation to unseen disasters, which is the core operational requirement: the deployed model must classify messages from events it was never trained on.

### 5.5.2 Design

The harness takes a model name from a registry and a directory of HumAID event test files (`<event>__test.json`). For each event, it runs the classifier on every message and computes per-label precision, recall, F1, balanced accuracy, and a 10x10 confusion matrix. All metric calls pass `labels=LABELS` to ensure consistent output shape regardless of which labels appear in each event's test set.

Outputs per run:
- `per_event_metrics.csv`: one row per event with macro-F1, balanced accuracy, and support
- `per_label_metrics.csv`: long format (event x label) with precision, recall, F1
- `confusion_<event>.csv`: one 10x10 confusion matrix per event
- `summary.json`: mean, min, max macro-F1 across events, plus low-support flags
- `run_log.json`: model name, events evaluated, total runtime

### 5.5.3 Results

The DistilBERT model (Member 3) achieves a macro-F1 of 0.755 on seen test events and 0.697 on the held-out event (cyclone_idai_2019). The key confusion hotspots are between `other_relevant_information` and `rescue_volunteering_or_donation_effort` (299 errors) and between `not_humanitarian` and `other_relevant_information` (361 errors). These reflect genuine label ambiguity in the HumAID dataset.

## 5.6 System Evidence

### 5.6.1 Endpoint latency

Measured with 20 runs per endpoint after warm-up, on the real stack (DistilBERT + retrieval index):

| Endpoint | p50 (ms) | p95 (ms) |
| --- | --- | --- |
| GET /api/health | 1.3 | 1.9 |
| POST /api/analyse | 127.6 | 213.6 |
| POST /api/reports | 164.6 | 173.5 |
| GET /api/reports/:id | 107.6 | 157.7 |
| GET /api/reports (list) | 4.0 | 5.3 |
| GET /api/search | 40.0 | 1078.7 |
| PATCH /api/reports/:id | 192.0 | 293.6 |

The search p95 spike (1079ms) is caused by the TF-IDF index cold start on the first query; subsequent searches are consistently under 50ms. The analyse endpoint (DistilBERT inference + retrieval) completes at p50=128ms, well within interactive latency budgets.

### 5.6.2 Failure scenario testing

14 failure scenarios were tested against the live backend:

| Scenario | Result |
| --- | --- |
| Empty text, whitespace-only text, missing text field | 422 validation error |
| Long text (14,000 chars), very long text (140,000 chars) | Handled (tokenizer truncation) |
| Unicode and emoji input | Classified correctly |
| Invalid label in correction | 422 rejection |
| PATCH/GET nonexistent report | 404 |
| Historical row protection | Only source_type=user accepted |
| Empty search query | 422 rejection |
| Special characters in search (XSS) | No injection |
| Concurrent submissions (10x) | 10 unique IDs, no corruption |
| Pagination boundary (page 9999) | Empty list returned |

All 14 scenarios pass. Results are saved to `outputs/results/system/failure_scenarios.json`.
