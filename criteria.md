# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. My own writing is rarely called AI

Submit 10 pieces I wrote myself to `POST /submit`, at least 3 of them in plain,
simple, everyday language. At most 1 of the 10 comes back with `"guess": "ai"`
(the high-confidence AI label). This must hold in every one of the three trials.

**Why this target:** On a writing site, wrongly accusing a real person is the
mistake that drives them away, while missing some AI text only costs the site a
little. My first signal (GPT-2 perplexity) rewards predictable text, so plain
writing is exactly what it is most likely to accuse; that is why 3 of the 10
must be plain, and why I allow 1 miss instead of 0.

---

## 2. Clearly-AI and clearly-human text score far apart

Submit 5 clearly AI-generated texts (pasted unedited from a chatbot) and 5
clearly human texts (informal personal writing). The average `confidence` of the
5 AI texts minus the average `confidence` of the 5 human texts is at least 0.30
in every trial. (`confidence` runs from 0 = confidently human to 1 = confidently
AI.)

**Why this target:** My unsure band is 0.35 to 0.65, which is 0.30 wide. If the
easy cases are not at least one band apart, the two signals are not separating
anything, and every threshold decision built on top of them is guesswork.

---

## 3. All three labels are actually reachable

Submit a fixed set of 15 inputs: 5 clearly AI, 5 clearly human, 5 mixed (lightly
edited AI, or formal human writing). Each of the three guesses (`"human"`,
`"unsure"`, `"ai"`) appears at least 2 times among the 15 responses, in every
trial.

**Why this target:** A label that never appears is a label nobody will ever read,
and a weighted average of two signals tends to pile scores into the middle. If
"unsure" eats everything, the system looks careful but tells writers nothing;
requiring 2 of each, not 1, means the reachability isn't a fluke of one input.

---

## 4. Every appeal changes status and is recorded

Submit 5 texts, then send `POST /appeal` with each real `content_id` and a
reason. All 5 appeals return HTTP 200, `GET /content/<id>` shows the item as
`under_review`, and `GET /log` shows one `"event": "appeal"` entry per appeal
with the reasoning text. Also send 3 appeals with made-up `content_id`s: all 3
return HTTP 404 and add nothing with that id to the log.

**Why this target:** The appeal is the only thing between a wrong accusation and
nothing at all, so "most of the time" is not good enough: 5 of 5. A fake id that
silently "succeeds" would tell a writer their appeal was filed when it wasn't.

---

## 5. Bad input is refused cleanly, never crashes

Send these 8 request bodies to `POST /submit`: no `text` field, `text` empty,
`text` only whitespace, `text` as `null`, `text` as a number, text under 20 words,
text over 5,000 words, and no `creator_id`. All 8 return HTTP 400 with a JSON
body containing an `error` field. 0 of the 8 return a 500, and 0 of the 8 return
a `guess` or `label`.

**Why this target:** Under about 20 words neither signal has enough to measure,
so any label would be invented; above 5,000 words (longer than most short
stories) the request is more likely abuse than writing. A label on bad input is
a decision about a writer made on nothing, and a 500 is a crash an attacker can
repeat.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 9 capstone criteria

Written for the shape B extension (failure handling) before any capstone test
was run. Criteria 1 to 4 are about the extension; criterion 5 is about the
system as it already worked. Every trial uses fresh creator_ids, so one trial
can't use up another trial's rate limit.

## 1. A broken detector never leads to an accusation

With the service started with `AI201_FAULTS=1` and every request sending
`X-Fault-Inject: detector_error`, submit 10 valid texts: 5 clearly AI-generated
(the textbook chatbot paragraphs from `scenarios.py`) and 5 of my own messages.
All 10 return HTTP 200 with `"degraded": true`, none returns `"guess": "ai"`,
and each one has a run record in `logs/runs.jsonl` whose `error` starts with
`detector_error`. Target: 10 of 10, in every trial.

**Why this target:** before unit 9, a detector failure was a 503, so a writer got
nothing. The fallback answers on two signals out of three, and a score built on
less evidence must never be the one that accuses someone. Five of the ten are
the most AI-sounding texts I have, on purpose: they're the ones most likely to
slip into the AI band if the cap doesn't hold. All ten because this is plain
code with no model in the loop, so a single miss would be a bug, not noise.

## 2. A stalled detector doesn't stall the writer

With `X-Fault-Inject: detector_slow` (the detector sleeps 20 seconds, past its
8-second budget), send 5 valid submissions one after another. All 5 return
HTTP 200 with `"degraded": true` in under 9.0 seconds each, timed at the client
from sending the request to receiving the full response. Target: 5 of 5 under
9.0 s, in every trial.

**Why this target:** the budget is 8 seconds, and 1 second on top covers the other
two signals and the HTTP round trip on this laptop. Past about 10 seconds a
writer assumes the page broke and resubmits, which doubles the load on a
service that's already struggling.

## 3. Requests the service refuses don't use up the writer's quota

From one creator_id, within one minute: send 6 requests that get refused with
400 (text under 20 words), then 5 valid submissions. All 6 refused requests
return 400 and all 5 valid ones return 200, with no 429. Target: 5 of 5 valid
submissions accepted, in every trial.

**Why this target:** my limit is 5 per minute. Before the change, the 6 refused
requests would each have spent quota and every valid submission after them
would have been turned away. Sending exactly 5 valid ones makes the test sharp:
if even one refused request is still counted, the fifth valid one gets a 429.

## 4. Every request leaves exactly one run record

Send a mixed batch of 20 requests: 8 valid (5 from one creator, 3 from others),
1 more from that same creator (which should be rate limited), 3 with the
detector forced to error, 2 with it forced to stall, 3 refused (too short, no
creator_id, not JSON), 2 oversized (300 KB bodies) and 1 to a route that doesn't
exist. For each response, find the record in `logs/runs.jsonl` with the
`request_id` the response returned in `X-Request-Id`. Target: 20 of 20 have
exactly one record, with `status` equal to the status code the client saw and a
`duration_ms` present, in every trial.

**Why this target:** the failures I care about most (a 413, a 429, a crash) are
exactly the ones that happen before or outside my route, where a log written
from inside the route would never see them. A request with no record is one I
can't investigate afterwards. 20 of 20 because every response passes through
the same after-request hook; a missing record means the hook has a gap.

## 5. The normal path stays fast right after a stall

Immediately after criterion 2's stalled requests (while those stalled detector
calls are still sleeping in the background), send 10 valid submissions with no
fault. At least 9 of 10 complete in under 1.0 second at the client, and 0 of
10 come back `degraded`. Target: at least 9 of 10 under 1.0 s and 0 degraded,
in every trial.

**Why this target:** a timed-out detector call keeps running in a background
thread, so a burst of stalls could leave the next normal requests waiting for a
free worker or timing out themselves. Warm, normal scoring takes well under a
second on this laptop, so 1.0 s is roomy for one request and tight enough to
catch requests queuing behind stuck ones. Degraded results on a healthy
detector would mean the fallback is firing when it shouldn't.
