# Benchmark: what the gate catches, and what it wrongly rejects

Two numbers, both measured, neither flattering by construction.

```
detection rate      (bad citations caught)   : 1.0000   over 1 221 cases
false positive rate (honest quotes rejected) : 0.1721   over 3 371 cases
```

The false-positive rate was **0.4254** when this benchmark was first run. Three
of the five failing modes were normalization gaps — soft hyphens, line-break
hyphenation and homoglyphs are the same characters encoded differently — and
fixing them took the rate to 0.1721 (−25.3 points) **without moving detection**,
which stayed at 1.0000 on all 1 221 bad citations. That constraint is the point:
every normalization that makes matching more forgiving risks waving through the
thing the gate exists to catch, so `test_transit_damage_does_not_rescue_a_fabrication`
in `tests/test_gate.py` guards the trade directly.

Corpus: **295 arXiv abstracts** (cs.CL, cs.IR, cs.SE — 430 881 chars), fetched by
`build_corpus.py`. Deliberately not this project's own documents: benchmarking a
matcher against the text it was written for measures the author's memory.

Reproduce:

```bash
python bench/build_corpus.py     # writes bench/corpus.json
python bench/bench_gate.py       # prints the table below
python bench/bench_gate.py --json > bench/results.json
```

Case construction is deterministic — fixed stride, no RNG — so the same corpus
yields the same 4 592 cases and the same numbers on any machine.

## Per mode

| Mode | n | correct | rate | |
|---|---:|---:|---:|---|
| **Fabrications the gate must reject** | | | | |
| `fabricated` — real sentence, claim flipped | 295 | 295 | 1.0000 | ✅ |
| `frankenquote` — real words, never one span | 295 | 295 | 1.0000 | ✅ |
| `misattributed` — verbatim, wrong document | 295 | 295 | 1.0000 | ✅ |
| `number_swap` — 12.4% becomes 21.4% | 16 | 16 | 1.0000 | ✅ |
| `negation` — one inserted "not" | 133 | 133 | 1.0000 | ✅ |
| `hedge_dropped` — "may" quietly removed | 73 | 73 | 1.0000 | ✅ |
| `synonym_swap` — one near-synonym | 114 | 114 | 1.0000 | ✅ |
| **Honest quotes the gate must accept** | | | | |
| `exact` | 295 | 295 | 1.0000 | ✅ |
| `case_shift` | 295 | 295 | 1.0000 | ✅ |
| `typography` — smart quotes, em-dash, … | 295 | 295 | 1.0000 | ✅ |
| `whitespace` — wraps, double spaces | 295 | 295 | 1.0000 | ✅ |
| `nbsp` — non-breaking spaces from HTML | 295 | 295 | 1.0000 | ✅ |
| `partial_span` — a phrase inside a sentence | 290 | 290 | 1.0000 | ✅ |
| `pdf_ligature` — ﬁ / ﬂ / ﬀ | 143 | 143 | 1.0000 | ✅ |
| `hyphen_linebreak` — `informa-\ntion` | 294 | 294 | 1.0000 | ✅ |
| `soft_hyphen` — U+00AD inside words | 294 | 294 | 1.0000 | ✅ |
| `cyrillic_homoglyph` — Cyrillic о/е for Latin | 295 | 295 | 1.0000 | ✅ |
| `editorial_ellipsis` — `"start … end"` | 285 | 0 | 0.0000 | ❌ |
| `bracketed_insertion` — `"it [the model] …"` | 295 | 0 | 0.0000 | ❌ |

## How to read this

**Detection is the strong half and it is real.** 1 221 bad citations, zero
waved through, including the four near-miss classes built specifically to beat a
substring check: a single flipped digit, a single inserted "not", a dropped
hedge, one near-synonym. Each of those shares almost every token with a true
sentence in the cited document — the exact input where embedding similarity or
an LLM judge scores high and says yes.

**The false-positive rate is the honest bad news**, and 17.2 points of it are
still here. What remains is structural, not a bug: `editorial_ellipsis` and
`bracketed_insertion` are quotes that are *deliberately not contiguous*, and
contiguity is exactly what makes frankenquote detection work. Supporting them
needs a second matcher — gapped-span matching with a bounded gap budget — not a
looser normalizer, so it is a design change rather than a fix and is not
attempted here.

Anyone dropping this in front of users today should know: it will not lose a
fabrication, and it will still argue with roughly one in six real quotes —
specifically, quotes an author shortened with an ellipsis or annotated in
brackets. Both halves of that sentence are measured, and the second one is why
this file exists.

## What is not measured here

* **Stage 2, the judge.** These numbers cover the deterministic gate only.
* **Real-world class balance.** The mix here is constructed, not sampled from
  production traffic, so the headline rates are per-suite, not per-user. Read
  the per-mode table, not the average, to predict behaviour on your own inputs.
* **Non-English text**, beyond the homoglyph case.
* **Long documents.** arXiv abstracts are ~1.5 kB; retrieval over full papers
  may behave differently.
