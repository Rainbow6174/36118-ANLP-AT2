"""Report detail page: the report, its category and approximate location, then related reports."""

from components.report_cards import (
    display_text,
    has_coordinates,
    location_text,
    related_row,
    report_badges,
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

# Coordinates are rounded to 2 decimals, so the real place is within this distance of the point.
_AREA_RADIUS_METERS = 800


def _category_editor(report: CrisisReport) -> None:
    """The "not verified" note and a button that opens the category correction form."""

    async def save(category: str) -> None:
        # Saving a report that awaited review counts as reviewing it.
        status = "resolved" if report.status == "needs_review" else None
        changed_category = category != report.board_label
        if not changed_category and status is None:
            ui.notify("Nothing to change.")
            return
        try:
            await api.update_report(
                report.message_id,
                board_label=category if changed_category else None,
                status=status,
            )
        except api.BackendError:
            ui.notify("This report could not be updated.", type="negative")
            return
        ui.notify("Category saved", type="positive")
        ui.navigate.to(f"/reports/{report.message_id}")

    can_edit = auth.is_admin() or (
        report.created_by is not None
        and report.created_by == auth.current_user()
    )

    with ui.column().classes("crisis-detail-footer"):
        with ui.row().classes("crisis-detail-footer-row"):
            ui.label("CrisisLens does not check whether a report is true.").classes(
                "text-caption"
            )
            if report.source_type == "humaid_history":
                ui.label("Historical records are read-only.").classes("text-caption")
                return
            if not can_edit:
                ui.label("Only the author or an admin can edit this report.").classes(
                    "text-caption"
                )
                return
            open_button = crisis_button(
                "Suggest a different category", variant="secondary", icon="edit"
            )

        # Closed until asked for, except for reports that await review.
        editor = ui.column().classes("crisis-category-editor")
        with editor:
            ui.label(suggestion_text(report)).classes("text-body-sm")
            if api.is_mock_model(report.model_version):
                ui.label(
                    "Suggested by the demo classifier, not the trained model."
                ).classes("text-caption")
            if report.board_label != report.predicted_label:
                ui.label("A person changed this category from the suggestion.").classes(
                    "text-body-sm"
                )
            if report.status == "needs_review":
                crisis_alert(
                    "review",
                    "Less certain",
                    "Please check this category and confirm it or choose another.",
                )
            category = crisis_select(
                "Correct the category", LABEL_DISPLAY_NAMES, report.board_label
            )
            crisis_button(
                "Save category",
                icon="check",
                on_click=lambda: save(category.value),
            )
            ui.label(
                "Anyone can change a category in this prototype. The model's "
                "original suggestion is always kept."
            ).classes("text-caption")
        editor.visible = report.status == "needs_review"

        def show_editor() -> None:
            editor.visible = True
            open_button.visible = False

        open_button.on_click(show_editor)
        open_button.visible = not editor.visible


def _location_panel(report: CrisisReport) -> None:
    place = report.location
    with ui.column().style("gap: 12px; width: 100%;"):
        crisis_heading("Approximate location", 3)
        ui.label(location_text(report.location) or "Map pin").classes("text-body-sm")
        ui.label("Shown as an area of about 1 km, not an exact position.").classes(
            "text-caption"
        )
        lat, lon = place.latitude, place.longitude
        detail_map = ui.leaflet(
            center=(lat, lon), zoom=12, options={"scrollWheelZoom": False}
        ).classes("crisis-detail-map")
        # A circle rather than a pin, because the point is rounded.
        detail_map.generic_layer(
            name="circle",
            args=[
                (lat, lon),
                {
                    "radius": _AREA_RADIUS_METERS,
                    "color": "#0F6B66",
                    "weight": 2,
                    "fillOpacity": 0.15,
                },
            ],
        )
        # Lets volunteers continue in a full map app.
        with ui.row().classes("crisis-map-links"):
            ui.link(
                "Open in OpenStreetMap",
                f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=13/{lat}/{lon}",
                new_tab=True,
            )
            ui.link(
                "Open in Google Maps",
                f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
                new_tab=True,
            )


@ui.page("/reports/{report_id}", response_timeout=PAGE_RESPONSE_TIMEOUT_SECONDS)
async def report_detail_page(report_id: str) -> None:
    # Read the role before any await (see home.py).
    is_admin = auth.is_admin()
    try:
        detail = await api.get_report_detail(report_id)
    except api.BackendError:
        with frame():
            crisis_error_state(
                "The report could not be loaded. Check your connection.",
                ui.navigate.reload,
            )
        return

    # A hidden report is removed from boards and search for everyone but an
    # administrator, so a direct link must not reveal it either.
    if detail is not None and detail[0].status == "hidden" and not is_admin:
        detail = None

    with frame():
        if detail is None:
            crisis_empty_state(
                "search_off",
                "Report not found",
                "It may have been removed, or the link is wrong.",
                "Search reports",
                "/search",
            )
            return

        report, related = detail
        board_name = LABEL_DISPLAY_NAMES[report.board_label]
        ui.page_title(f"{board_name} report · CrisisLens")

        with ui.column().classes("crisis-page"):
            crisis_button(
                f"Back to {board_name}",
                variant="ghost",
                icon="arrow_back",
                on_click=lambda: ui.navigate.to(f"/boards/{report.board_label}"),
            ).style("align-self: flex-start;")

            # The visible title is the report text, so this h1 is for screen readers only.
            crisis_heading("Report details", 1).classes("sr-only", remove="text-h1")

            has_map = has_coordinates(report.location)
            grid_class = "crisis-detail-grid"
            if not has_map:
                grid_class += " crisis-detail-grid--single"
            with crisis_card():
                with ui.element("div").classes(grid_class):
                    with ui.column().classes("crisis-detail-main"):
                        report_badges(report, show_category=True)
                        ui.label(display_text(report.text, report.source_type)).classes(
                            "crisis-report-full-text"
                        )
                        report_meta(report)
                        _category_editor(report)

                    if has_map:
                        with ui.column().classes("crisis-detail-map-area"):
                            _location_panel(report)

            with crisis_card():
                with ui.column().style("gap: 8px; width: 100%;"):
                    crisis_heading("Related reports", 3)
                    if related:
                        with ui.column().classes("crisis-related-list"):
                            for item in related:
                                related_row(item)
                    else:
                        ui.label("No similar reports yet.").classes("text-body-sm")
