#!/usr/bin/env python3
"""
Unit 9 capstone: run my five criteria (criteria.md, "Unit 9 capstone
criteria") three times each, and measure what one run costs.

    AI201_FAULTS=1 PORT=5050 python app.py          # terminal 1
    PORT=5050 python run_capstone.py --label before # terminal 2
    PORT=5050 python run_capstone.py --cost         # cost only

Each trial runs, in this order: criterion 1, criterion 2, criterion 5 (right
after 2, on purpose), criterion 3, criterion 4. Every trial uses fresh
creator_ids, so the rate limit from one trial can't leak into the next.

The verdicts are counted here against the targets in criteria.md, and the
real responses and run records are saved next to the counts.
"""

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import requests

import config
from scenarios import CLEARLY_AI, MY_WRITING

URL = f"http://{config.HOST}:{config.PORT}"
VALID = MY_WRITING + CLEARLY_AI
SHORT = "This is far too short to judge."


def send(path="/submit", body=None, fault=None, raw=None, content_type="application/json", method="POST"):
    headers = {"Content-Type": content_type}
    if fault:
        headers["X-Fault-Inject"] = fault
    start = time.perf_counter()
    if method == "GET":
        r = requests.get(URL + path, timeout=60)
    elif raw is not None:
        r = requests.post(URL + path, data=raw, headers=headers, timeout=60)
    else:
        r = requests.post(URL + path, data=json.dumps(body), headers=headers, timeout=60)
    elapsed = time.perf_counter() - start
    try:
        data = r.json()
    except ValueError:
        data = {"_not_json": r.text[:120]}
    return {"status": r.status_code, "elapsed_s": round(elapsed, 3),
            "request_id": r.headers.get("X-Request-Id"), "body": data}


def run_records():
    path = Path(config.RUN_LOG)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def records_for(request_id):
    return [r for r in run_records() if r.get("request_id") == request_id]


def c1(tag):
    rows = []
    texts = CLEARLY_AI[:5] + MY_WRITING[:5]
    for i, text in enumerate(texts):
        res = send(body={"text": text, "creator_id": f"c1_{tag}_{i}"}, fault="detector_error")
        recs = records_for(res["request_id"])
        b = res["body"]
        ok = (res["status"] == 200 and b.get("degraded") is True and b.get("guess") != "ai"
              and len(recs) == 1 and str(recs[0].get("error", "")).startswith("detector_error"))
        rows.append({**res, "record": recs[0] if recs else None, "pass": ok})
    return rows


def c2(tag):
    rows = []
    for i in range(5):
        res = send(body={"text": VALID[i], "creator_id": f"c2_{tag}_{i}"}, fault="detector_slow")
        ok = res["status"] == 200 and res["body"].get("degraded") is True and res["elapsed_s"] < 9.0
        rows.append({**res, "pass": ok})
    return rows


def c5(tag):
    rows = []
    for i in range(10):
        res = send(body={"text": VALID[i % len(VALID)], "creator_id": f"c5_{tag}_{i}"})
        rows.append({**res, "fast": res["elapsed_s"] < 1.0, "degraded": res["body"].get("degraded") is True})
    return rows


def c3(tag):
    creator = f"c3_{tag}"
    refused = [send(body={"text": SHORT, "creator_id": creator}) for _ in range(6)]
    valid = [send(body={"text": VALID[i], "creator_id": creator}) for i in range(5)]
    return {"refused": refused, "valid": valid}


def c4(tag):
    big = json.dumps({"text": "word " * 60000, "creator_id": f"c4_{tag}_big"})
    plan = []
    for i in range(5):
        plan.append(("valid same creator", dict(body={"text": VALID[i], "creator_id": f"c4_{tag}_same"})))
    for i in range(3):
        plan.append(("valid other creator", dict(body={"text": VALID[5 + i], "creator_id": f"c4_{tag}_o{i}"})))
    plan.append(("sixth from same creator", dict(body={"text": VALID[8], "creator_id": f"c4_{tag}_same"})))
    for i in range(3):
        plan.append(("detector error", dict(body={"text": VALID[i], "creator_id": f"c4_{tag}_e{i}"}, fault="detector_error")))
    for i in range(2):
        plan.append(("detector stall", dict(body={"text": VALID[3 + i], "creator_id": f"c4_{tag}_s{i}"}, fault="detector_slow")))
    plan.append(("too short", dict(body={"text": SHORT, "creator_id": f"c4_{tag}_short"})))
    plan.append(("no creator_id", dict(body={"text": VALID[0]})))
    plan.append(("not JSON", dict(raw="this is not json", content_type="application/json")))
    plan.append(("oversized 300 KB", dict(raw=big)))
    plan.append(("oversized 300 KB", dict(raw=big)))
    plan.append(("unknown route", dict(path="/does-not-exist", method="GET")))
    rows = []
    for kind, kw in plan:
        res = send(**kw)
        rows.append({"kind": kind, **res})
    time.sleep(0.5)
    for row in rows:
        recs = records_for(row["request_id"]) if row["request_id"] else []
        row["records"] = len(recs)
        row["pass"] = (len(recs) == 1 and recs[0].get("status") == row["status"]
                       and recs[0].get("duration_ms") is not None)
        row["record"] = recs[0] if recs else None
    return rows


def one_trial(trial, label):
    tag = f"{label}{trial}_{dt.datetime.now().strftime('%H%M%S')}"
    out = {"trial": trial, "tag": tag}
    out["c1"] = c1(tag)
    out["c2"] = c2(tag)
    out["c5"] = c5(tag)
    out["c3"] = c3(tag)
    out["c4"] = c4(tag)
    return out


def summarize(t):
    c3_ok = sum(r["status"] == 200 for r in t["c3"]["valid"])
    c3_429 = sum(r["status"] == 429 for r in t["c3"]["valid"])
    c3_ref = sum(r["status"] == 400 for r in t["c3"]["refused"])
    return {
        "c1": sum(r["pass"] for r in t["c1"]),
        "c2": sum(r["pass"] for r in t["c2"]),
        "c2_times": [r["elapsed_s"] for r in t["c2"]],
        "c3": c3_ok, "c3_429": c3_429, "c3_refused400": c3_ref,
        "c4": sum(r["pass"] for r in t["c4"]),
        "c5_fast": sum(r["fast"] for r in t["c5"]),
        "c5_degraded": sum(r["degraded"] for r in t["c5"]),
        "c5_times": [r["elapsed_s"] for r in t["c5"]],
    }


def verdicts(sums):
    return {
        "1": all(s["c1"] == 10 for s in sums),
        "2": all(s["c2"] == 5 for s in sums),
        "3": all(s["c3"] == 5 and s["c3_refused400"] == 6 for s in sums),
        "4": all(s["c4"] == 20 for s in sums),
        "5": all(s["c5_fast"] >= 9 and s["c5_degraded"] == 0 for s in sums),
    }


def cost():
    ids = []
    send(body={"text": VALID[0], "creator_id": "cost_warm"})
    for i in range(10):
        res = send(body={"text": VALID[i], "creator_id": f"cost_{dt.datetime.now().strftime('%H%M%S')}_{i}"})
        ids.append(res["request_id"])
    time.sleep(0.3)
    recs = [records_for(i)[0] for i in ids]
    dur = [r["duration_ms"] for r in recs]
    cpu = [r["cpu_ms"] for r in recs]
    model = [r["stages_ms"]["model"] for r in recs]
    return {"runs": 10, "avg_duration_ms": round(sum(dur) / 10, 1), "avg_cpu_ms": round(sum(cpu) / 10, 1),
            "avg_model_ms": round(sum(model) / 10, 1), "duration_ms": dur, "cpu_ms": cpu,
            "records": recs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--cost", action="store_true")
    args = ap.parse_args()
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    Path("results").mkdir(exist_ok=True)

    if args.cost:
        c = cost()
        out = Path("results") / f"capstone_cost_{stamp}.json"
        out.write_text(json.dumps(c, indent=2))
        print(json.dumps({k: v for k, v in c.items() if k != "records"}, indent=2))
        print(f"Wrote {out}")
        return

    trials = []
    for n in (1, 2, 3):
        t = one_trial(n, args.label)
        s = summarize(t)
        print(f"trial {n}: {s}")
        trials.append((t, s))
    sums = [s for _, s in trials]
    v = verdicts(sums)
    lines = [f"# Capstone run ({args.label})", "",
             "- Produced by: `run_capstone.py::main`",
             f"- Service: `app.py::submit` with AI201_FAULTS=1, {stamp}", "",
             "| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |", "|---|---|---|---|---|---|"]
    lines.append("| 1. Broken detector never accuses | 10 of 10 | " + " | ".join(f"{s['c1']}/10" for s in sums) + f" | {'MET' if v['1'] else 'MISSED'} |")
    lines.append("| 2. Stalled detector answers under 9.0 s | 5 of 5 | " + " | ".join(f"{s['c2']}/5" for s in sums) + f" | {'MET' if v['2'] else 'MISSED'} |")
    lines.append("| 3. Refused requests don't spend quota | 5 of 5 valid accepted | " + " | ".join(f"{s['c3']}/5 ({s['c3_429']} x 429)" for s in sums) + f" | {'MET' if v['3'] else 'MISSED'} |")
    lines.append("| 4. Every request leaves one run record | 20 of 20 | " + " | ".join(f"{s['c4']}/20" for s in sums) + f" | {'MET' if v['4'] else 'MISSED'} |")
    lines.append("| 5. Normal path fast right after a stall | 9+ of 10 under 1.0 s, 0 degraded | " + " | ".join(f"{s['c5_fast']}/10 fast, {s['c5_degraded']} degraded" for s in sums) + f" | {'MET' if v['5'] else 'MISSED'} |")
    lines += ["", "## Timings", ""]
    for i, s in enumerate(sums, 1):
        lines.append(f"- Trial {i}: criterion 2 times {s['c2_times']}; criterion 5 times {s['c5_times']}")
    lines += ["", "## Raw results", "", "Full JSON for all three trials: the `.json` file with the same name.", ""]
    out = Path("results") / f"capstone_{stamp}_{args.label}"
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    out.with_suffix(".json").write_text(json.dumps([t for t, _ in trials], indent=2, default=str))
    print("\n".join(lines[6:12]))
    print(f"Wrote {out}.md and .json")


if __name__ == "__main__":
    main()
