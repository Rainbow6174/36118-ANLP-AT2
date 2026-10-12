"""Session-based authentication for CrisisLens (prototype).

Two mock accounts:
    admin / admin    -> role "admin"
    user  / user     -> role "user"

Uses NiceGUI's per-browser storage (app.storage.user) so sessions
survive page reloads but not a server restart.
"""

from __future__ import annotations

from nicegui import app

USERS: dict[str, dict] = {
    "admin": {"password": "admin", "role": "admin", "display_name": "Admin"},
    "user": {"password": "user", "role": "user", "display_name": "User"},
}


def authenticate(username: str, password: str) -> str | None:
    """Return the role on success, None on failure."""
    record = USERS.get(username)
    if record and record["password"] == password:
        return record["role"]
    return None


def login(username: str, role: str) -> None:
    """Store the session after a successful authenticate()."""
    app.storage.user["username"] = username
    app.storage.user["role"] = role
    app.storage.user["display_name"] = USERS[username]["display_name"]
    app.storage.user["authenticated"] = True


def logout() -> None:
    app.storage.user.clear()


def current_user() -> str | None:
    """The logged-in username, or None."""
    if app.storage.user.get("authenticated"):
        return app.storage.user.get("username")
    return None


def current_role() -> str | None:
    if app.storage.user.get("authenticated"):
        return app.storage.user.get("role")
    return None


def display_name() -> str:
    return app.storage.user.get("display_name", "Guest")


def is_admin() -> bool:
    return current_role() == "admin"


def is_authenticated() -> bool:
    return bool(app.storage.user.get("authenticated"))
