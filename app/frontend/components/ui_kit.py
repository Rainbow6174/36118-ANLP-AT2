"""Reusable NiceGUI elements wired to the shared CSS classes."""

from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement

_ALERT_ICONS = {"review": "⚠", "error": "⚠", "success": "✓"}


class _Heading(TextElement):
    """A text element rendered as <h1>..<h6>."""

    def __init__(self, text: str, level: int) -> None:
        super().__init__(tag=f"h{level}", text=text)


def crisis_heading(text: str, level: int = 2):
    """A real HTML heading (for screen readers) styled as text-h1/h2/h3."""
    return _Heading(text, level).classes(f"text-h{level}")


def crisis_button(
    text: str,
    on_click=None,
    variant: str = "primary",
    icon: str | None = None,
):
    """variant: primary | secondary | ghost."""
    button = (
        ui.button(text, on_click=on_click)
        .classes("crisis-btn")
        .props("no-caps unelevated")
    )
    if icon:
        button.props(f"icon={icon}")
    if variant == "secondary":
        button.props("outline")
    elif variant == "ghost":
        button.props("flat")
    return button


def crisis_input(label: str | None, icon: str | None = None, **kwargs):
    """Outlined text input; label=None shows the placeholder instead of a floating label."""
    field = ui.input(label=label, **kwargs).classes("w-full").props("outlined")
    if icon:
        with field.add_slot("prepend"):
            ui.icon(icon).classes("text-text-secondary")
    return field


def crisis_textarea(label: str, max_length: int | None = None, **kwargs):
    """Multi-line input with an optional character counter."""
    textarea = ui.textarea(label=label, **kwargs).classes("w-full").props("outlined")
    if max_length:
        textarea.props(f"maxlength={max_length} counter")
    return textarea


def crisis_select(
    label: str, options: dict[str, str], value: str | None = None, **kwargs
):
    """Dropdown; options maps each stored value to its visible text."""
    return (
        ui.select(options, label=label, value=value, **kwargs)
        .classes("w-full")
        .props("outlined")
    )


def crisis_empty_state(
    icon: str,
    title: str,
    message: str,
    action_label: str | None = None,
    action_target: str | None = None,
    on_action=None,
):
    """Empty list message; its button opens action_target or calls on_action."""
    with ui.column().classes("crisis-empty"):
        ui.icon(icon).classes("crisis-empty-icon")
        crisis_heading(title, 3)
        ui.label(message).classes("text-body-sm")
        if action_label and (action_target or on_action):
            crisis_button(
                action_label,
                variant="secondary",
                on_click=on_action or (lambda: ui.navigate.to(action_target)),
            )


def crisis_error_state(message: str, on_retry):
    """Load-failure message with a retry button."""
    with ui.column().classes("crisis-empty"):
        ui.icon("cloud_off").classes("crisis-empty-icon")
        crisis_heading("Could not load this page", 3)
        ui.label(message).classes("text-body-sm")
        crisis_button(
            "Try again", variant="secondary", icon="refresh", on_click=on_retry
        )


def crisis_card():
    """A bordered container: `with crisis_card(): ...`."""
    return ui.element("div").classes("crisis-card")


def crisis_alert(tone: str, title: str, message: str | None = None):
    """tone: review | error | success."""
    with ui.element("div").classes(f"crisis-alert crisis-alert--{tone}"):
        ui.label(_ALERT_ICONS[tone])
        with ui.column().style("gap: 4px;"):
            ui.label(title).classes("text-body").style("font-weight: 500;")
            if message:
                ui.label(message).classes("text-body-sm")


def crisis_skeleton_cards(count: int = 3) -> None:
    """Grey placeholders shaped like report cards, shown while data loads."""
    for _ in range(count):
        _skeleton_card()


def _skeleton_card() -> None:
    with (
        ui.element("div")
        .classes("crisis-card")
        .style("display: flex; flex-direction: column; gap: 8px;")
    ):
        ui.element("div").classes("crisis-skeleton-block").style(
            "height: 16px; width: 40%;"
        )
        ui.element("div").classes("crisis-skeleton-block").style(
            "height: 20px; width: 75%;"
        )
        ui.element("div").classes("crisis-skeleton-block").style(
            "height: 16px; width: 55%;"
        )
