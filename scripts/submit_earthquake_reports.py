"""Submit realistic earthquake test reports to a running CrisisLens backend.

Based on the October 2026 magnitude 4.8 earthquake near Leongatha, South
Gippsland, Victoria, Australia. The quake was felt in Melbourne's eastern
suburbs. A magnitude 3.1 aftershock followed about 55 minutes later.

Usage:
    uv run python scripts/submit_earthquake_reports.py [BASE_URL]

Default BASE_URL is http://localhost:8000.
"""

from __future__ import annotations

import sys
import time

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

REPORTS = [
    {
        "text": (
            "Earthquake just hit south-east Melbourne, whole house was shaking "
            "for about 10 seconds. Magnitude 4.8 near Leongatha according to "
            "Geoscience Australia. Everyone okay here but very scared."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Melbourne",
            "latitude": -37.81,
            "longitude": 144.96,
        },
    },
    {
        "text": (
            "Minor cracks appearing in the walls of our apartment building in "
            "Dandenong after the earthquake. Power flickered but came back. "
            "Can someone check if the building is structurally safe?"
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Dandenong",
            "latitude": -37.98,
            "longitude": 145.21,
        },
    },
    {
        "text": (
            "Road blocked by fallen debris near Korumburra after the quake. "
            "Power lines down on the Bass Highway between Leongatha and "
            "Korumburra. Avoid the area."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Korumburra",
            "latitude": -38.43,
            "longitude": 145.82,
        },
    },
    {
        "text": (
            "Aftershock magnitude 3.1 felt about an hour after the main quake. "
            "Bureau of Meteorology says no tsunami threat. Stay away from "
            "damaged buildings until inspected."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Leongatha",
            "latitude": -38.47,
            "longitude": 145.95,
        },
    },
    {
        "text": (
            "Water main burst in Gippsland after the earthquake, several "
            "streets flooded. Families in Warragul need bottled water, the "
            "tap water is not safe to drink right now."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Warragul",
            "latitude": -38.16,
            "longitude": 145.93,
        },
    },
    {
        "text": (
            "Volunteers setting up a relief station at the Leongatha Memorial "
            "Hall. Collecting blankets, torches, and non-perishable food for "
            "people whose homes were damaged by the earthquake."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Leongatha",
            "latitude": -38.47,
            "longitude": 145.95,
        },
    },
    {
        "text": (
            "Has anyone heard from the family on Creek Road near Korumburra? "
            "Their house is near the epicentre and we cannot reach them by "
            "phone since the quake."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Korumburra",
            "latitude": -38.43,
            "longitude": 145.82,
        },
    },
    {
        "text": (
            "Thinking of everyone in Gippsland tonight. Melbourne felt the "
            "shaking too. Stay safe and check on your neighbours."
        ),
        "location": {
            "country": "Australia",
            "region": "Victoria",
            "city": "Melbourne",
            "latitude": -37.81,
            "longitude": 144.96,
        },
    },
]


def main() -> None:
    client = httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=30.0)

    # Verify backend is up
    health = client.get("/api/health")
    health.raise_for_status()
    runtime = health.json()["runtime"]["active_runtime"]
    print(f"Backend is running ({runtime} mode) at {BASE_URL}\n")

    for i, report in enumerate(REPORTS, 1):
        # Step 1: analyse the text
        analyse_resp = client.post(
            "/api/analyse",
            json={"text": report["text"], "location": report.get("location")},
        )
        analyse_resp.raise_for_status()
        prediction = analyse_resp.json()["prediction"]

        # Step 2: save the report
        create_body = {
            "text": report["text"],
            "predicted_label": prediction["predicted_label"],
            "confidence": prediction["confidence"],
            "model_version": prediction["model_version"],
            "needs_review": prediction["needs_review"],
            "location": report.get("location"),
        }
        save_resp = client.post("/api/reports", json=create_body)
        save_resp.raise_for_status()
        saved = save_resp.json()

        review = " [REVIEW]" if saved["needs_review"] else ""
        print(
            f"  [{i}/{len(REPORTS)}] {prediction['predicted_label']:<45s} "
            f"conf={prediction['confidence']:.3f}{review}"
        )
        print(f"          {report['text'][:80]}...")
        print(f"          ID: {saved['message_id']}")
        print()

        # Small delay to preserve ordering
        time.sleep(0.3)

    client.close()
    print(f"Done. {len(REPORTS)} earthquake reports submitted to {BASE_URL}.")
    print("Visit http://localhost:8080 to see them on the boards.")


if __name__ == "__main__":
    main()
