"""Report cards, rows and pagination shared by the list pages."""

from collections.abc import Callable
from datetime import UTC, datetime

from constants.labels import LABEL_DISPLAY_NAMES, LABEL_ICONS
from nicegui import ui
from schemas.api import CrisisReport, RelatedReport

from components.badges import (
    badge,
    category_badge,
    demo_badge,
    source_badge,
    status_badges,
)
from components.category_card import category_style


def format_time_ago(iso_time: str) -> str:
    """'18 min ago', '3 h ago', '2 d ago', or a date after a week."""
    try:
        then = datetime.fromisoformat(iso_time)
    except ValueError:
        return ""
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)

    seconds = max(0, int((datetime.now(UTC) - then).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    if days < 7:
        return f"{days} d ago"
    return then.strftime("%d %b %Y")


def location_text(report: CrisisReport) -> str | None:
    return report.location.location_name if report.location else None


def has_coordinates(report: CrisisReport) -> bool:
    place = report.location
    return (
        place is not None and place.latitude is not None and place.longitude is not None
    )


def report_badges(
    report: CrisisReport,
    *,
    highlight: bool = False,
    show_category: bool = False,
    compact: bool = False,
    show_demo: bool = True,
) -> None:
    """Badges at the top of a report; compact drops the source, show_demo=False the demo badge."""
    with ui.row().classes("crisis-report-badges"):
        if highlight:
            badge("New", "success")
        if show_category:
            category_badge(report.board_label)
        if not compact:
            source_badge(report.source_type)
        if report.source_type == "user":
            status_badges(report.status)
        if report.is_demo and show_demo:
            demo_badge()


def report_meta(report: CrisisReport) -> None:
    """Time posted and place."""
    with ui.row().classes("crisis-report-meta"):
        with ui.row().classes("crisis-report-meta-item"):
            ui.icon("schedule").classes("text-body-sm")
            ui.label(format_time_ago(report.created_at))

        # A pin without a place name is still a location.
        place = location_text(report) or (
            "Approximate location included" if has_coordinates(report) else None
        )

        if place:
            with ui.row().classes("crisis-report-meta-item"):
                ui.icon("place").classes("text-body-sm")
                ui.label(place)
        elif report.source_type == "user":
            with ui.row().classes("crisis-report-meta-item crisis-report-meta--muted"):
                ui.icon("location_off").classes("text-body-sm")
                ui.label("Location not provided")


HISTORY_NOTE = "From the HumAID dataset (past disasters)"


def _card(href: str | None, extra_classes: str = ""):
    """A link card, or a plain card when href is None (historical records have no page)."""
    classes = f"crisis-card crisis-report-card {extra_classes}".strip()
    if href is None:
        return ui.element("div").classes(f"{classes} crisis-report-card--reference")
    return ui.link(target=href).classes(f"{classes} crisis-card--clickable")


def report_card(
    report: CrisisReport,
    *,
    highlight: bool = False,
    show_category: bool = False,
    compact: bool = False,
    show_demo: bool = True,
):
    """A summary of one report (compact and show_demo as in report_badges)."""
    is_history = report.source_type == "humaid_history"
    href = None if is_history else f"/reports/{report.message_id}"

    with _card(href, "crisis-report-card--new" if highlight else "").style(
        category_style(report.board_label)
    ):
        report_badges(
            report,
            highlight=highlight,
            show_category=show_category,
            compact=compact,
            show_demo=show_demo,
        )
        ui.label(report.text).classes("text-body crisis-report-text")
        report_meta(report)

        if is_history:
            ui.label(HISTORY_NOTE).classes("text-caption crisis-report-note")


def related_card(related: RelatedReport, context: str = "Related report"):
    """A compact card for a retrieval or search result; context says why it is shown."""
    is_history = related.source_type == "humaid_history"
    with _card(None if is_history else f"/reports/{related.id}"):
        with ui.row().classes("crisis-report-badges"):
            category_badge(related.board_label)
            source_badge(related.source_type)
        ui.label(related.text_preview).classes("text-body crisis-report-text")
        note = f"{context} · {HISTORY_NOTE}" if is_history else context
        ui.label(note).classes("text-caption crisis-report-note")


def related_row(related: RelatedReport):
    """A one-line link to a related report; historical records are plain text."""
    is_history = related.source_type == "humaid_history"
    if is_history:
        row = ui.element("div").classes(
            "crisis-related-row crisis-related-row--reference"
        )
    else:
        row = ui.link(target=f"/reports/{related.id}").classes("crisis-related-row")
    row.style(category_style(related.board_label)).props(
        f'title="{LABEL_DISPLAY_NAMES[related.board_label]}"'
    )
    with row:
        ui.icon(LABEL_ICONS[related.board_label])
        ui.label(related.text_preview).classes("crisis-related-text")
        if is_history:
            ui.label("Historical").classes("crisis-related-tag")


def suggestion_text(report: CrisisReport) -> str:
    """What the model suggested for a report, with its confidence."""
    return (
        f"Suggested by CrisisLens: {LABEL_DISPLAY_NAMES[report.predicted_label]} "
        f"({round(report.confidence * 100)}% confidence)"
    )


def report_count(total: int) -> str:
    """'1 report' or '5 reports'."""
    return f"{total} {'report' if total == 1 else 'reports'}"


def crisis_pagination(page: int, total_pages: int, on_change: Callable[[int], None]):
    """Page buttons, drawn only when there is more than one page."""
    if total_pages <= 1:
        return None
    return ui.pagination(
        1,
        total_pages,
        direction_links=True,
        value=page,
        on_change=lambda event: on_change(event.value),
    ).classes("crisis-pagination")
