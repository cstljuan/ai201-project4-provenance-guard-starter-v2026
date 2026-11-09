#!/usr/bin/env python3
"""
Capstone stretch: latency breakdown and load observation.

    AI201_FAULTS=1 PORT=5050 python app.py
    PORT=5050 python load_test.py

1. Normal rate: 1 request per second for 30 seconds (30 requests).
2. Ten times that: 10 requests per second for 30 seconds (300 requests),
   sent from a thread pool so they overlap like real traffic would.
3. A stall burst: 24 requests at once with the detector forced to stall,
   to see the 16-call in-flight cap work.

Every request uses its own creator_id, so the per-creator rate limit doesn't
decide the result; what's being measured is the service itself. Latency is
timed at the client; the per-stage breakdown comes from logs/runs.jsonl.
"""

import concurrent.futures as cf
import datetime as dt
import json
import statistics
import time
from pathlib import Path

import requests

import config
from scenarios import CLEARLY_AI, MY_WRITING

URL = f"http://{config.HOST}:{config.PORT}/submit"
TEXTS = MY_WRITING + CLEARLY_AI


def one(i, tag, fault=None):
    headers = {"Content-Type": "application/json"}
    if fault:
        headers["X-Fault-Inject"] = fault
    body = {"text": TEXTS[i % len(TEXTS)], "creator_id": f"load_{tag}_{i}"}
    t = time.perf_counter()
    try:
        r = requests.post(URL, data=json.dumps(body), headers=headers, timeout=60)
        data = r.json()
        return {"status": r.status_code, "s": time.perf_counter() - t,
                "degraded": data.get("degraded"), "request_id": r.headers.get("X-Request-Id")}
    except Exception as exc:
        return {"status": None, "s": time.perf_counter() - t, "error": f"{type(exc).__name__}"}


def paced(rate, seconds, tag):
    results, futures = [], []
    with cf.ThreadPoolExecutor(max_workers=64) as pool:
        start = time.perf_counter()
        for i in range(rate * seconds):
            target = start + i / rate
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            futures.append(pool.submit(one, i, tag))
        results = [f.result() for f in futures]
    return results


def burst(n, tag, fault):
    with cf.ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(lambda i: one(i, tag, fault), range(n)))


def summary(rows):
    ok = [r for r in rows if r["status"] == 200]
    secs = sorted(r["s"] for r in ok)
    pct = lambda p: round(secs[min(len(secs) - 1, int(p * len(secs)))] * 1000, 1) if secs else None  # noqa: E731
    statuses = {}
    for r in rows:
        statuses[str(r["status"])] = statuses.get(str(r["status"]), 0) + 1
    return {"requests": len(rows), "statuses": statuses,
            "degraded": sum(bool(r.get("degraded")) for r in ok),
            "p50_ms": pct(0.50), "p95_ms": pct(0.95), "max_ms": pct(1.0)}


def stage_breakdown(request_ids):
    recs = {}
    for line in Path(config.RUN_LOG).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r.get("request_id")] = r
    rows = [recs[i] for i in request_ids if i in recs and recs[i].get("stages_ms") and not recs[i].get("degraded")]
    def stat(vals):
        vals = sorted(vals)
        return {"mean": round(statistics.mean(vals), 1), "p50": round(vals[len(vals) // 2], 1),
                "p95": round(vals[min(len(vals) - 1, int(0.95 * len(vals)))], 1)}
    model = [r["stages_ms"]["model"] for r in rows]
    style = [r["stages_ms"]["style"] for r in rows]
    phrase = [r["stages_ms"]["phrase"] for r in rows]
    total = [r["duration_ms"] for r in rows]
    other = [t - m - s - p for t, m, s, p in zip(total, model, style, phrase)]
    return {"runs": len(rows), "model": stat(model), "style": stat(style), "phrase": stat(phrase),
            "everything_else": stat(other), "total": stat(total)}


def main():
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    tag = dt.datetime.now().strftime("%H%M%S")
    normal = paced(1, 30, f"n{tag}")
    time.sleep(2)
    heavy = paced(10, 30, f"h{tag}")
    time.sleep(2)
    stalls = burst(24, f"s{tag}", "detector_slow")
    time.sleep(1)
    out = {
        "normal_1_per_s": summary(normal),
        "ten_x_10_per_s": summary(heavy),
        "stall_burst_24": summary(stalls),
        "stall_burst_fast_answers": sum(1 for r in stalls if r["status"] == 200 and r["s"] < 1.0),
        "breakdown_normal": stage_breakdown([r.get("request_id") for r in normal]),
        "breakdown_ten_x": stage_breakdown([r.get("request_id") for r in heavy]),
    }
    path = Path("results") / f"capstone_load_{stamp}.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
