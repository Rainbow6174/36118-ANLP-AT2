"""Evaluation helpers for the retrieval experiments.

Used by notebooks/member5/retrieval_experiments.ipynb. Experiment indexes are
built from chosen splits only (for example, training tweets for the tuning
queries), so a query is never part of the index it searches. Results are
ranked with retrieval.rank_scores(), the same ranking used by retrieve().
"""

from __future__ import annotations

import pickle
import re
import time

import numpy as np
import pandas as pd

try:
    from models.retrieval.build_index import clean_text, embed_texts, fit_tfidf, semantic_scores, tfidf_scores
    from models.retrieval.retrieval import rank_scores
except ModuleNotFoundError:  # run from models/retrieval/
    from build_index import clean_text, embed_texts, fit_tfidf, semantic_scores, tfidf_scores
    from retrieval import rank_scores

TFIDF_SETTINGS = {
    "L1": {"lowercase": True, "ngram_range": (1, 1), "min_df": 2, "sublinear_tf": True, "norm": "l2"},
    "L2": {"lowercase": True, "ngram_range": (1, 2), "min_df": 2, "sublinear_tf": True, "norm": "l2"},
}
# Names shown in tables and figures. L1 and L2 are setting labels only; both
# settings use L2 normalisation.
SETTING_NAMES = {"L1": "Unigram", "L2": "Unigram + bigram"}


def build_tfidf_index(history: pd.DataFrame, splits: list[str], settings: dict) -> dict:
    """Fit TF-IDF on the given splits and return the index with its size and build time."""
    records = history[history["split"].isin(splits)].reset_index(drop=True)
    start = time.perf_counter()
    vectorizer, matrix = fit_tfidf(records["clean_text"], settings)
    build_seconds = time.perf_counter() - start
    size_bytes = (
        matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
        + len(pickle.dumps(vectorizer))
    )
    return {
        "records": records,
        "vectorizer": vectorizer,
        "matrix": matrix,
        "messages": matrix.shape[0],
        "vocabulary": matrix.shape[1],
        "build_seconds": build_seconds,
        "size_mb": size_bytes / 1_000_000,
    }


def rank_tfidf(index: dict, text: str, k: int, exclude_ids=None, filters=None, group_matrix=None) -> list[dict]:
    """Rank with the index. group_matrix, if given, groups near-duplicates instead of the index's own matrix,
    as search() does with its all-words index."""
    scores = tfidf_scores(text, index["vectorizer"], index["matrix"])
    matrix = index["matrix"] if group_matrix is None else group_matrix
    return rank_scores(scores, k, index["records"], matrix, filters, exclude_ids)


def build_semantic_index(tfidf_index: dict, model, batch_size: int = 64) -> dict:
    """Embed the same records as a TF-IDF index.

    The TF-IDF rows are kept so near-duplicates are grouped by the same rule
    for both methods.
    """
    records = tfidf_index["records"]
    start = time.perf_counter()
    embeddings = embed_texts(records["clean_text"], model, batch_size=batch_size, show_progress=True)
    build_seconds = time.perf_counter() - start
    return {
        "records": records,
        "embeddings": embeddings,
        "matrix": tfidf_index["matrix"],
        "messages": embeddings.shape[0],
        "dimension": embeddings.shape[1],
        "build_seconds": build_seconds,
        "size_mb": embeddings.nbytes / 1_000_000,
    }


def rank_semantic(index: dict, text: str, k: int, model, exclude_ids=None, filters=None) -> list[dict]:
    scores = semantic_scores(text, model, index["embeddings"])
    return rank_scores(scores, k, index["records"], index["matrix"], filters, exclude_ids)


def rankings_table(results_by_method: dict[str, dict[str, list[dict]]]) -> pd.DataFrame:
    """Flatten {method: {query_id: results}} into one row per returned message."""
    rows = []
    for method, by_query in results_by_method.items():
        for query_id, results in by_query.items():
            for rank, r in enumerate(results, start=1):
                rows.append({
                    "method": method,
                    "query_id": query_id,
                    "rank": rank,
                    "doc_id": r["id"],
                    "similarity": r["similarity"],
                    "board_label": r["board_label"],
                    "text_preview": r["text_preview"],
                })
    return pd.DataFrame(rows)


def judgement_sheet(rankings: pd.DataFrame, queries: pd.DataFrame, seed: int) -> pd.DataFrame:
    """One row per distinct (query, message) pair, shuffled, with no method or score shown."""
    pairs = rankings.drop_duplicates(["query_id", "doc_id"])[["query_id", "doc_id", "text_preview"]]
    pairs = pairs.merge(queries[["query_id", "query_text"]], on="query_id")
    pairs = pairs.sample(frac=1, random_state=seed)
    pairs["query_order"] = pairs["query_id"].map({q: i for i, q in enumerate(queries["query_id"])})
    pairs = pairs.sort_values("query_order", kind="stable")
    sheet = pairs.rename(columns={"text_preview": "doc_text"})[
        ["query_id", "query_text", "doc_id", "doc_text"]
    ].reset_index(drop=True)
    sheet["relevant"] = ""
    return sheet


def _relevant_values(sheet: pd.DataFrame) -> pd.Series:
    """The 'relevant' column as "1", "0" or "" (empty). Raises an error for any other value."""
    values = sheet["relevant"].fillna("").astype(str).str.strip().replace({"1.0": "1", "0.0": "0"})
    invalid = ~values.isin(["", "1", "0"])
    if invalid.any():
        rows = (sheet.index[invalid] + 2).tolist()  # spreadsheet row numbers
        raise ValueError(f"'relevant' must be 1 or 0. Check spreadsheet rows: {rows}")
    return values



def precision_at_k(rankings: pd.DataFrame, judgements: pd.DataFrame, ks: tuple[int, ...] = (5, 10)) -> pd.DataFrame:
    """Precision@k per method and query. Missing results count as not relevant."""
    judged = rankings.merge(judgements, on=["query_id", "doc_id"], how="left")
    if judged["relevant"].isna().any():
        raise ValueError("Some ranked messages have no judgement.")
    rows = []
    for (method, query_id), group in judged.groupby(["method", "query_id"]):
        group = group.sort_values("rank")
        row = {"method": method, "query_id": query_id}
        for k in ks:
            row[f"precision@{k}"] = group["relevant"].head(k).sum() / k
        rows.append(row)
    return pd.DataFrame(rows)


def pooled_sheet(rankings: pd.DataFrame, queries: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Blind judgement sheet for the pooled results of every method.

    One row per distinct (query, message) pair, shuffled within each query,
    with no method, rank or score. For a paraphrased query, a message already
    in its original query's pool is marked in reused_from: its judgement is
    taken from the original query unless a value is typed in.
    """
    sheet = judgement_sheet(rankings, queries, seed)
    parents = queries.set_index("query_id")["parent_query_id"].dropna()
    pools = rankings.groupby("query_id")["doc_id"].agg(set)
    sheet["reused_from"] = [
        parents[q] if q in parents.index and doc in pools.get(parents[q], set()) else ""
        for q, doc in zip(sheet["query_id"], sheet["doc_id"])
    ]
    return sheet[["query_id", "query_text", "doc_id", "doc_text", "reused_from", "relevant"]]


def resolve_judgements(sheet: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Return all judgements, the rows still to judge and the number of reused judgements.

    An empty 'relevant' value on a reused row takes the judgement of the same
    message under the original query.
    """
    values = _relevant_values(sheet)
    reused_from = sheet["reused_from"].fillna("").astype(str).str.strip()
    own = dict(zip(zip(sheet["query_id"], sheet["doc_id"]), values))

    resolved, reused = [], 0
    for query_id, doc_id, value, parent in zip(sheet["query_id"], sheet["doc_id"], values, reused_from):
        if value == "" and parent:
            value = own.get((parent, doc_id), "")
            reused += value != ""
        resolved.append(value)
    resolved = pd.Series(resolved, index=sheet.index)

    done = resolved != ""
    judgements = sheet.loc[done, ["query_id", "doc_id"]].assign(relevant=resolved[done].astype(int))
    return judgements, int((~done).sum()), reused


def retrieval_metrics(rankings: pd.DataFrame, judgements: pd.DataFrame, ks: tuple[int, ...] = (5, 10)) -> pd.DataFrame:
    """Precision@k and pooled Recall@k per method and query.

    Pooled Recall@k divides the relevant messages in a method's top k by all
    relevant messages found in that query's pool (every method's ranked
    results). Relevant messages outside the pool were not examined, so this is
    not recall over the whole collection. It is empty for a query whose pool
    has no relevant message.
    """
    judged = rankings.merge(judgements, on=["query_id", "doc_id"], how="left")
    if judged["relevant"].isna().any():
        raise ValueError("Some ranked messages have no judgement.")
    pool_relevant = judged[judged["relevant"] == 1].groupby("query_id")["doc_id"].nunique()

    rows = []
    for (method, query_id), group in judged.groupby(["method", "query_id"]):
        group = group.sort_values("rank")
        total = pool_relevant.get(query_id, 0)
        row = {"method": method, "query_id": query_id, "pool_relevant": total}
        for k in ks:
            found = group["relevant"].head(k).sum()
            row[f"precision@{k}"] = found / k
            row[f"pooled_recall@{k}"] = found / total if total else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def time_queries(rank, texts: list[str], repeats: int = 5) -> np.ndarray:
    """Milliseconds per query for rank(text), after one warm-up query."""
    rank(texts[0])
    times = []
    for _ in range(repeats):
        for text in texts:
            start = time.perf_counter()
            rank(text)
            times.append((time.perf_counter() - start) * 1000)
    return np.array(times)


# Duplicate experiments --------------------------------------------------------

DUPLICATE_KEY_RE = re.compile(r"^rt @\w+:?\s*|https?://\S+|www\.\S+|@\w+|[^\w\s]")


def duplicate_key(text: str) -> str:
    """Text used to find real duplicates, independent of TF-IDF and embeddings.

    Lowercase, then remove a leading "RT @user:", links, @usernames and
    punctuation, and collapse spaces. This is broader than the EDA rule, which
    keeps punctuation and retweet prefixes.
    """
    return re.sub(r"\s+", " ", DUPLICATE_KEY_RE.sub(" ", text.lower())).strip()


def duplicate_groups(records: pd.DataFrame) -> pd.DataFrame:
    """Messages whose duplicate_key is shared with at least one other message."""
    keys = records["text_display"].map(duplicate_key)
    keyed = records.assign(duplicate_key=keys)[keys != ""]
    shared = keyed[keyed["duplicate_key"].duplicated(keep=False)]
    group_ids = {key: f"G{n:02d}" for n, key in enumerate(sorted(shared["duplicate_key"].unique()), start=1)}
    return shared.assign(group=shared["duplicate_key"].map(group_ids)).sort_values(["group", "id"])


COPY_TYPES = {
    "retweet": lambda text: f"RT @news_update: {text}",
    "link": lambda text: f"{text} https://t.co/x1y2z3",
    "case_punctuation": lambda text: text.upper().replace(".", "!") + " !!",
}


def make_copies(records: pd.DataFrame, n: int, seed: int, min_words: int = 5) -> pd.DataFrame:
    """Controlled copies: n sampled messages, each copied in three typical ways."""
    eligible = records[records["text_display"].str.split().str.len() >= min_words]
    originals = eligible.sample(n, random_state=seed)
    rows = []
    for original in originals.itertuples():
        for copy_type, make in COPY_TYPES.items():
            rows.append({
                "original_id": original.id,
                "copy_id": f"copy-{original.id}-{copy_type}",
                "copy_type": copy_type,
                "original_text": original.text_display,
                "copy_text": make(original.text_display),
                "board_label": original.board_label,
            })
    return pd.DataFrame(rows)


def tfidf_pair_similarity(vectorizer, texts_a, texts_b) -> np.ndarray:
    """TF-IDF cosine similarity between each pair (texts_a[i], texts_b[i])."""
    a = vectorizer.transform([clean_text(t) for t in texts_a])
    b = vectorizer.transform([clean_text(t) for t in texts_b])
    return np.asarray(a.multiply(b).sum(axis=1)).ravel()


def grouped_share(ranked_ids: list[int], matrix, threshold: float) -> tuple[int, list[tuple[int, int, float]]]:
    """How many results in an ungrouped ranking would be grouped under an earlier one."""
    kept, grouped, pairs = [], 0, []
    for i in ranked_ids:
        if kept:
            overlap = (matrix[kept] @ matrix[i].T).toarray().ravel()
            best = int(np.argmax(overlap))
            if overlap[best] >= threshold:
                grouped += 1
                pairs.append((kept[best], i, float(overlap[best])))
                continue
        kept.append(i)
    return grouped, pairs


def duplicate_recall(groups: pd.DataFrame, rank, ks: tuple[int, ...] = (5, 10)) -> pd.DataFrame:
    """For each group member used as a query, whether another member appears in the top k.

    A member counts as found when it is a result or is grouped under one.
    rank(text, k, exclude_ids) must return results in the retrieve() format.
    """
    rows = []
    for member in groups.itertuples():
        others = set(groups.loc[groups["group"] == member.group, "id"]) - {member.id}
        results = rank(member.text_display, max(ks), [member.id])
        row = {"query_id": member.id, "group": member.group}
        for k in ks:
            shown = {r["id"] for r in results[:k]} | {d for r in results[:k] for d in r["duplicate_ids"]}
            row[f"found@{k}"] = bool(shown & others)
        rows.append(row)
    return pd.DataFrame(rows)


def suppression(copies: pd.DataFrame, rank, k: int = 10) -> dict:
    """Top-k results for each original, counting its own copies shown separately.

    rank(text, k) must return results in the retrieve() format. A "family" is
    an original message and its controlled copies.
    """
    family = dict(zip(copies["copy_id"], copies["original_id"]))
    family.update({original: original for original in copies["original_id"]})
    repeated, distinct = [], []
    for original_id, group in copies.groupby("original_id", sort=False):
        results = rank(group["original_text"].iloc[0], k)
        members = [r["id"] for r in results if family.get(r["id"]) == original_id]
        repeated.append(max(len(members) - 1, 0))
        distinct.append(len({family.get(r["id"], r["id"]) for r in results}))
    return {
        "queries": len(repeated),
        "mean repeated family members in top 10": float(np.mean(repeated)),
        "queries with any repeat (%)": 100 * float(np.mean([r > 0 for r in repeated])),
        "mean distinct messages in top 10 (up to 10)": float(np.mean(distinct)),
    }


# Saved results -----------------------------------------------------------------

METHOD_NAMES = {"TF-IDF": "tfidf", "Semantic": "semantic"}


def save_rows(path, rows: pd.DataFrame, key: str) -> None:
    """Write rows into a shared results file, replacing earlier rows with the same key.

    Several notebook sections write to one file. Rerunning a section replaces
    its own rows (for example all rows with stage == "tuning") and keeps the rest.
    """
    if path.exists():
        existing = pd.read_csv(path, keep_default_na=False)
        existing = existing[~existing[key].astype(str).isin(rows[key].astype(str).unique())]
        rows = pd.concat([existing, rows], ignore_index=True)
    rows.to_csv(path, index=False)


def long_rows(table: pd.DataFrame, experiment: str, group: str = "all", subgroup: str = "all") -> pd.DataFrame:
    """Turn a table with one row per method and one column per measure into long rows."""
    long = table.rename(index=METHOD_NAMES).rename_axis("method").reset_index().melt(
        id_vars="method", var_name="measure", value_name="value"
    )
    long.insert(0, "subgroup", subgroup)
    long.insert(0, "group", group)
    long.insert(0, "experiment", experiment)
    return long[["experiment", "group", "subgroup", "method", "measure", "value"]]



def load_judgements(path, stage: str) -> pd.DataFrame:
    """Completed judgements for one stage from relevance_judgements.csv (empty if none).

    Rows whose 'relevant' cell is still empty are left out.
    """
    if not path.exists():
        return pd.DataFrame(columns=["stage", "query_id", "doc_id", "relevant", "reused_from"])
    saved = pd.read_csv(path, dtype=str, keep_default_na=False)
    saved = saved[(saved["stage"] == stage) & (saved["relevant"].str.strip() != "")]
    return saved.assign(relevant=saved["relevant"].str.strip().astype(float).astype(int)).reset_index(drop=True)


JUDGEMENT_COLUMNS = ["stage", "query_id", "query_text", "doc_id", "doc_text", "relevant", "reused_from"]


def collect_judgements(stage: str, rankings: pd.DataFrame, queries: pd.DataFrame,
                       judgements_path, seed: int) -> tuple[pd.DataFrame | None, int, int, str]:
    """Judgements for every ranked message of one stage, kept in relevance_judgements.csv.

    Ranked messages that have no row yet are added to the file with an empty
    'relevant' cell, shuffled within each query and without the method, rank
    or score, so they can be judged blind in the same file. For a paraphrased
    query, a message already judged for its original query is prefilled and
    marked in reused_from; it can still be changed. Returns (judgements, rows
    still empty, rows marked in reused_from, status message).
    """
    if judgements_path.exists():
        all_rows = pd.read_csv(judgements_path, dtype=str, keep_default_na=False)
    else:
        all_rows = pd.DataFrame(columns=JUDGEMENT_COLUMNS)
    rows = all_rows[all_rows["stage"] == stage].reset_index(drop=True)

    known = set(zip(rows["query_id"], rows["doc_id"]))
    judged = {(q, d): v for q, d, v in zip(rows["query_id"], rows["doc_id"], rows["relevant"].str.strip()) if v}
    new = pooled_sheet(rankings, queries, seed)
    new = new[[(q, d) not in known for q, d in zip(new["query_id"], new["doc_id"])]].reset_index(drop=True)
    if len(new):
        new["relevant"] = [
            judged.get((parent, doc), "") if parent else ""
            for parent, doc in zip(new["reused_from"], new["doc_id"])
        ]
        rows = pd.concat([rows, new.assign(stage=stage)[JUDGEMENT_COLUMNS]], ignore_index=True)
        save_rows(judgements_path, rows, key="stage")

    judgements, remaining, _ = resolve_judgements(rows)
    reused = int((rows["reused_from"].astype(str).str.strip() != "").sum())
    if remaining:
        return None, remaining, reused, (
            f"{remaining} '{stage}' rows in {judgements_path.name} still need a judgement "
            "(empty 'relevant' cell). Fill them in and run the notebook again."
        )
    return judgements, 0, reused, f"Using {len(judgements)} {stage} judgements from {judgements_path.name}."
