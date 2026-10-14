"""Search and browse crisis reports."""

from components.report_cards import (
    crisis_pagination,
    related_card,
    report_card,
    report_count,
)
from components.ui_kit import (
    crisis_button,
    crisis_empty_state,
    crisis_error_state,
    crisis_heading,
    crisis_input,
    crisis_select,
    crisis_skeleton_cards,
)
from constants.labels import LABEL_DISPLAY_NAMES, STATUS_FILTER_OPTIONS
from layout import frame
from nicegui import ui
from services import api, auth

PAGE_SIZE = 6

# The backend returns no total for a search, so up to this many results are paged here.
SEARCH_LIMIT = 60
SOURCE_OPTIONS = {
    "all": "All sources",
    "user": "Community reports",
    "humaid_history": "Historical dataset",
}


def _valid(value: str, options, fallback: str = "all") -> str:
    """The value if it is a valid option, else the fallback."""
    return value if value in options else fallback


@ui.page("/search", title="Search reports · CrisisLens")
async def search_page(
    q: str = "", category: str = "all", status: str = "all", source: str = "user"
) -> None:
    """The query and filters can come from the URL."""
    client = ui.context.client
    category_options = {"all": "All categories", **LABEL_DISPLAY_NAMES}

    state = {
        "page": 1,
        "q": q.strip(),
        "category": _valid(category, category_options),
        "status": _valid(status, STATUS_FILTER_OPTIONS),
        "source": _valid(source, SOURCE_OPTIONS, fallback="user"),
    }
    if state["source"] == "humaid_history":
        state["status"] = "all"

    def filter_value(key: str) -> str | None:
        return None if state[key] == "all" else state[key]

    @ui.refreshable
    async def results() -> None:
        try:
            # Historical and mixed-source browsing comes from Member 5's
            # read-only index. Community-only browsing comes from SQLite.
            if state["q"] or state["source"] != "user":
                found = await api.search_reports(
                    state["q"],
                    board_label=filter_value("category"),
                    source_type=filter_value("source"),
                    status=filter_value("status"),
                    k=SEARCH_LIMIT,
                )
                total = len(found)
                start = (state["page"] - 1) * PAGE_SIZE
                shown = await api.fill_details(found[start : start + PAGE_SIZE])

                def draw(item):
                    related_card(item, "Search match")

            else:
                listing = await api.list_reports(
                    board_label=filter_value("category"),
                    source_type=filter_value("source"),
                    status=filter_value("status"),
                    page=state["page"],
                    page_size=PAGE_SIZE,
                    exclude_hidden=not auth.is_admin(),
                )
                total = listing.total
                shown = listing.items

                def draw(report):
                    report_card(report, show_category=True)

        except api.BackendError:
            crisis_error_state(
                "The reports could not be loaded. Check your connection.",
                results.refresh,
            )
            return

        summary = report_count(total)
        if state["q"]:
            if total >= SEARCH_LIMIT:
                summary = f"Showing the top {total} matches"
            summary += f" for “{state['q']}”"
        ui.label(summary).classes("text-body-sm")

        if not total:
            if state["q"] and state["source"] == "user":
                crisis_empty_state(
                    "search_off",
                    "No community reports found",
                    "Try all sources to include historical references.",
                    "Search all sources",
                    on_action=search_all_sources,
                )
            else:
                crisis_empty_state(
                    "search_off",
                    "No reports found",
                    "Try different words, or remove a filter. Search reports "
                    "using keywords such as “water”, “shelter” or “evacuation”.",
                    "Clear search",
                    "/search",
                )
            return

        with ui.column().classes("crisis-report-list"):
            for item in shown:
                draw(item)
        crisis_pagination(state["page"], max(1, -(-total // PAGE_SIZE)), go_to_page)

    def go_to_page(page: int) -> None:
        state["page"] = page
        results.refresh()

    def apply() -> None:
        # Historical records have no review status: reset it, which runs apply() again.
        if source_select.value == "humaid_history" and status_select.value != "all":
            status_select.value = "all"
            return
        status_select.set_enabled(source_select.value != "humaid_history")
        state["q"] = (search_box.value or "").strip()
        state["category"] = category_select.value or "all"
        state["status"] = status_select.value or "all"
        state["source"] = source_select.value or "all"
        state["page"] = 1
        results.refresh()

    def search_all_sources() -> None:
        """Setting the filter runs apply() through its change handler."""
        source_select.value = "all"

    with frame():
        with ui.column().classes("crisis-page"):
            crisis_heading("Search crisis reports", 1)

            # Stays in view while the results scroll.
            with ui.column().classes("crisis-search-controls"):
                with ui.element("div").classes("crisis-search-row"):
                    search_box = crisis_input(
                        "Search for needs, damage, supplies or keywords",
                        icon="search",
                        value=state["q"],
                    )
                    search_box.on("keydown.enter", apply)
                    crisis_button("Search", icon="search", on_click=apply)

                with ui.element("div").classes("crisis-filter-row"):
                    category_select = crisis_select(
                        "Category", category_options, state["category"]
                    )
                    status_select = crisis_select(
                        "Status", STATUS_FILTER_OPTIONS, state["status"]
                    )
                    source_select = crisis_select(
                        "Source", SOURCE_OPTIONS, state["source"]
                    )
                status_select.set_enabled(state["source"] != "humaid_history")
                for select in (category_select, status_select, source_select):
                    select.on_value_change(apply)

            holder = ui.column().classes("w-full")
            with holder, ui.column().classes("crisis-report-list"):
                crisis_skeleton_cards()

    try:
        await client.connected()
    except TimeoutError:
        return
    holder.clear()
    with holder:
        await results()
