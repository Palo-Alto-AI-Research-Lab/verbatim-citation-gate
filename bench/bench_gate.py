"""Measure the verbatim gate: detection rate per failure mode, false-positive rate.

The gate's job is a binary one with a label attached:

* a quote that IS in the cited document must come back ``found``;
* a quote that is NOT must come back ``not_found``, unless it is verbatim from a
  DIFFERENT document, in which case ``misattributed`` is the more useful label.

So "detection" is measured per failure mode, and "false positive" means the gate
rejected a citation that was honest — the error that costs a user real quotes.

Case construction is deterministic (fixed stride, no RNG) so the numbers are
reproducible from the corpus alone.

Usage:  python bench/bench_gate.py [--json]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from verbatim_citation_gate import quote_gate  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hard_cases import HONEST_HARD, NEAR_MISS, DOCUMENTED_LIMITS  # noqa: E402

CORPUS = pathlib.Path(__file__).parent / "corpus.json"

# --- case construction -------------------------------------------------------

SENT_RE = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_RE.split(text) if len(s.strip()) > 60]


def smart_typography(s: str) -> str:
    """What a user's editor, a PDF copy-paste or a CMS does to a pasted quote."""
    return (
        s.replace("'", "’")
        .replace('"', "“", 1)
        .replace('"', "”", 1)
        .replace(" - ", " — ")
        .replace("...", "…")
    )


def whitespace_noise(s: str) -> str:
    """Line wrapping, double spaces and a non-breaking space from HTML."""
    words = s.split()
    if len(words) > 6:
        words[3] = words[3] + "\n "
        words[5] = " " + words[5]
    return "  ".join(words)


def frankenquote(sents: list[str]) -> str | None:
    """Every word real, in the right document — but never written as one span."""
    if len(sents) < 2:
        return None
    head = sents[0].split()
    tail = sents[1].split()
    if len(head) < 6 or len(tail) < 6:
        return None
    return " ".join(head[: len(head) // 2] + tail[len(tail) // 2 :])


FABRICATION_SWAPS = [
    ("improves", "degrades"),
    ("increase", "reduction"),
    ("we propose", "we disprove"),
    ("significant", "negligible"),
    ("outperforms", "underperforms"),
    ("effective", "unusable"),
    ("show", "refute"),
    ("large", "miniature"),
]


def fabricate(sent: str) -> str | None:
    """A plausible sentence that was never written: real sentence, flipped claim.

    This is the hard case on purpose — it shares almost every token with a real
    sentence in the cited document, so anything doing bag-of-words matching
    passes it through.
    """
    for old, new in FABRICATION_SWAPS:
        if old in sent:
            return sent.replace(old, new, 1)
    words = sent.split()
    if len(words) < 8:
        return None
    # No lexical hook to flip: reverse an inner span. Still fluent-looking,
    # still never written.
    words[2:6] = list(reversed(words[2:6]))
    return " ".join(words)


def build_cases(docs: dict[str, str]) -> list[dict]:
    doc_ids = list(docs)
    cases: list[dict] = []

    for i, doc_id in enumerate(doc_ids):
        sents = sentences(docs[doc_id])
        if len(sents) < 2:
            continue
        other_id = doc_ids[(i + 7) % len(doc_ids)]  # fixed stride, not random
        if other_id == doc_id:
            continue
        other_sents = sentences(docs[other_id])
        if not other_sents:
            continue

        base = sents[0]

        # --- honest citations: must come back "found" --------------------
        cases.append({"mode": "exact", "expect": "found", "doc": doc_id, "quote": base})
        cases.append(
            {"mode": "typography", "expect": "found", "doc": doc_id, "quote": smart_typography(base)}
        )
        cases.append(
            {"mode": "whitespace", "expect": "found", "doc": doc_id, "quote": whitespace_noise(base)}
        )
        cases.append(
            {"mode": "case_shift", "expect": "found", "doc": doc_id, "quote": base.upper()}
        )
        words = base.split()
        if len(words) > 10:
            cases.append(
                {
                    "mode": "partial_span",
                    "expect": "found",
                    "doc": doc_id,
                    "quote": " ".join(words[2:9]),
                }
            )

        # --- fabrications: must come back "not_found" --------------------
        fab = fabricate(base)
        if fab:
            cases.append({"mode": "fabricated", "expect": "not_found", "doc": doc_id, "quote": fab})
        fr = frankenquote(sents)
        if fr:
            cases.append({"mode": "frankenquote", "expect": "not_found", "doc": doc_id, "quote": fr})

        # --- real quote, wrong document: must come back "misattributed" ---
        cases.append(
            {
                "mode": "misattributed",
                "expect": "misattributed",
                "doc": doc_id,
                "quote": other_sents[0],
            }
        )

        # --- hard: honest quotes mangled in transit (PDF, editor, CMS) -----
        for mode, fn in HONEST_HARD.items():
            q = fn(base)
            if q and q != base:
                cases.append({"mode": mode, "expect": "found", "doc": doc_id, "quote": q})

        # --- hard: near-miss fabrications a substring check might wave through
        for mode, fn in NEAR_MISS.items():
            q = fn(base)
            if q and q != base:
                cases.append({"mode": mode, "expect": "not_found", "doc": doc_id, "quote": q})

    return cases


def drop_accidental_truths(cases: list[dict], docs: dict[str, str]) -> tuple[list[dict], int]:
    """A 'fabrication' that happens to exist somewhere is not a fabrication.

    Without this the gate would be charged for our construction error rather
    than its own miss.
    """
    from verbatim_citation_gate import normalize

    haystacks = {d: normalize(t) for d, t in docs.items()}
    kept, dropped = [], 0
    for c in cases:
        if c["expect"] == "not_found":
            needle = normalize(c["quote"])
            if any(needle in h for h in haystacks.values()):
                dropped += 1
                continue
        kept.append(c)
    return kept, dropped


# --- measurement -------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    docs = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases, dropped = drop_accidental_truths(build_cases(docs), docs)

    per_mode: dict[str, dict[str, int]] = {}
    failures: list[dict] = []

    for c in cases:
        got = quote_gate(c["quote"], c["doc"], docs)
        slot = per_mode.setdefault(c["mode"], {"n": 0, "ok": 0})
        slot["n"] += 1
        if got == c["expect"]:
            slot["ok"] += 1
        elif len(failures) < 40:
            failures.append({**c, "got": got, "quote": c["quote"][:110]})

    EASY_HONEST = {"exact", "typography", "whitespace", "case_shift", "partial_span"}
    honest = [m for m in per_mode if m in EASY_HONEST or m in HONEST_HARD]
    EASY_BAD = {"fabricated", "frankenquote", "misattributed"}
    dishonest = [m for m in per_mode if m in EASY_BAD or m in NEAR_MISS]

    honest_n = sum(per_mode[m]["n"] for m in honest)
    honest_ok = sum(per_mode[m]["ok"] for m in honest)
    dis_n = sum(per_mode[m]["n"] for m in dishonest)
    dis_ok = sum(per_mode[m]["ok"] for m in dishonest)

    report = {
        "corpus": {"docs": len(docs), "chars": sum(len(v) for v in docs.values())},
        "cases": len(cases),
        "dropped_as_accidentally_real": dropped,
        "per_mode": {
            m: {
                "n": v["n"],
                "correct": v["ok"],
                "rate": round(v["ok"] / v["n"], 4) if v["n"] else None,
            }
            for m, v in sorted(per_mode.items())
        },
        "headline": {
            "detection_rate": round(dis_ok / dis_n, 4) if dis_n else None,
            "false_positive_rate": round((honest_n - honest_ok) / honest_n, 4) if honest_n else None,
            "honest_cases": honest_n,
            "bad_cases": dis_n,
        },
        "failures_sample": failures,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    h = report["headline"]
    print(f"corpus: {report['corpus']['docs']} arXiv abstracts, {report['corpus']['chars']} chars")
    print(f"cases : {report['cases']}  (dropped as accidentally real: {dropped})")
    print()
    print(f"{'mode':<16}{'n':>6}{'correct':>9}{'rate':>9}")
    for m, v in report["per_mode"].items():
        print(f"{m:<16}{v['n']:>6}{v['correct']:>9}{v['rate']:>9.4f}")
    print()
    print(f"detection rate      (bad citations caught)   : {h['detection_rate']:.4f}  over {h['bad_cases']}")
    print(f"false positive rate (honest quotes rejected) : {h['false_positive_rate']:.4f}  over {h['honest_cases']}")
    if failures:
        print(f"\nfirst {min(5, len(failures))} failures:")
        for f in failures[:5]:
            print(f"  [{f['mode']}] expected {f['expect']}, got {f['got']}: {f['quote']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
