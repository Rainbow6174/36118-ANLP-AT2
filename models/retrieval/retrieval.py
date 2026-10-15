"""Retrieval and search functions used by the backend (Member 4).

    from models.retrieval.retrieval import (
        retrieve, search, add_to_index, remove_from_index, warm_up
    )

retrieve(text, k, filters=None)   related reports for a new message
search(query, filters=None, k=20) keyword search with filters
add_to_index(message)             add or update a saved user report
remove_from_index(message_id)     remove a saved user report
warm_up()                         load the indexes and model when the server starts
reset_index()                     reload the saved indexes, dropping in-memory reports

Each result uses the shared result fields (id, similarity, board_label,
text_preview, source_type) plus duplicate_count and duplicate_ids, which list
near-duplicates grouped under the result. Similarity is context for the user,
not a label prediction or a fact check.

Setup (once, from the repository root, after the EDA notebook):

    uv run python models/retrieval/build_index.py

retrieve() ranks with DEFAULT_METHOD (semantic), selected by the evaluation
in notebooks/member5/. search() is designed for keyword searching, so it ranks
with SEARCH_METHOD (TF-IDF) on an index that keeps every word, rebuilt after a
user report is added so that every word in the report can be searched. Both
accept method="tfidf" or method="semantic". Call warm_up() once when the
backend starts, so the first request does not wait for the model and indexes
to load.

User reports added with add_to_index() are held in memory and can be removed
with remove_from_index(). The backend should add its saved user reports again
when the server starts. The public functions take turns through one lock, so
they are safe to call from several requests at once. See
models/retrieval/README.md for usage notes.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from functools import wraps

import numpy as np
import pandas as pd
from scipy import sparse

try:
    from models.retrieval.build_index import (
        HISTORY_PATH,
        SEARCH_SETTINGS,
        clean_text,
        embed_texts,
        fit_tfidf,
        load_embeddings,
        load_model,
        load_tfidf,
        repair_text,
        semantic_scores,
        tfidf_scores,
    )
except ModuleNotFoundError:  # run as a script from models/retrieval/
    from build_index import (
        HISTORY_PATH,
        SEARCH_SETTINGS,
        clean_text,
        embed_texts,
        fit_tfidf,
        load_embeddings,
        load_model,
        load_tfidf,
        repair_text,
        semantic_scores,
        tfidf_scores,
    )

# Two results are grouped when their TF-IDF similarity to each other reaches
# this value. The same rule is used whichever method ranks the results.
DUPLICATE_THRESHOLD = 0.9
PREVIEW_CHARS = 200
METHODS = ("tfidf", "semantic")
# retrieve() ranks by meaning (semantic), selected in the evaluation in notebooks/member5/.
# search() is designed for keyword searching, so it ranks by TF-IDF word matching.
DEFAULT_METHOD = "semantic"
SEARCH_METHOD = "tfidf"

EXACT_FILTERS = ("board_label", "source_type", "status", "needs_review")
LOCATION_FILTERS = ("country", "region", "city")
TIME_FILTERS = ("created_after", "created_before")
SUPPORTED_FILTERS = EXACT_FILTERS + LOCATION_FILTERS + TIME_FILTERS

RECORD_COLUMNS = [
    "id", "text_display", "clean_text", "board_label", "source_type", "status",
    "needs_review", "country", "region", "city", "created_at",
]

_state: dict | None = None
# The backend may handle several requests at once. The lock lets one call at a time read or
# change the shared index, so a search never sees a report that is only half added.
_lock = threading.RLock()


def _locked(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with _lock:
            return function(*args, **kwargs)
    return wrapper


def _get_state() -> dict:
    """Load the historical records and the TF-IDF index once, on first use."""
    global _state
    if _state is None:
        if not HISTORY_PATH.exists():
            raise FileNotFoundError(
                f"{HISTORY_PATH} not found. Run models/retrieval/build_index.py first."
            )
        history = pd.read_parquet(HISTORY_PATH)
        for column in ("needs_review", "country", "region", "city"):
            history[column] = None
        vectorizer, matrix = load_tfidf()
        _state = {
            "records": history[RECORD_COLUMNS].reset_index(drop=True),
            "vectorizer": vectorizer,
            "matrix": matrix,
            "model": None,
            "embeddings": None,
            "search_vectorizer": None,  # built on first search, see _get_search_index()
            "search_matrix": None,
        }
    return _state


@_locked
def reset_index() -> None:
    """Forget the loaded index and any user reports added in memory.

    The next call reloads the saved index files, for example after they are
    rebuilt or after temporary test reports.
    """
    global _state
    _state = None


@_locked
def warm_up(method: str = DEFAULT_METHOD) -> None:
    """Load the saved indexes and the model, build the search index and run one query each.

    Call once when the backend starts, after adding the saved user reports;
    otherwise the first request waits several seconds while the model loads.
    """
    retrieve("warm-up query", 1, method=method)
    search("warm-up query", k=1)


def _get_semantic(state: dict) -> dict:
    """Load the sentence-embedding model and embeddings on first semantic use.

    User reports added before this point are embedded here, so the embeddings
    always have one row per record, in the same order.
    """
    if state["embeddings"] is None:
        records = state["records"]
        historical = (records["source_type"] == "humaid_history").to_numpy()
        saved = load_embeddings(records.loc[historical, "id"], records.loc[historical, "clean_text"])
        model = load_model()
        embeddings = np.empty((len(records), saved.shape[1]), dtype=np.float32)
        embeddings[historical] = saved
        if (~historical).any():
            embeddings[~historical] = embed_texts(records.loc[~historical, "clean_text"], model)
        state["model"], state["embeddings"] = model, embeddings
    return state


def _get_search_index(state: dict) -> dict:
    """Build the TF-IDF index for search() from all records on first use.

    It keeps every word (SEARCH_SETTINGS), so a name that appears in only one
    message can be found. Index updates clear it, so the next search rebuilds
    it and reflects added, changed or removed user reports (under a second).
    """
    if state["search_matrix"] is None:
        state["search_vectorizer"], state["search_matrix"] = fit_tfidf(
            state["records"]["clean_text"], SEARCH_SETTINGS
        )
    return state


def _as_list(value) -> list:
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _filter_mask(records: pd.DataFrame, filters: dict | None) -> np.ndarray:
    """Rows that satisfy every filter. Empty filter values are ignored."""
    mask = np.ones(len(records), dtype=bool)
    for key, value in (filters or {}).items():
        if value is None or value == "" or value == []:
            continue
        if key not in SUPPORTED_FILTERS:
            raise ValueError(
                f"Unknown filter '{key}'. Supported filters: {', '.join(SUPPORTED_FILTERS)}."
            )
        if key == "needs_review":
            wanted = {_as_bool(v) for v in _as_list(value)}
            mask &= records[key].isin(wanted).to_numpy()
        elif key in EXACT_FILTERS:
            mask &= records[key].isin(_as_list(value)).to_numpy()
        elif key in LOCATION_FILTERS:
            wanted = {str(v).strip().casefold() for v in _as_list(value)}
            mask &= records[key].map(
                lambda v, accepted=wanted: isinstance(v, str)
                and v.strip().casefold() in accepted
            ).to_numpy()
        else:
            limit = pd.Timestamp(value)
            limit = limit.tz_localize("UTC") if limit.tzinfo is None else limit.tz_convert("UTC")
            times = records["created_at"]
            mask &= (times >= limit if key == "created_after" else times <= limit).fillna(False).to_numpy()
    return mask


def _preview(text: str) -> str:
    return text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 3].rstrip() + "..."


def _optional(value):
    """Convert pandas missing values to JSON-friendly None."""
    return None if value is None or pd.isna(value) else value


def _created_at(value) -> str | None:
    value = _optional(value)
    return None if value is None else pd.Timestamp(value).isoformat()


def _rank(
    scores: np.ndarray,
    k: int,
    filters: dict | None,
    exclude_ids,
) -> list[dict]:
    state = _get_state()
    return rank_scores(scores, k, state["records"], state["matrix"], filters, exclude_ids)


def rank_scores(
    scores: np.ndarray,
    k: int,
    records: pd.DataFrame,
    matrix: sparse.csr_matrix,
    filters: dict | None = None,
    exclude_ids=None,
    duplicate_threshold: float | None = DUPLICATE_THRESHOLD,
) -> list[dict]:
    """Filter, sort and group near-duplicates, then return the top k results.

    scores holds one similarity per row of records. matrix holds the TF-IDF
    rows of records and is used only to group near-duplicates. The
    experiments call this directly with their own indexes, so they rank
    results exactly as retrieve() and search() do. duplicate_threshold=None
    switches grouping off, which the duplicate experiments use for comparison.
    """
    mask = _filter_mask(records, filters) & (scores > 0)
    if exclude_ids:
        mask &= ~records["id"].isin(_as_list(exclude_ids)).to_numpy()
    candidates = np.flatnonzero(mask)

    # Only the best-scoring candidates are checked for duplicates, which keeps
    # a query fast. duplicate_count therefore counts duplicates in this window.
    window = min(len(candidates), max(200, 20 * k))
    top = candidates[np.argpartition(-scores[candidates], window - 1)[:window]] if window else candidates
    order = top[np.argsort(-scores[top], kind="stable")]

    kept: list[int] = []
    groups: dict[int, list[int]] = {}
    for i in order:
        if kept and duplicate_threshold is not None:
            overlap = (matrix[kept] @ matrix[i].T).toarray().ravel()
            best = int(np.argmax(overlap))
            if overlap[best] >= duplicate_threshold:
                groups[kept[best]].append(i)
                continue
        if len(kept) < k:
            kept.append(i)
            groups[i] = []

    return [
        {
            "id": records.at[i, "id"],
            "similarity": round(float(scores[i]), 4),
            "board_label": records.at[i, "board_label"],
            "text_preview": _preview(records.at[i, "text_display"]),
            "source_type": records.at[i, "source_type"],
            "created_at": _created_at(records.at[i, "created_at"]),
            "status": _optional(records.at[i, "status"]),
            "country": _optional(records.at[i, "country"]),
            "region": _optional(records.at[i, "region"]),
            "city": _optional(records.at[i, "city"]),
            "duplicate_count": len(groups[i]),
            "duplicate_ids": [records.at[j, "id"] for j in groups[i]],
        }
        for i in kept
    ]


def _scores(text: str, method: str, for_search: bool = False) -> np.ndarray:
    if method not in METHODS:
        raise ValueError(f"Unknown method '{method}'. Available methods: {', '.join(METHODS)}.")
    state = _get_state()
    if method == "semantic":
        state = _get_semantic(state)
        return semantic_scores(text, state["model"], state["embeddings"])
    if for_search:
        state = _get_search_index(state)
        return tfidf_scores(text, state["search_vectorizer"], state["search_matrix"])
    return tfidf_scores(text, state["vectorizer"], state["matrix"])


@_locked
def retrieve(
    text: str,
    k: int,
    filters: dict | None = None,
    method: str = DEFAULT_METHOD,
    exclude_ids=None,
) -> list[dict]:
    """Return up to k reports related to a new message, most similar first.

    A message with no words left after cleaning (for example only a link or an
    @username) has nothing to compare, so it returns no reports.
    """
    if not clean_text(text):
        return []
    return _rank(_scores(text, method), k, filters, exclude_ids)


@_locked
def search(
    query: str,
    filters: dict | None = None,
    k: int = 20,
    method: str = SEARCH_METHOD,
    exclude_ids=None,
) -> list[dict]:
    """Keyword search with filters, ranked by TF-IDF word matching.

    An empty query returns the reports that match the filters, newest first,
    with similarity None. A query with text but no words left after cleaning
    (for example only a link or an @username) returns no reports.
    """
    if clean_text(query):
        return _rank(_scores(query, method, for_search=True), k, filters, exclude_ids)
    if query is not None and str(query).strip():
        return []

    records = _get_state()["records"]
    mask = _filter_mask(records, filters)
    if exclude_ids:
        mask &= ~records["id"].isin(_as_list(exclude_ids)).to_numpy()
    newest = records[mask].sort_values("created_at", ascending=False, kind="stable")
    return [
        {
            "id": row.id,
            "similarity": None,
            "board_label": row.board_label,
            "text_preview": _preview(row.text_display),
            "source_type": row.source_type,
            "created_at": _created_at(row.created_at),
            "status": _optional(row.status),
            "country": _optional(row.country),
            "region": _optional(row.region),
            "city": _optional(row.city),
            "duplicate_count": 0,
            "duplicate_ids": [],
        }
        for row in newest.head(k).itertuples()
    ]


@_locked
def add_to_index(message: dict) -> None:
    """Add a saved user report, or update it if its message_id is already indexed.

    Expects the stored message fields (message_id, text,
    board_label, source_type, status, needs_review, created_at) and an optional
    location, either nested as {"location": {"country": ...}} or as flat keys.
    search() rebuilds its index on the next call, so every word in the report can
    be searched. For duplicate grouping and retrieve(method="tfidf"), words that
    are not in the historical vocabulary are ignored until the index is rebuilt.
    """
    state = _get_state()
    records, matrix = state["records"], state["matrix"]
    message_id = str(message["message_id"])
    location = message.get("location") or {}

    created_at = pd.Timestamp(message.get("created_at") or datetime.now(timezone.utc))
    created_at = created_at.tz_localize("UTC") if created_at.tzinfo is None else created_at.tz_convert("UTC")

    row = pd.DataFrame([{
        "id": message_id,
        "text_display": repair_text(message.get("text") or ""),
        "clean_text": clean_text(message.get("text")),
        "board_label": message.get("board_label") or message.get("predicted_label"),
        "source_type": message.get("source_type", "user"),
        "status": message.get("status", "unverified"),
        "needs_review": message.get("needs_review"),
        "country": location.get("country", message.get("country")),
        "region": location.get("region", message.get("region")),
        "city": location.get("city", message.get("city")),
        "created_at": created_at,
    }])
    vector = state["vectorizer"].transform([clean_text(message.get("text"))])

    keep = (records["id"] != message_id).to_numpy()
    state["records"] = pd.concat([records[keep], row], ignore_index=True)
    state["matrix"] = sparse.vstack([matrix[keep], vector]).tocsr()
    if state["embeddings"] is not None:
        embedding = embed_texts([clean_text(message.get("text"))], state["model"])
        state["embeddings"] = np.vstack([state["embeddings"][keep], embedding])
    state["search_vectorizer"] = state["search_matrix"] = None  # rebuilt on the next search


@_locked
def remove_from_index(message_id: str) -> bool:
    """Remove one report from the in-memory indexes.

    Returns True when the report was present. Historical records are protected
    by the database layer, so the backend uses this only for hidden or deleted
    user reports.
    """
    state = _get_state()
    records = state["records"]
    keep = (records["id"].astype(str) != str(message_id)).to_numpy()
    if keep.all():
        return False

    state["records"] = records.loc[keep].reset_index(drop=True)
    state["matrix"] = state["matrix"][keep].tocsr()
    if state["embeddings"] is not None:
        state["embeddings"] = state["embeddings"][keep]
    state["search_vectorizer"] = state["search_matrix"] = None
    return True


def _show(title: str, results: list[dict]) -> None:
    print(f"\n{title}")
    if not results:
        print("  (no results)")
    for rank, r in enumerate(results, start=1):
        similarity = "  n/a" if r["similarity"] is None else f"{r['similarity']:.3f}"
        duplicates = f" (+{r['duplicate_count']} similar)" if r["duplicate_count"] else ""
        print(f"  {rank}. {similarity}  {r['source_type']:<14} {r['board_label']:<38} "
              f"{r['text_preview'][:70]}{duplicates}")


def main() -> None:
    message = "Families need drinking water at the shelter"
    _show(f"retrieve('{message}', k=5)", retrieve(message, k=5))
    _show(
        "retrieve(..., k=5, filters={'board_label': 'requests_or_urgent_needs'})",
        retrieve(message, k=5, filters={"board_label": "requests_or_urgent_needs"}),
    )
    _show("search('collapsed bridge', k=5)", search("collapsed bridge", k=5))
    _show("retrieve('Praying for everyone affected by the fires', k=5)",
          retrieve("Praying for everyone affected by the fires", k=5))

    add_to_index({
        "message_id": "user-demo-1",
        "text": "Several families need drinking water near the community hall.",
        "board_label": "requests_or_urgent_needs",
        "source_type": "user",
        "status": "unverified",
        "needs_review": False,
        "location": {"country": "Australia"},
    })
    _show("After add_to_index: search('drinking water', filters={'country': 'Australia'})",
          search("drinking water", filters={"country": "Australia"}))
    _show("search('', filters={'source_type': 'user'})", search("", filters={"source_type": "user"}))

    runs = 50
    start = time.perf_counter()
    for _ in range(runs):
        retrieve(message, k=10)
    print(f"\nAverage retrieve() time over {runs} runs: "
          f"{(time.perf_counter() - start) / runs * 1000:.1f} ms")


if __name__ == "__main__":
    main()
