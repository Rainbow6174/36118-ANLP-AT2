"""Report flow: describe, review the suggested category, publish (the person always has the last word)."""

from components.location_picker import LocationPicker
from components.report_cards import related_card
from components.ui_kit import (
    crisis_alert,
    crisis_button,
    crisis_card,
    crisis_heading,
    crisis_select,
    crisis_textarea,
)
from constants.labels import (
    LABEL_DESCRIPTIONS,
    LABEL_DISPLAY_NAMES,
    LABEL_ICONS,
    LABELS,
    label_colors,
)
from layout import frame
from nicegui import ui
from schemas.api import AnalyseResponse, LocationInput
from services import api, auth


def _ordered_categories(analysis: AnalyseResponse) -> dict[str, str]:
    """All categories, with the model's three most likely ones listed first."""
    probabilities = analysis.prediction.probabilities
    likely = sorted(
        LABELS, key=lambda label: probabilities.get(label, 0.0), reverse=True
    )
    return {label: LABEL_DISPLAY_NAMES[label] for label in likely}


@ui.page("/submit", title="Report a crisis · CrisisLens")
def submit_page() -> None:
    draft_text = ""
    draft_location: LocationInput | None = None
    draft_revision = 0
    pin_left_out = False
    analysis_busy = False
    publishing_busy = False

    def set_step(active: int) -> None:
        for number, chip in enumerate(step_chips, start=1):
            if number == active:
                chip.classes(add="crisis-submit-step--active")
            else:
                chip.classes(remove="crisis-submit-step--active")

    def reset_review() -> None:
        """Drop the review step whenever the draft changes."""
        nonlocal draft_revision

        had_review = review_card.visible or analysis_busy

        draft_revision += 1
        review_card.visible = False
        set_step(1)

        if had_review:
            feedback.set_text(
                "Your report has changed. Click Review report "
                "again to update the suggested category."
            )
            feedback.classes(
                add="crisis-form-feedback--notice",
                remove="crisis-form-feedback--error",
            )
        else:
            feedback.set_text("")

    def back_to_editing() -> None:
        reset_review()
        ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'})")

    async def analyse() -> None:
        """Check the draft and ask the backend for a suggestion."""
        nonlocal draft_text, draft_location, pin_left_out, analysis_busy
        if analysis_busy or publishing_busy:
            return
        text = (description.value or "").strip()
        if not text:
            feedback.set_text("Please describe the situation first.")
            feedback.classes(add="crisis-form-feedback--error")
            return
        # An unconfirmed pin is never submitted; the review step says so.
        pin_left_out = location_picker.has_unconfirmed_pin()
        chosen = location_picker.get_location()
        draft_location = LocationInput(**chosen.as_api_location()) if chosen else None
        draft_text = text
        request_revision = draft_revision
        feedback.set_text("")
        analysis_busy = True
        analyse_button.disable()
        analyse_button.props("loading")
        try:
            result = await api.analyse(text, draft_location)
        except api.BackendError:
            if request_revision == draft_revision:
                # Also shown by the button, because a pop-up is easy to miss.
                feedback.set_text(
                    "The report could not be analysed. Check your connection "
                    "and press Review report again. Your text is still here."
                )
                feedback.classes(
                    add="crisis-form-feedback--error",
                    remove="crisis-form-feedback--notice",
                )
                ui.notify("Analysis failed. Please try again.", type="negative")
            return
        finally:
            analysis_busy = False
            analyse_button.props(remove="loading")
            analyse_button.enable()

        # The draft changed while waiting: ignore this answer.
        if request_revision != draft_revision:
            return
        show_review(result)

    def show_review(result: AnalyseResponse) -> None:
        prediction = result.prediction
        suggested = prediction.predicted_label
        review_body.clear()

        with review_body:
            crisis_heading("Review the suggested category", 2)

            with ui.column().classes("crisis-summary"):
                ui.label("Your report").classes("text-caption")
                ui.label(draft_text).classes("text-body crisis-report-text")
                if draft_location is None:
                    ui.label(
                        "The map pin was not confirmed, so no location is "
                        "included. Go back to confirm it."
                        if pin_left_out
                        else "No location included in this report."
                    ).classes("text-body-sm")
                else:
                    # A confirmed point counts even without a place name.
                    with ui.row().classes("crisis-report-meta-item"):
                        ui.icon("place").classes("text-body-sm")
                        ui.label(
                            draft_location.location_name
                            or "Approximate location included (place name unavailable)"
                        )

            background, foreground = label_colors(suggested)

            with (
                ui.column()
                .classes("crisis-suggestion")
                .style(
                    f"background-color: {background}; "
                    f"border-left: 4px solid {foreground};"
                )
            ):
                ui.label("CrisisLens suggests").classes("text-caption")
                with ui.row().classes("items-center gap-2"):
                    ui.icon(LABEL_ICONS[suggested]).style(f"color: {foreground}")

                    ui.label(LABEL_DISPLAY_NAMES[suggested]).classes(
                        "crisis-suggestion-name"
                    ).style(f"color: {foreground}")

                ui.label(f"Confidence: {round(prediction.confidence * 100)}%").classes(
                    "text-body-sm"
                )
                if api.is_mock_model(prediction.model_version):
                    ui.label(
                        "Demo classifier: the trained model is not connected yet."
                    ).classes("text-caption")

            if prediction.needs_review:
                crisis_alert(
                    "review",
                    "We are less certain about this report",
                    "Please check the category below before publishing. The "
                    "report will also be listed in the Review queue so someone "
                    "else can check its category.",
                )

            category = crisis_select(
                "Category",
                _ordered_categories(result),
                suggested,
            )
            category_hint = ui.label(LABEL_DESCRIPTIONS[suggested]).classes(
                "text-body-sm"
            )
            category.on_value_change(
                lambda event: category_hint.set_text(LABEL_DESCRIPTIONS[event.value])
            )

            if result.related_reports:
                crisis_heading("Similar reports", 3)
                with ui.column().classes("crisis-report-list"):
                    for related in result.related_reports:
                        related_card(related, "Similar to your report")

            ui.label(
                "Once published, your report is visible to everyone. Only its author "
                "or an administrator can change its category."
            ).classes("text-body-sm")
            publish_feedback = ui.label("").classes(
                "crisis-form-feedback crisis-form-feedback--error"
            )
            with ui.row().classes("crisis-submit-actions"):
                crisis_button(
                    "Back to editing",
                    variant="secondary",
                    icon="edit",
                    on_click=back_to_editing,
                )
                publish_button = crisis_button("Publish report", icon="publish")
                publish_button.on_click(
                    lambda: publish(
                        result, category.value, publish_button, publish_feedback
                    )
                )

        review_card.visible = True
        set_step(2)
        ui.run_javascript(
            f"document.getElementById('c{review_card.id}')"
            ".scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    async def publish(
        result: AnalyseResponse, board_label: str, button, message
    ) -> None:
        nonlocal publishing_busy
        if publishing_busy or analysis_busy or not review_card.visible:
            return
        publishing_busy = True
        message.set_text("")
        button.disable()
        button.props("loading")
        try:
            report = await api.create_report(
                draft_text, result.prediction, board_label, draft_location,
                created_by=auth.current_user(),
            )
        except api.BackendError:
            message.set_text(
                "The report could not be published. Check your connection "
                "and try again. Nothing was saved."
            )
            ui.notify("The report could not be published.", type="negative")
            return
        except Exception:
            message.set_text(
                "Something went wrong. Please try again."
            )
            return
        else:
            ui.navigate.to(f"/boards/{report.board_label}?new={report.message_id}")
        finally:
            publishing_busy = False
            button.props(remove="loading")
            button.enable()

    with frame():
        with ui.column().classes("crisis-submit-page"):
            crisis_heading("Report a crisis", 1)
            ui.label(
                "Share what is happening. CrisisLens helps organise "
                "community reports but does not verify them."
            ).classes("text-body-sm")

            crisis_alert(
                "review",
                "In immediate danger?",
                "Contact your local emergency number first (000 in Australia, "
                "112 in many other countries). CrisisLens is not an emergency "
                "service and cannot send help.",
            )

            with ui.row().classes("crisis-submit-steps"):
                step_chips = [
                    ui.label("1  Describe").classes(
                        "crisis-submit-step crisis-submit-step--active"
                    ),
                    ui.label("2  Review category").classes("crisis-submit-step"),
                    ui.label("3  Publish").classes("crisis-submit-step"),
                ]

            with crisis_card():
                with ui.column().classes("crisis-submit-card"):
                    with ui.column().classes("crisis-report-description w-full"):
                        description = crisis_textarea(
                            "What's happening? *",
                            max_length=2000,
                            placeholder=(
                                "e.g. Families near the school need clean drinking water"
                            ),
                        )
                        description.on_value_change(reset_review)
                        with ui.row().classes("crisis-privacy-note"):
                            ui.icon("privacy_tip")
                            ui.label(
                                "Please do not include names, phone numbers, home "
                                "addresses or any other personal or sensitive "
                                "information."
                            )

                    ui.separator().classes("w-full")

                    with ui.column().classes("crisis-report-location w-full"):
                        location_picker = LocationPicker(on_change=reset_review)

                    ui.separator().classes("w-full")
                    feedback = ui.label("").classes(
                        "crisis-form-feedback crisis-form-feedback--error"
                    )
                    analyse_button = crisis_button(
                        "Review report", icon="arrow_forward", on_click=analyse
                    )

            # Hidden until the report has been analysed.
            with crisis_card() as review_card:
                review_body = ui.column().classes("crisis-submit-card")
            review_card.visible = False
