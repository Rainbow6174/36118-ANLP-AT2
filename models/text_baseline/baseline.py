"""Shared utilities for the CrisisLens traditional text baseline."""

from __future__ import annotations

import re


LABEL_ORDER = [
    "caution_and_advice",
    "displaced_people_and_evacuations",
    "infrastructure_and_utility_damage",
    "injured_or_dead_people",
    "missing_or_found_people",
    "not_humanitarian",
    "other_relevant_information",
    "requests_or_urgent_needs",
    "rescue_volunteering_or_donation_effort",
    "sympathy_and_support",
]


_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"@\w+")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: object) -> str:
    """Apply the shared CrisisLens modelling text normalisation.

    The transformation mirrors the current Transformer preprocessing:
    URLs are removed, mentions are replaced with ``@user``, hashtag
    markers are removed while preserving hashtag text, and repeated
    whitespace is collapsed.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    text = _URL_RE.sub("", text)
    text = _MENTION_RE.sub("@user", text)
    text = text.replace("#", "")
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text