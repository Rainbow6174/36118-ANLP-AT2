"""Saves the demo community reports into a running backend, so a real-backend demo starts with content.

Run from the repository root: uv run python app/frontend/scripts/seed_demo_reports.py [BACKEND_URL]
"""

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.api import approximate
from services.mock_backend import backend

# The UI marks model versions starting with "demo" as demo data.
DEMO_MODEL_VERSION = "demo-seed"


def location_payload(place) -> dict | None:
    if place is None:
        return None
    return {
        "country": place.country,
        "region": place.region,
        "city": place.city,
        "latitude": approximate(place.latitude),
        "longitude": approximate(place.longitude),
    }


def has_demo_reports(client: httpx.Client) -> bool:
    response = client.get("/api/reports", params={"source_type": "user", "k": 100})
    response.raise_for_status()
    items = response.json()["items"]
    return any(item["model_version"].startswith("demo") for item in items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "url",
        nargs="?",
        default=os.environ.get("CRISISLENS_API_URL") or "http://localhost:8000",
        help="address of the backend (default: CRISISLENS_API_URL or http://localhost:8000)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="add the reports even if demo reports exist",
    )
    args = parser.parse_args()

    # Oldest first, so the newest report gets the latest time.
    reports = list(
        reversed(backend.list_reports(source_type="user", page_size=100).items)
    )

    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=30.0) as client:
            if not args.force and has_demo_reports(client):
                print("Demo reports already exist. Use --force to add them again.")
                return 0

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
                        "location": location_payload(report.location),
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
    except httpx.HTTPError as exc:
        print(f"Could not seed the backend at {args.url}: {exc}")
        return 1

    print(f"Saved {len(reports)} demo reports to {args.url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
