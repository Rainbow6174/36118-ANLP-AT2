"""Badges for status, source and category, so their wording stays the same everywhere."""

from constants.labels import LABEL_DISPLAY_NAMES, LABEL_ICONS
from nicegui import ui

from components.category_card import category_style


def badge(text: str, tone: str = "neutral"):
    """A small pill label."""
    return ui.label(text).classes(f"crisis-badge crisis-badge--{tone}")


def status_badges(status: str) -> None:
    """Always "Unverified" (reports are never fact-checked), plus whether the category was reviewed."""
    badge("Unverified", "neutral")
    if status == "needs_review":
        badge("⚠ Category needs review", "review")
    elif status == "resolved":
        badge("✓ Category reviewed", "success")


def source_badge(source_type: str):
    if source_type == "humaid_history":
        return badge("Historical reference", "neutral")
    return badge("Community report", "primary")


def demo_badge():
    """Marks synthetic records."""
    return badge("Demo data", "neutral")


def category_badge(label: str):
    """A category in its own colour; Urgent Needs gets an extra class."""
    extra_class = (
        " crisis-category-badge--urgent" if label == "requests_or_urgent_needs" else ""
    )

    with (
        ui.element("span")
        .classes(f"crisis-badge crisis-category-badge{extra_class}")
        .style(category_style(label))
    ):
        ui.icon(LABEL_ICONS[label])
        ui.label(LABEL_DISPLAY_NAMES[label])
