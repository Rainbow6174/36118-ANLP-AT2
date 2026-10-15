"""Prepare a running CrisisLens backend for a demonstration.

Each deployment serves one event. Three starting points are provided:

    empty   Remove every community report, so the event starts with no messages
            and the database fills only with what users submit.
    nepal   Load the Nepal flood and landslide scenario (the same nine reports
            the demo mode shows), marked as demo data.
    event   Replay messages from one HumAID disaster as the current event. Each
            message goes through the running classifier, so categories,
            confidence and review flags are real model outputs. Only the event's
            test split is used, because the model was trained on the other splits.

Usage, from the repository root with the backend running:
    python scripts/demo_data.py empty --yes
    python scripts/demo_data.py nepal [--replace]
    python scripts/demo_data.py event kerala_floods_2018 [--limit 40] [--replace]
    python scripts/demo_data.py event --list
    python scripts/demo_data.py nepal --url http://localhost:8000

A brand-new database file (a new CRISISLENS_DB_PATH) is also an empty start.
Past-disaster messages (HumAID) are not stored in the database and are never
removed; they stay available for the historical search mode and board examples.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "frontend"))

from schemas.api import approximate
from services.mock_backend import backend as demo_scenario

# The interface marks model versions starting with "demo" as demo data.
DEMO_MODEL_VERSION = "demo-seed"
PAGE_SIZE = 200
# Downloaded by notebooks/01_crisis_eda.ipynb.
EVENTS_DIR = ROOT / "data" / "raw" / "humaid_events"


def community_reports(client: httpx.Client) -> list[dict]:
    """Every community report, hidden ones included."""
    reports, page = [], 1
    while True:
        response = client.get(
            "/api/reports",
            params={"source_type": "user", "k": PAGE_SIZE, "page": page},
        )
        response.raise_for_status()
        body = response.json()
        reports.extend(body["items"])
        if page * PAGE_SIZE >= body["total"]:
            return reports
        page += 1


def clear(client: httpx.Client) -> int:
    reports = community_reports(client)
    for report in reports:
        client.delete(f"/api/reports/{report['message_id']}").raise_for_status()
    return len(reports)


def _location(place) -> dict | None:
    if place is None:
        return None
    return {
        "country": place.country,
        "region": place.region,
        "city": place.city,
        "latitude": approximate(place.latitude),
        "longitude": approximate(place.longitude),
    }


def load_nepal(client: httpx.Client) -> int:
    # Oldest first, so the newest report gets the latest time.
    reports = list(
        reversed(demo_scenario.list_reports(source_type="user", page_size=100).items)
    )
    for report in reports:
        created = client.post(
            "/api/reports",
            json={
                "text": report.text,
                "predicted_label": report.predicted_label,
                "board_label": report.board_label,
                "confidence": report.confidence,
                "model_version": DEMO_MODEL_VERSION,
                "needs_review": report.needs_review,
                "location": _location(report.location),
            },
        )
        created.raise_for_status()
        if report.status == "resolved":
            client.patch(
                f"/api/reports/{created.json()['message_id']}",
                json={"status": "resolved"},
            ).raise_for_status()
        # The backend stores whole seconds; this keeps the order of the reports.
        time.sleep(1.1)
    return len(reports)


def available_events() -> list[str]:
    return sorted(p.name.split("__")[0] for p in EVENTS_DIR.glob("*__test.json"))


def _anonymise(text: str) -> str:
    """Remove links and usernames, as for historical messages in the interface."""
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "@user", text)
    return re.sub(r"\s+", " ", text).strip()


def load_event(client: httpx.Client, event: str, limit: int, seed: int) -> int:
    path = EVENTS_DIR / f"{event}__test.json"
    if not path.exists():
        raise SystemExit(
            f"No test file for '{event}' in {EVENTS_DIR}. "
            "Run notebooks/01_crisis_eda.ipynb to download the events, "
            "or use --list to see the available ones."
        )
    messages = [m for m in json.loads(path.read_text(encoding="utf-8")) if m.get("tweet_text")]
    sample = random.Random(seed).sample(messages, min(limit, len(messages)))
    for message in sample:
        text = _anonymise(message["tweet_text"])[:2000]
        if not text:
            continue
        analysed = client.post("/api/analyse", json={"text": text})
        analysed.raise_for_status()
        prediction = analysed.json()["prediction"]
        client.post(
            "/api/reports",
            json={
                "text": text,
                "predicted_label": prediction["predicted_label"],
                "confidence": prediction["confidence"],
                # Marked as demo data; the real model version is kept after the prefix.
                "model_version": f"demo-{event}/{prediction['model_version']}",
                "needs_review": prediction["needs_review"],
            },
        ).raise_for_status()
    return len(sample)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=["empty", "nepal", "event"])
    parser.add_argument("event_name", nargs="?", help="event: HumAID event, e.g. kerala_floods_2018")
    parser.add_argument("--list", action="store_true", help="event: list the available events")
    parser.add_argument("--limit", type=int, default=40, help="event: number of messages (default 40)")
    parser.add_argument("--seed", type=int, default=42, help="event: sampling seed (default 42)")
    parser.add_argument(
        "--url",
        default=os.environ.get("CRISISLENS_API_URL") or "http://localhost:8000",
        help="backend address (default: CRISISLENS_API_URL or http://localhost:8000)",
    )
    parser.add_argument("--yes", action="store_true", help="confirm removing reports")
    parser.add_argument(
        "--replace", action="store_true", help="nepal/event: remove existing reports first"
    )
    args = parser.parse_args()

    if args.scenario == "event" and (args.list or not args.event_name):
        print("Available events:", ", ".join(available_events()) or "none (run the EDA notebook)")
        return 0 if args.list else 1

    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=60.0) as client:
            existing = community_reports(client)
            if args.scenario == "empty":
                if existing and not args.yes:
                    print(f"{len(existing)} community reports would be removed. "
                          "Run again with --yes to confirm.")
                    return 1
                print(f"Removed {clear(client)} community reports. The event starts empty.")
                return 0

            if args.replace:
                print(f"Removed {clear(client)} community reports.")
            elif existing:
                print(f"The event already has {len(existing)} reports. "
                      "Use --replace to remove them first.")
                return 0
            if args.scenario == "nepal":
                print(f"Loaded {load_nepal(client)} Nepal demo reports.")
            else:
                count = load_event(client, args.event_name, args.limit, args.seed)
                print(f"Loaded {count} messages from {args.event_name} "
                      "(classified by the running model, marked as demo data).")
            return 0
    except httpx.HTTPError as exc:
        print(f"Could not reach the backend at {args.url}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
