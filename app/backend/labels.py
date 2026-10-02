"""Ten HumAID labels, fixed alphabetical order. Shared across API responses."""

LABELS: tuple[str, ...] = (
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
)

LABEL_SET = frozenset(LABELS)

CONFIDENCE_REVIEW_THRESHOLD = 0.60
