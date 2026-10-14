"""Loads the stylesheets from styles/ and applies the colour palette (restart after editing CSS)."""

from pathlib import Path

from nicegui import ui

STYLES_DIR = Path(__file__).resolve().parent / "styles"

# Later files win when two rules are equally specific.
STYLE_FILES = (
    "tokens.css",
    "base.css",
    "layout.css",
    "components.css",
    "home.css",
    "submit.css",
    "reports.css",
)

# Palette for NiceGUI's own components; keep in step with styles/tokens.css.
PALETTE = {
    "primary": "#0F6B66",
    "secondary": "#52676B",
    "accent": "#E8755B",
    "positive": "#027A48",
    "negative": "#B42318",
    "warning": "#B54708",
    "dark": "#102A2E",
}

FONT_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

_STYLES = "\n".join(
    (STYLES_DIR / name).read_text(encoding="utf-8") for name in STYLE_FILES
)


def apply_theme() -> None:
    """Set the palette, font, page language and styles for every page."""
    ui.colors(**PALETTE)
    ui.add_head_html(FONT_HTML, shared=True)
    ui.add_head_html(
        '<script>document.documentElement.lang = "en";</script>', shared=True
    )
    ui.add_head_html(f"<style>{_STYLES}</style>", shared=True)
