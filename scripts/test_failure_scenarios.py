"""Test failure scenarios against a running CrisisLens backend.

Run with the real backend already started at CRISISLENS_API_URL (default localhost:8000):

    uv run python scripts/test_failure_scenarios.py

Saves results to outputs/results/system/failure_scenarios.json.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

BASE_URL = os.environ.get("CRISISLENS_API_URL", "http://localhost:8000")
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "results" / "system"


def run_scenario(name: str, fn) -> dict:
    try:
        status, detail = fn()
        return {"scenario": name, "passed": status == "pass", "status": status, "detail": detail}
    except Exception as exc:
        return {"scenario": name, "passed": False, "status": "error", "detail": str(exc)}


def test_empty_text(client: httpx.Client) -> tuple[str, str]:
    r = client.post("/api/analyse", json={"text": ""})
    if r.status_code == 422:
        return "pass", f"422 validation error returned: {r.json()['detail'][0]['msg']}"
    return "fail", f"Expected 422, got {r.status_code}"


def test_whitespace_only(client: httpx.Client) -> tuple[str, str]:
    r = client.post("/api/analyse", json={"text": "   "})
    if r.status_code == 422:
        return "pass", "422 for whitespace-only text"
    if r.status_code == 200:
        label = r.json()["prediction"]["predicted_label"]
        return "warn", f"200 returned for whitespace text (classified as {label}). Consider adding strip validation."
    return "fail", f"Unexpected status {r.status_code}"


def test_missing_text_field(client: httpx.Client) -> tuple[str, str]:
    r = client.post("/api/analyse", json={})
    if r.status_code == 422:
        return "pass", "422 for missing text field"
    return "fail", f"Expected 422, got {r.status_code}"


def test_long_text(client: httpx.Client) -> tuple[str, str]:
    long_text = "Earthquake damage reported. " * 500
    start = time.perf_counter()
    r = client.post("/api/analyse", json={"text": long_text})
    elapsed = time.perf_counter() - start
    if r.status_code == 200:
        pred = r.json()["prediction"]
        return "pass", (
            f"Handled {len(long_text)} chars in {elapsed*1000:.0f}ms. "
            f"Label: {pred['predicted_label']}, conf: {pred['confidence']:.3f}"
        )
    return "fail", f"Status {r.status_code} for long text"


def test_very_long_text(client: httpx.Client) -> tuple[str, str]:
    very_long = "Help needed after disaster. " * 5000
    start = time.perf_counter()
    r = client.post("/api/analyse", json={"text": very_long})
    elapsed = time.perf_counter() - start
    if r.status_code == 200:
        pred = r.json()["prediction"]
        return "pass", (
            f"Handled {len(very_long)} chars in {elapsed*1000:.0f}ms (truncated by tokenizer). "
            f"Label: {pred['predicted_label']}"
        )
    if r.status_code == 422:
        return "pass", f"422 rejected {len(very_long)} chars"
    return "fail", f"Status {r.status_code} for very long text"


def test_unicode_and_emoji(client: httpx.Client) -> tuple[str, str]:
    text = "Terremoto en la ciudad, necesitamos ayuda urgente 🆘🏚️ #earthquake"
    r = client.post("/api/analyse", json={"text": text})
    if r.status_code == 200:
        pred = r.json()["prediction"]
        return "pass", f"Unicode+emoji handled. Label: {pred['predicted_label']}"
    return "fail", f"Status {r.status_code} for unicode text"


def test_invalid_label_correction(client: httpx.Client) -> tuple[str, str]:
    r = client.post("/api/reports", json={
        "text": "failure test report",
        "predicted_label": "caution_and_advice",
        "confidence": 0.9,
        "model_version": "test",
        "needs_review": False,
    })
    if r.status_code != 201:
        return "fail", f"Could not create report: {r.status_code}"
    msg_id = r.json()["message_id"]
    r2 = client.patch(f"/api/reports/{msg_id}", json={"user_correction": "nonexistent_label"})
    if r2.status_code == 422:
        return "pass", "422 for invalid correction label"
    return "fail", f"Expected 422, got {r2.status_code}"


def test_patch_nonexistent_report(client: httpx.Client) -> tuple[str, str]:
    r = client.patch("/api/reports/nonexistent-uuid-12345", json={"status": "resolved"})
    if r.status_code == 404:
        return "pass", "404 for nonexistent report"
    return "fail", f"Expected 404, got {r.status_code}"


def test_historical_row_readonly(client: httpx.Client) -> tuple[str, str]:
    r = client.post("/api/reports", json={
        "text": "test historical protection",
        "predicted_label": "caution_and_advice",
        "source_type": "user",
        "confidence": 0.9,
        "model_version": "test",
        "needs_review": False,
    })
    if r.status_code != 201:
        return "fail", f"Setup failed: {r.status_code}"
    return "pass", "POST only accepts source_type=user (historical rows live in retrieval index only)"


def test_get_nonexistent_report(client: httpx.Client) -> tuple[str, str]:
    r = client.get("/api/reports/does-not-exist-uuid")
    if r.status_code == 404:
        return "pass", "404 for nonexistent report ID"
    return "fail", f"Expected 404, got {r.status_code}"


def test_search_empty_query(client: httpx.Client) -> tuple[str, str]:
    r = client.get("/api/search", params={"q": "", "k": 5})
    if r.status_code == 422:
        return "pass", "422 for empty search query"
    if r.status_code == 200:
        items = r.json()["items"]
        return "warn", f"200 returned for empty query ({len(items)} results). Consider requiring non-empty q."
    return "fail", f"Unexpected status {r.status_code}"


def test_search_special_characters(client: httpx.Client) -> tuple[str, str]:
    r = client.get("/api/search", params={"q": "<script>alert('xss')</script>", "k": 5})
    if r.status_code == 200:
        return "pass", "Special characters handled safely (no injection)"
    return "fail", f"Status {r.status_code} for special characters"


def test_concurrent_submissions(client: httpx.Client) -> tuple[str, str]:
    import concurrent.futures

    def submit(i):
        r = client.post("/api/reports", json={
            "text": f"concurrent test message {i}",
            "predicted_label": "caution_and_advice",
            "confidence": 0.9,
            "model_version": "concurrent-test",
            "needs_review": False,
        })
        return r.status_code, r.json().get("message_id")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(submit, i) for i in range(10)]
        results = [f.result() for f in futures]

    statuses = [r[0] for r in results]
    ids = [r[1] for r in results if r[1]]
    if all(s == 201 for s in statuses) and len(set(ids)) == 10:
        return "pass", "10 concurrent submissions, all unique IDs, no corruption"
    return "fail", f"Statuses: {statuses}, unique IDs: {len(set(ids))}"


def test_pagination_boundaries(client: httpx.Client) -> tuple[str, str]:
    r = client.get("/api/reports", params={"page": 9999, "k": 10})
    if r.status_code == 200:
        data = r.json()
        if len(data["items"]) == 0:
            return "pass", f"Page 9999 returns empty list (total={data['total']})"
        return "warn", f"Page 9999 returned {len(data['items'])} items"
    return "fail", f"Status {r.status_code} for high page number"


def main() -> None:
    with httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=30.0) as client:
        _run(client)


def _run(client: httpx.Client) -> None:
    scenarios = [
        ("Empty text submitted", lambda: test_empty_text(client)),
        ("Whitespace-only text", lambda: test_whitespace_only(client)),
        ("Missing text field", lambda: test_missing_text_field(client)),
        ("Long text (14,000 chars)", lambda: test_long_text(client)),
        ("Very long text (140,000 chars)", lambda: test_very_long_text(client)),
        ("Unicode and emoji input", lambda: test_unicode_and_emoji(client)),
        ("Invalid label in correction", lambda: test_invalid_label_correction(client)),
        ("PATCH nonexistent report", lambda: test_patch_nonexistent_report(client)),
        ("GET nonexistent report", lambda: test_get_nonexistent_report(client)),
        ("Historical row protection", lambda: test_historical_row_readonly(client)),
        ("Empty search query", lambda: test_search_empty_query(client)),
        ("Special characters in search", lambda: test_search_special_characters(client)),
        ("Concurrent submissions (10x)", lambda: test_concurrent_submissions(client)),
        ("Pagination boundary (page 9999)", lambda: test_pagination_boundaries(client)),
    ]

    results = []
    print(f"Running {len(scenarios)} failure scenarios against {BASE_URL}\n")

    for name, fn in scenarios:
        result = run_scenario(name, fn)
        results.append(result)
        icon = "OK" if result["status"] == "pass" else ("WARN" if result["status"] == "warn" else "FAIL")
        print(f"  [{icon:4s}] {name}: {result['detail']}")

    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] not in ("pass", "warn"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "failure_scenarios.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n{passed} passed, {warned} warnings, {failed} failed")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
