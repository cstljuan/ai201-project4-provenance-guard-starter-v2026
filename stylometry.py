"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies: the coefficient of variation (standard
    deviation of sentence lengths in words, divided by the mean).

    Returns:
        A float from 0 up, usually 0.1 to 1.0. **Higher means more human**:
        people put a three-word sentence next to a forty-word one, while
        generated prose marches in step.

    A submission with fewer than two sentences has no spread to measure, so it
    returns SPREAD_NEUTRAL, a value that maps to the middle of the style score
    rather than pretending one sentence looks machine-even.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return SPREAD_NEUTRAL
    mean = statistics.mean(lengths)
    return statistics.stdev(lengths) / mean if mean else SPREAD_NEUTRAL


def type_token_ratio(text: str) -> float:
    """
    Vocabulary variety, as a moving-average type-token ratio (MATTR): the
    unique-to-total word ratio inside every 50-word window, averaged.

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    A plain unique/total ratio falls as text gets longer, so a long essay
    would look "less varied" than a short note just for being long. The
    moving window fixes that. Texts shorter than the window use the plain
    ratio.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    if len(tokens) <= TTR_WINDOW:
        return len(set(tokens)) / len(tokens)
    ratios = [
        len(set(tokens[i:i + TTR_WINDOW])) / TTR_WINDOW
        for i in range(len(tokens) - TTR_WINDOW + 1)
    ]
    return statistics.mean(ratios)


def punctuation_density(text: str) -> float:
    """
    Expressive punctuation per 100 words: everything except plain full stops
    and commas (so ! ? ; : dashes, brackets, quotes, apostrophes, ellipses).

    Returns:
        A float from 0 up. Higher means more human.

    Full stops and commas are left out because every writer uses them at
    similar rates. The rest vary a lot between people, and generated prose
    tends to use very little of it.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    marks = re.findall(r"[!?;:()\[\]\"'\u2018\u2019\u201c\u201d\u2013\u2014-]|\.\.\.", text)
    return 100.0 * len(marks) / len(tokens)


# ── Combining them ───────────────────────────────────────────────────────────
#
# Each measure is mapped onto 0-1 where 1 means "looks like AI", by a straight
# line between a value that looks fully human and one that looks fully AI,
# clipped at both ends. The anchors come from the calibration table
# (python calibration.py), and they're written down in the README.

SPREAD_NEUTRAL = 0.425        # maps to exactly 0.5 below
TTR_WINDOW = 50

SPREAD_AI, SPREAD_HUMAN = 0.20, 0.65    # CV of sentence length
TTR_AI, TTR_HUMAN = 0.70, 0.90          # MATTR
PUNCT_AI, PUNCT_HUMAN = 0.0, 6.0        # expressive marks per 100 words

STYLE_WEIGHTS = {"spread": 0.4, "ttr": 0.2, "punct": 0.4}


def _toward_ai(value: float, ai_end: float, human_end: float) -> float:
    """Place a value on 0 (human end) .. 1 (AI end), clipped."""
    position = (value - human_end) / (ai_end - human_end)
    return min(max(position, 0.0), 1.0)


def style_signal(text: str) -> float:
    """
    The style signal as a 0-1 score. **Higher means more likely AI.**

    All three measures run "higher = more human", so each is flipped by
    `_toward_ai`, then combined with STYLE_WEIGHTS. Spread and punctuation
    get 0.4 each; vocabulary variety gets 0.2 because it separated the
    calibration inputs least.
    """
    parts = {
        "spread": _toward_ai(sentence_length_spread(text), SPREAD_AI, SPREAD_HUMAN),
        "ttr": _toward_ai(type_token_ratio(text), TTR_AI, TTR_HUMAN),
        "punct": _toward_ai(punctuation_density(text), PUNCT_AI, PUNCT_HUMAN),
    }
    score = sum(STYLE_WEIGHTS[k] * v for k, v in parts.items())
    return round(score, 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
