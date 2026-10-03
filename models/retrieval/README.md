# Retrieval and search (Member 5)

This folder provides related reports and keyword search for CrisisLens. `retrieve()` returns earlier reports that describe the same type of situation as a new message, and `search()` finds reports containing the words a user types. Similarity is context for the user, not a classification or a fact check.

## Setup

Run once from the repository root, after `notebooks/01_crisis_eda.ipynb` has downloaded the HumAID data:

```bash
uv run python models/retrieval/prepare.py
uv run python models/retrieval/tfidf_retriever.py
uv run python models/retrieval/semantic_retriever.py
```

The scripts write about 150 MB to `models/retrieval/index/`, which is not committed. The last step embeds 76,484 messages and takes 2 to 3 minutes on a CPU. The first run also downloads the sentence model `all-MiniLM-L6-v2` (about 90 MB) from Hugging Face, which is then cached.

The component adds one dependency, `sentence-transformers` (version 6.1 or later, below 7), recorded in `pyproject.toml`, `requirements.txt` and `uv.lock`. It also installs `torch` (2.14.1) and `transformers` (5.17.0).

## Usage

```python
from models.retrieval.retrieval import retrieve, search, add_to_index, warm_up, reset_index

warm_up()  # once at server start, after adding the saved user reports

related = retrieve("Families need drinking water at the shelter", k=5)
results = search("bridge", filters={"board_label": "infrastructure_and_utility_damage"}, k=20)
```

| Function | Purpose |
| --- | --- |
| `retrieve(text, k, filters=None)` | Up to `k` reports related to a message, ranked by meaning (semantic retrieval) |
| `search(query, filters=None, k=20)` | Keyword search ranked by TF-IDF word matching (an empty query lists the filtered reports newest first) |
| `add_to_index(message)` | Adds a saved user report, or updates it if its `message_id` is already indexed |
| `warm_up()` | Loads the indexes and the model and builds the search index, so the first request is fast |
| `reset_index()` | Reloads the saved indexes and drops reports added in memory |

Both `retrieve()` and `search()` also accept `method="tfidf"` or `method="semantic"`, and `exclude_ids` to leave out given IDs.

## Result fields

Each result is a dictionary of plain Python values, ready to return as JSON:

| Field | Meaning |
| --- | --- |
| `id` | `history-<tweet_id>` for historical messages, or the `message_id` of a user report |
| `similarity` | Cosine similarity, higher is closer (`None` for an empty search) |
| `board_label` | Board of the report |
| `text_preview` | Original message, cut at 200 characters |
| `source_type` | `humaid_history` or `user` |
| `duplicate_count`, `duplicate_ids` | Near-identical messages grouped under this result |

## Filters

Each filter takes one value or a list. Empty values are ignored.

| Filter | Applies to | Behaviour |
| --- | --- | --- |
| `board_label`, `source_type` | All reports | Exact match |
| `status`, `needs_review` | User reports | Exact match (`needs_review` also accepts "true" or "false" as text) |
| `country`, `region`, `city` | User reports | Match ignoring capitals and surrounding spaces |
| `created_after`, `created_before` | All reports | Posting time on or after, and on or before, the given date (UTC) |

## Notes for the backend

- **User reports:** call `add_to_index()` after each report is saved and again after a board correction. Reports are held in memory, so add the saved reports again when the server starts, before `warm_up()`.
- **Related reports for a saved report:** pass `exclude_ids=[message_id]`, otherwise the report itself is returned first with similarity 1.0.
- **New words:** the first `search()` after `add_to_index()` rebuilds the search index (under a second), so every word in the new report can be searched.
- **Errors:** an unknown filter name or method raises `ValueError`, which the API can return as a 422 response.
- **Empty text:** `retrieve()` returns no reports for a message with no words left after cleaning, such as only a link or an @username.
- **Several requests at once:** the functions take turns through one lock, so they are safe to call from parallel requests.
- **Word forms:** `search()` matches whole words only, so "bridge" does not find "bridges".

## Evidence

The evaluation is in `notebooks/member5/retrieval_experiments.ipynb`, with results in `outputs/results/retrieval/`. `metadata.json` records the selected methods and their evidence, the model version, the cleaning steps and the filters.
