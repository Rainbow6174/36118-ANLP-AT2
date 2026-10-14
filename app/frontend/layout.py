"""Shared page layout: header, notices and the main content area."""

from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import quote

from nicegui import ui
from nicegui.element import Element
from services import api, auth
from theme import apply_theme

PAGE_RESPONSE_TIMEOUT_SECONDS = 25.0

NAV_LINKS = (
    ("Home", "/", "home"),
    ("Report", "/submit", "add_circle_outline"),
    ("Browse", "/search", "search"),
    ("Review", "/review", "flag"),
)


def _is_active(current_path: str, route: str) -> bool:
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
            display_label = label
            if route == "/review" and not auth.is_admin():
                display_label = "My Reports"

            active = _is_active(current_path, route)
            classes = "crisis-nav-link"
            if active:
                classes += " crisis-nav-link--active"

            with ui.link(target=route).classes(classes) as link:
                if active:
                    link.props('aria-current="page"')
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon).classes("text-body")
                    ui.label(display_label)

        if auth.is_admin():
            active = current_path == "/admin"
            classes = "crisis-nav-link"
            if active:
                classes += " crisis-nav-link--active"
            with ui.link(target="/admin").classes(classes):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("admin_panel_settings").classes("text-body")
                    ui.label("Admin")


def _render_header_search() -> None:
    """A compact search bar in the center of the header."""
    def go_search() -> None:
        query = (header_search.value or "").strip()
        ui.navigate.to(f"/search?q={quote(query)}" if query else "/search")

    with ui.element("div").classes("crisis-header-search"):
        header_search = (
            ui.input(placeholder="Search reports...")
            .classes("crisis-header-search-input")
            .props("dense outlined borderless")
        )
        header_search.on("keydown.enter", go_search)
        with header_search.add_slot("prepend"):
            ui.icon("search").style("font-size: 20px; color: var(--color-text-secondary);")


def _render_user_icon() -> None:
    """User avatar icon on the right side of the header with a dropdown menu."""
    is_logged_in = auth.is_authenticated()
    name = auth.display_name() if is_logged_in else "Guest"
    role = auth.current_role()
    initial = "A" if role == "admin" else "U"

    with ui.element("div").classes("crisis-user-area"):
        avatar_btn = (
            ui.button(initial)
            .classes("crisis-avatar-btn")
            .props("round flat")
        )
        with ui.menu().classes("crisis-user-menu"):
            with ui.column().classes("crisis-user-menu-header"):
                ui.label(name).style("font-weight: 600; font-size: 14px;")
                if role:
                    ui.label(role.capitalize()).style(
                        "font-size: 12px; color: var(--color-text-secondary);"
                    )

            if is_logged_in:
                if auth.is_admin():
                    ui.menu_item(
                        "Admin Dashboard",
                        on_click=lambda: ui.navigate.to("/admin"),
                    )
                ui.separator()
                ui.menu_item(
                    "Sign out",
                    on_click=lambda: (auth.logout(), ui.navigate.to("/login")),
                )
            else:
                ui.menu_item(
                    "Sign in",
                    on_click=lambda: ui.navigate.to("/login"),
                )


def _render_mobile_navigation() -> None:
    with (
        ui.button(icon="menu")
        .props('flat round aria-label="Open navigation"')
        .classes("crisis-mobile-menu")
    ):
        with ui.menu():
            for label, route, _ in NAV_LINKS:
                display_label = label
                if route == "/review" and not auth.is_admin():
                    display_label = "My Reports"
                ui.menu_item(
                    display_label,
                    on_click=lambda _, path=route: ui.navigate.to(path),
                )
            if auth.is_admin():
                ui.menu_item(
                    "Admin",
                    on_click=lambda: ui.navigate.to("/admin"),
                )
            ui.separator()
            if auth.is_authenticated():
                ui.menu_item(
                    "Sign out",
                    on_click=lambda: (auth.logout(), ui.navigate.to("/login")),
                )
            else:
                ui.menu_item(
                    "Sign in",
                    on_click=lambda: ui.navigate.to("/login"),
                )


def _render_notices(current_path: str) -> None:
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
            _render_header_search()
            _render_navigation(current_path)
            _render_user_icon()
            _render_mobile_navigation()

    _render_notices(current_path)

    with ui.column().classes("crisis-main").props("id=crisis-main") as main:
        yield main

    _render_footer()
