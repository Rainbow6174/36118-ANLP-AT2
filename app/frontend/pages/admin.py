"""Admin dashboard: confirm or correct categories, and hide, restore or delete community reports."""

import time

from components.report_cards import report_badges, report_count, report_meta
from components.ui_kit import (
    crisis_button,
    crisis_card,
    crisis_empty_state,
    crisis_error_state,
    crisis_heading,
    crisis_select,
)
from constants.labels import LABEL_DISPLAY_NAMES
from layout import frame
from nicegui import app, ui
from services import api, auth

PAGE_SIZE = 8

# After an admin ticks "Don't ask again", deleting skips the confirmation for this
# long. It is kept in the admin's session, so signing out ends it.
SKIP_DELETE_CONFIRM_SECONDS = 60 * 60
_SKIP_DELETE_CONFIRM_KEY = "skip_delete_confirm_until"


def _delete_confirmation_skipped() -> bool:
    try:
        until = float(app.storage.user.get(_SKIP_DELETE_CONFIRM_KEY, 0))
    except (TypeError, ValueError):
        return False
    return time.time() < until

# Same wording as the badges and the report: a review concerns the category,
# never the truth of the report.
STATUS_OPTIONS = {
    "all": "All statuses",
    "unverified": "Unverified",
    "needs_review": "Category needs review",
    "resolved": "Category reviewed",
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

    async def confirm_category(message_id: str) -> None:
        try:
            await api.update_report(message_id, status="resolved")
        except api.BackendError:
            ui.notify("Could not update report.", type="negative")
            return
        ui.notify("Category confirmed.", type="positive")
        report_list.refresh()

    async def set_hidden(message_id: str, hidden: bool) -> None:
        try:
            await api.update_report(message_id, hidden=hidden)
        except api.BackendError:
            ui.notify("Could not update report.", type="negative")
            return
        ui.notify("Report hidden." if hidden else "Report restored.", type="positive")
        report_list.refresh()

    async def delete_report_action(message_id: str) -> None:
        try:
            await api.delete_report(message_id)
        except api.BackendError:
            ui.notify("Could not delete report.", type="negative")
            return
        ui.notify("Report deleted.", type="positive")
        report_list.refresh()

    async def ask_delete(message_id: str) -> None:
        """Deleting cannot be undone, so it needs a second click unless the admin
        chose to skip the confirmation for an hour."""
        if _delete_confirmation_skipped():
            await delete_report_action(message_id)
            return

        with ui.dialog() as dialog, ui.element("div").classes(
            "crisis-card crisis-dialog"
        ):
            ui.label("Delete this report permanently?").classes("crisis-dialog-title")
            ui.label(
                "It will be removed from boards and search. Hide it instead if it "
                "may need to be restored."
            ).classes("text-body-sm")
            skip = ui.checkbox("Don't ask again for 1 hour").classes(
                "crisis-dialog-skip"
            )

            async def confirmed() -> None:
                if skip.value:
                    app.storage.user[_SKIP_DELETE_CONFIRM_KEY] = (
                        time.time() + SKIP_DELETE_CONFIRM_SECONDS
                    )
                dialog.close()
                await delete_report_action(message_id)

            with ui.element("div").classes("crisis-dialog-actions"):
                crisis_button("Cancel", on_click=dialog.close, variant="secondary")
                crisis_button("Delete", on_click=confirmed, icon="delete").props(
                    "color=negative"
                )
        dialog.open()

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
                        ui.label(STATUS_OPTIONS.get(report.status, report.status)).classes(
                            "crisis-badge"
                        )

                ui.label(report.text).classes(
                    "text-body crisis-report-full-text"
                ).style("max-height: 80px; overflow: hidden;")
                report_meta(report)

                with ui.row().classes("crisis-admin-actions"):
                    if report.status == "needs_review":
                        ui.button(
                            "Confirm category",
                            on_click=lambda e, m=mid: confirm_category(m),
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
                            on_click=lambda e, m=mid: set_hidden(m, True),
                            icon="visibility_off",
                        ).classes("crisis-btn").props("no-caps unelevated outline")
                    else:
                        ui.button(
                            "Restore",
                            on_click=lambda e, m=mid: set_hidden(m, False),
                            icon="visibility",
                        ).classes("crisis-btn").props("no-caps unelevated outline")

                    ui.button(
                        "Delete",
                        on_click=lambda e, m=mid: ask_delete(m),
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
                "Manage community reports: confirm or correct categories, and hide, "
                "restore or delete reports. Confirming a category records that a "
                "person checked the sorting; it does not verify that a report is true."
            ).classes("text-body-sm")

            with ui.row().classes("crisis-admin-filters"):
                status_filter = crisis_select(
                    "Filter by status", STATUS_OPTIONS, state["status"]
                )
                status_filter.on_value_change(apply_filter)

            await report_list()
