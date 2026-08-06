"""Fetch a public corpus of arXiv abstracts to benchmark the gate against.

Deliberately NOT our own docs: benchmarking a matcher on the text it was
written against measures the author's memory, not the matcher.

Writes bench/corpus.json: {doc_id: abstract_text}.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
OUT = pathlib.Path(__file__).parent / "corpus.json"

# Fixed queries + fixed order => same corpus on every run (no Date/random).
CATEGORIES = ["cs.CL", "cs.IR", "cs.SE"]
PER_CATEGORY = 100


def fetch(category: str, count: int) -> list[tuple[str, str]]:
    url = (
        f"{API}?search_query=cat:{category}"
        f"&start=0&max_results={count}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "verbatim-citation-gate-bench"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        root = ET.fromstring(resp.read())

    out: list[tuple[str, str]] = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id") or ""
        summary = entry.findtext(f"{ATOM}summary") or ""
        # arXiv wraps abstracts at ~80 cols; unwrap to natural prose so that
        # sentence splitting is not an artifact of the feed's line breaks.
        text = " ".join(summary.split())
        doc_id = raw_id.rsplit("/", 1)[-1]
        if doc_id and len(text) > 400:
            out.append((doc_id, text))
    return out


def main() -> int:
    docs: dict[str, str] = {}
    for cat in CATEGORIES:
        got = fetch(cat, PER_CATEGORY)
        for doc_id, text in got:
            docs[doc_id] = text
        print(f"{cat}: {len(got)} abstracts", file=sys.stderr)
        time.sleep(3)  # arXiv asks for >=3s between requests

    OUT.write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    chars = sum(len(v) for v in docs.values())
    print(f"wrote {OUT} — {len(docs)} docs, {chars} chars", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
