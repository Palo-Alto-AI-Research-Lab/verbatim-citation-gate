"""The cases that actually break a verbatim matcher.

The easy suite scores 1.00/0.00, which measures the suite, not the gate. These
are the transformations a real citation survives on its way to a user — PDF
extraction, editorial ellipsis, a CMS — plus the near-miss fabrications that a
substring check has the best chance of waving through.

Each case is labelled with WHO is at fault when it fails, so the report can
separate "the gate has a bug" from "the gate is behaving as documented and the
limit belongs in the README".
"""

from __future__ import annotations

import re

# --- honest quotes that get mangled in transit (failure here = false positive) --


def pdf_ligature(s: str) -> str:
    """Copy-paste out of a PDF: fi/fl/ff become single glyphs."""
    return s.replace("fi", "ﬁ").replace("fl", "ﬂ").replace("ff", "ﬀ")


def soft_hyphen(s: str) -> str:
    """PDF line-break hyphenation leaves U+00AD inside words."""
    words = s.split()
    for i, w in enumerate(words):
        if len(w) > 8:
            words[i] = w[:4] + "­" + w[4:]
    return " ".join(words)


def hyphen_linebreak(s: str) -> str:
    """The other PDF artifact: a real hyphen plus newline inside a word."""
    words = s.split()
    for i, w in enumerate(words):
        if len(w) > 8:
            words[i] = w[:4] + "-\n" + w[4:]
            break
    return " ".join(words)


def editorial_ellipsis(s: str) -> str:
    """Standard scholarly practice: elide the middle, keep both ends."""
    words = s.split()
    if len(words) < 12:
        return s
    return " ".join(words[:4]) + " ... " + " ".join(words[-4:])


def bracketed_insertion(s: str) -> str:
    """Editor clarifies a pronoun: 'it [the model] improves'."""
    words = s.split()
    if len(words) < 8:
        return s
    words.insert(4, "[sic]")
    return " ".join(words)


def cyrillic_homoglyph(s: str) -> str:
    """Text that round-tripped through a tool that swapped look-alike glyphs."""
    return s.replace("o", "о", 2).replace("e", "е", 2)


def nbsp(s: str) -> str:
    return s.replace(" ", " ", 3)


HONEST_HARD = {
    "pdf_ligature": pdf_ligature,
    "soft_hyphen": soft_hyphen,
    "hyphen_linebreak": hyphen_linebreak,
    "editorial_ellipsis": editorial_ellipsis,
    "bracketed_insertion": bracketed_insertion,
    "cyrillic_homoglyph": cyrillic_homoglyph,
    "nbsp": nbsp,
}

# --- near-miss fabrications (failure here = a fabrication reaches the user) ----


def swap_one_number(s: str) -> str | None:
    """The most dangerous edit in a cited claim: 12.4% quietly becomes 21.4%."""
    m = re.search(r"\d+\.?\d*", s)
    if not m:
        return None
    digits = m.group()
    flipped = digits[::-1] if digits[::-1] != digits else digits + "1"
    return s[: m.start()] + flipped + s[m.end() :]


def negate(s: str) -> str | None:
    """Insert a 'not' — every other token identical to a real sentence."""
    for verb in (" is ", " are ", " was ", " can ", " does "):
        if verb in s:
            return s.replace(verb, verb[:-1] + " not ", 1)
    return None


def drop_one_word(s: str) -> str | None:
    """A single elided word can invert a hedged claim into a flat one."""
    for hedge in ("may ", "often ", "can ", "potentially ", "largely ", "partially "):
        if hedge in s:
            return s.replace(hedge, "", 1)
    return None


def swap_synonym(s: str) -> str | None:
    """One word changed to a near-synonym: bag-of-words scoring stays ~identical."""
    pairs = [
        ("method", "technique"),
        ("results", "findings"),
        ("model", "system"),
        ("dataset", "corpus"),
        ("approach", "strategy"),
        ("performance", "accuracy"),
    ]
    for old, new in pairs:
        if old in s:
            return s.replace(old, new, 1)
    return None


NEAR_MISS = {
    "number_swap": swap_one_number,
    "negation": negate,
    "hedge_dropped": drop_one_word,
    "synonym_swap": swap_synonym,
}

# Which honest-hard modes the gate is DOCUMENTED not to survive. Failing these
# is a known limit, not a regression — but it still counts in the headline FPR,
# because a user whose quote was rejected does not care whose fault it is.
DOCUMENTED_LIMITS = {"editorial_ellipsis", "bracketed_insertion"}
