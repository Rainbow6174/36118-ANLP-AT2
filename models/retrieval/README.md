# Retrieval and Search (Member 5)

This folder contains the retrieval and search functions of CrisisLens. The functions show
earlier reports related to a new message and allow users to search the boards by keyword.
The similarity score is provided as context for the user, not as a classification or a fact
check.

## Key Deliverables

Six functions are delivered for the backend, with `retrieve()` and `search()` as the two
main functions.

- **`retrieve(text, k, filters=None)`:** returns up to `k` earlier reports that describe the
  same type of need, damage or situation as a new message.
  - Model adopted: semantic retrieval with the sentence model `all-MiniLM-L6-v2`.
  - The model selection is presented in Section 4 (Evaluation of retrieve() and search()) of
    `notebooks/member5/retrieval_experiments.ipynb`.
- **`search(query, filters=None, k=20)`:** returns reports containing the words in the query,
  with optional filters. An empty query lists the filtered reports from newest to oldest.
  - Model adopted: TF-IDF word matching, with every word kept in the index.
  - The model selection is presented in Section 5.5 (Name Search) of the same notebook.
- **`add_to_index(message)`:** adds a saved user report to the index, or updates the report
  if its `message_id` already exists, allowing both functions to return it.
- **`remove_from_index(message_id)`:** removes a hidden or deleted user report from the
  in-memory retrieval and search indexes.
- **`warm_up()`:** loads the indexes and the sentence model and builds the search index in
  advance, ensuring that the first request does not wait.
- **`reset_index()`:** reloads the saved indexes and removes the reports added in memory.

Additionally, both `retrieve()` and `search()` group near-identical messages under one result
and accept the filters listed in the notes for Member 4.

## Dependency Change for the Group

The retrieval functions use `sentence-transformers` 5.x. This works with the
Transformers 4.x runtime used by the deployed classifier, so both components
run in the shared environment.

- **Recorded files:** the dependency was tested locally and recorded in `pyproject.toml`,
  `requirements.txt` and `uv.lock` together.
- **Related packages:** `torch` and `transformers` are installed from the shared lock file.
- **Action required:** `uv sync` should be run after pulling these changes.

## Setup

The indexes are not committed to the repository and should be built once on each machine.

1. `notebooks/01_crisis_eda.ipynb` should be run once to download the HumAID data into
   `data/raw/`.
2. The indexes are then built from the repository root with the command below.

   ```bash
   uv run python models/retrieval/build_index.py
   ```

   - **Process:** the script cleans the 76,484 HumAID messages, builds the TF-IDF index and
     embeds the messages with the sentence model.
   - **Output:** approximately 150 MB is written to `models/retrieval/index/`, which is
     excluded from Git.
   - **Run time:** the build takes 2 to 3 minutes on a CPU. The first run also downloads the
     sentence model (approximately 90 MB), which is cached for later runs.

## Backend integration

`app/backend/services.py` connects this module to the FastAPI service.

**When the server starts**

- The service resets the index, adds the visible user reports stored in SQLite
  with `add_to_index()`, and calls `warm_up()` once. Hidden reports are skipped
  when the index is rebuilt after a restart.

**When a report is saved or its board is corrected**

- The service calls `add_to_index()` so retrieval and search can return the
  updated report straight away.

**When a report is hidden or restored**

- A hidden report is removed from the live index. Restoring it adds the report
  again using its current category and status.

**When a report is deleted**

- The service calls `remove_from_index()` after the SQLite deletion succeeds,
  so the report no longer appears in retrieval or search results.

**When showing results**

- The report-detail endpoint passes `exclude_ids=[message_id]` so a report is
  not returned as its own first result.
- A message or query with no words left after cleaning (for example, only a link or an
  @username) returns no reports, while an empty query lists reports from newest to oldest.

**Errors and parallel requests**

- An unknown filter or method raises a `ValueError`, which can be returned as a 422 error.
- The functions run one at a time through a shared lock, so they are safe to call from
  parallel requests.

**Differences from the plan**

The functions follow the plan, with the additions below. All filter names in the plan are
kept.

- **Extra functions:** `add_to_index()`, `remove_from_index()`, `warm_up()` and
  `reset_index()` keep user reports in step with SQLite and load the model before the
  first request.
- **Extra parameter:** `exclude_ids` leaves out the given IDs, such as the report being
  viewed.
- **Extra result fields:** `duplicate_count` and `duplicate_ids` show the
  near-identical messages grouped under each result. Both fields are included
  in the API schema.
- **Extra filters:** `created_after` and `created_before` filter reports by posting time.

**Result fields**

Each result is returned as a dictionary with the fields below.

| Field | Meaning |
| --- | --- |
| `id` | `history-<tweet_id>` or the `message_id` of a user report |
| `similarity` | Cosine similarity, higher is closer |
| `board_label` | Board of the report |
| `text_preview` | Original message, cut at 200 characters |
| `source_type` | `humaid_history` or `user` |
| `created_at` | Posting time when available |
| `status` | Application status for user reports |
| `country`, `region`, `city` | Saved location fields for user reports |
| `duplicate_count`, `duplicate_ids` | Near-identical messages grouped under this result |

**Filters**

Each filter accepts one value or a list of values, and empty values are ignored.

- **`board_label` and `source_type`:** exact match, applied to all reports.
- **`status` and `needs_review`:** exact match, applied to user reports. `needs_review` also
  accepts "true" or "false" as text.
- **`country`, `region` and `city`:** match ignoring capital letters and surrounding spaces,
  applied to user reports.
- **`created_after` and `created_before`:** posting time on or after, and on or before, the
  given date and time (UTC), applied to all reports. A date without a time means midnight at
  the start of that day.

## Files

The folder contains the files below.

| File | Contents |
| --- | --- |
| `retrieval.py` | The functions above |
| `build_index.py` | Cleaning and index building |
| `evaluate.py` | Helper functions for the evaluation |
