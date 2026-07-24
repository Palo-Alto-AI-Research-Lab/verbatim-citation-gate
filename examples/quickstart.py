"""Quickstart: audit a batch of cited claims.

The gate half runs with no dependencies and no API key. The judge half takes
any callable ``llm_call(system, user) -> str`` — the ``_demo_llm`` below is a
stand-in so this file runs offline; swap it for your real model in one line.
"""

from verbatim_citation_gate import audit_citation

DOCS = {
    "veltranib-rct": (
        "In the veltranib randomized controlled trial, fasting plasma glucose "
        "fell by 28 mg/dL in the veltranib arm. Body weight was unchanged in both arms."
    ),
    "restatin-meta": (
        "Restatin reduced the relative risk of non-fatal myocardial infarction by 25%. "
        "In the low-risk subgroup the reduction was not statistically significant."
    ),
}

# --- your model goes here ---------------------------------------------------
# Anthropic:  lambda sys, usr: client.messages.create(model="claude-...",
#                 system=sys, max_tokens=1024,
#                 messages=[{"role": "user", "content": usr}]).content[0].text
# OpenAI:     lambda sys, usr: client.chat.completions.create(model="gpt-...",
#                 messages=[{"role": "system", "content": sys},
#                           {"role": "user", "content": usr}]).choices[0].message.content
# Cohere / Gemini / Mistral / local Qwen: same shape — return the model's text.


def _demo_llm(system: str, user: str) -> str:
    # Offline stand-in: pretend the model judged the one real, on-point quote as supporting.
    return '{"reasoning": "demo", "verdict": "supports", "confidence": 0.8}'


CITATIONS = [
    # (claim, doc_id, quote)
    ("Body weight did not change on veltranib.", "veltranib-rct", "Body weight was unchanged in both arms."),
    # fabricated — the gate rejects this for zero tokens, the model is never called
    ("Veltranib caused rapid weight loss.", "veltranib-rct", "Veltranib produced dramatic weight loss."),
    # frankenquote — real words, sentence never written — also rejected for free
    ("Restatin cut heart attacks even in low-risk patients.", "restatin-meta",
     "Restatin reduced the relative risk of non-fatal myocardial infarction by 25% in the low-risk subgroup."),
]

if __name__ == "__main__":
    for claim, doc_id, quote in CITATIONS:
        verdict = audit_citation(claim, doc_id, quote, DOCS, llm_call=_demo_llm)
        print(f"{verdict:>14}  |  {claim}")
