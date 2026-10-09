"""Build the retrieval indexes from the HumAID messages.

Run once from the repository root, after notebooks/01_crisis_eda.ipynb has
downloaded the data:

    uv run python models/retrieval/build_index.py

The script runs three steps and saves the results to models/retrieval/index/,
which is generated and not committed:

1. Read the event-wise HumAID files, clean each message and save one table of
   historical messages (history.parquet).
2. Fit the TF-IDF index on the cleaned messages.
3. Embed the cleaned messages with the sentence model. The model is downloaded
   once into the Hugging Face cache, outside the repository.

The functions below are also used at query time by retrieval.py and by the
evaluation notebook, so new messages and search queries are cleaned and scored
in the same way as the historical messages.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVENTS_RAW = PROJECT_ROOT / "data" / "raw" / "humaid_events"
INDEX_DIR = PROJECT_ROOT / "models" / "retrieval" / "index"
HISTORY_PATH = INDEX_DIR / "history.parquet"
VECTORIZER_PATH = INDEX_DIR / "tfidf_vectorizer.joblib"
MATRIX_PATH = INDEX_DIR / "tfidf_matrix.npz"
EMBEDDINGS_PATH = INDEX_DIR / "semantic_embeddings.npy"
INFO_PATH = INDEX_DIR / "semantic_info.json"

EXPECTED_ROWS = 76_484
EXPECTED_EVENTS = 19


# ---------------------------------------------------------------------------
# Step 1: historical messages and cleaning
# ---------------------------------------------------------------------------

# Tweet IDs contain their posting time: the bits above the lowest 22 are
# milliseconds since Twitter's ID epoch (4 November 2010, 01:42:54.657 UTC).
TWITTER_EPOCH_MS = 1_288_834_974_657

# Link and @username patterns from the EDA notebook (cell 12).
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
MENTION_RE = re.compile(r"@\w+")
RETWEET_PREFIX_RE = re.compile(r"^\s*rt\s+@\w+\s*:?")
RETWEET_MARKER_RE = re.compile(r"\brt\b\s*:?")

# In the HumAID release, some emoji were saved as one Greek Extended character
# (U+1F00-U+1FFF) followed by one hex digit, e.g. "ὢ2" instead of U+1F622.
# The Greek character holds the first four hex digits of the emoji code point
# and the next character holds the last digit. Every Greek Extended character
# in HumAID follows this pattern, so no genuine Greek text is changed.
BROKEN_EMOJI_RE = re.compile(f"[{chr(0x1F00)}-{chr(0x1FFF)}][0-9A-Fa-f]")


def repair_emoji(text: str) -> str:
    """Rebuild emoji that were stored as a Greek character plus a hex digit."""
    return BROKEN_EMOJI_RE.sub(
        lambda match: chr(ord(match.group(0)[0]) * 16 + int(match.group(0)[1], 16)),
        text,
    )


def repair_text(text: str) -> str:
    """Repair emoji and HTML entities such as &amp; so the text displays as written."""
    return html.unescape(repair_emoji(text))


def clean_text(text: str | None) -> str:
    """Clean one message for ranking and duplicate grouping.

    Links, @usernames and retweet markers carry little meaning for either
    method and make copies of a message look different, so they are removed.
    Hashtag words are kept without the "#". The original text is kept
    separately for display.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = repair_text(text).lower()
    text = RETWEET_PREFIX_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = RETWEET_MARKER_RE.sub(" ", text)
    text = text.replace("#", "")
    return re.sub(r"\s+", " ", text).strip()


def tweet_time(tweet_ids: pd.Series) -> pd.Series:
    """Decode the posting time (UTC) from tweet IDs."""
    milliseconds = np.right_shift(tweet_ids.astype("int64").to_numpy(), 22) + TWITTER_EPOCH_MS
    return pd.Series(pd.to_datetime(milliseconds, unit="ms", utc=True), index=tweet_ids.index)


def load_history(data_dir: Path | str = EVENTS_RAW) -> pd.DataFrame:
    """Read the event-wise HumAID files and return one row per historical message."""
    data_dir = Path(data_dir)
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(
            f"No HumAID event files in {data_dir}. Run notebooks/01_crisis_eda.ipynb first."
        )

    rows = []
    for path in paths:
        # File names look like cyclone_idai_2019__train.json.
        event, split = path.stem.rsplit("__", 1)
        split = {"dev": "validation"}.get(split, split)
        # json keeps the 19-digit tweet IDs as exact integers.
        for record in json.loads(path.read_text(encoding="utf-8")):
            rows.append(
                {
                    "tweet_id": str(record["tweet_id"]),
                    "text": record["tweet_text"] or "",
                    "board_label": record["class_label"],
                    "event": event,
                    "split": split,
                }
            )

    history = pd.DataFrame(rows)
    history.insert(0, "id", "history-" + history["tweet_id"])
    history["text_display"] = history["text"].map(repair_text)
    history["clean_text"] = history["text"].map(clean_text)
    history["source_type"] = "humaid_history"
    history["status"] = None
    history["created_at"] = tweet_time(history["tweet_id"])

    columns = [
        "id", "text", "text_display", "clean_text", "board_label",
        "source_type", "status", "created_at", "event", "split",
    ]
    return history[columns]


def check_history(history: pd.DataFrame) -> None:
    """Stop with a clear message if the table does not match the EDA counts."""
    if len(history) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, found {len(history)}.")
    if history["event"].nunique() != EXPECTED_EVENTS:
        raise ValueError(
            f"Expected {EXPECTED_EVENTS} events, found {history['event'].nunique()}."
        )
    if history["id"].duplicated().any():
        raise ValueError("Message IDs are not unique.")


# ---------------------------------------------------------------------------
# Step 2: TF-IDF index
# ---------------------------------------------------------------------------

# Word unigrams, selected in the notebook over unigrams + bigrams.
DEFAULT_SETTINGS = {
    "lowercase": True,
    "ngram_range": (1, 1),
    "min_df": 2,
    "sublinear_tf": True,
    "norm": "l2",
}

# search() is designed for keyword searching, so it keeps every word (min_df=1) and a
# name that appears in only one message can still be found. This index is not saved:
# retrieval.py builds it in memory from all records when it is first needed.
# retrieve() and duplicate grouping keep DEFAULT_SETTINGS.
SEARCH_SETTINGS = {**DEFAULT_SETTINGS, "min_df": 1}


def fit_tfidf(
    texts: pd.Series | list[str], settings: dict | None = None
) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    """Fit a vectoriser on already-cleaned texts and return it with the document matrix."""
    vectorizer = TfidfVectorizer(**(settings or DEFAULT_SETTINGS))
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix.tocsr()


def save_tfidf(vectorizer: TfidfVectorizer, matrix: sparse.csr_matrix, index_dir: Path = INDEX_DIR) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, index_dir / VECTORIZER_PATH.name)
    sparse.save_npz(index_dir / MATRIX_PATH.name, matrix)


def load_tfidf(index_dir: Path = INDEX_DIR) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    vectorizer_path = index_dir / VECTORIZER_PATH.name
    if not vectorizer_path.exists():
        raise FileNotFoundError(
            f"No TF-IDF index in {index_dir}. Run models/retrieval/build_index.py first."
        )
    return joblib.load(vectorizer_path), sparse.load_npz(index_dir / MATRIX_PATH.name)


def tfidf_scores(text: str, vectorizer: TfidfVectorizer, matrix: sparse.csr_matrix) -> np.ndarray:
    """Cosine similarity between one raw message and every indexed message.

    Rows are L2-normalised, so the dot product equals cosine similarity.
    """
    query = vectorizer.transform([clean_text(text)])
    return (matrix @ query.T).toarray().ravel()


# ---------------------------------------------------------------------------
# Step 3: sentence-embedding (semantic) index
# ---------------------------------------------------------------------------

# Embeddings are L2-normalised, so the dot product equals cosine similarity.
# The model runs on the CPU so its timing is comparable with TF-IDF.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "cpu"
BATCH_SIZE = 64


def load_model(name: str = MODEL_NAME, device: str = DEVICE):
    """Load the pretrained model. Imported here so TF-IDF works without the package."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name, device=device)


def embed_texts(texts, model, batch_size: int = BATCH_SIZE, show_progress: bool = False) -> np.ndarray:
    """Embed already-cleaned texts as L2-normalised float32 vectors."""
    return model.encode(
        list(texts),
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    ).astype(np.float32)


def semantic_scores(text: str, model, embeddings: np.ndarray) -> np.ndarray:
    """Cosine similarity between one raw message and every embedded message."""
    query = embed_texts([clean_text(text)], model)[0]
    return embeddings @ query


def index_fingerprint(ids, texts) -> str:
    """Short fingerprint of the messages and their cleaned text, in order.

    Used to check that saved embeddings match history.parquet, including after
    a change to the cleaning steps.
    """
    lines = (f"{message_id}\t{text}" for message_id, text in zip(ids, texts))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def save_embeddings(embeddings: np.ndarray, ids, texts, index_dir: Path = INDEX_DIR) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    np.save(index_dir / EMBEDDINGS_PATH.name, embeddings)
    info = {
        "model_name": MODEL_NAME,
        "dimension": int(embeddings.shape[1]),
        "messages": int(embeddings.shape[0]),
        "fingerprint": index_fingerprint(ids, texts),
    }
    (index_dir / INFO_PATH.name).write_text(json.dumps(info, indent=2), encoding="utf-8")


def load_embeddings(ids, texts, index_dir: Path = INDEX_DIR) -> np.ndarray:
    """Load saved embeddings and check they belong to the given messages and cleaned text."""
    path = index_dir / EMBEDDINGS_PATH.name
    if not path.exists():
        raise FileNotFoundError(
            f"No semantic index in {index_dir}. Run models/retrieval/build_index.py first."
        )
    info = json.loads((index_dir / INFO_PATH.name).read_text(encoding="utf-8"))
    if info.get("fingerprint") != index_fingerprint(ids, texts):
        raise ValueError(
            "The semantic index does not match history.parquet. "
            "Rerun models/retrieval/build_index.py."
        )
    return np.load(path)


# ---------------------------------------------------------------------------
# Run all three steps
# ---------------------------------------------------------------------------

def main() -> None:
    print("Step 1 of 3: historical messages")
    history = load_history()
    check_history(history)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    history.to_parquet(HISTORY_PATH, index=False)
    emoji_repaired = history["text"].str.contains(BROKEN_EMOJI_RE).sum()
    html_repaired = (history["text"] != history["text"].map(html.unescape)).sum()
    print(f"  Messages: {len(history):,} from {history['event'].nunique()} events")
    print(f"  Repaired: {emoji_repaired:,} with broken emoji, {html_repaired:,} with HTML entities")
    print(f"  Posting times: {history['created_at'].min():%Y-%m-%d} to {history['created_at'].max():%Y-%m-%d}")

    print("Step 2 of 3: TF-IDF index")
    start = time.perf_counter()
    vectorizer, matrix = fit_tfidf(history["clean_text"])
    save_tfidf(vectorizer, matrix)
    print(f"  Vocabulary: {matrix.shape[1]:,} words, built in {time.perf_counter() - start:.1f} s")

    print("Step 3 of 3: sentence-embedding index (2 to 3 minutes on a CPU)")
    start = time.perf_counter()
    model = load_model()
    print(f"  Model loaded in {time.perf_counter() - start:.1f} s: {MODEL_NAME}")
    start = time.perf_counter()
    embeddings = embed_texts(history["clean_text"], model, show_progress=True)
    save_embeddings(embeddings, history["id"], history["clean_text"])
    print(f"  Embedded {embeddings.shape[0]:,} messages in {time.perf_counter() - start:.1f} s")

    size_mb = sum(path.stat().st_size for path in INDEX_DIR.iterdir()) / 1_000_000
    print(f"Saved {size_mb:.0f} MB to {INDEX_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
