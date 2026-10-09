"""Board page: the reports of one category, community reports apart from historical ones."""

import asyncio

from components.category_card import category_icon
from components.report_cards import crisis_pagination, report_card, report_count
from components.ui_kit import (
    crisis_alert,
    crisis_button,
    crisis_empty_state,
    crisis_error_state,
    crisis_heading,
    crisis_select,
)
from constants.labels import (
    LABEL_DESCRIPTIONS,
    LABEL_DISPLAY_NAMES,
    LABELS,
    STATUS_FILTER_OPTIONS,
)
from layout import PAGE_RESPONSE_TIMEOUT_SECONDS, frame
from nicegui import ui
from services import api

PAGE_SIZE = 5


@ui.page("/boards/{label}", response_timeout=PAGE_RESPONSE_TIMEOUT_SECONDS)
async def board_page(label: str, new: str = "") -> None:
    """`new` is the id of a report that was just published."""
    if label not in LABELS:
        with frame():
            crisis_empty_state(
                "search_off",
                "Unknown category",
                "That board does not exist.",
                "See all categories",
                "/boards",
            )
        return

    name = LABEL_DISPLAY_NAMES[label]
    ui.page_title(f"{name} · CrisisLens")
    state = {"page": 1, "status": "all"}

    # Extras loaded together; if they fail, the board still shows.
    async def load_published():
        try:
            return await api.get_report(new) if new else None
        except api.BackendError:
            return None

    async def load_history():
        try:
            return await api.list_reports(
                board_label=label, source_type="humaid_history", page=1, page_size=3
            )
        except api.BackendError:
            return None

    published, history = await asyncio.gather(load_published(), load_history())

    @ui.refreshable
    async def community_reports() -> None:
        try:
            result = await api.list_reports(
                board_label=label,
                source_type="user",
                status=None if state["status"] == "all" else state["status"],
                page=state["page"],
                page_size=PAGE_SIZE,
            )
        except api.BackendError:
            crisis_error_state(
                "The reports could not be loaded. Check your connection.",
                community_reports.refresh,
            )
            return

        if not result.items:
            filtered = state["status"] != "all"
            crisis_empty_state(
                "forum",
                "No reports match" if filtered else "No reports on this board yet",
                (
                    "Try a different status."
                    if filtered
                    else "Reports sorted into this category will appear here."
                ),
                None if filtered else "Report a crisis",
                None if filtered else "/submit",
            )
            return

        ui.label(report_count(result.total)).classes("text-body-sm")
        with ui.column().classes("crisis-report-list"):
            for report in result.items:
                report_card(report, highlight=report.message_id == new)
        crisis_pagination(result.page, result.total_pages, go_to_page)

    def go_to_page(page: int) -> None:
        state["page"] = page
        community_reports.refresh()

    def apply_filters() -> None:
        state["status"] = status_select.value or "all"
        state["page"] = 1
        community_reports.refresh()

    with frame():
        with ui.column().classes("crisis-page"):
            with ui.element("div").classes("crisis-board-header"):
                category_icon(label)
                with ui.column().style("gap: 2px;"):
                    crisis_heading(name, 1)
                    ui.label(LABEL_DESCRIPTIONS[label]).classes("text-body-sm")

            if published is not None and published.board_label == label:
                crisis_alert(
                    "success",
                    f"Your report was published to {name}",
                    (
                        "The model was unsure about its category, so it is also "
                        "listed in the Review queue for a second check."
                        if published.status == "needs_review"
                        else "CrisisLens does not check whether a report is true, "
                        "so it is shown as Unverified."
                    ),
                )

            with ui.column().classes("crisis-section"):
                with ui.element("div").classes("crisis-section-head"):
                    crisis_heading("Community reports", 2)
                    crisis_button(
                        "Report a crisis",
                        variant="secondary",
                        icon="add_circle_outline",
                        on_click=lambda: ui.navigate.to("/submit"),
                    )

                with ui.element("div").classes("crisis-filter-row"):
                    status_select = crisis_select(
                        "Status", STATUS_FILTER_OPTIONS, "all"
                    )
                    status_select.on_value_change(apply_filters)

                await community_reports()

            if history is not None and history.items:
                with ui.column().classes("crisis-section"):
                    crisis_heading("Related historical references", 2)
                    ui.label(
                        "Past examples for context. These are not current reports."
                    ).classes("text-body-sm")
                    with ui.column().classes("crisis-report-list"):
                        for report in history.items:
                            report_card(report)
