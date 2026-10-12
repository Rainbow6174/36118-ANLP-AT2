"""Review page: admin sees the review queue; regular users see their own reported crises."""

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
from services import api, auth

PAGE_SIZE = 5

STATUS_DISPLAY = {
    "unverified": ("schedule", "Unverified", "var(--color-text-secondary)"),
    "needs_review": ("flag", "Needs review", "var(--color-warning, #e6a700)"),
    "resolved": ("check_circle", "Resolved", "var(--color-success, #2e7d32)"),
    "hidden": ("visibility_off", "Hidden", "var(--color-text-secondary)"),
}


@ui.page(
    "/review",
    title="Review · CrisisLens",
    response_timeout=PAGE_RESPONSE_TIMEOUT_SECONDS,
)
async def review_page() -> None:
    if auth.is_admin():
        await _admin_review_queue()
    else:
        await _user_my_reports()


async def _admin_review_queue() -> None:
    """Admin view: reports needing category confirmation."""
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
                _review_item(report, confirm)
        crisis_pagination(result.page, result.total_pages, go_to_page)

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
            await queue()


def _review_item(report: CrisisReport, confirm_callback) -> None:
    with crisis_card().classes("crisis-report-card"):
        report_badges(report, show_category=True)
        ui.label(report.text).classes("text-body crisis-report-full-text")
        report_meta(report)
        ui.label(suggestion_text(report)).classes("text-body-sm")

        with ui.element("div").classes("crisis-review-actions"):
            category = crisis_select(
                "Category", LABEL_DISPLAY_NAMES, report.board_label
            )
            ui.button(
                "Confirm category",
                on_click=lambda e, r=report, c=category: confirm_callback(r, c.value),
                icon="check",
            ).classes("crisis-btn").props("no-caps unelevated")
            crisis_button(
                "Open report",
                variant="ghost",
                icon="open_in_new",
                on_click=lambda _=None, r=report: ui.navigate.to(
                    f"/reports/{r.message_id}"
                ),
            )


async def _user_my_reports() -> None:
    """Regular user view: status tracker for their own submitted reports."""
    current_user = auth.current_user()
    state = {"page": 1}

    def go_to_page(page: int) -> None:
        state["page"] = page
        my_list.refresh()

    @ui.refreshable
    async def my_list() -> None:
        try:
            result = await api.list_reports(
                source_type="user",
                page=state["page"],
                page_size=PAGE_SIZE,
                exclude_hidden=True,
            )
        except api.BackendError:
            crisis_error_state(
                "Your reports could not be loaded. Check your connection.",
                my_list.refresh,
            )
            return

        own = [r for r in result.items if r.created_by == current_user]

        if not own:
            crisis_empty_state(
                "description",
                "No reports yet",
                "Reports you submit will appear here so you can track their status.",
                "Report a crisis",
                "/submit",
            )
            return

        ui.label(f"{len(own)} of your reports").classes("text-body-sm")
        with ui.column().classes("crisis-report-list"):
            for report in own:
                _my_report_item(report)

    with frame():
        with ui.column().classes("crisis-page"):
            crisis_heading("My reports", 1)
            ui.label(
                "Track the status of crises you have reported."
            ).classes("text-body-sm")
            await my_list()


def _my_report_item(report: CrisisReport) -> None:
    icon, label, color = STATUS_DISPLAY.get(
        report.status, ("help", report.status, "var(--color-text-secondary)")
    )
    with crisis_card().classes("crisis-report-card"):
        with ui.row().classes("items-center gap-2"):
            report_badges(report, show_category=True)
            with ui.row().classes("items-center gap-1"):
                ui.icon(icon).style(f"color: {color}; font-size: 18px;")
                ui.label(label).style(
                    f"color: {color}; font-weight: 600; font-size: 13px; text-transform: capitalize;"
                )
        ui.label(report.text).classes("text-body crisis-report-full-text")
        report_meta(report)
        crisis_button(
            "View details",
            variant="ghost",
            icon="open_in_new",
            on_click=lambda _=None, r=report: ui.navigate.to(
                f"/reports/{r.message_id}"
            ),
        )
