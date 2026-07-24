"""Offline tests. The gate is fully deterministic and needs no model or network.

The judge is exercised through a fake ``llm_call`` so the two-stage control
flow — and the fail-closed behavior — is covered without an API key.
"""

from verbatim_citation_gate import (
    Verdict,
    audit_citation,
    judge_support,
    normalize,
    quote_gate,
)

# Three tiny documents. The frankenquote trap stitches real fragments from
# RESTATIN across a sentence boundary that was never written.
DOCS = {
    "veltranib-rct": (
        "In the veltranib randomized controlled trial, fasting plasma glucose "
        "fell by 28 mg/dL in the veltranib arm. Body weight was unchanged in both arms."
    ),
    "restatin-meta": (
        "Restatin reduced the relative risk of non-fatal myocardial infarction by 25%. "
        "In the low-risk subgroup the reduction was not statistically significant."
    ),
    "coffee-cohort": (
        "Higher coffee consumption was associated with lower all-cause mortality "
        "in this observational cohort."
    ),
}


# --- Stage 1: the verbatim gate --------------------------------------------

def test_real_quote_is_found():
    assert quote_gate("Body weight was unchanged in both arms.", "veltranib-rct", DOCS) == "found"


def test_typography_and_case_insensitive():
    # smart quotes, em dash, odd casing, extra whitespace all normalize away
    assert quote_gate("  body   WEIGHT was unchanged in both arms.  ", "veltranib-rct", DOCS) == "found"


def test_frankenquote_is_not_found():
    # every word is real, but this sentence was never written in restatin-meta
    franken = "Restatin reduced the relative risk of non-fatal myocardial infarction by 25% in the low-risk subgroup."
    assert quote_gate(franken, "restatin-meta", DOCS) == "not_found"


def test_fabrication_is_not_found():
    assert quote_gate("Fasting plasma glucose fell by 28 mg/dL in the veltranib arm.", "restatin-meta", DOCS) == "misattributed"
    assert quote_gate("Veltranib cured the disease in every patient.", "veltranib-rct", DOCS) == "not_found"


def test_misattributed_real_quote_from_wrong_doc():
    q = "Body weight was unchanged in both arms."
    assert quote_gate(q, "restatin-meta", DOCS) == "misattributed"


def test_empty_quote_fails_closed():
    assert quote_gate("", "veltranib-rct", DOCS) == "not_found"
    assert quote_gate("   ", "veltranib-rct", DOCS) == "not_found"


def test_unknown_doc_id_fails_closed_not_raises():
    # a real quote attributed to a doc id we do not have -> misattributed, no KeyError
    assert quote_gate("Body weight was unchanged in both arms.", "does-not-exist", DOCS) == "misattributed"
    # a fabricated quote attributed to an unknown doc -> not_found, no KeyError
    assert quote_gate("nothing like this anywhere", "does-not-exist", DOCS) == "not_found"


def test_normalize_preserves_numbers_and_percent():
    assert "25%" in normalize("...by 25% in...")
    assert "28" in normalize("fell by 28 mg/dL")


# --- Stage 2 + the two-stage audit -----------------------------------------

def _fake_supports(system, user):
    return '{"reasoning": "matches", "verdict": "supports", "confidence": 0.9}'


def _fake_garbage(system, user):
    return "the model rambled and returned no json at all"


def _fake_raises(system, user):
    raise RuntimeError("model exploded")


def test_audit_fabrication_never_calls_judge():
    calls = []

    def spy(system, user):
        calls.append(1)
        return _fake_supports(system, user)

    # a fabricated quote should be rejected by the gate for zero model calls
    result = audit_citation("some claim", "restatin-meta", "totally made up quote", DOCS, llm_call=spy)
    assert result == "not_found"
    assert calls == []  # judge was never reached


def test_audit_found_quote_reaches_judge():
    result = audit_citation(
        "Body weight did not change.", "veltranib-rct",
        "Body weight was unchanged in both arms.", DOCS, llm_call=_fake_supports,
    )
    assert result == "supports"


def test_audit_without_llm_returns_found():
    result = audit_citation(
        "Body weight did not change.", "veltranib-rct",
        "Body weight was unchanged in both arms.", DOCS, llm_call=None,
    )
    assert result == "found"


def test_judge_fails_closed_on_garbage():
    v = judge_support("c", "q", "s", _fake_garbage)
    assert isinstance(v, Verdict)
    assert v.verdict == "unrelated"
    assert v.confidence == 0.0


def test_judge_fails_closed_when_call_raises():
    v = judge_support("c", "q", "s", _fake_raises)
    assert v.verdict == "unrelated"
    assert v.confidence == 0.0


def test_judge_rejects_out_of_vocabulary_verdict():
    def sneaky(system, user):
        return '{"reasoning": "x", "verdict": "definitely_supports", "confidence": 1.0}'

    v = judge_support("c", "q", "s", sneaky)
    assert v.verdict == "unrelated"  # unknown label -> fail closed
