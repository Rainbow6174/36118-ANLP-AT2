"""End-to-end check of a running CrisisLens backend, intended for the real runtime.

Start the backend first (see README "Run the backend"), then run:

    python scripts/real_mode_check.py            # default http://localhost:8000
    python scripts/real_mode_check.py http://host:port

It submits a few clearly marked test reports, walks through the user and
administrator journeys (analyse, save, browse, search, hide, restore, delete)
and deletes every report it created. It exits with code 1 if any check fails.
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
TAG = f"rmcheck{uuid.uuid4().hex[:6]}"  # unique word, so search hits only our reports
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{' - ' + detail if detail else ''}")


def main() -> int:
    created: list[str] = []
    with httpx.Client(base_url=BASE, timeout=60) as c:
        health = c.get("/api/health").json()
        runtime = health["runtime"]
        check("Backend runs the real classifier and retrieval index",
              runtime["active_runtime"] == "real",
              f"{runtime['classifier']} / {runtime['retriever']}")

        text = f"Families at the school need drinking water and blankets tonight {TAG}"
        t0 = time.perf_counter()
        analysed = c.post("/api/analyse", json={"text": text}).json()
        ms = (time.perf_counter() - t0) * 1000
        pred = analysed["prediction"]
        check("Analyse returns a DistilBERT prediction",
              pred["model_version"] == runtime["classifier"]
              and abs(sum(pred["probabilities"].values()) - 1) < 1e-3,
              f"{pred['predicted_label']} at {pred['confidence']:.2f} in {ms:.0f} ms")
        related = analysed["related_reports"]
        check("Similar reports come only from the current event, never past disasters",
              all(r["source_type"] == "user" for r in related),
              f"{len(related)} related")

        def save(body_text: str, author: str | None, needs_review: bool) -> dict:
            p = c.post("/api/analyse", json={"text": body_text}).json()["prediction"]
            body = {"text": body_text, "predicted_label": p["predicted_label"],
                    "confidence": p["confidence"], "model_version": p["model_version"],
                    "needs_review": needs_review, "created_by": author}
            saved = c.post("/api/reports", json=body).json()
            created.append(saved["message_id"])
            return saved

        mine = save(text, "user", needs_review=False)
        waiting = save(f"Not sure what is happening near the bridge {TAG}", "user", needs_review=True)
        save(f"Volunteers are collecting food at the hall {TAG}", "admin", needs_review=False)
        check("Saved reports keep their author", mine.get("created_by") == "user")

        again = c.post("/api/analyse", json={
            "text": f"The families at the school still need drinking water and blankets {TAG}",
        }).json()["related_reports"]
        check("A new report finds an earlier report about the same situation",
              mine["message_id"] in {r["id"] for r in again}
              and all(r["source_type"] == "user" for r in again),
              f"{len(again)} similar, top similarity "
              f"{again[0]['similarity']:.2f}" if again else "none")

        own = c.get("/api/reports", params={"created_by": "user", "k": 200}).json()
        own_ids = {r["message_id"] for r in own["items"]}
        check("My reports lists only this user's reports",
              {mine["message_id"], waiting["message_id"]} <= own_ids
              and all(r["created_by"] == "user" for r in own["items"]),
              f"{own['total']} report(s) for 'user'")

        detail = c.get(f"/api/reports/{mine['message_id']}").json()
        rel = detail["related_reports"]
        check("Report detail shows similar reports of the current event, excluding itself",
              all(r["source_type"] == "user" and r["id"] != mine["message_id"]
                  for r in rel), f"{len(rel)} related")

        def search_ids(**params) -> set[str]:
            return {i["id"] for i in c.get("/api/search", params={"q": TAG, "k": 50, **params}).json()["items"]}

        check("A new report is searchable immediately", mine["message_id"] in search_ids())

        hide = c.patch(f"/api/reports/{waiting['message_id']}", json={"hidden": True}).json()
        check("Administrator can hide a report", hide["status"] == "hidden")
        check("A hidden report leaves search results", waiting["message_id"] not in search_ids())
        public = c.get("/api/reports", params={"exclude_hidden": "true", "k": 200}).json()
        check("A hidden report leaves public lists",
              waiting["message_id"] not in {r["message_id"] for r in public["items"]})
        queue = c.get("/api/reports", params={"status": "needs_review", "k": 200}).json()
        check("A hidden report leaves the review queue",
              waiting["message_id"] not in {r["message_id"] for r in queue["items"]})

        restored = c.patch(f"/api/reports/{waiting['message_id']}", json={"hidden": False}).json()
        check("Restore returns the report to its previous status",
              restored["status"] == "needs_review", restored["status"])
        check("A restored report is searchable again", waiting["message_id"] in search_ids())

        confirmed = c.patch(f"/api/reports/{waiting['message_id']}", json={"status": "resolved"}).json()
        check("Confirming a category marks it reviewed", confirmed["status"] == "resolved")

        check("Search date filter keeps today's reports",
              mine["message_id"] in search_ids(created_after="2026-01-01T00:00:00Z"))
        check("Search date filter removes reports outside the range",
              mine["message_id"] not in search_ids(created_before="2020-01-01T00:00:00Z"))
        check("Empty search is rejected by design",
              c.get("/api/search", params={"q": ""}).status_code == 422)

        history = c.get("/api/search", params={"q": "water", "source_type": "humaid_history",
                                               "board_label": "requests_or_urgent_needs", "k": 3}).json()
        check("Historical messages can be searched by board",
              history["items"] and all(i["source_type"] == "humaid_history" for i in history["items"]),
              f"{len(history['items'])} results")

        for message_id in created:
            c.delete(f"/api/reports/{message_id}")
        check("Deleted reports leave search and storage",
              not search_ids() and all(
                  c.get(f"/api/reports/{m}").status_code == 404 for m in created))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
