#!/usr/bin/env python3
"""
Provenance Guard — the web service.

    python app.py

Then, in another terminal:

    curl -X POST http://127.0.0.1:5000/ping \
      -H "Content-Type: application/json" \
      -d '{"message": "hello"}'

That's the example route. It works right now, before you've written anything.
**Leave it alone** — it's your control. When something breaks later, check that
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself.

Routes:

    POST /ping        the worked example. Already works. Don't edit it
    POST /submit      ← YOU BUILD THIS (Milestone 3, 4, 5)
    POST /appeal      ← YOU BUILD THIS (Milestone 5)
    GET  /content/<id> one item's current status (stretch)
    POST /verify/start, /verify/complete   the verified-human path (stretch)
    GET  /log         the audit log. Already works
    GET  /health      is the service up, and is the model loaded
"""

import uuid

from flask import Flask, jsonify, request

import audit
import config
import detector
import phrases
import scoring
import stylometry

app = Flask(__name__)


# ── Rate limiting — UNIT 8 ────────────────────────────────────────────────────
# Off until you turn it on. In unit 8, Milestone 1:
#
#   1. Set RATE_LIMITING_ENABLED = True in config.py (or AI201_RATE_LIMITS=1)
#   2. Choose your numbers there
#   3. Uncomment the @limiter.limit(...) line on /submit below
#
# The order doesn't matter. While limiting is off, that decorator is a no-op
# that quietly does nothing, so uncommenting it early costs you nothing — but
# it also means no 429 until you've done step 1.
#
# The storage backend is preconfigured, which stops Flask-Limiter printing a
# warning on every start. In-memory is right for one laptop and wrong for
# anything real — a restart forgets every count.

class _LimiterOff:
    """
    Stands in for the real limiter while rate limiting is off.

    It makes @limiter.limit(...) a decorator that returns the route
    untouched, so uncommenting the line before you flip the setting is
    harmless instead of a crash on startup.
    """

    def limit(self, *args, **kwargs):
        return lambda view: view


limiter = _LimiterOff()
if config.RATE_LIMITING_ENABLED:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def rate_limit_key():
        """
        Who a request counts against.

        Falling back to the caller's address is the easy version. Unit 8's
        stretch asks about per-creator limits instead — and the difference
        matters: one script can look like a thousand callers, and one household
        can look like one.
        """
        payload = request.get_json(silent=True)
        # A body that parses as JSON but isn't an object — a bare list or
        # string — has no .get. Without this guard the key function raises
        # BEFORE the route runs, and a malformed request becomes a 500 that
        # looks like your handler crashed when your handler never ran.
        if not isinstance(payload, dict):
            return get_remote_address()
        creator = payload.get("creator_id")
        return creator if isinstance(creator, str) and creator.strip() else get_remote_address()

    limiter = Limiter(
        key_func=rate_limit_key,
        app=app,
        storage_uri=config.RATE_LIMIT_STORAGE,
        default_limits=[],
    )

    @app.errorhandler(429)
    def rate_limited(exc):
        """
        A rejected request still leaves a trace.

        ⚠️ An attack that shows up only as an absence is one you'll never find.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="rate_limited",
            limit=str(exc.description),
        )
        return jsonify({
            "error": "rate_limited",
            "message": "Too many submissions. Try again shortly.",
            "limit": str(exc.description),
        }), 429


# ── The worked example. Already works. Don't edit. ────────────────────────────

@app.post("/ping")
def ping():
    """
    Everything a route needs, in six lines.

    JSON arrives as a dict. You pull things out of it. You return a dict and
    the framework turns it into a response. That's the whole idea.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "you_sent": payload.get("message"),
        "service": "provenance-guard",
    })


@app.get("/health")
def health():
    """Is the service up, and has the model been downloaded yet?"""
    import detector

    loaded = detector._model is not None
    return jsonify({
        "ok": True,
        "detector_model": config.DETECTOR_MODEL,
        "detector_loaded": loaded,
        "rate_limiting": config.RATE_LIMITING_ENABLED,
        "log_entries": len(audit.read_entries()),
    })


# ── YOU BUILD THIS ────────────────────────────────────────────────────────────

@app.post("/submit")
# @limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute;{config.RATE_LIMIT_PER_DAY}/day")
def submit():
    """
    Take a piece of text, decide about it, log the decision, answer.
    ← TODO — Milestones 3, 4 and 5

    Expects JSON:
        {"text": "...", "creator_id": "..."}

    Should return JSON with, at minimum:
        {"content_id": "...", "guess": "...", "confidence": 0.0, "label": "...",
         "model_score": 0.0, "style_score": 0.0}

    ⚠️ **Both signal scores go in the response, not just the log.** Unit 8's
    `run_attacks.py` and `run_eval.py` read `model_score` and `style_score`
    straight off this response and put them in your reports. Leave them out and
    every row of next unit's evidence says `null` — which is exactly the
    diagnostic you need to name a stage and a mechanism. You do not want to
    find that out after running the attack set.

    ─────────────────────────────────────────────────────────────────────────
    Build it in three passes. Do not skip ahead — the ordering is how you tell
    a broken route from a broken signal.

    **Milestone 3 — the route answers.**
      1. Return a hardcoded response. Confirm `curl` gets it back before you
         add any logic at all.
      2. Then pull `text` and `creator_id` out of the payload.
      3. Then call ONE signal — `detector.model_signal(text)` — and put the
         real number in. Leave confidence and label as placeholders.
      4. Log every submission with `audit.log_decision(...)`. The content_id
         matters: `/appeal` needs it, and a student who skips it rebuilds this
         whole flow later.

    **Milestone 4 — the second signal and the score.**
      5. Add `stylometry.style_signal(text)`.
      6. Combine them with `scoring.combine_signals(...)`.
      7. Log BOTH signal scores alongside the combined one, and put them in the
         response too. Next unit you can't diagnose anything without them.

    **Milestone 5 — the label.**
      8. `scoring.score_to_label(...)` and put the real label in the response.

    ─────────────────────────────────────────────────────────────────────────
    Worth deciding early, because unit 8's attack set will decide it for you:
    what should this do when `text` is missing, empty, or enormous? A crash on
    a malformed input is one of the most common real failures there is.
    """
    payload = request.get_json(silent=True)
    problem = _validate_submission(payload)
    if problem:
        creator = payload.get("creator_id") if isinstance(payload, dict) else None
        audit.log_rejection(
            creator_id=creator if isinstance(creator, str) else "unknown",
            reason=problem["error"],
        )
        return jsonify(problem), 400

    text = payload["text"].strip()
    creator_id = payload["creator_id"].strip()
    content_id = uuid.uuid4().hex[:12]

    try:
        model_score = detector.model_signal(text)
    except detector.DetectorUnavailable as exc:
        return jsonify({"error": "detector_unavailable", "message": str(exc)}), 503
    style_score = stylometry.style_signal(text)
    phrase_score = phrases.phrase_signal(text)
    confidence = scoring.combine_signals(model_score, style_score, phrase_score)

    guess, label = scoring.score_to_label(confidence)
    creator_verified = _is_verified(creator_id)
    if creator_verified:
        label = f"{label} {VERIFIED_NOTE}"

    audit.log_decision(
        content_id=content_id,
        creator_id=creator_id,
        guess=guess,
        model_score=model_score,
        style_score=style_score,
        combined_score=confidence,
        label=label,
        phrase_score=phrase_score,
        creator_verified=creator_verified,
    )
    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "guess": guess,
        "confidence": confidence,
        "label": label,
        "model_score": model_score,
        "style_score": style_score,
        "phrase_score": phrase_score,
        "creator_verified": creator_verified,
        "status": "decided",
    })


def _validate_submission(payload) -> dict | None:
    """
    Refuse anything that can't honestly be judged. Returns an error body, or
    None if the submission is fine. Criterion 5 in criteria.md is the contract.
    """
    if not isinstance(payload, dict):
        return {"error": "invalid_json", "message": "Send a JSON object with text and creator_id."}

    creator_id = payload.get("creator_id")
    if not isinstance(creator_id, str) or not creator_id.strip():
        return {"error": "missing_creator_id", "message": "creator_id is required."}

    text = payload.get("text")
    if "text" not in payload or text is None:
        return {"error": "missing_text", "message": "text is required."}
    if not isinstance(text, str):
        return {"error": "text_not_string", "message": "text must be a string."}
    if not text.strip():
        return {"error": "empty_text", "message": "text is empty."}

    word_count = len(text.split())
    if word_count < config.MIN_WORDS:
        return {
            "error": "text_too_short",
            "message": f"We need at least {config.MIN_WORDS} words to say anything "
                       f"useful about a piece. This one has {word_count}.",
        }
    if word_count > config.MAX_WORDS:
        return {
            "error": "text_too_long",
            "message": f"Submissions are limited to {config.MAX_WORDS} words. "
                       f"This one has {word_count}.",
        }
    return None


@app.post("/appeal")
def appeal():
    """
    A writer says you got it wrong. ← TODO — Milestone 5

    Expects JSON:
        {"content_id": "...", "reasoning": "..."}

    Should:
      1. Check the content_id actually exists — `audit.entries_for(id)` tells
         you. A typo here fails silently and looks like a broken endpoint,
         which is the single most common way this milestone eats an hour.
      2. Record the appeal with `audit.log_appeal(...)`, which moves the item
         to `under_review`.
      3. Confirm to the writer. No automatic re-checking needed.

    This is the smallest endpoint in the project and the one that matters most
    to the person on the other end. It's the only thing standing between a
    wrong accusation and nothing at all.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_json",
                        "message": "Send a JSON object with content_id and reasoning."}), 400

    content_id = payload.get("content_id")
    reasoning = payload.get("reasoning")
    if not isinstance(content_id, str) or not content_id.strip():
        return jsonify({"error": "missing_content_id", "message": "content_id is required."}), 400
    if not isinstance(reasoning, str) or not reasoning.strip():
        return jsonify({"error": "missing_reasoning",
                        "message": "Tell us why you think the label is wrong."}), 400

    decision = _latest_decision(content_id.strip())
    if decision is None:
        return jsonify({"error": "not_found",
                        "message": f"No submission with content_id '{content_id}'."}), 404

    audit.log_appeal(
        content_id=decision["content_id"],
        creator_id=decision["creator_id"],
        reasoning=reasoning.strip(),
    )
    return jsonify({
        "content_id": decision["content_id"],
        "status": "under_review",
        "message": "Thanks. Your appeal is recorded and this piece is now marked "
                   "as under review. The original label stays on file, and a "
                   "person will look at it with your reasoning.",
        "original_guess": decision.get("guess"),
        "original_label": decision.get("label"),
    })


@app.get("/content/<content_id>")
def content(content_id):
    """
    One item's current state (stretch feature): the latest decision, the
    current status, and every appeal on record. Read from the audit log, so it
    can't disagree with it.
    """
    entries = audit.entries_for(content_id)
    decision = _latest_decision(content_id)
    if decision is None:
        return jsonify({"error": "not_found",
                        "message": f"No submission with content_id '{content_id}'."}), 404

    appeals = [
        {"timestamp": e["timestamp"], "reasoning": e.get("reasoning")}
        for e in entries if e.get("event") == "appeal"
    ]
    return jsonify({
        "content_id": content_id,
        "creator_id": decision["creator_id"],
        "status": entries[-1].get("status", "decided"),
        "guess": decision.get("guess"),
        "confidence": decision.get("combined_score"),
        "label": decision.get("label"),
        "model_score": decision.get("model_score"),
        "style_score": decision.get("style_score"),
        "phrase_score": decision.get("phrase_score"),
        "creator_verified": decision.get("creator_verified", False),
        "submitted_at": decision["timestamp"],
        "appeals": appeals,
    })


def _latest_decision(content_id: str) -> dict | None:
    """The decision entry for a content_id, or None if it was never decided."""
    decisions = [e for e in audit.entries_for(content_id) if "event" not in e]
    return decisions[-1] if decisions else None


# ── Verified-human path (stretch) ────────────────────────────────────────────
#
# A writer earns a credential by writing a short piece to a prompt they only
# see once they ask, inside a time limit. That's an extra step a copy-paste
# from an existing AI essay can't take, and the piece still has to clear the
# detector. Every step is an audit-log event, so the credential is traceable.

VERIFY_PROMPTS = [
    "Describe the room you're sitting in right now, and one thing in it that has a story.",
    "Write about a meal you remember, and who you ate it with.",
    "Tell us about the last time you got lost, or almost did.",
    "Describe a sound from your neighborhood that you would miss if it stopped.",
    "Write about something you changed your mind about, and what did it.",
]
VERIFY_MIN_WORDS = 60
VERIFY_TIME_LIMIT_SECONDS = 15 * 60
VERIFIED_NOTE = "This writer has completed our verified-writer check."


def _is_verified(creator_id: str) -> bool:
    return any(
        e.get("event") == "verified" and e.get("creator_id") == creator_id
        for e in audit.read_entries()
    )


@app.post("/verify/start")
def verify_start():
    """Step one: ask for a challenge. Returns a prompt and a challenge_id."""
    payload = request.get_json(silent=True)
    creator_id = payload.get("creator_id") if isinstance(payload, dict) else None
    if not isinstance(creator_id, str) or not creator_id.strip():
        return jsonify({"error": "missing_creator_id", "message": "creator_id is required."}), 400
    creator_id = creator_id.strip()

    if _is_verified(creator_id):
        return jsonify({"creator_id": creator_id, "verified": True,
                        "message": "You're already verified."})

    challenge_id = uuid.uuid4().hex[:12]
    prompt = VERIFY_PROMPTS[int(challenge_id, 16) % len(VERIFY_PROMPTS)]
    audit.log_event("verify_start", creator_id, "challenge_open",
                    challenge_id=challenge_id, prompt=prompt)
    return jsonify({
        "challenge_id": challenge_id,
        "prompt": prompt,
        "min_words": VERIFY_MIN_WORDS,
        "time_limit_seconds": VERIFY_TIME_LIMIT_SECONDS,
        "message": "Write a response to this prompt in your own words and send it "
                   "to /verify/complete before the time runs out.",
    })


@app.post("/verify/complete")
def verify_complete():
    """Step two: answer the prompt. Passing earns the verified_human credential."""
    from datetime import datetime, timezone

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_json",
                        "message": "Send a JSON object with challenge_id and text."}), 400
    challenge_id, text = payload.get("challenge_id"), payload.get("text")
    if not isinstance(challenge_id, str) or not isinstance(text, str) or not text.strip():
        return jsonify({"error": "missing_fields",
                        "message": "challenge_id and text are required."}), 400

    events = [e for e in audit.read_entries() if e.get("challenge_id") == challenge_id]
    start = next((e for e in events if e.get("event") == "verify_start"), None)
    if start is None:
        return jsonify({"error": "not_found", "message": "No such challenge."}), 404
    if any(e.get("event") in ("verified", "verify_failed") for e in events):
        return jsonify({"error": "challenge_used",
                        "message": "This challenge was already answered. Start a new one."}), 409

    creator_id = start["creator_id"]
    started = datetime.fromisoformat(start["timestamp"])
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    def fail(reason, message, **scores):
        audit.log_event("verify_failed", creator_id, "not_verified",
                        challenge_id=challenge_id, reason=reason, **scores)
        return jsonify({"verified": False, "reason": reason, "message": message}), 200

    if elapsed > VERIFY_TIME_LIMIT_SECONDS:
        return fail("expired", "The time limit passed. You can start a new challenge.")
    if len(text.split()) < VERIFY_MIN_WORDS:
        return fail("too_short", f"Please write at least {VERIFY_MIN_WORDS} words.")

    model_score = detector.model_signal(text)
    style_score = stylometry.style_signal(text)
    phrase_score = phrases.phrase_signal(text)
    confidence = scoring.combine_signals(model_score, style_score, phrase_score)
    guess, _ = scoring.score_to_label(confidence)
    scores = {"model_score": model_score, "style_score": style_score,
              "phrase_score": phrase_score, "combined_score": confidence}
    if guess == "ai":
        return fail("scored_as_ai",
                    "We couldn't verify this one. You can try again with a new prompt, "
                    "and nothing about your existing work changes.", **scores)

    credential_id = f"vh_{uuid.uuid4().hex[:10]}"
    audit.log_event("verified", creator_id, "verified_human",
                    challenge_id=challenge_id, credential_id=credential_id, **scores)
    return jsonify({
        "verified": True,
        "creator_id": creator_id,
        "credential": "verified_human",
        "credential_id": credential_id,
        "message": "You're verified. Your future submissions will show that you "
                   "completed our verified-writer check.",
    })


# ── Already works ─────────────────────────────────────────────────────────────

@app.get("/log")
def get_log():
    """
    The audit log, most recent last.

        curl "http://127.0.0.1:5000/log?limit=10"

    You need this in unit 8 to paste entries into your README, and you need it
    now to see whether your logging is actually working.
    """
    limit = request.args.get("limit", type=int)
    entries = audit.read_entries(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


def main():
    print(f"Provenance Guard on http://{config.HOST}:{config.PORT}")
    print(f"  detector model:  {config.DETECTOR_MODEL}")
    print(f"  rate limiting:   {'ON' if config.RATE_LIMITING_ENABLED else 'off (unit 8)'}")
    print(f"  audit log:       {config.AUDIT_LOG}")
    print()
    print("Check it's alive:")
    print(f'  curl -X POST http://{config.HOST}:{config.PORT}/ping \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"message\": \"hello\"}'")
    print()
    # debug=True hands out an interactive debugger, so it's local-only — see config.py
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
