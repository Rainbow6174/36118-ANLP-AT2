"""Review queue: reports whose category the model was unsure about (confirming never means the report is true)."""

from components.report_cards import (
    crisis_pagination,
    report_badges,
    report_count,
    report_meta,
    suggestion_text,
)
from components.ui_kit import (
    crisis_alert,
    crisis_button,
    crisis_card,
    crisis_empty_state,
    crisis_error_state,
    crisis_heading,
    crisis_select,
)
from constants.labels import LABEL_DISPLAY_NAMES
from layout import PAGE_RESPONSE_TIMEOUT_SECONDS, frame
from nicegui import ui
from schemas.api import CrisisReport
from services import api

PAGE_SIZE = 5


@ui.page(
    "/review",
    title="Review queue · CrisisLens",
    response_timeout=PAGE_RESPONSE_TIMEOUT_SECONDS,
)
async def review_page() -> None:
    state = {"page": 1}

    async def confirm(report: CrisisReport, category: str) -> None:
        try:
            await api.update_report(
                report.message_id,
                board_label=None if category == report.board_label else category,
                status="resolved",
            )
        except api.BackendError:
            ui.notify("This report could not be updated.", type="negative")
            return
        ui.notify(
            f"Category confirmed: {LABEL_DISPLAY_NAMES[category]}", type="positive"
        )
        queue.refresh()

    def go_to_page(page: int) -> None:
        state["page"] = page
        queue.refresh()

    async def fetch_page():
        return await api.list_reports(
            source_type="user",
            status="needs_review",
            page=state["page"],
            page_size=PAGE_SIZE,
        )

    @ui.refreshable
    async def queue() -> None:
        try:
            result = await fetch_page()
            if not result.items and state["page"] > 1:
                # The last item of this page was just reviewed: step back a page.
                state["page"] = result.total_pages
                result = await fetch_page()
        except api.BackendError:
            crisis_error_state(
                "The review queue could not be loaded. Check your connection.",
                queue.refresh,
            )
            return

        if not result.items:
            crisis_empty_state(
                "task_alt",
                "Nothing is waiting for review",
                "Reports the model is unsure about will appear here.",
                "Browse reports",
                "/search",
            )
            return

        ui.label(f"{report_count(result.total)} waiting").classes("text-body-sm")
        with ui.column().classes("crisis-report-list"):
            for report in result.items:
                review_item(report)
        crisis_pagination(result.page, result.total_pages, go_to_page)

    def review_item(report: CrisisReport) -> None:
        with crisis_card().classes("crisis-report-card"):
            report_badges(report, show_category=True)
            ui.label(report.text).classes("text-body crisis-report-full-text")
            report_meta(report)
            ui.label(suggestion_text(report)).classes("text-body-sm")

            with ui.element("div").classes("crisis-review-actions"):
                category = crisis_select(
                    "Category", LABEL_DISPLAY_NAMES, report.board_label
                )
                crisis_button(
                    "Confirm category",
                    icon="check",
                    on_click=lambda _=None, r=report, c=category: confirm(r, c.value),
                )
                crisis_button(
                    "Open report",
                    variant="ghost",
                    icon="open_in_new",
                    on_click=lambda _=None, r=report: ui.navigate.to(
                        f"/reports/{r.message_id}"
                    ),
                )

    with frame():
        with ui.column().classes("crisis-page"):
            crisis_heading("Review queue", 1)
            crisis_alert(
                "review",
                "These categories are less certain",
                "Check each category and confirm it or choose a better one. "
                "Confirming records that a person checked the sorting. It does "
                "not mean the report has been verified as true.",
            )
            ui.label(
                "In this prototype anyone can review. A real deployment would "
                "limit this to trained moderators."
            ).classes("text-body-sm")
            await queue()
