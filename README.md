# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

## Stretch Features (declared before building)

I'm attempting all three stretch features this unit. This section was written and
committed before any of them was built, so the commit history shows the plan came
first.

1. **A third signal: stock-phrase density.** It counts how often the text uses
   stock phrases and filler words that language models lean on ("it is important
   to note", "delve", "in conclusion", "furthermore"), per 100 words. It measures
   word *choice*. Signal one measures predictability and signal two measures
   shape, so this is a third, separate idea. How the three are weighted against
   each other will be written up in Signals and Scoring once it's built.
2. **`GET /content/<id>`.** Returns one item's current state: its latest decision,
   its status (`decided` or `under_review`), and any appeal on record. Built from
   the audit log, so it can't drift from what the log says.
3. **A verified-human path.** A writer asks for a challenge with
   `POST /verify/start` and gets a short prompt back. They answer it with
   `POST /verify/complete` within a time limit. If the answer is long enough and
   doesn't score as high-confidence AI, the creator earns a `verified_human`
   credential, recorded in the audit log. From then on, every `/submit` from
   that creator carries `"creator_verified": true`, and the label a reader sees
   says so.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

Provenance Guard is a small backend service a writing site could plug into. A
piece of text goes in; a guess, a confidence score, a plain-English label and an
appeal path come out. This is the path one submission takes:

1. **The writer's site sends `POST /submit`** with `{"text": ..., "creator_id": ...}`
   (`app.py::submit`).
2. **The route checks the input** (`app.py::_validate_submission`). Missing, empty,
   non-string, under 20 words or over 5,000 words is refused with a 400 and a JSON
   error, and the refusal is written to the audit log. Nothing gets a label it
   wasn't actually judged on.
3. **Signal one, the model signal** (`detector.py::model_signal`): GPT-2 runs on
   this machine and measures how predictable the text is. 0 to 1, higher = more
   AI-like.
4. **Signal two, the style signal** (`stylometry.py::style_signal`) measures the
   text's shape: sentence-length spread, vocabulary variety and expressive
   punctuation. **Signal three, the stock-phrase signal** (`phrases.py::phrase_signal`,
   stretch) counts stock phrases chat models lean on.
5. **The combining rule** (`scoring.py::combine_signals`) turns the three into one
   0 to 1 `confidence`, pulls toward the middle when the signals disagree, and
   refuses to call anything AI on the model signal alone.
6. **The label** (`scoring.py::score_to_label`) maps that number to one of three
   sentences a reader sees. If the writer has a verified-human credential, a note
   saying so is added.
7. **Every decision is written to `logs/audit.jsonl`** (`audit.py`) with all three
   signal scores, and the JSON response goes back with a `content_id`. If the
   writer disagrees, `POST /appeal` with that id moves it to `under_review`, and
   `GET /content/<id>` shows its current state.

---

## Signals and Scoring

### Signal one: the model signal

**What it measures:** Perplexity under GPT-2: how surprised a language model is by
each next word, squashed onto 0 to 1 (`detector.py::model_signal`, midpoint 45,
unchanged from the starter). Low perplexity = high score = more AI-like.

**Why that might differ between human and AI writing:** A chat model writes by
picking likely next words, so its text is text a model finds easy to predict.
People make odder choices: specific details, abrupt turns, rare words.

**What it can't see:** Authorship. It rewards plain, common words in short,
ordinary sentences, which is how second-language writers, younger writers and
anyone writing simply on purpose write. In my calibration, a plain paragraph
about cooking rice and beans scored **0.836**, about the same as clearly-AI text
(**0.870**). It also reads ornate, rare-word prose as human whoever wrote it.

### Signal two: the style signal

**What it measures:** The shape of the text, never its meaning
(`stylometry.py::style_signal`). Three measures, each mapped onto 0 (human end)
to 1 (AI end) between anchors taken from the calibration table:

| Measure | What it is | Human end | AI end | Weight |
|---|---|---|---|---|
| `sentence_length_spread` | std dev / mean of sentence lengths | 0.65 | 0.20 | 0.4 |
| `type_token_ratio` | moving-average type-token ratio, 50-word window | 0.90 | 0.70 | 0.2 |
| `punctuation_density` | `! ? ; : ( ) " ' -` and ellipses per 100 words (not `.` or `,`) | 6.0 | 0.0 | 0.4 |

A one-sentence text has no spread, so spread returns a neutral value that maps
to exactly 0.5 instead of pretending it looks machine-even. The moving-window
TTR is there because plain unique/total falls as text gets longer.

**Why that might differ between human and AI writing:** Generated prose tends
toward even, mid-length sentences and very little expressive punctuation. People
are lumpier: a three-word sentence next to a forty-word one, a question, a
bracket, a dash.

**What it can't see:** It can't read. Anything that changes the shape without
changing the words fools it. When I chopped AI sentences short and added a few
`!`, `?` and brackets, the style score fell to **0.00** (fully human). It also
reads plain, even writing as AI: the rice-and-beans paragraph scored **0.855**.

### Signal three: the stock-phrase signal (stretch)

**What it measures:** Word choice. Stock phrases and filler models lean on
("it is important to note", "furthermore", "delve", "in conclusion"; the full
list is in `phrases.py::STOCK_PHRASES`), per 100 words. 0 hits = 0.0; 3 or more
per 100 words = 1.0.

**Why that might differ:** Chat models reach for the same connectives and
"essay voice" phrases over and over. Most people writing about their own lives
don't.

**What it can't see:** It's a word list. AI text prompted to "sound casual"
drops these phrases at once, and people taught the five-paragraph essay use
them on purpose. That second group is exactly who my sample-run appeal below
comes from.

### The combining rule

**The rule:**

1. Weighted average of the three signals.
2. **Disagreement pulls toward unsure.** If the model and style signals are more
   than 0.40 apart, the score is pulled halfway back toward 0.5. Two methods
   disagreeing is uncertainty, and "unsure" is the label that costs a real
   writer least.
3. **Nothing is called AI without the style signal agreeing.** If the score
   lands in the AI band but the style signal is under 0.5, the score is capped
   at 0.69, which shows as "unsure".

Rules 2 and 3 can only move a score *away* from the AI label. That's the
false-positive decision: a missed detection costs the site a little, a wrong
accusation costs a person a lot.

**The numbers:** (all in `config.py`)

| Setting | Value |
|---|---|
| `WEIGHT_MODEL_SIGNAL` | 0.40 |
| `WEIGHT_STYLE_SIGNAL` | 0.30 |
| `WEIGHT_PHRASE_SIGNAL` | 0.30 |
| `DISAGREEMENT_GAP` | 0.40 |
| `HUMAN_THRESHOLD` | 0.35 (below = human) |
| `AI_THRESHOLD` | 0.70 (at or above = AI) |

**How the three are weighted against each other, and why:** I started at
0.45 / 0.35 / 0.20 with the AI line at 0.65. The calibration table
(`python calibration.py`) then showed my plain human paragraph scoring 0.676,
labelled **AI**: both the model and style signals read plain writing as
machine-like, and the phrase signal was the only one that read it as human
(0.000). So I moved weight toward the phrase signal (0.40 / 0.30 / 0.30) and
raised the AI line to 0.70. The plain paragraph now scores 0.591 (unsure, not an
accusation). The model signal keeps the largest single weight because it's the
only one that reads the words in context; the phrase signal never outweighs it
because it's the easiest to game.

Calibration table after the change:

```
input                 model  style phrase  combined  guess
clearly_ai            0.870  0.699  1.000     0.858  ai
lightly_edited_ai     0.778  0.734  0.538     0.693  unsure
clearly_human         0.581  0.288  0.000     0.319  human
plain_human           0.836  0.855  0.000     0.591  unsure
formal_human          0.727  0.666  0.000     0.491  unsure
```

**Where it lives:** `scoring.py::combine_signals`

**A case where my two signals split, and what my rule does with it:** The
clearly-AI paragraph, with its sentence lengths broken up (one 3-word sentence,
one 40-word sentence) and one `!` added. The model signal still read it as AI
(**0.773**) because the words were unchanged; the style signal read it as fairly
human (**0.358**) because the shape changed. The gap is 0.415, over 0.40, so rule
2 pulled the weighted score of 0.548 to **0.524: unsure**. That's what I want:
when one signal says AI and the other doesn't, the system shouldn't pick a side.

---

## Label Variants

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 up to (not including) 0.35 | We think a person most likely wrote this. Our check found the variety in sentences and word choice that we usually see in human writing. |
| unsure | 0.35 up to (not including) 0.70 | We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything. |
| high-confidence AI | 0.70 to 1.00 | Our check found strong signs that this may have been written with AI. Automated checks can be wrong, and this one is not proof. If you wrote this yourself, you can ask for a review, and it will be marked as under review while a person looks at it. |

Every score from 0 to 1 falls in exactly one range (`scoring.label_ranges()`),
and all three were reached by the calibration inputs above. A verified writer's
label gets one more sentence: *This writer has completed our verified-writer
check.*

**Why I worded the "unsure" one this way:** Most of the people who land here
are writing plainly or formally, which is the false positive this whole project
is about. So it says outright that it isn't an accusation, names the kinds of
writing that throw the check off (so a plain writer recognises themselves
instead of feeling caught), and tells them they don't have to do anything. It
never uses "score", "confidence" or "threshold".

---

## Sample Run

**A submission**

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Artificial intelligence has become an increasingly important part of modern society. It is important to note that AI offers numerous benefits across a wide range of industries. Furthermore, AI systems can help organizations improve efficiency and make better decisions. In conclusion, AI will continue to play a crucial role in shaping our future.", "creator_id": "juan"}'
```

```json
{
    "confidence": 0.9089,
    "content_id": "8550d702179c",
    "creator_id": "juan",
    "creator_verified": false,
    "guess": "ai",
    "label": "Our check found strong signs that this may have been written with AI. Automated checks can be wrong, and this one is not proof. If you wrote this yourself, you can ask for a review, and it will be marked as under review while a person looks at it.",
    "model_score": 0.8922,
    "phrase_score": 1.0,
    "status": "decided",
    "style_score": 0.84
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "8550d702179c", "reasoning": "I wrote this for a class assignment. My teacher taught us to use words like furthermore and in conclusion."}'
```

```json
{
    "content_id": "8550d702179c",
    "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
    "original_guess": "ai",
    "original_label": "Our check found strong signs that this may have been written with AI. Automated checks can be wrong, and this one is not proof. If you wrote this yourself, you can ask for a review, and it will be marked as under review while a person looks at it.",
    "status": "under_review"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=2"
```

```json
{
    "count": 2,
    "entries": [
        {
            "combined_score": 0.9089,
            "content_id": "8550d702179c",
            "creator_id": "juan",
            "creator_verified": false,
            "guess": "ai",
            "label": "Our check found strong signs that this may have been written with AI. Automated checks can be wrong, and this one is not proof. If you wrote this yourself, you can ask for a review, and it will be marked as under review while a person looks at it.",
            "model_score": 0.8922,
            "phrase_score": 1.0,
            "status": "decided",
            "style_score": 0.84,
            "timestamp": "2026-10-29T15:23:28+00:00"
        },
        {
            "content_id": "8550d702179c",
            "creator_id": "juan",
            "event": "appeal",
            "reasoning": "I wrote this for a class assignment. My teacher taught us to use words like furthermore and in conclusion.",
            "status": "under_review",
            "timestamp": "2026-10-29T15:23:29+00:00"
        }
    ]
}
```

The original decision is untouched; the appeal sits after it with the new
status. An appeal on a `content_id` that doesn't exist returns a 404 and writes
nothing.

---

## Stretch Features: what was built

All three were declared above (commit `cc1e5fd`) before any of them was built.

### `GET /content/<id>`

Returns one item's current state, built from the audit log so it can't disagree
with it (`app.py::content`). The same item as the sample run, after the appeal:

```bash
$ curl http://127.0.0.1:5000/content/8550d702179c
```

```json
{
    "appeals": [
        {
            "reasoning": "I wrote this for a class assignment. My teacher taught us to use words like furthermore and in conclusion.",
            "timestamp": "2026-10-29T15:23:29+00:00"
        }
    ],
    "confidence": 0.9089,
    "content_id": "8550d702179c",
    "creator_id": "juan",
    "creator_verified": false,
    "guess": "ai",
    "label": "Our check found strong signs that this may have been written with AI. Automated checks can be wrong, and this one is not proof. If you wrote this yourself, you can ask for a review, and it will be marked as under review while a person looks at it.",
    "model_score": 0.8922,
    "phrase_score": 1.0,
    "status": "under_review",
    "style_score": 0.84,
    "submitted_at": "2026-10-29T15:23:28+00:00"
}
```

An unknown id returns a 404.

### A third signal

See **Signal three** and **How the three are weighted** in Signals and Scoring.
What it changed: it's the only signal that reads plain human writing as human,
and adding it at 0.30 moved the plain calibration paragraph from AI to unsure.

### A verified-human path

**The extra step:** a writer calls `POST /verify/start` with their `creator_id`
and gets a prompt they couldn't have seen before ("Describe the room you're
sitting in right now..."). They answer with `POST /verify/complete` within 15
minutes, in at least 60 words. The answer is scored by the same three signals;
if it isn't labelled high-confidence AI, the writer earns a `verified_human`
credential, written to the audit log. A challenge can only be answered once
(a second try returns 409). From then on every `/submit` from that creator
carries `"creator_verified": true` and the label ends with *"This writer has
completed our verified-writer check."*

The credential being earned, then appearing on an item (audit log entries):

```json
{"timestamp": "2026-10-29T15:23:10+00:00", "creator_id": "maria_writes", "event": "verify_start", "status": "challenge_open", "challenge_id": "473209e390cb"}
{"timestamp": "2026-10-29T15:23:12+00:00", "creator_id": "maria_writes", "event": "verified", "status": "verified_human", "challenge_id": "473209e390cb", "credential_id": "vh_01317e6872", "model_score": 0.4631, "style_score": 0.3188, "phrase_score": 0.0, "combined_score": 0.2809}
{"timestamp": "2026-10-29T15:23:12+00:00", "content_id": "db764cb8cfe0", "creator_id": "maria_writes", "guess": "unsure", "model_score": 0.7273, "style_score": 0.6658, "combined_score": 0.4907, "label": "We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything. This writer has completed our verified-writer check.", "status": "decided", "phrase_score": 0.0, "creator_verified": true}
```

**What it changed:** `/submit` now checks the log for a credential and adds
`creator_verified` to the response and log entry. The credential does not change
the score; it adds context for the reader.

**Its blind spot:** it doesn't check that the answer is about the prompt, and it
can't tell whether the writer typed it or pasted it from a chatbot told to
"write casually". It raises the cost of faking, it doesn't prove anything.

---

## How I Used AI

I built this with Claude Code (Anthropic's coding assistant) working in my
repository.

**Moment 1: the acceptance criteria**

- *What I asked for:* I asked Claude to suggest criteria and let me pick. It
  gave me one multiple-choice question per area (false positives, score spread,
  label coverage, bad input) with two or three possible targets each, and said
  the appeal criterion should be "every time".
- *What came back:* Options like "at most 1 / 0 / 2 of 10 of my own pieces
  labelled AI" and "spread at least 0.20 / 0.30 / 0.40".
- *What I changed:* I picked at most 1 of 10 for false positives and at least 2
  of each label, and left the spread (0.30) and the length limits (20 to 5,000
  words) to Claude. Claude then wrote the criteria text and the reasons from
  those picks, and I kept the requirement that 3 of my 10 pieces be plain
  writing, because that's the writing signal one is most likely to accuse.

**Moment 2: the weights**

- *What I asked for:* Claude built the three signals and a first combining rule
  (0.45 / 0.35 / 0.20, AI line at 0.65), then ran the calibration table.
- *What came back:* The plain human paragraph was labelled **AI** at 0.676.
  Both the model and style signals read short, plain sentences as machine-like.
- *What changed:* Claude proposed, and I kept, weights of 0.40 / 0.30 / 0.30 and
  an AI line of 0.70, so
  the phrase signal (the only one that read plain writing as human) counts more.
  The plain paragraph moved to unsure. Lightly-edited AI moved to unsure too,
  which is the trade: fewer wrong accusations, more AI getting through.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
