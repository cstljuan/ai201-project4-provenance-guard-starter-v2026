#!/usr/bin/env python3
"""
Turn a run_eval.py results file into the numbers my five criteria name.

    python summarize_eval.py results/run_<date>_before.md

run_eval.py leaves the Verdict column blank because it can't know my targets.
This reads the JSON it pasted per trial and counts, per criterion:

  1. own writing labelled "ai"           (target: at most 1 of 10)
  2. mean AI confidence - mean human     (target: at least 0.30)
  3. count of each guess in 15 inputs    (target: each at least 2)
  5. bad inputs answered 400, never 500, never a guess (target: 8 of 8)

Criterion 4 (appeals) comes from run_appeals.py.
"""

import json
import re
import sys


def trials_by_scenario(path):
    text = open(path, encoding="utf-8").read()
    out = {}
    for block in re.split(r"\n### ", text)[1:]:
        name = block.split("\n", 1)[0].strip()
        out[name] = [json.loads(m) for m in re.findall(r"```json\n(.*?)\n```", block, re.S)]
    return out


def main(path):
    s = trials_by_scenario(path)
    for t in range(3):
        own = s["my own writing"][t]
        ai = s["spread ai"][t]
        hu = s["spread human"][t]
        cov = s["label coverage"][t]
        bad = s["bad input"][t]
        c1 = sum(r["guess"] == "ai" for r in own)
        spread = (sum(r["confidence"] for r in ai) / len(ai)) - (sum(r["confidence"] for r in hu) / len(hu))
        counts = {g: sum(r["guess"] == g for r in cov) for g in ("human", "unsure", "ai")}
        c5 = sum(r["status"] == 400 and r["guess"] is None for r in bad)
        fivehundreds = sum((r["status"] or 0) >= 500 for r in bad)
        print(f"trial {t + 1}: c1 ai={c1}/10 | c2 spread={spread:.3f} "
              f"(ai {sum(r['confidence'] for r in ai) / 5:.3f}, human {sum(r['confidence'] for r in hu) / 5:.3f}) | "
              f"c3 {counts} | c5 {c5}/8 refused, {fivehundreds} 5xx")
        print("    own-writing scores:", [round(r["confidence"], 3) for r in own])


if __name__ == "__main__":
    main(sys.argv[1])
