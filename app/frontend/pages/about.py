"""About page: how CrisisLens works, what to keep in mind, where the information comes from and privacy."""

from components.ui_kit import crisis_card, crisis_heading
from layout import frame
from nicegui import ui

INTRO = (
    "After a disaster, useful information is scattered and hard to sort. "
    "CrisisLens lets people share what they see and helps others find it by topic."
)

SECTIONS = (
    (
        "How it works",
        (
            "Write a short report and CrisisLens suggests a category, such as urgent "
            "needs, damage or evacuation. You can confirm or change it before "
            "publishing. After that, anyone can browse the reports by category, "
            "search the current event and read similar reports already saved for that "
            "event. A separate Historical dataset mode searches past disasters. When "
            "the model is unsure, the report also goes to a review queue, where a "
            "person checks its category."
        ),
    ),
    (
        "What to keep in mind",
        (
            "CrisisLens is not an emergency service and cannot send help. If you are "
            "in danger, call your local emergency number first. It does not check "
            "whether a report is true either, so every report is marked Unverified. "
            "Categories come from a model and can be wrong; “Category reviewed” only "
            "means that a person looked at the category. The category is a topic, "
            "not a measure of urgency, and CrisisLens does not replace official "
            "warnings or emergency information. It currently works with reports "
            "written in English."
        ),
    ),
    (
        "Where the information comes from",
        (
            "Community reports are written by the people who use this app. Historical "
            "search results and the examples on empty boards come from HumAID, a "
            "public dataset of tweets from earlier disasters, so they are not current. "
            "In demo mode, all reports and the classifier are simulated."
        ),
    ),
    (
        "Your privacy",
        (
            "Please leave names, phone numbers and home addresses out of your report. "
            "A location is shared only as an approximate area of about 1 km, never as "
            "an exact pin. Place suggestions use Photon, confirming a pin uses "
            "Nominatim and the maps come from OpenStreetMap; each one receives only "
            "what you send when you use that feature, and the page font loads from "
            "Google Fonts. Tweets from the past are shown without @usernames and links."
        ),
    ),
    (
        "About this project",
        (
            "CrisisLens is a prototype from a university group project (UTS 36118 "
            "ANLP, Group 2). It is not a production system, and its data can be reset."
        ),
    ),
)


@ui.page("/about", title="About · CrisisLens")
def about_page() -> None:
    with frame():
        with ui.column().classes("crisis-page crisis-about"):
            crisis_heading("About CrisisLens", 1)
            ui.label(INTRO).classes("text-body")
            for title, text in SECTIONS:
                with crisis_card(), ui.column().classes("crisis-about-lines"):
                    crisis_heading(title, 2).classes("text-h3", remove="text-h2")
                    ui.label(text).classes("text-body")
