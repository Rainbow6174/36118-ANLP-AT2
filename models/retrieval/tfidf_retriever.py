"""TF-IDF index for retrieval and search.

Run from the repository root after prepare.py has saved history.parquet:

    uv run python models/retrieval/tfidf_retriever.py

The script fits a TF-IDF vectoriser on the cleaned historical messages and
saves the vectoriser and document matrix to models/retrieval/index/. The index
folder is generated and is not committed; rerun this script to rebuild it.

fit_tfidf() takes any list of texts and any settings, so the experiments can
build training-only or training + validation indexes and compare settings.

search() uses a second TF-IDF index built with SEARCH_SETTINGS. It is not saved:
retrieval.py builds it in memory from all records when it is first needed.
"""

from __future__ import annotations

import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from models.retrieval.prepare import HISTORY_PATH, INDEX_DIR, PROJECT_ROOT, clean_text
except ModuleNotFoundError:  # run as a script from models/retrieval/
    from prepare import HISTORY_PATH, INDEX_DIR, PROJECT_ROOT, clean_text

VECTORIZER_PATH = INDEX_DIR / "tfidf_vectorizer.joblib"
MATRIX_PATH = INDEX_DIR / "tfidf_matrix.npz"

# L1: word unigrams. The experiments compare this with L2 (ngram_range=(1, 2)).
DEFAULT_SETTINGS = {
    "lowercase": True,
    "ngram_range": (1, 1),
    "min_df": 2,
    "sublinear_tf": True,
    "norm": "l2",
}

# search() is designed for keyword searching, so it keeps every word (min_df=1) and a
# name that appears in only one message can still be found. retrieve() and duplicate
# grouping keep DEFAULT_SETTINGS.
SEARCH_SETTINGS = {**DEFAULT_SETTINGS, "min_df": 1}


def fit_tfidf(
    texts: pd.Series | list[str], settings: dict | None = None
) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    """Fit a vectoriser on already-cleaned texts and return it with the document matrix."""
    vectorizer = TfidfVectorizer(**(settings or DEFAULT_SETTINGS))
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix.tocsr()


def save_tfidf(
    vectorizer: TfidfVectorizer,
    matrix: sparse.csr_matrix,
    index_dir: Path = INDEX_DIR,
) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, index_dir / VECTORIZER_PATH.name)
    sparse.save_npz(index_dir / MATRIX_PATH.name, matrix)


def load_tfidf(index_dir: Path = INDEX_DIR) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    vectorizer_path = index_dir / VECTORIZER_PATH.name
    if not vectorizer_path.exists():
        raise FileNotFoundError(
            f"No TF-IDF index in {index_dir}. Run models/retrieval/tfidf_retriever.py first."
        )
    return joblib.load(vectorizer_path), sparse.load_npz(index_dir / MATRIX_PATH.name)


def tfidf_scores(
    text: str, vectorizer: TfidfVectorizer, matrix: sparse.csr_matrix
) -> np.ndarray:
    """Cosine similarity between one raw message and every indexed message.

    Rows are L2-normalised, so the dot product equals cosine similarity.
    """
    query = vectorizer.transform([clean_text(text)])
    return (matrix @ query.T).toarray().ravel()


def main() -> None:
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(
            f"{HISTORY_PATH} not found. Run models/retrieval/prepare.py first."
        )
    history = pd.read_parquet(HISTORY_PATH)

    start = time.perf_counter()
    vectorizer, matrix = fit_tfidf(history["clean_text"])
    build_seconds = time.perf_counter() - start
    save_tfidf(vectorizer, matrix)

    size_mb = (VECTORIZER_PATH.stat().st_size + MATRIX_PATH.stat().st_size) / 1_000_000
    print(f"Settings:        {DEFAULT_SETTINGS}")
    print(f"Messages:        {matrix.shape[0]:,}")
    print(f"Vocabulary size: {matrix.shape[1]:,}")
    print(f"Build time:      {build_seconds:.1f} s")
    print(f"Saved size:      {size_mb:.1f} MB")
    print(f"Saved to:        {INDEX_DIR.relative_to(PROJECT_ROOT)}/")

    # A quick look that the index works. Proper evaluation is done later.
    examples = [
        "Families need drinking water at the shelter",
        "Bridge collapsed and the main road is closed",
        "Praying for everyone affected by the fires",
    ]
    for text in examples:
        scores = tfidf_scores(text, vectorizer, matrix)
        top = np.argsort(scores)[::-1][:5]
        print(f"\nQuery: {text}")
        for rank, i in enumerate(top, start=1):
            row = history.iloc[i]
            print(f"  {rank}. {scores[i]:.3f}  {row['board_label']:<40} {row['text_display'][:90]}")


if __name__ == "__main__":
    main()
