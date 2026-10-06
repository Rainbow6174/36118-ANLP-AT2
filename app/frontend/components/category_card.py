"""Category colours and the card and icon tile that show a category."""

from constants.labels import LABEL_DISPLAY_NAMES, LABEL_ICONS, label_colors
from nicegui import ui


def category_style(label: str) -> str:
    """Inline CSS variables with one category's colours."""
    background, accent = label_colors(label)
    return f"--category-bg: {background}; --category-accent: {accent};"


def category_card(label: str):
    """A card linking to the category's board."""
    card = (
        ui.link(target=f"/boards/{label}")
        .classes("crisis-card crisis-card--clickable crisis-category-card")
        .style(f"text-align: center; {category_style(label)}")
    )
    with card, ui.column().style("align-items: center; gap: 8px; width: 100%;"):
        ui.icon(LABEL_ICONS[label]).classes("crisis-card-icon")
        ui.label(LABEL_DISPLAY_NAMES[label]).classes("text-body-sm").style(
            "font-weight: 500;"
        )


def category_icon(label: str):
    """The coloured icon tile in a board header."""
    with ui.element("div").classes("crisis-board-icon").style(category_style(label)):
        ui.icon(LABEL_ICONS[label])
