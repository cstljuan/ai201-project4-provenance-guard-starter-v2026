"""
Turning two numbers into one, and one number into something a person can read.
← YOU BUILD THIS IN MILESTONES 4 AND 5

Two functions live here, and both are stubs.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import config


def combine_signals(model_score: float, style_score: float,
                    phrase_score: float | None = None) -> float:
    """
    Combine the signals into one 0-1 score. Higher means more likely AI.

    The rule, in words:

      1. Weighted average: model 0.40, style 0.30, phrases 0.30 (config.py).
         With no phrase score, the model and style weights are rescaled to
         sum to 1.
      2. Disagreement pulls toward the middle. When the model and style
         signals are more than DISAGREEMENT_GAP apart, the combined score is
         pulled halfway back toward 0.5. Two methods disagreeing IS
         uncertainty, and "unsure" is the label that costs a real writer
         least.
      3. Nothing is called AI on one signal alone. If the score lands in the
         AI band but the style signal reads human-ish (below 0.5), the score
         is capped just under the AI threshold, so it shows as "unsure".

    Rules 2 and 3 only ever move a score away from "ai", never toward it.
    That's the false-positive decision from Milestone 1: a missed detection
    is cheaper than a wrong accusation.
    """
    if phrase_score is None:
        total = config.WEIGHT_MODEL_SIGNAL + config.WEIGHT_STYLE_SIGNAL
        score = (config.WEIGHT_MODEL_SIGNAL * model_score
                 + config.WEIGHT_STYLE_SIGNAL * style_score) / total
    else:
        score = (config.WEIGHT_MODEL_SIGNAL * model_score
                 + config.WEIGHT_STYLE_SIGNAL * style_score
                 + config.WEIGHT_PHRASE_SIGNAL * phrase_score)

    if abs(model_score - style_score) > config.DISAGREEMENT_GAP:
        score = 0.5 + (score - 0.5) * 0.5

    if score >= config.AI_THRESHOLD and style_score < 0.5:
        score = config.AI_THRESHOLD - 0.01

    return round(min(max(score, 0.0), 1.0), 4)


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn a score into a guess and the text a reader actually sees.
    ← TODO (Milestone 5)

    Returns:
        (guess, label_text) — where `guess` is a short machine-readable string
        like "ai" / "human" / "unsure", and `label_text` is the full sentence
        shown to a person.

    ⚠️ Write the label text for someone who has never heard the word
    "threshold".

        ✗ "human, 0.81 confidence"
        ✓ "We think this was probably written by a person."

    All three labels have to be **reachable**. If no score can produce one of
    them, your ranges have a gap — and Milestone 5 asks you to submit text that
    produces each one, which is how you'd find out.

    The hardest one to write is "unsure". It has to admit uncertainty without
    sounding like an accusation, because the person reading it may well have
    written every word themselves. Your breakout asks your group what they'd
    think if they got it on their own work. That question is the whole
    milestone.
    """
    if score >= config.AI_THRESHOLD:
        return "ai", LABEL_AI
    if score < config.HUMAN_THRESHOLD:
        return "human", LABEL_HUMAN
    return "unsure", LABEL_UNSURE


LABEL_HUMAN = (
    "We think a person most likely wrote this. Our check found the variety in "
    "sentences and word choice that we usually see in human writing."
)

LABEL_UNSURE = (
    "We can't tell whether this was written by a person or with help from AI, "
    "so we are not making a call either way. This is not an accusation. Our "
    "check is easily thrown off by short, plain, or very formal writing. If you "
    "wrote this, you don't need to do anything."
)

LABEL_AI = (
    "Our check found strong signs that this may have been written with AI. "
    "Automated checks can be wrong, and this one is not proof. If you wrote "
    "this yourself, you can ask for a review, and it will be marked as under "
    "review while a person looks at it."
)


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 up to (not including) {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} up to (not including) {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} to 1.00"),
    ]
