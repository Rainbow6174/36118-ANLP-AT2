"""Login page matching the CrisisLens visual language."""

from nicegui import ui
from services import auth
from theme import apply_theme


@ui.page("/login", title="Sign in · CrisisLens")
def login_page() -> None:
    if auth.is_authenticated():
        ui.navigate.to("/")
        return

    apply_theme()

    def attempt_login() -> None:
        username = username_input.value.strip()
        password = password_input.value.strip()
        if not username or not password:
            error_label.set_text("Please enter both fields.")
            return
        role = auth.authenticate(username, password)
        if role is None:
            error_label.set_text("Invalid username or password.")
            return
        auth.login(username, role)
        ui.navigate.to("/")

    with ui.column().classes("crisis-login-page"):
        with ui.column().classes("crisis-login-card"):
            ui.html(
                '<img src="/assets/crisislens-logo.png" '
                'class="crisis-login-logo" alt="CrisisLens" '
                'width="600" height="104" loading="eager">',
                sanitize=False,
            )
            ui.label("Sign in to CrisisLens").classes("crisis-login-title")
            ui.label(
                "Use your credentials to access the platform."
            ).classes("crisis-login-subtitle")

            username_input = (
                ui.input("Username")
                .classes("w-full")
                .props("outlined")
            )
            password_input = (
                ui.input("Password", password=True, password_toggle_button=True)
                .classes("w-full")
                .props("outlined")
            )
            password_input.on("keydown.enter", attempt_login)

            error_label = ui.label("").classes("crisis-login-error")

            (
                ui.button("Sign in", on_click=attempt_login)
                .classes("crisis-btn crisis-login-btn")
                .props("no-caps unelevated color=primary")
            )

            with ui.column().classes("crisis-login-hint"):
                ui.label("Demo accounts").style("font-weight: 600;")
                with ui.row().classes("gap-4"):
                    with ui.column().style("gap: 2px;"):
                        ui.label("Admin").style("font-weight: 500; font-size: 13px;")
                        ui.label("admin / admin").classes("crisis-login-credential")
                    with ui.column().style("gap: 2px;"):
                        ui.label("User").style("font-weight: 500; font-size: 13px;")
                        ui.label("user / user").classes("crisis-login-credential")
