#!/usr/bin/env python3
"""Retrieval quality eval for scripts/lookup.py's search path.

Runs every question in tests/retrieval-questions.json through
`lookup.run_search()` — the exact scoring/ranking `--search` uses — and
reports hit@1, hit@3 and MRR, plus a per-question rank table.

A question counts as a hit at rank R if the result at rank R's identifier
is in the question's `expect` list. Only the top `--limit` results are
considered; an expected id that appears beyond that is scored as a miss
(rank None, contributes 0 to MRR).

Stdlib only.

Examples:
    python3 scripts/eval_retrieval.py
    python3 scripts/eval_retrieval.py --scoped     # one domain per question
    python3 scripts/eval_retrieval.py --limit 20
    python3 scripts/eval_retrieval.py --json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lookup as L  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS_PATH = os.path.join(ROOT, "tests", "retrieval-questions.json")


def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["questions"]


def rank_of(results, expect, limit):
    """1-indexed rank of the first result (within the top `limit`) whose
    identifier is in `expect`; None if no such result appears in range.

    A single-domain index emits bare identifiers (`ATLB-01`), a merged one
    qualifies them (`decisions:ATLB-01`), so accept either spelling.
    """
    expect_set = set(expect) | {e.split(":", 1)[1] for e in expect if ":" in e}
    for i, (_score, _typ, ident, _text, _ctx) in enumerate(results[:limit], start=1):
        if ident in expect_set:
            return i
    return None


def evaluate(idx, questions, limit, scoped=False):
    """`scoped` reproduces the retrieval SKILL.md actually prescribes: pick the
    domain first, then search inside it. The gap between the two runs is the cost
    of searching every domain at once."""
    cache = {}

    def index_for(q):
        if not scoped:
            return idx
        dom = q["expect"][0].split(":", 1)[0]
        if dom not in cache:
            cache[dom] = L.load_indexes(dom)
        return cache[dom]

    rows = []
    for q in questions:
        results = L.run_search(index_for(q), q["q"], pack_filter=None, kind="all")
        rank = rank_of(results, q["expect"], limit)
        top = results[0][2] if results else None
        rows.append({
            "q": q["q"],
            "expect": q["expect"],
            "why": q.get("why", ""),
            "rank": rank,
            "top": top,
        })
    return rows


def summarize(rows):
    n = len(rows)
    hit1 = sum(1 for r in rows if r["rank"] == 1)
    hit3 = sum(1 for r in rows if r["rank"] is not None and r["rank"] <= 3)
    mrr = sum(1.0 / r["rank"] for r in rows if r["rank"]) / n if n else 0.0
    return {
        "n": n,
        "hit@1": hit1 / n if n else 0.0,
        "hit@1_count": hit1,
        "hit@3": hit3 / n if n else 0.0,
        "hit@3_count": hit3,
        "mrr": mrr,
    }


def print_table(rows):
    print("%-4s  %-58s  %-24s  %s" % ("RANK", "QUESTION", "TOP RESULT", "EXPECTED"))
    print("-" * 120)
    for r in rows:
        rank = str(r["rank"]) if r["rank"] is not None else "miss"
        q = r["q"] if len(r["q"]) <= 58 else r["q"][:55] + "..."
        top = r["top"] or "(none)"
        expect = ",".join(r["expect"])
        marker = "OK " if r["rank"] == 1 else ("~  " if r["rank"] else "X  ")
        print("%-4s %-58s  %-24s  %s  %s" % (rank, q, top[:24], marker, expect))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=10,
                    help="only consider the top N search results per question (default 10)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a table")
    ap.add_argument("--questions", default=QUESTIONS_PATH, help="path to the questions file")
    ap.add_argument("--scoped", action="store_true",
                    help="search only the question's own domain, as SKILL.md prescribes")
    args = ap.parse_args()

    questions = load_questions(args.questions)
    idx = L.load_indexes(None)
    rows = evaluate(idx, questions, args.limit, scoped=args.scoped)
    summary = summarize(rows)

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, indent=2))
        return

    print_table(rows)
    print()
    print("n=%d  hit@1=%.3f (%d/%d)  hit@3=%.3f (%d/%d)  MRR=%.3f"
          % (summary["n"],
             summary["hit@1"], summary["hit@1_count"], summary["n"],
             summary["hit@3"], summary["hit@3_count"], summary["n"],
             summary["mrr"]))


if __name__ == "__main__":
    main()
