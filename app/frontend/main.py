"""Register routes and launch the CrisisLens frontend."""

import os
from pathlib import Path

from nicegui import app, ui
from pages import (  # noqa: F401
    about,
    admin,
    board,
    boards,
    home,
    login,
    report_detail,
    review,
    search,
    submit,
)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
app.add_static_files("/assets", str(ASSETS_DIR))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="CrisisLens",
        favicon="🧭",
        reload=False,
        port=int(os.environ.get("PORT", "8080")),
        show="PORT" not in os.environ,
        storage_secret="crisislens-prototype-secret",
    )
