"""Prepare the historical HumAID messages for retrieval and search.

Run from the repository root after the EDA notebook has downloaded the data:

    uv run python models/retrieval/prepare.py

The script reads the event-wise HumAID files in data/raw/humaid_events/,
builds one table of historical messages and saves it to
models/retrieval/index/history.parquet. The index folder is generated and is
not committed; rerun this script to rebuild it.

clean_text() is also used at query time, so new user messages and search
queries are cleaned in the same way as the historical messages.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVENTS_RAW = PROJECT_ROOT / "data" / "raw" / "humaid_events"
INDEX_DIR = PROJECT_ROOT / "models" / "retrieval" / "index"
HISTORY_PATH = INDEX_DIR / "history.parquet"

EXPECTED_ROWS = 76_484
EXPECTED_EVENTS = 19

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
    """Repair emoji and HTML codes such as &amp; so the text displays as written."""
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


def tweet_time(tweet_ids: pd.Series) -> pd.Series:
    """Decode the posting time (UTC) from tweet IDs."""
    milliseconds = np.right_shift(tweet_ids.astype("int64").to_numpy(), 22) + TWITTER_EPOCH_MS
    return pd.Series(pd.to_datetime(milliseconds, unit="ms", utc=True), index=tweet_ids.index)


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


def main() -> None:
    history = load_history()
    check_history(history)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    history.to_parquet(HISTORY_PATH, index=False)

    emoji_repaired = history["text"].str.contains(BROKEN_EMOJI_RE)
    html_repaired = history["text"] != history["text"].map(html.unescape)
    repaired = emoji_repaired | html_repaired
    print(f"Rows:                          {len(history):,}")
    print(f"Events:                        {history['event'].nunique()}")
    print(f"Tweets with repaired emoji:    {emoji_repaired.sum():,}")
    print(f"Tweets with repaired HTML codes: {html_repaired.sum():,}")
    print(f"Posting times:                 {history['created_at'].min():%Y-%m-%d} "
          f"to {history['created_at'].max():%Y-%m-%d}")
    print(f"Saved to:                      {HISTORY_PATH.relative_to(PROJECT_ROOT)}")

    print("\nRows per board label:")
    print(history["board_label"].value_counts().to_string())

    print("\nExamples (original -> cleaned):")
    examples = pd.concat([history[repaired].head(2), history[~repaired].head(3)])
    for _, row in examples.iterrows():
        print(f"\n[{row['id']}] {row['board_label']}")
        print(f"  original: {row['text']}")
        print(f"  display:  {row['text_display']}")
        print(f"  cleaned:  {row['clean_text']}")


if __name__ == "__main__":
    main()
