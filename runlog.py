"""
Unit 9 capstone: the structured run log.

One JSON record per request in logs/runs.jsonl, written after the response is
built, so failures leave a record too. Fields:

  timestamp     when the request finished (UTC)
  request_id    also returned to the caller in the X-Request-Id header
  method, route, status
  duration_ms   wall time inside the service, request in to response out
  cpu_ms        CPU time the service process used during the request
  input         for POST bodies: chars, words, a short hash, creator_id
                (never the text itself, so the log can't leak someone's writing)
  output        guess, confidence, content_id when a decision was made
  stages_ms     model / style / phrase timings for /submit
  degraded      true when signal one was unavailable
  error         what failed, when something did
  fault         the injected fault, when testing asked for one

GET /log and GET /health are not recorded: they're read-only and would bury
the requests that matter.
"""

import datetime as dt
import hashlib
import json
import time
import uuid
from pathlib import Path

from flask import g, request

import config

SKIP = {("GET", "/log"), ("GET", "/health")}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def start():
    g.request_id = uuid.uuid4().hex[:12]
    g.t0 = time.perf_counter()
    g.cpu0 = time.process_time()
    g.run = {}


def _input_summary():
    if request.method != "POST":
        return None
    try:
        payload = request.get_json(silent=True)
    except Exception:  # an oversized body raises here; the 413 is already decided
        return {"unreadable": True, "content_length": request.content_length}
    if not isinstance(payload, dict):
        return {"json_object": False, "content_length": request.content_length}
    text = payload.get("text")
    summary = {"creator_id": payload.get("creator_id") if isinstance(payload.get("creator_id"), str) else None}
    if isinstance(text, str):
        summary.update(chars=len(text), words=len(text.split()),
                       sha8=hashlib.sha256(text.encode()).hexdigest()[:8])
    elif "content_id" in payload:
        summary["content_id"] = payload.get("content_id")
    return summary


def finish(response):
    if (request.method, request.path) in SKIP:
        return response
    run = getattr(g, "run", {}) or {}
    record = {
        "timestamp": _now(),
        "request_id": getattr(g, "request_id", None),
        "method": request.method,
        "route": request.path,
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - getattr(g, "t0", time.perf_counter())) * 1000, 1),
        "cpu_ms": round((time.process_time() - getattr(g, "cpu0", time.process_time())) * 1000, 1),
        "input": _input_summary(),
        "output": ({k: run[k] for k in ("guess", "confidence", "content_id") if k in run} or None),
        "stages_ms": run.get("stages_ms"),
        "degraded": run.get("degraded"),
        "error": run.get("error") or (response.get_json(silent=True) or {}).get("error") if response.is_json else run.get("error"),
        "fault": run.get("fault"),
    }
    path = Path(config.RUN_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    response.headers["X-Request-Id"] = record["request_id"] or ""
    return response
