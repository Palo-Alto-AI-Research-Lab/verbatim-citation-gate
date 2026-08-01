# verbatim-citation-gate

📖 **Docs: <https://palo-alto-ai-research-lab.github.io/verbatim-citation-gate/>** — the two stages, the API, the verdicts, and every known limit with its issue.

**Catch fabricated RAG citations before they reach the user.** A two-stage,
framework-agnostic auditor for quote-style citations — the deterministic half
runs with zero dependencies and zero tokens; the model half plugs into
whatever LLM your pipeline already speaks.

RAG systems love to cite. The problem is *how they fail*: a quote that reads as
authoritative and word-for-word can still be

- **fabricated** — a plausible sentence that appears in no source,
- a **frankenquote** — every word is real, but the sentence was stitched
  together and never actually written, or
- **misattributed** — a real quote lifted from a *different* document.

A judge model, asked "does this quote support this claim?", waves all three
through: they read as fluent and supportive. The fix is to ask the cheaper,
prior question first, deterministically.

## The two stages

```
                 ┌─────────────────────────┐
 claim + quote → │ 1. verbatim gate (free)  │ → not_found / misattributed   (rejected, 0 tokens)
   + doc id      └─────────────┬───────────┘
                               │ found
                               ▼
                 ┌─────────────────────────┐
                 │ 2. skeptical judge (LLM) │ → supports / partial / unrelated / contradicts
                 └─────────────────────────┘
```

**Stage 1 — the verbatim gate.** Pure `re` + substring matching over a
normalized form (case, smart quotes, dashes, and whitespace folded; numbers and
`%` preserved). It cannot be sweet-talked, and every fabrication it rejects
costs zero model calls. Frankenquotes fail because the match is contiguous, not
bag-of-words. A real quote from the wrong document is surfaced as
`misattributed` instead of being collapsed into `not_found`.

**Stage 2 — the skeptical judge.** For quotes that *do* exist, a burden-of-proof
prompt decides whether the passage actually establishes the claim:

1. **Default-refute** — the verdict starts at *unsupported*; the quote must earn
   `supports`, and ties break against the claim.
2. **Outside knowledge is inadmissible** — a claim can be true in the world and
   still unsupported by *this* source.
3. **Full-strength support** — same population, direction, magnitude, and
   certainty, or the verdict caps at `partial` (subgroup→everyone,
   correlation→causation, "may"→"does").

If the judge's output does not parse, it **fails closed** — an unverifiable
citation never counts as support.

## Install

Not on PyPI yet — install from the repository:

```bash
pip install "git+https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate"

# from a clone, with the test extra:
pip install -e ".[test]" && pytest -q
```

## Use

```python
from verbatim_citation_gate import audit_citation

docs = {"veltranib-rct": "... Body weight was unchanged in both arms."}

# Stage 1 only — no model, no key, fully offline:
audit_citation("Body weight did not change.", "veltranib-rct",
               "Body weight was unchanged in both arms.", docs)   # -> "found"

# Both stages — supply any model as llm_call(system, user) -> str:
def llm_call(system, user):
    return client.messages.create(              # Anthropic shown; any vendor works
        model="claude-haiku-4-5", system=system, max_tokens=1024,
        messages=[{"role": "user", "content": user}],
    ).content[0].text

audit_citation("Body weight did not change.", "veltranib-rct",
               "Body weight was unchanged in both arms.", docs, llm_call=llm_call)
# -> "supports" | "partial" | "unrelated" | "contradicts" | "not_found" | "misattributed"
```

`llm_call` is deliberately the smallest possible contract — `(system, user) → text`
— so the judge wires to Claude, GPT, Gemini, Mistral, Cohere, or a local Qwen
without adapters. OpenAI, Cohere, and other one-liners are in
[`examples/quickstart.py`](examples/quickstart.py).

## Why the gate goes first

The number you page on for a citation auditor is **recall of unfaithful
citations** — the fraction of bad citations you actually catch. The gate lifts
that recall for free on the three failure modes a judge is *worst* at
(fabricated, franken, misattributed), because those are exactly the ones that
look supportive. What reaches the model is only the genuinely ambiguous case:
a real quote whose *sufficiency* is a judgment call.

## Scope

The gate presumes **quote-style** citations. If your pipeline cites by document
id or character offsets, resolve the span to its source text first, then gate
that text. Contributions wiring this into specific frameworks (Haystack,
LlamaIndex, LangChain, Cohere, Qwen-Agent, …) are welcome.

## AI contributors

This project is built by a human + AI team, and the git log says so: Claude
writes most of the code, Codex and Grok review it, Gemini feeds the research.
Each is credited on a commit **only if its output changed that commit's
content** — no decorative credits. Lab-wide policy, one source for every repo:
[AI-CONTRIBUTORS.md](https://github.com/Palo-Alto-AI-Research-Lab/.github/blob/main/AI-CONTRIBUTORS.md).

## License

MIT © Palo Alto AI Research Lab

## Contact

Questions, war stories, or you want to run this on your own fleet:

- 💬 WhatsApp: **+1 341 222 9178**
- 🐦 X: [@Tony_Stef_](https://x.com/Tony_Stef_)
- 📣 Telegram: [@ClawRus](https://t.me/ClawRus) (RU) · [@ClawEng](https://t.me/ClawEng) (EN)
- 🌐 [palo-alto.ai](https://palo-alto.ai) · [Palo Alto AI Research Lab](https://github.com/Palo-Alto-AI-Research-Lab)

## Contributors welcome — and there is a queue

The queue is visible: **[verbatim-citation-gate — roadmap](https://github.com/users/Palo-Alto-AI-Research-Lab/projects/1)** — Now (an open PR exists), Next (scoped, free to take), Later (deferred, with the reason on the card), Shipped. Shipped is empty on purpose: there is no tagged release yet, and that is [issue #10](https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate/issues/10).

Issues labelled [`accepted`](https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate/issues?q=is%3Aissue+is%3Aopen+label%3Aaccepted)
are scoped, free to take, and nobody is on them. Comment **"claiming this"** — no permission needed —
and it is yours for 7 days. New here? Start with
[`good first issue`](https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

**You keep the copyright to your code.** No CLA, no assignment, ever — your contribution goes in
under this repo's existing license, the same terms as ours. We answer every issue and PR within
48 hours, including "no, and here is why"; our silence is our bug, so ping the thread.

Full deal: [CONTRIBUTING.md](https://github.com/Palo-Alto-AI-Research-Lab/.github/blob/main/CONTRIBUTING.md)
