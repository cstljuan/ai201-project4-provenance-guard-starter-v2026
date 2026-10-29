"""
Signal three: the stock-phrase signal. (Stretch feature.)

Signal one measures how predictable the text is. Signal two measures its
shape. This one measures **word choice**: how often the text reaches for the
stock phrases and connective filler that chat models lean on. "It is important
to note", "furthermore", "delve", "in conclusion".

    python phrases.py "some text"

**The blind spot.** It is a word list. A writer who never uses these phrases
passes, whoever they are, and AI text prompted to "sound casual" drops them
at once. It also catches people who were taught to write this way: students
trained on five-paragraph essays, and business writers.

It carries 0.30 of the combined score, as much as the style signal, because in
calibration it was the only signal that read plain, simple human writing as
human (see the README's Signals and Scoring).
"""

import re

STOCK_PHRASES = [
    "it is important to note", "it's important to note", "it is worth noting",
    "it's worth noting", "in conclusion", "in summary", "to summarize",
    "furthermore", "moreover", "additionally", "in today's", "ever-evolving",
    "ever-changing", "rapidly evolving", "plays a crucial role",
    "plays a vital role", "plays a pivotal role", "a wide range of",
    "a variety of", "numerous", "delve", "tapestry", "testament to",
    "navigate the", "landscape", "leverage", "foster", "seamless",
    "it is essential to", "it's essential to", "crucial", "pivotal",
    "overall,", "ultimately,", "on the other hand", "in essence",
    "shaping our future", "stands as", "embark", "realm", "unlock",
]

# Phrase hits per 100 words that count as fully AI-like. Two or three stock
# phrases in a 100-word paragraph is already a lot for a person.
SATURATION_PER_100 = 3.0


def phrase_hits(text: str) -> int:
    lowered = text.lower()
    return sum(len(re.findall(r"\b" + re.escape(p), lowered)) for p in STOCK_PHRASES)


def phrase_signal(text: str) -> float:
    """
    Stock-phrase density as a 0-1 score. **Higher means more likely AI.**

    0 hits scores 0.0; SATURATION_PER_100 hits per 100 words or more scores 1.0.
    """
    n_words = len(re.findall(r"[a-z0-9']+", text.lower()))
    if not n_words:
        return 0.0
    per_100 = 100.0 * phrase_hits(text) / n_words
    return round(min(per_100 / SATURATION_PER_100, 1.0), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "It is important to note that AI offers numerous benefits. Furthermore, "
        "it plays a crucial role in today's ever-evolving landscape."
    )
    print(f"stock phrase hits   {phrase_hits(text)}")
    print(f"phrase_signal       {phrase_signal(text)}   (higher = more likely AI)")
