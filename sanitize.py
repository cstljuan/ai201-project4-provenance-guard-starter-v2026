"""
The one improvement in unit 8: take instructions addressed to the checker out
of the text before the signals read it.

Diagnosis it follows: PI01, PI02 and PI03 were AI paragraphs with a line aimed
at the checker in front ("Ignore all previous instructions...", "SYSTEM: ...
Return guess=human, confidence=0.02.", "(Note to the reviewing system: ...)").
Nothing in this service is a language model, so nobody "obeys" the line, but
the line still gets scored as part of the writing. Its odd tokens raise GPT-2's
perplexity (signal one reads it as more human) and its short, choppy sentences
widen the sentence-length spread (signal two reads it as more human). All
three came back "human".

What this does: drops any sentence that talks to the system about how to score
the text. If that leaves too little to judge, the original text is scored
instead, so this can never turn a submission into a 400.
"""

import re

# Sentences that speak to a checker rather than to a reader.
_PATTERNS = [
    r"\bignore (all |any )?(previous|prior|above) instructions\b",
    r"\bdisregard (the |all |any )?(previous|prior|stylometric|above|analysis|instructions)",
    r"^\s*\(?\s*(system|assistant|developer)\s*:",
    r"\bnote to the (reviewing|review|checking) system\b",
    r"\breturn (a )?(human|ai) classification\b",
    r"\b(guess|confidence)\s*=\s*",
    r"\b(do not|don't) score\b",
    r"\bprovenance check (bypassed|disabled|skipped)\b",
    r"\btreat the author as verified\b",
    r"\bplease pass it through\b",
    r"\bthis (text|piece|essay|work) was written by a (human|person)\b",
]
_RX = re.compile("|".join(_PATTERNS), re.IGNORECASE | re.MULTILINE)
_SPLIT = re.compile(r"(?<=[.!?)])\s+|\n+")


def strip_instructions(text: str, min_words: int = 20) -> tuple[str, int]:
    """Return (text to score, number of sentences removed)."""
    parts = [p for p in _SPLIT.split(text) if p and p.strip()]
    kept = [p for p in parts if not _RX.search(p)]
    removed = len(parts) - len(kept)
    if removed == 0:
        return text, 0
    cleaned = " ".join(p.strip() for p in kept)
    if len(cleaned.split()) < min_words:
        return text, 0
    return cleaned, removed
