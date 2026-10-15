"""All categories page: a link to every board."""

from components.category_card import category_card
from components.ui_kit import crisis_heading
from constants.labels import LABELS
from layout import frame
from nicegui import ui


@ui.page("/boards", title="All categories · CrisisLens")
def boards_page() -> None:
    with frame():
        with ui.column().classes("crisis-page"):
            crisis_heading("All categories", 1)
            ui.label(
                "Every report is sorted into one of ten boards. Pick a board to "
                "see the current event's reports. Empty boards may also show "
                "marked examples from past disasters."
            ).classes("text-body-sm")
            with ui.element("div").classes("crisis-category-grid"):
                for label in LABELS:
                    category_card(label)
