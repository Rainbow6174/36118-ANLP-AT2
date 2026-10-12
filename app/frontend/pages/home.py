"""Home page: hero with search, category links and the latest community reports."""

from urllib.parse import quote

from components.category_card import category_style
from components.report_cards import report_card
from components.ui_kit import (
    crisis_alert,
    crisis_button,
    crisis_empty_state,
    crisis_heading,
    crisis_input,
    crisis_skeleton_cards,
)
from constants.labels import (
    FEATURED_LABELS,
    LABEL_DISPLAY_NAMES,
    LABEL_ICONS,
    LABELS,
)
from layout import frame
from nicegui import ui
from services import api, auth

LATEST_REPORT_COUNT = 3
SEARCH_EXAMPLES = ("water", "shelter", "medical help", "looking for family")


def _category_link(label: str) -> None:
    """A category as a coloured link."""
    link = (
        ui.link(target=f"/boards/{label}")
        .classes("crisis-home-category-link")
        .style(category_style(label))
    )
    with link:
        ui.icon(LABEL_ICONS[label])
        ui.label(LABEL_DISPLAY_NAMES[label])


@ui.page("/")
async def home_page() -> None:
    """The latest reports load after the page is shown."""
    client = ui.context.client

    def go_to_search() -> None:
        query = (search_box.value or "").strip()
        ui.navigate.to(f"/search?q={quote(query)}" if query else "/search")

    def show_loading() -> None:
        updates.clear()
        with updates:
            crisis_skeleton_cards(LATEST_REPORT_COUNT)

    async def load_latest() -> None:
        """Show the newest community reports, or why they are missing."""
        try:
            result = await api.list_reports(
                source_type="user", page=1, page_size=LATEST_REPORT_COUNT,
                exclude_hidden=not auth.is_admin(),
            )
        except api.BackendError:
            updates.clear()
            with updates:
                crisis_alert(
                    "error",
                    "Reports could not be loaded",
                    "Please check your connection and try again.",
                )
                crisis_button(
                    "Try again", variant="secondary", icon="refresh", on_click=retry
                )
            return

        updates_title.set_text(f"Recent community reports · {result.total}")
        updates.clear()
        with updates:
            if not result.items:
                crisis_empty_state(
                    "forum",
                    "No community reports yet",
                    "Be the first to share what is happening in your area.",
                    "Report a crisis",
                    "/submit",
                )
                return
            for report in result.items[:LATEST_REPORT_COUNT]:
                report_card(
                    report,
                    show_category=True,
                    compact=True,
                    # The demo-mode banner already says it is all demo data.
                    show_demo=not api.USING_MOCK_BACKEND,
                )

    async def retry() -> None:
        show_loading()
        await load_latest()

    category_state = {"expanded": False}

    def toggle_categories() -> None:
        category_state["expanded"] = not category_state["expanded"]
        category_browser.refresh()

    @ui.refreshable
    def category_browser() -> None:
        expanded = category_state["expanded"]
        labels = LABELS if expanded else FEATURED_LABELS

        with ui.element("div").classes("crisis-section-head"):
            crisis_heading("Browse categories", 3)
            toggle_label = "Show fewer" if expanded else f"View all {len(LABELS)}"
            crisis_button(
                toggle_label,
                variant="ghost",
                icon="expand_less" if expanded else "expand_more",
                on_click=toggle_categories,
            ).props(f'aria-label="{toggle_label}"')
        list_class = "crisis-home-category-list"
        if expanded:
            list_class += " crisis-home-category-list--expanded"
        with ui.element("div").classes(list_class):
            for label in labels:
                _category_link(label)

    with frame(), ui.column().classes("crisis-home"):
        with ui.column().classes("crisis-home-hero"):
            crisis_heading("Clearer crisis information, when it matters.", 1).classes(
                "crisis-hero-title", remove="text-h1"
            )
            ui.label(
                "Submit crisis reports, explore organised updates, "
                "and discover related information in one place."
            ).classes("crisis-hero-copy")
            with ui.row().classes("crisis-search-row crisis-hero-actions"):
                crisis_button(
                    "Report a crisis",
                    icon="add_circle_outline",
                    on_click=lambda: ui.navigate.to("/submit"),
                )
                search_box = crisis_input(
                    None,
                    icon="search",
                    placeholder="Search reports by need or keyword",
                ).props('aria-label="Search reports"')
                search_box.on("keydown.enter", go_to_search)
                with search_box.add_slot("append"):
                    ui.button(icon="arrow_forward", on_click=go_to_search).props(
                        'round unelevated color=primary aria-label="Search"'
                    )

            with ui.row().classes("crisis-search-examples"):
                ui.label("Try:")
                # source=all, so examples have results before any community report exists.
                for example in SEARCH_EXAMPLES:
                    ui.link(example, f"/search?q={quote(example)}&source=all")

        # Categories on the left, latest reports on the right (stacked on phones).
        with ui.element("div").classes("crisis-home-discovery"):
            with ui.column().classes("crisis-home-categories"):
                category_browser()

            with ui.column().classes("crisis-home-updates"):
                with ui.element("div").classes("crisis-section-head"):
                    updates_title = crisis_heading("Recent community reports", 3)
                    crisis_button(
                        "View all",
                        variant="ghost",
                        icon="arrow_forward",
                        on_click=lambda: ui.navigate.to("/search"),
                    )
                updates = ui.column().classes("crisis-home-report-list")
                show_loading()

    # The page is already showing placeholders; now fetch the reports.
    try:
        await client.connected()
    except TimeoutError:
        return
    await load_latest()
