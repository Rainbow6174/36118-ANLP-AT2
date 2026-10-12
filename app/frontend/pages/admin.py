"""Admin dashboard: verify, edit, delete and hide community reports."""

from components.report_cards import report_badges, report_count, report_meta
from components.ui_kit import (
    crisis_card,
    crisis_empty_state,
    crisis_error_state,
    crisis_heading,
    crisis_select,
)
from constants.labels import LABEL_DISPLAY_NAMES
from layout import frame
from nicegui import ui
from services import api, auth

PAGE_SIZE = 8

STATUS_OPTIONS = {
    "all": "All statuses",
    "unverified": "Unverified",
    "needs_review": "Needs review",
    "resolved": "Resolved",
    "hidden": "Hidden",
}


@ui.page("/admin", title="Admin · CrisisLens")
async def admin_page() -> None:
    if not auth.is_admin():
        ui.navigate.to("/")
        return

    state = {"page": 1, "status": "all"}

    def go_to_page(page: int) -> None:
        state["page"] = page
        report_list.refresh()

    def apply_filter() -> None:
        state["status"] = status_filter.value or "all"
        state["page"] = 1
        report_list.refresh()

    async def set_status(message_id: str, new_status: str) -> None:
        try:
            await api.update_report(message_id, status=new_status)
        except api.BackendError:
            ui.notify("Could not update report.", type="negative")
            return
        ui.notify(f"Status changed to {new_status}.", type="positive")
        report_list.refresh()

    async def delete_report_action(message_id: str) -> None:
        try:
            await api.delete_report(message_id)
        except api.BackendError:
            ui.notify("Could not delete report.", type="negative")
            return
        ui.notify("Report deleted.", type="positive")
        report_list.refresh()

    async def correct_category(message_id: str, new_label: str) -> None:
        try:
            await api.update_report(message_id, board_label=new_label)
        except api.BackendError:
            ui.notify("Could not update category.", type="negative")
            return
        ui.notify("Category updated.", type="positive")
        report_list.refresh()

    @ui.refreshable
    async def report_list() -> None:
        status_val = None if state["status"] == "all" else state["status"]
        try:
            result = await api.list_reports(
                source_type="user",
                status=status_val,
                page=state["page"],
                page_size=PAGE_SIZE,
            )
        except api.BackendError:
            crisis_error_state(
                "Reports could not be loaded.",
                report_list.refresh,
            )
            return

        if not result.items:
            crisis_empty_state(
                "inbox",
                "No reports found",
                "Try a different filter.",
            )
            return

        ui.label(report_count(result.total)).classes("text-body-sm")

        for report in result.items:
            mid = report.message_id
            with crisis_card().classes("crisis-admin-card"):
                with ui.row().classes("crisis-admin-card-header"):
                    report_badges(report, show_category=True)
                    with ui.row().classes("crisis-admin-status-badge"):
                        ui.label(report.status).classes("crisis-badge")

                ui.label(report.text).classes(
                    "text-body crisis-report-full-text"
                ).style("max-height: 80px; overflow: hidden;")
                report_meta(report)

                with ui.row().classes("crisis-admin-actions"):
                    if report.status == "needs_review":
                        ui.button(
                            "Verify",
                            on_click=lambda e, m=mid: set_status(m, "resolved"),
                            icon="check_circle",
                        ).classes("crisis-btn").props("no-caps unelevated")

                    cat_select = crisis_select(
                        "Category",
                        LABEL_DISPLAY_NAMES,
                        report.board_label,
                    )
                    ui.button(
                        "Update category",
                        on_click=lambda e, m=mid, sel=cat_select: correct_category(
                            m, sel.value
                        ),
                        icon="edit",
                    ).classes("crisis-btn").props("no-caps unelevated outline")

                    if report.status != "hidden":
                        ui.button(
                            "Hide",
                            on_click=lambda e, m=mid: set_status(m, "hidden"),
                            icon="visibility_off",
                        ).classes("crisis-btn").props("no-caps unelevated outline")
                    else:
                        ui.button(
                            "Unhide",
                            on_click=lambda e, m=mid: set_status(m, "unverified"),
                            icon="visibility",
                        ).classes("crisis-btn").props("no-caps unelevated outline")

                    ui.button(
                        "Delete",
                        on_click=lambda e, m=mid: delete_report_action(m),
                        icon="delete",
                    ).classes("crisis-btn").props("no-caps unelevated outline")

        if result.total_pages > 1:
            with ui.row().classes("crisis-pagination"):
                for p in range(1, result.total_pages + 1):
                    btn = ui.button(
                        str(p),
                        on_click=lambda _, pg=p: go_to_page(pg),
                    ).props("flat no-caps")
                    if p == state["page"]:
                        btn.classes("crisis-pagination-active")

    with frame():
        with ui.column().classes("crisis-page"):
            crisis_heading("Admin Dashboard", 1)
            ui.label(
                "Manage all community reports. Verify, edit categories, "
                "hide or delete reports."
            ).classes("text-body-sm")

            with ui.row().classes("crisis-admin-filters"):
                status_filter = crisis_select(
                    "Filter by status", STATUS_OPTIONS, state["status"]
                )
                status_filter.on_value_change(apply_filter)

            await report_list()
