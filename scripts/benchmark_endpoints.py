"""Measure p50 and p95 latency per CrisisLens API endpoint.

Run with the real backend already started at CRISISLENS_API_URL (default localhost:8000):

    uv run python scripts/benchmark_endpoints.py

Saves results to outputs/results/system/endpoint_latency.json and prints a summary table.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import time
from pathlib import Path

import httpx

BASE_URL = os.environ.get("CRISISLENS_API_URL", "http://localhost:8000")
RUNS = 20
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "results" / "system"

ANALYSE_TEXTS = [
    "Several families need drinking water after the flood",
    "Building collapsed in downtown area, multiple trapped",
    "Sending prayers and thoughts to all affected by the hurricane",
    "Road blocked by fallen trees, no power in the neighbourhood",
    "Volunteers distributing blankets at the shelter tonight",
    "Missing person: elderly man last seen near river crossing",
    "Warning: do not drink tap water until further notice",
    "Three people confirmed dead after landslide hit village",
    "Local school converted to evacuation centre, 200 sheltering",
    "Government announces emergency aid package for flood victims",
]

SEARCH_QUERIES = [
    "earthquake damage",
    "water needed urgently",
    "missing person flood",
    "evacuation shelter",
    "rescue volunteers",
]


def percentile(values: list[float], pct: int) -> float:
    sorted_vals = sorted(values)
    rank = max(0, int(math.ceil(len(sorted_vals) * pct / 100)) - 1)
    return sorted_vals[rank]


def bench_health(client: httpx.Client) -> list[float]:
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        r = client.get("/api/health")
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def bench_analyse(client: httpx.Client) -> list[float]:
    times = []
    for i in range(RUNS):
        text = ANALYSE_TEXTS[i % len(ANALYSE_TEXTS)]
        start = time.perf_counter()
        r = client.post("/api/analyse", json={"text": text})
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def bench_report_create(client: httpx.Client) -> tuple[list[float], list[str]]:
    times = []
    created_ids = []
    for i in range(RUNS):
        text = ANALYSE_TEXTS[i % len(ANALYSE_TEXTS)]
        payload = {
            "text": f"[bench] {text}",
            "predicted_label": "caution_and_advice",
            "confidence": 0.85,
            "model_version": "benchmark",
            "needs_review": False,
        }
        start = time.perf_counter()
        r = client.post("/api/reports", json=payload)
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
        created_ids.append(r.json()["message_id"])
    return times, created_ids


def bench_report_get(client: httpx.Client, ids: list[str]) -> list[float]:
    times = []
    for msg_id in ids[:RUNS]:
        start = time.perf_counter()
        r = client.get(f"/api/reports/{msg_id}")
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def bench_report_list(client: httpx.Client) -> list[float]:
    times = []
    boards = ["caution_and_advice", "infrastructure_and_utility_damage",
              "requests_or_urgent_needs", "sympathy_and_support"]
    for i in range(RUNS):
        board = boards[i % len(boards)]
        start = time.perf_counter()
        r = client.get("/api/reports", params={"board_label": board, "k": 10})
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def bench_search(client: httpx.Client) -> list[float]:
    times = []
    for i in range(RUNS):
        q = SEARCH_QUERIES[i % len(SEARCH_QUERIES)]
        start = time.perf_counter()
        r = client.get("/api/search", params={"q": q, "k": 10})
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def bench_patch(client: httpx.Client, ids: list[str]) -> list[float]:
    times = []
    labels = ["infrastructure_and_utility_damage", "requests_or_urgent_needs",
              "sympathy_and_support", "caution_and_advice"]
    for i, msg_id in enumerate(ids[:RUNS]):
        correction = labels[i % len(labels)]
        start = time.perf_counter()
        r = client.patch(f"/api/reports/{msg_id}", json={"user_correction": correction})
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        times.append(elapsed)
    return times


def summarise(name: str, times: list[float]) -> dict:
    return {
        "endpoint": name,
        "runs": len(times),
        "p50_ms": round(percentile(times, 50) * 1000, 1),
        "p95_ms": round(percentile(times, 95) * 1000, 1),
        "mean_ms": round(statistics.mean(times) * 1000, 1),
        "min_ms": round(min(times) * 1000, 1),
        "max_ms": round(max(times) * 1000, 1),
    }


def main() -> None:
    with httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=30.0) as client:
        print(f"Benchmarking {BASE_URL} ({RUNS} runs per endpoint)\n")

        # Warm up (first request loads model into cache)
        client.get("/api/health")
        client.post("/api/analyse", json={"text": "warm up"})
        client.get("/api/search", params={"q": "warm up", "k": 1})

        results = []

        print("GET  /api/health ...", end=" ", flush=True)
        results.append(summarise("GET /api/health", bench_health(client)))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("POST /api/analyse ...", end=" ", flush=True)
        results.append(summarise("POST /api/analyse", bench_analyse(client)))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("POST /api/reports ...", end=" ", flush=True)
        create_times, created_ids = bench_report_create(client)
        results.append(summarise("POST /api/reports", create_times))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("GET  /api/reports/:id ...", end=" ", flush=True)
        results.append(summarise("GET /api/reports/:id", bench_report_get(client, created_ids)))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("GET  /api/reports (list) ...", end=" ", flush=True)
        results.append(summarise("GET /api/reports", bench_report_list(client)))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("GET  /api/search ...", end=" ", flush=True)
        results.append(summarise("GET /api/search", bench_search(client)))
        print(f"p50={results[-1]['p50_ms']}ms")

        print("PATCH /api/reports/:id ...", end=" ", flush=True)
        results.append(summarise("PATCH /api/reports/:id", bench_patch(client, created_ids)))
        print(f"p50={results[-1]['p50_ms']}ms")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "endpoint_latency.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'Endpoint':<28} {'p50':>8} {'p95':>8} {'mean':>8} {'min':>8} {'max':>8}")
    print("-" * 76)
    for r in results:
        print(
            f"{r['endpoint']:<28} {r['p50_ms']:>7.1f}ms {r['p95_ms']:>7.1f}ms "
            f"{r['mean_ms']:>7.1f}ms {r['min_ms']:>7.1f}ms {r['max_ms']:>7.1f}ms"
        )

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
