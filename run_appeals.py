#!/usr/bin/env python3
"""
Criterion 4, three trials: every appeal changes status and is recorded.

    python app.py                               # in one terminal
    python run_appeals.py --label before        # in another

run_eval.py only sends submissions, and an appeal needs a real content_id from
a submission first, so this criterion gets its own small runner. Each trial:

  1. submits 5 texts (each under its own creator_id, so the rate limit never
     decides the result),
  2. appeals each content_id with a reason,
  3. checks the appeal returned 200, GET /content/<id> says under_review, and
     GET /log holds exactly one "appeal" entry for that id with the reason,
  4. sends 3 appeals with made-up content_ids and checks each returns 404 and
     adds nothing with that id to the log.

Writes results/appeal_check_<date>_<label>.md with the raw responses.
"""

import argparse
import datetime as dt
import json
import uuid
from pathlib import Path

import requests

import config

URL = f"http://{config.HOST}:{config.PORT}"

TEXTS = [
    "I went to the market this morning and the line for bread was out the door again, so I bought tortillas instead and nobody at home noticed.",
    "My laptop fan has started making a clicking noise whenever I open more than three tabs, which is a problem because I always have about thirty open.",
    "We tried a new route to school today and it was longer but there was a dog on every porch, so honestly it was worth the extra ten minutes.",
    "The library closes at nine on weekdays but the study rooms upstairs lock at eight, which nobody tells you until you are already packed up and confused.",
    "I finally fixed the bug that was breaking my app. It was a missing comma in a config file, and I had been staring at the wrong file for two hours.",
]


def log_entries():
    return requests.get(f"{URL}/log", params={"limit": 5000}, timeout=30).json()["entries"]


def one_trial(trial, tag):
    rows = []
    for i, text in enumerate(TEXTS, 1):
        creator = f"appeal_{tag}_t{trial}_{i}"
        sub = requests.post(f"{URL}/submit", json={"text": text, "creator_id": creator}, timeout=120)
        cid = sub.json().get("content_id")
        reason = f"I wrote this myself (trial {trial}, item {i})."
        ap = requests.post(f"{URL}/appeal", json={"content_id": cid, "reasoning": reason}, timeout=30)
        content = requests.get(f"{URL}/content/{cid}", timeout=30).json()
        appeals = [e for e in log_entries() if e.get("content_id") == cid and e.get("event") == "appeal"]
        ok = (
            ap.status_code == 200
            and content.get("status") == "under_review"
            and len(appeals) == 1
            and appeals[0].get("reasoning") == reason
        )
        rows.append({"kind": "real", "content_id": cid, "appeal_status": ap.status_code,
                     "appeal_response": ap.json(), "content_status": content.get("status"),
                     "appeal_log_entries": len(appeals), "pass": ok})
    for j in range(3):
        fake = uuid.uuid4().hex[:12]
        ap = requests.post(f"{URL}/appeal", json={"content_id": fake, "reasoning": "fake id"}, timeout=30)
        in_log = [e for e in log_entries() if e.get("content_id") == fake]
        rows.append({"kind": "fake", "content_id": fake, "appeal_status": ap.status_code,
                     "appeal_response": ap.json(), "log_entries_with_id": len(in_log),
                     "pass": ap.status_code == 404 and not in_log})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    tag = f"{args.label}_{dt.datetime.now().strftime('%H%M%S')}"

    trials = [one_trial(t, tag) for t in (1, 2, 3)]
    lines = [f"# Appeal check, criterion 4 ({args.label})", "",
             "- Produced by: `run_appeals.py::main`",
             "- Target: 5 of 5 real appeals pass, 3 of 3 fake ids return 404 and leave no trace", ""]
    lines += ["| Trial | Real appeals passing | Fake ids passing |", "|---|---|---|"]
    for t, rows in enumerate(trials, 1):
        real = [r for r in rows if r["kind"] == "real"]
        fake = [r for r in rows if r["kind"] == "fake"]
        lines.append(f"| {t} | {sum(r['pass'] for r in real)}/5 | {sum(r['pass'] for r in fake)}/3 |")
        print(f"trial {t}: real {sum(r['pass'] for r in real)}/5, fake {sum(r['pass'] for r in fake)}/3")
    lines += ["", "## Raw results, trial 1", "", "```json", json.dumps(trials[0], indent=2), "```", ""]
    out = Path("results") / f"appeal_check_{stamp}_{args.label}.md"
    out.write_text("\n".join(lines))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
