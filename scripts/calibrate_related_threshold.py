"""Choose the minimum similarity for "similar reports" from Member 5's judgements.

Member 5 judged 1,427 (query, message) pairs by hand: a message is relevant when it
describes the same type of need, damage or situation as the query. This script
scores every pair with the deployed MiniLM model, chooses the threshold on the
tuning queries and reports how it performs on the final queries, which were not
used for the choice.

Run from the repository root, with the retrieval index built:
    python scripts/calibrate_related_threshold.py
Writes outputs/results/retrieval/related_threshold.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.retrieval import retrieval
from models.retrieval.retrieval import clean_text, embed_texts

JUDGEMENTS = ROOT / "outputs" / "results" / "retrieval" / "relevance_judgements.csv"
OUTPUT = ROOT / "outputs" / "results" / "retrieval" / "related_threshold.csv"
# A similar report shown to the user should be relevant at least this often,
# matching the Precision@5 reached by semantic retrieval (0.800).
TARGET_PRECISION = 0.80
CANDIDATES = np.round(np.arange(0.20, 0.81, 0.01), 2)


def pair_similarities(judgements: pd.DataFrame) -> pd.Series:
    state = retrieval._get_semantic(retrieval._get_state())
    records, embeddings, model = state["records"], state["embeddings"], state["model"]
    row_of = pd.Series(np.arange(len(records)), index=records["id"].astype(str))

    queries = judgements["query_text"].drop_duplicates()
    query_vectors = dict(zip(queries, embed_texts(queries.map(clean_text), model)))
    doc_vectors = embeddings[row_of.loc[judgements["doc_id"].astype(str)].to_numpy()]
    query_matrix = np.stack([query_vectors[q] for q in judgements["query_text"]])
    # Both sides are normalised by embed_texts, so the dot product is the cosine.
    return pd.Series((query_matrix * doc_vectors).sum(axis=1), index=judgements.index)


def scores(frame: pd.DataFrame, threshold: float) -> dict:
    shown = frame[frame["similarity"] >= threshold]
    relevant = frame["relevant"] == 1
    return {
        "threshold": threshold,
        "shown": len(shown),
        "precision": shown["relevant"].mean() if len(shown) else np.nan,
        "recall": (shown["relevant"] == 1).sum() / relevant.sum(),
    }


def main() -> None:
    judgements = pd.read_csv(JUDGEMENTS)
    judgements["similarity"] = pair_similarities(judgements)
    tuning = judgements[judgements["stage"] == "tuning"]
    final = judgements[judgements["stage"] == "final"]

    table = pd.DataFrame([scores(tuning, t) for t in CANDIDATES])
    meets = table[table["precision"] >= TARGET_PRECISION]
    # The lowest threshold that meets the target keeps as many relevant reports as possible.
    chosen = float(meets["threshold"].min())

    for name, frame in (("relevant", judgements[judgements["relevant"] == 1]),
                        ("not relevant", judgements[judgements["relevant"] == 0])):
        q = frame["similarity"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(3).tolist()
        print(f"{name:13s} n={len(frame):4d} similarity quantiles 10/25/50/75/90%: {q}")

    result = pd.DataFrame(
        [
            {"set": "tuning", **scores(tuning, chosen)},
            {"set": "final (held out)", **scores(final, chosen)},
        ]
    )
    print(f"\nChosen threshold (tuning precision >= {TARGET_PRECISION}): {chosen}")
    print(result.round(3).to_string(index=False))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.round(4).to_csv(OUTPUT, index=False)
    print(f"\nWrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
