# Retrieval and Search (Member 5)

This folder contains the retrieval and search functions of CrisisLens. The functions show
earlier reports related to a new message and allow users to search the boards by keyword.
The similarity score is provided as context for the user, not as a classification or a fact
check.

## Key Deliverables

Five functions are delivered for the backend, with `retrieve()` and `search()` as the two
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
- **`warm_up()`:** loads the indexes and the sentence model and builds the search index in
  advance, ensuring that the first request does not wait.
- **`reset_index()`:** reloads the saved indexes and removes the reports added in memory.

Additionally, both `retrieve()` and `search()` group near-identical messages under one result
and accept the filters listed in the notes for Member 4.

## Dependency Change for the Group

**Original member-local environment** (Member 5's development setup, kept as a record;
do not install it alongside the shared environment):

One dependency, namely `sentence-transformers` (version 6.1 or later, below 7), is added for
the retrieval functions.

- **Recorded files:** the dependency was tested locally and recorded in `pyproject.toml`,
  `requirements.txt` and `uv.lock` together.
- **Related packages:** `torch` (2.14.1) and `transformers` (5.17.0) are installed with it.
- **Action required:** `uv sync` should be run after pulling these changes.

> **Shared integrated environment (current; use this).** The merged environment pins
> `sentence-transformers>=5,<6` and `transformers>=4.40,<5`, because the deployed
> DistilBERT package needs Transformers 4.x. The retrieval functions were checked with
> this combination. Run `uv sync` and do not install the versions listed above by hand.

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

## Notes for Member 4

> **Integration note (added at merge).** These steps are now done in
> `app/backend/services.py` and `app/backend/api/reports.py`. `retrieval.py` also returns
> `created_at`, `status`, `country`, `region` and `city` so the API can show them, and the
> API schema includes `duplicate_count` and `duplicate_ids`.

**When the server starts**

- Add each user report stored in the database with `add_to_index()`. User reports are held in
  memory only, so they are cleared whenever the server stops.
- Then call `warm_up()` once, which loads the sentence model in advance (approximately 8
  seconds).

**When a report is saved or its board is corrected**

- Call `add_to_index()` with the report, so both functions can return it straight away,
  including its new words in `search()`.

**When showing results**

- For a saved report, pass `exclude_ids=[message_id]` to `retrieve()`. Otherwise, the report is
  returned as its own first result.
- A message or query with no words left after cleaning (for example, only a link or an
  @username) returns no reports, while an empty query lists reports from newest to oldest.

**Errors and parallel requests**

- An unknown filter or method raises a `ValueError`, which can be returned as a 422 error.
- The functions run one at a time through a shared lock, so they are safe to call from
  parallel requests.

**Differences from the plan**

The functions follow the plan, with the additions below. All filter names in the plan are
kept.

- **Extra functions:** `add_to_index()`, `warm_up()` and `reset_index()` are added to keep
  user reports in the index and to load the model before the first request.
- **Extra parameter:** `exclude_ids` leaves out the given IDs, such as the report being
  viewed.
- **Extra result fields:** `duplicate_count` and `duplicate_ids` show the near-identical
  messages grouped under each result. These fields are not part of the planned response and
  should be added to the API response if they are to be shown.
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
