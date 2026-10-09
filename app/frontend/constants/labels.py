"""The ten HumAID labels and how each one is named, described, drawn and coloured."""

LABELS: list[str] = [
    "caution_and_advice",
    "displaced_people_and_evacuations",
    "infrastructure_and_utility_damage",
    "injured_or_dead_people",
    "missing_or_found_people",
    "not_humanitarian",
    "other_relevant_information",
    "requests_or_urgent_needs",
    "rescue_volunteering_or_donation_effort",
    "sympathy_and_support",
]


LABEL_DISPLAY_NAMES: dict[str, str] = {
    "caution_and_advice": "Caution & Advice",
    "displaced_people_and_evacuations": "Displacement & Evacuation",
    "infrastructure_and_utility_damage": "Infrastructure Damage",
    "injured_or_dead_people": "Injured or Deceased",
    "missing_or_found_people": "Missing or Found People",
    "not_humanitarian": "Not Humanitarian",
    "other_relevant_information": "Other Relevant Information",
    "requests_or_urgent_needs": "Urgent Needs",
    "rescue_volunteering_or_donation_effort": "Rescue & Donations",
    "sympathy_and_support": "Sympathy & Support",
}


LABEL_DESCRIPTIONS: dict[str, str] = {
    "caution_and_advice": "Warnings, safety advice and places or actions to avoid.",
    "displaced_people_and_evacuations": (
        "Evacuations, shelters and people who had to leave their homes."
    ),
    "infrastructure_and_utility_damage": (
        "Damage to roads, buildings, power, water and communications."
    ),
    "injured_or_dead_people": "Reports of people who were injured or died.",
    "missing_or_found_people": "People who are missing, or who have been found.",
    "not_humanitarian": "Posts that contain no humanitarian information.",
    "other_relevant_information": "Useful updates that fit none of the other boards.",
    "requests_or_urgent_needs": (
        "Requests for water, food, shelter, medicine or other urgent help."
    ),
    "rescue_volunteering_or_donation_effort": (
        "Rescue work, volunteering and donation efforts."
    ),
    "sympathy_and_support": "Messages of sympathy and support.",
}


LABEL_ICONS: dict[str, str] = {
    "caution_and_advice": "warning_amber",
    "displaced_people_and_evacuations": "directions_walk",
    "infrastructure_and_utility_damage": "construction",
    "injured_or_dead_people": "medical_services",
    "missing_or_found_people": "person_search",
    "not_humanitarian": "block",
    "other_relevant_information": "info",
    "requests_or_urgent_needs": "priority_high",
    "rescue_volunteering_or_donation_effort": "volunteer_activism",
    "sympathy_and_support": "favorite",
}


FEATURED_LABELS: list[str] = [
    "requests_or_urgent_needs",
    "rescue_volunteering_or_donation_effort",
    "infrastructure_and_utility_damage",
    "displaced_people_and_evacuations",
    "missing_or_found_people",
    "caution_and_advice",
]


# One hue per category (background, text), text at least 4.5:1 on its background.
LABEL_COLORS = {
    "requests_or_urgent_needs": ("#FCE8E6", "#BA2B20"),  # red
    "rescue_volunteering_or_donation_effort": ("#E4F3EA", "#2A7549"),  # green
    "infrastructure_and_utility_damage": ("#E6EFFA", "#2F6DB3"),  # blue
    "displaced_people_and_evacuations": ("#FEEFD8", "#A35600"),  # orange
    "missing_or_found_people": ("#EEE8F8", "#6D4AA8"),  # purple
    "caution_and_advice": ("#F7F2B8", "#6F6100"),  # olive yellow
    "injured_or_dead_people": ("#F1E7DF", "#6B4226"),  # brown
    "other_relevant_information": ("#DFF3F8", "#0E7490"),  # cyan
    "sympathy_and_support": ("#FCE7F1", "#A8326D"),  # pink
    "not_humanitarian": ("#EEF0EF", "#5B6663"),  # grey
}


def label_colors(label: str) -> tuple[str, str]:
    """(background, text) colours of a category; grey when unknown."""
    return LABEL_COLORS.get(label, LABEL_COLORS["not_humanitarian"])


# Status filter wording: it describes the category check, never whether a report is true.
STATUS_FILTER_OPTIONS: dict[str, str] = {
    "all": "Any status",
    "unverified": "No category review needed",
    "needs_review": "Category needs review",
    "resolved": "Category reviewed",
}
