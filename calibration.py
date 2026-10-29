#!/usr/bin/env python3
"""
The Milestone 4 calibration inputs, and a table of every signal on each.

    python calibration.py

Prints model, style and phrase signals side by side plus the combined score,
so a surprising number can be traced to the signal that produced it.

Where the texts come from:
  - clearly_ai, lightly_edited_ai: written by a chatbot (Claude) when asked for
    a generic essay paragraph; the edited one had a few words changed by hand.
  - formal_human: the Gettysburg Address (1863, public domain).
  - clearly_human, plain_human: short informal pieces in a personal voice.
    These are stand-ins until Juan's own writing goes into scenarios.py.
"""

CALIBRATION = {
    "clearly_ai": (
        "Artificial intelligence has become an increasingly important part of "
        "modern society. It is important to note that AI offers numerous benefits "
        "across a wide range of industries. Furthermore, AI systems can help "
        "organizations improve efficiency and make better decisions. However, it "
        "is also essential to consider the potential challenges associated with "
        "this technology. In conclusion, by carefully balancing innovation and "
        "responsibility, we can ensure that AI continues to play a positive role "
        "in shaping our future."
    ),
    "lightly_edited_ai": (
        "AI has become a pretty big part of everyday life. It offers a lot of "
        "benefits across many industries, and AI systems can help companies work "
        "faster and make better decisions. But we also have to think about the "
        "challenges that come with this technology. If we balance innovation with "
        "responsibility, AI can keep playing a positive role in shaping our "
        "future."
    ),
    "clearly_human": (
        "Okay so the bus was late again. Twenty minutes! I stood there in the "
        "rain holding a coffee that went cold before I even got to drink half of "
        "it, and some guy next to me kept humming the same three notes over and "
        "over. Honestly? I almost walked. Then the bus shows up, packed, and the "
        "driver just waves like nothing happened. I laughed. What else are you "
        "going to do at 7am on a Tuesday."
    ),
    "plain_human": (
        "I like to cook on Sundays. I make rice and beans for the week. My mom "
        "taught me how to make them when I was small. I put them in boxes in the "
        "fridge. Then I do not have to cook after work. It saves me a lot of "
        "money and time. Sometimes I add chicken too."
    ),
    "formal_human": (
        "Four score and seven years ago our fathers brought forth on this "
        "continent, a new nation, conceived in Liberty, and dedicated to the "
        "proposition that all men are created equal. Now we are engaged in a "
        "great civil war, testing whether that nation, or any nation so conceived "
        "and so dedicated, can long endure. We are met on a great battle-field of "
        "that war. We have come to dedicate a portion of that field, as a final "
        "resting place for those who here gave their lives that that nation "
        "might live. It is altogether fitting and proper that we should do this."
    ),
}


if __name__ == "__main__":
    import detector
    import phrases
    import scoring
    import stylometry

    print(f"{'input':20} {'model':>6} {'style':>6} {'phrase':>6} {'combined':>9}  "
          f"{'spread':>6} {'mattr':>6} {'punct':>6}  guess")
    for name, text in CALIBRATION.items():
        m = detector.model_signal(text)
        s = stylometry.style_signal(text)
        p = phrases.phrase_signal(text)
        c = scoring.combine_signals(m, s, p)
        guess, _ = scoring.score_to_label(c)
        print(f"{name:20} {m:6.3f} {s:6.3f} {p:6.3f} {c:9.3f}  "
              f"{stylometry.sentence_length_spread(text):6.3f} "
              f"{stylometry.type_token_ratio(text):6.3f} "
              f"{stylometry.punctuation_density(text):6.2f}  {guess}")
