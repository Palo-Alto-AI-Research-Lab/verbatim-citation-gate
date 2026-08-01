"""Stage 1 — the deterministic verbatim gate.

Zero dependencies, zero tokens. Before any model is asked whether a quote
*supports* a claim, this stage asks the cheaper, prior question: **does the
quote exist, verbatim, in the document it is attributed to?**

A bag-of-words comparison would pass frankenquotes — stitched "quotes" whose
every word appears in the source but whose sentence was never written. So the
gate matches the normalized quote as a contiguous substring. A real quote that
lives in a *different* document is flagged ``misattributed`` rather than
silently failing, which keeps that failure mode visible instead of collapsing
it into ``not_found``.

Because it is pure string work, the gate cannot be sweet-talked by a persuasive
citation, and every fabrication it rejects costs zero model calls.
"""

from __future__ import annotations

import unicodedata

__all__ = ["normalize", "quote_gate", "GateResult"]

# The three outcomes the gate can return.
GateResult = str  # Literal["found", "misattributed", "not_found"]


def normalize(text: str) -> str:
    """Case/typography/whitespace-insensitive form for verbatim matching.

    Applies Unicode compatibility normalization and case folding, drops
    punctuation that does not carry meaning, and collapses runs of whitespace.
    Percent signs and decimal points survive because ``25%`` and ``0.5`` are
    load-bearing in the kind of quantitative claims citations usually support.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        char if char in "%." or unicodedata.category(char)[0] in "LNM" else " "
        for char in text
    )
    return " ".join(text.split())


def quote_gate(quote: str, cited_doc_id: str, docs: dict[str, str]) -> GateResult:
    """Check a quote against the document it is attributed to.

    Returns one of:

    * ``"found"``        — the quote appears verbatim in ``docs[cited_doc_id]``.
    * ``"misattributed"``— the quote appears verbatim in some *other* document.
    * ``"not_found"``    — the quote appears in no document (fabricated /
      frankenquote), or the quote / citation is empty.

    Fails closed: an empty quote or an unknown ``cited_doc_id`` yields
    ``"not_found"`` rather than raising, so a malformed citation can never be
    mistaken for a supported one.
    """
    q = normalize(quote)
    if not q:
        return "not_found"
    cited = docs.get(cited_doc_id)
    if cited is not None and q in normalize(cited):
        return "found"
    if any(q in normalize(text) for doc_id, text in docs.items() if doc_id != cited_doc_id):
        return "misattributed"
    return "not_found"
