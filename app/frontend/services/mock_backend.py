"""In-memory demo backend: a keyword classifier, keyword search and sample reports that reset on restart."""

import math
import re
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from constants.labels import LABELS
from schemas.api import (
    ClassificationResponse,
    CrisisReport,
    LocationInput,
    RelatedReport,
    ReportListResponse,
)

MOCK_MODEL_VERSION = "mock-keyword-v0"
# The deployed DistilBERT's review threshold (models/transformer/metadata.json).
REVIEW_THRESHOLD = 0.8866

VALID_STATUSES = ("unverified", "needs_review", "resolved", "hidden")

_LOGIT_PER_HIT = 1.15
# With no keyword hits the text leans weakly to "other information".
_OTHER_PRIOR = 0.6

_KEYWORDS: dict[str, tuple[str, ...]] = {
    label: tuple(words.split(","))
    for label, words in {
        "requests_or_urgent_needs": "need,urgent,help,water,food,shelter,medicine,supplies,blankets,stranded,trapped,stuck,require",
        "rescue_volunteering_or_donation_effort": "rescue,volunteers,donate,donation,fund,relief,distribution,collecting,aid,team",
        "infrastructure_and_utility_damage": "road,bridge,power,electricity,damage,collapsed,blocked,landslide,outage,building,destroyed,network",
        "displaced_people_and_evacuations": "evacuate,displaced,camp,fled,relocated,homeless,households,moved",
        "injured_or_dead_people": "injured,dead,death,killed,casualties,wounded,hospital",
        "missing_or_found_people": "missing,found,whereabouts,looking for,last seen,contact",
        "caution_and_advice": "warning,avoid,caution,advice,alert,do not,danger,unsafe,unstable,risk",
        "sympathy_and_support": "pray,thoughts,condolences,heartbreaking,sorry,thank",
        "not_humanitarian": "lol,meme,game,movie,celebrity,match",
        "other_relevant_information": "update,news,weather,rain,officials,government,notice,announced",
    }.items()
}

_WORD = re.compile(r"[a-z']+")
_STOPWORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "near",
        "are",
        "was",
        "were",
        "been",
        "this",
        "that",
        "these",
        "those",
        "there",
        "here",
        "they",
        "you",
        "our",
        "their",
        "his",
        "her",
        "its",
        "but",
        "not",
        "who",
        "what",
        "which",
        "when",
        "where",
        "how",
        "all",
        "any",
        "some",
        "many",
        "much",
        "more",
        "most",
        "can",
        "could",
        "will",
        "would",
        "should",
        "may",
        "might",
        "have",
        "has",
        "had",
        "does",
        "did",
        "also",
        "very",
        "just",
        "into",
        "out",
        "over",
        "after",
        "before",
        "than",
        "then",
        "about",
        "while",
        "still",
    ]
)


def _tokens(text: str) -> list[str]:
    return [
        w for w in _WORD.findall(text.lower()) if len(w) >= 3 and w not in _STOPWORDS
    ]


def _same_stem(a: str, b: str) -> bool:
    """Loose match, so 'need' finds 'needs' and 'evacuate' finds 'evacuation'."""
    if a == b:
        return True
    shared = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        shared += 1
    return shared >= max(4, min(len(a), len(b)) - 1)


def _keyword_hit(keyword: str, tokens: list[str], normalised: str) -> bool:
    if " " in keyword:
        return keyword in normalised
    return any(_same_stem(keyword, token) for token in tokens)


def classify(text: str) -> ClassificationResponse:
    tokens = _tokens(text)
    normalised = " ".join(_WORD.findall(text.lower()))

    logits = []
    for label in LABELS:
        hits = sum(_keyword_hit(kw, tokens, normalised) for kw in _KEYWORDS[label])
        prior = _OTHER_PRIOR if label == "other_relevant_information" else 0.0
        logits.append(_LOGIT_PER_HIT * hits + prior)

    peak = max(logits)
    exps = [math.exp(value - peak) for value in logits]
    total = sum(exps)
    # Light smoothing: a calibrated model is almost never 100% sure.
    probabilities = {
        label: round(0.97 * e / total + 0.003, 4)
        for label, e in zip(LABELS, exps, strict=True)
    }

    predicted = max(LABELS, key=lambda label: probabilities[label])
    confidence = probabilities[predicted]
    return ClassificationResponse(
        predicted_label=predicted,
        probabilities=probabilities,
        confidence=confidence,
        model_version=MOCK_MODEL_VERSION,
        needs_review=confidence < REVIEW_THRESHOLD,
    )


def _similarity(a: list[str], b: list[str]) -> float:
    """Word overlap between two token lists (0 means nothing in common)."""
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    matched = sum(
        1 for word in set_a if any(_same_stem(word, other) for other in set_b)
    )
    return matched / math.sqrt(len(set_a) * len(set_b))


def _preview(text: str, limit: int = 140) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _related(report: CrisisReport) -> RelatedReport:
    return RelatedReport(
        id=report.message_id,
        board_label=report.board_label,
        text_preview=_preview(report.text),
        source_type=report.source_type,
    )


def _place(city: str, region: str, lat: float, lon: float) -> LocationInput:
    """A place in Nepal."""
    return LocationInput(
        location_name=f"{city}, {region}, Nepal",
        country="Nepal",
        region=region,
        city=city,
        latitude=lat,
        longitude=lon,
    )


def _seed_reports() -> list[CrisisReport]:
    """Synthetic demo records; none are real reports or HumAID rows."""
    now = datetime.now(UTC)
    bagmati, koshi = "Bagmati Province", "Koshi Province"
    sindhupalchok = _place("Sindhupalchok", bagmati, 27.95, 85.69)
    kathmandu = _place("Kathmandu", bagmati, 27.72, 85.32)
    solukhumbu = _place("Solukhumbu", koshi, 27.79, 86.66)
    lalitpur = _place("Lalitpur", bagmati, 27.66, 85.32)
    kavre = _place("Kavrepalanchok", bagmati, 27.53, 85.55)

    def demo(
        number: str,
        text: str,
        label: str,
        confidence: float,
        minutes_ago: int,
        place: LocationInput | None,
        status: str,
        *,
        predicted: str | None = None,
        source: str = "user",
    ) -> CrisisReport:
        predicted = predicted or label
        return CrisisReport(
            message_id=f"demo-{number}",
            text=text,
            predicted_label=predicted,
            board_label=label,
            source_type=source,
            confidence=confidence,
            model_version=MOCK_MODEL_VERSION,
            needs_review=confidence < REVIEW_THRESHOLD,
            created_at=(now - timedelta(minutes=minutes_ago)).isoformat(),
            status=status,
            user_correction=label if label != predicted else None,
            location=place,
            is_demo=True,
        )

    community = [
        demo(
            "001",
            "Families sheltering in the school building need clean drinking water and blankets tonight.",
            "requests_or_urgent_needs",
            0.93,
            18,
            sindhupalchok,
            "unverified",
        ),
        demo(
            "002",
            "Several elderly residents are stuck on an upper floor and need help to reach their medicine.",
            "requests_or_urgent_needs",
            0.71,
            42,
            kathmandu,
            "needs_review",
        ),
        demo(
            "003",
            "The road to the upper village is blocked by a landslide and the footbridge has collapsed.",
            "infrastructure_and_utility_damage",
            0.92,
            75,
            solukhumbu,
            "unverified",
        ),
        demo(
            "004",
            "Local volunteers are collecting rice, tarps and dry food at the community hall until 6pm.",
            "rescue_volunteering_or_donation_effort",
            0.9,
            130,
            lalitpur,
            "unverified",
        ),
        demo(
            "005",
            "About thirty households have been moved to a temporary camp near the river.",
            "displaced_people_and_evacuations",
            0.82,
            190,
            kavre,
            "needs_review",
        ),
        demo(
            "006",
            "Looking for my uncle, last seen near the bus park before the road closed. Please contact the ward office if found.",
            "missing_or_found_people",
            0.66,
            300,
            kathmandu,
            "needs_review",
        ),
        demo(
            "007",
            "Please avoid the river path today. The slope above it still looks unstable after the rain.",
            "caution_and_advice",
            0.94,
            370,
            sindhupalchok,
            "unverified",
        ),
        demo(
            "008",
            "Mobile network coverage is patchy in the valley, so the ward office has posted notices at the main gate.",
            "infrastructure_and_utility_damage",
            0.58,
            540,
            solukhumbu,
            "resolved",
            predicted="other_relevant_information",
        ),
        demo(
            "009",
            "Thank you to everyone helping our neighbours. Our thoughts are with the affected families.",
            "sympathy_and_support",
            0.9,
            700,
            kathmandu,
            "unverified",
        ),
    ]
    # Stand-ins for HumAID rows.
    history = [
        demo(
            "h01",
            "Roads under water, boats needed to reach families stuck on rooftops. Please send help.",
            "requests_or_urgent_needs",
            0.95,
            60 * 24 * 400,
            None,
            "unverified",
            source="humaid_history",
        ),
        demo(
            "h02",
            "The bridge washed away overnight and the village is cut off from the main road.",
            "infrastructure_and_utility_damage",
            0.93,
            60 * 24 * 420,
            None,
            "unverified",
            source="humaid_history",
        ),
        demo(
            "h03",
            "Volunteers are sorting donated clothes and clean water at the church hall.",
            "rescue_volunteering_or_donation_effort",
            0.91,
            60 * 24 * 450,
            None,
            "unverified",
            source="humaid_history",
        ),
        demo(
            "h04",
            "Thousands evacuated as the river keeps rising and shelters are filling up.",
            "displaced_people_and_evacuations",
            0.9,
            60 * 24 * 500,
            None,
            "unverified",
            source="humaid_history",
        ),
    ]
    return community + history


class MockBackend:
    def __init__(self) -> None:
        self._reports = _seed_reports()
        # Status each hidden report had before hiding, so restoring can bring it back.
        self._status_before_hidden: dict[str, str] = {}

    def classify(self, text: str) -> ClassificationResponse:
        return classify(text)

    def retrieve(
        self,
        text: str,
        k: int = 5,
        exclude_id: str | None = None,
    ) -> list[RelatedReport]:
        """Like the real backend: the current event's reports in any category,
        hidden reports and past-disaster messages left out."""
        query = _tokens(text)
        scored = []
        for report in self._reports:
            if report.message_id == exclude_id or report.status == "hidden":
                continue
            if report.source_type != "user":
                continue
            score = _similarity(query, _tokens(report.text))
            if score >= 0.15:
                scored.append((score, report))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [_related(report) for _, report in scored[:k]]

    def create_report(
        self,
        text: str,
        prediction: ClassificationResponse,
        board_label: str,
        location: LocationInput | None,
        created_by: str | None = None,
    ) -> CrisisReport:
        text = text.strip()
        if not text:
            raise ValueError("A report needs some text.")
        if board_label not in LABELS:
            raise ValueError(f"Unknown category: {board_label}")

        report = CrisisReport(
            message_id=f"user-{uuid.uuid4().hex[:8]}",
            text=text,
            predicted_label=prediction.predicted_label,
            board_label=board_label,
            source_type="user",
            confidence=prediction.confidence,
            model_version=prediction.model_version,
            needs_review=prediction.needs_review,
            created_at=datetime.now(UTC).isoformat(),
            status="needs_review" if prediction.needs_review else "unverified",
            user_correction=(
                board_label if board_label != prediction.predicted_label else None
            ),
            location=location,
            is_demo=True,
            created_by=created_by,
        )
        self._reports.insert(0, report)
        return report

    def get_report(self, message_id: str) -> CrisisReport | None:
        return next((r for r in self._reports if r.message_id == message_id), None)

    def update_report(
        self,
        message_id: str,
        board_label: str | None = None,
        status: str | None = None,
        hidden: bool | None = None,
    ) -> CrisisReport:
        report = self.get_report(message_id)
        if report is None:
            raise KeyError(message_id)
        if report.source_type == "humaid_history":
            raise PermissionError("Historical records are read-only.")

        changes: dict[str, object] = {}
        if board_label is not None:
            if board_label not in LABELS:
                raise ValueError(f"Unknown category: {board_label}")
            changes["board_label"] = board_label
            changes["user_correction"] = (
                board_label if board_label != report.predicted_label else None
            )
        if hidden is True or status == "hidden":
            if report.status != "hidden":
                self._status_before_hidden[message_id] = report.status
            changes["status"] = "hidden"
        elif hidden is False:
            if report.status == "hidden":
                changes["status"] = self._status_before_hidden.pop(
                    message_id,
                    "needs_review" if report.needs_review else "unverified",
                )
        elif status is not None:
            if status not in VALID_STATUSES:
                raise ValueError(f"Unknown status: {status}")
            changes["status"] = status
            self._status_before_hidden.pop(message_id, None)

        updated = replace(report, **changes)
        self._reports[self._reports.index(report)] = updated
        return updated

    def delete_report(self, message_id: str) -> None:
        report = self.get_report(message_id)
        if report is None:
            raise KeyError(message_id)
        if report.source_type == "humaid_history":
            raise PermissionError("Historical records are read-only.")
        self._reports.remove(report)

    def list_reports(
        self,
        *,
        board_label: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        needs_review: bool | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 6,
        exclude_hidden: bool = False,
        created_by: str | None = None,
    ) -> ReportListResponse:
        items = [
            r
            for r in self._reports
            if (board_label is None or r.board_label == board_label)
            and (source_type is None or r.source_type == source_type)
            and (status is None or r.status == status)
            and (needs_review is None or r.needs_review == needs_review)
            and (not exclude_hidden or r.status != "hidden")
            and (created_by is None or r.created_by == created_by)
        ]
        items.sort(key=lambda r: r.created_at, reverse=True)

        query = _tokens(q or "")
        if query:
            ranked = []
            for report in items:
                place = report.location.location_name if report.location else ""
                words = _tokens(f"{report.text} {place or ''}")
                matched = sum(
                    1 for word in query if any(_same_stem(word, w) for w in words)
                )
                if matched / len(query) >= 0.34:
                    ranked.append((matched / len(query), report))
            # A stable sort keeps newest first among equal scores.
            ranked.sort(key=lambda pair: pair[0], reverse=True)
            items = [report for _, report in ranked]

        page = max(1, page)
        start = (page - 1) * page_size
        return ReportListResponse(
            items=items[start : start + page_size],
            page=page,
            page_size=page_size,
            total=len(items),
        )

    def search(
        self,
        q: str,
        *,
        board_label: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        k: int = 20,
    ) -> list[RelatedReport]:
        result = self.list_reports(
            board_label=board_label,
            source_type=source_type,
            status=status,
            q=q,
            page=1,
            page_size=k,
            exclude_hidden=True,
        )
        return [_related(report) for report in result.items]


backend = MockBackend()
