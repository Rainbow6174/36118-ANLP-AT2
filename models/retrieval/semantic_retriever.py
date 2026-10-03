"""Sentence-embedding index for retrieval (experimental alternative to TF-IDF).

Run from the repository root after prepare.py has saved history.parquet:

    uv run python models/retrieval/semantic_retriever.py

The script embeds the cleaned historical messages with a pretrained
sentence-embedding model and saves the embeddings to models/retrieval/index/.
The model is downloaded once into the Hugging Face cache, outside the
repository. The index folder is generated and is not committed.

Embeddings are L2-normalised, so the dot product equals cosine similarity.
The model runs on the CPU so its timing is comparable with TF-IDF.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from models.retrieval.prepare import HISTORY_PATH, INDEX_DIR, PROJECT_ROOT, clean_text
except ModuleNotFoundError:  # run as a script from models/retrieval/
    from prepare import HISTORY_PATH, INDEX_DIR, PROJECT_ROOT, clean_text

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "cpu"
BATCH_SIZE = 64

EMBEDDINGS_PATH = INDEX_DIR / "semantic_embeddings.npy"
INFO_PATH = INDEX_DIR / "semantic_info.json"


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
            f"No semantic index in {index_dir}. Run models/retrieval/semantic_retriever.py first."
        )
    info = json.loads((index_dir / INFO_PATH.name).read_text(encoding="utf-8"))
    if info.get("fingerprint") != index_fingerprint(ids, texts):
        raise ValueError(
            "The semantic index does not match history.parquet. "
            "Rerun models/retrieval/semantic_retriever.py."
        )
    return np.load(path)


def main() -> None:
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"{HISTORY_PATH} not found. Run models/retrieval/prepare.py first.")
    history = pd.read_parquet(HISTORY_PATH)

    start = time.perf_counter()
    model = load_model()
    load_seconds = time.perf_counter() - start

    start = time.perf_counter()
    embeddings = embed_texts(history["clean_text"], model, show_progress=True)
    build_seconds = time.perf_counter() - start
    save_embeddings(embeddings, history["id"], history["clean_text"])

    print(f"Model:           {MODEL_NAME} on {DEVICE}")
    print(f"Messages:        {embeddings.shape[0]:,}")
    print(f"Dimension:       {embeddings.shape[1]}")
    print(f"Model load time: {load_seconds:.1f} s")
    print(f"Build time:      {build_seconds:.1f} s")
    print(f"Saved size:      {EMBEDDINGS_PATH.stat().st_size / 1_000_000:.1f} MB")
    print(f"Saved to:        {INDEX_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
