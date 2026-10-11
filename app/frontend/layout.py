"""Shared page layout: header, notices and the main content area."""

from collections.abc import Generator
from contextlib import contextmanager

from nicegui import ui
from nicegui.element import Element
from services import api
from theme import apply_theme

# NiceGUI's default 3 s is too short for pages that load data before showing.
PAGE_RESPONSE_TIMEOUT_SECONDS = 25.0

NAV_LINKS = (
    ("Home", "/", "home"),
    ("Report a crisis", "/submit", "add_circle_outline"),
    ("Search", "/search", "search"),
    ("Review queue", "/review", "flag"),
)


def _is_active(current_path: str, route: str) -> bool:
    """Boards and report pages count as part of Search."""
    if route == "/search":
        return current_path == route or current_path.startswith(
            ("/boards/", "/reports/")
        )
    return current_path == route


def _render_brand() -> None:
    with ui.link(target="/").classes("crisis-logo"):
        ui.html(
            '<img src="/assets/crisislens-logo.png" '
            'class="crisis-brand-image" alt="CrisisLens home" '
            'width="600" height="104" loading="eager" decoding="sync">',
            sanitize=False,
        )


def _render_navigation(current_path: str) -> None:
    with ui.row().classes("crisis-nav-links"):
        for label, route, icon in NAV_LINKS:
            active = _is_active(current_path, route)
            classes = "crisis-nav-link"
            if active:
                classes += " crisis-nav-link--active"

            with ui.link(target=route).classes(classes) as link:
                if active:
                    link.props('aria-current="page"')
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon).classes("text-body")
                    ui.label(label)


def _render_mobile_navigation() -> None:
    with (
        ui.button(icon="menu")
        .props('flat round aria-label="Open navigation"')
        .classes("crisis-mobile-menu")
    ):
        with ui.menu():
            for label, route, _ in NAV_LINKS:
                ui.menu_item(
                    label,
                    on_click=lambda _, path=route: ui.navigate.to(path),
                )


def _render_notices(current_path: str) -> None:
    """Full-width bands under the header: the safety line, and the demo-mode note."""
    # The submit page has its own, larger safety box.
    show_safety = current_path != "/submit"
    if not (show_safety or api.USING_MOCK_BACKEND):
        return

    with ui.element("div").classes("crisis-notices"):
        if show_safety:
            with ui.element("div").classes("crisis-safety-strip").props('role="note"'):
                ui.icon("info_outline")
                ui.label(
                    "Not an emergency service. In danger, call your local "
                    "emergency number first."
                )

        if api.USING_MOCK_BACKEND:
            with ui.element("div").classes("crisis-demo-banner").props('role="status"'):
                ui.label(
                    "Demo mode: reports and the classifier are simulated, "
                    "and everything resets when the app restarts."
                )


def _render_footer() -> None:
    with ui.element("footer").classes("crisis-footer"):
        ui.label("Student prototype. Reports are not verified.")
        ui.link("About", "/about")


@contextmanager
def frame() -> Generator[Element, None, None]:
    """Header, notices and the main content container of a page."""
    apply_theme()
    current_path = ui.context.client.request.url.path

    with ui.header().classes("crisis-header"):
        ui.html(
            '<a class="crisis-skip-link" href="#crisis-main">Skip to main content</a>',
            sanitize=False,
        )
        with ui.row().classes("crisis-nav"):
            _render_brand()
            _render_navigation(current_path)
            _render_mobile_navigation()

    _render_notices(current_path)

    with ui.column().classes("crisis-main").props("id=crisis-main") as main:
        yield main

    _render_footer()
