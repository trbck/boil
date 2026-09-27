#!/usr/bin/env python3
"""Propose cross-pack rule pairs worth a registry entry — conflict or convergence.

A new domain starts with an empty conflict registry, which silently degrades the
advisor's most valuable behaviour: surfacing that two sources disagree instead of
blending them. This narrows thousands of rule pairs to a reviewable shortlist.

It finds *topical adjacency across packs*, then splits the shortlist by polarity:
opposed pairs are conflict candidates, aligned pairs are convergence candidates.
Both belong in the registry — where two independent books agree, the conclusion is
better supported than either alone, and saying so is worth as much as flagging a
disagreement.

It is a candidate generator, not a detector. Deciding two rules genuinely disagree
(or genuinely agree) needs reading both in context, so output is a review queue and
nothing is written to conflicts.md automatically. Expect false positives; that is
acceptable for a list this short, and the alternative is reading thousands of pairs
by hand.

Signals combined:
  - different packs (a book rarely contradicts itself)
  - at least one shared topic (they must be about the same thing)
  - shared subject vocabulary (lexical overlap on content terms)
  - opposed polarity (one prohibits where the other prescribes)

Usage:
    python3 scripts/suggest_conflicts.py --domain trading [--limit 20] [--out PATH]
"""

import argparse
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

PROHIBIT = re.compile(r"\b(never|avoid|do not|don't|refuse|reject|resist|stop|"
                      r"cannot|must not|no longer|not a|is not|rarely)\b", re.I)
PRESCRIBE = re.compile(r"\b(always|must|should|prefer|use|adopt|favou?r|ensure|"
                       r"require|treat|make|apply|keep|report)\b", re.I)

STOP = set("""a an the and or but if then than that this these those of to in on at by for with as
is are be was were been being it its it's their there here what when where which while who whom how
why do does did not no nor so such very can could would should may might must will just only also
you your we our they them he she from into over under out up down off again more most other same
each few both all any some own because therefore however instead rather still yet even much many
rule rules chapter always never avoid prefer use using used make makes made get gets
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z\-]{2,}")


def content_terms(text):
    return {w for w in TOKEN_RE.findall(K.strip_md(text).lower()) if w not in STOP}


def polarity(text):
    """+1 prescriptive, -1 prohibitive, 0 neither/both."""
    neg = len(PROHIBIT.findall(text))
    pos = len(PRESCRIBE.findall(text))
    if neg and neg >= pos:
        return -1
    if pos and pos > neg:
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--min-overlap", type=int, default=2,
                    help="shared content words required before a pair is considered")
    ap.add_argument("--out")
    args = ap.parse_args()

    domains = K.load_domains(args.domain)
    if not domains:
        sys.exit("unknown domain %r" % args.domain)
    domain = domains[0]

    index_path = os.path.join(domain["generated"], "index.json")
    if not os.path.exists(index_path):
        sys.exit("no index for %s — run: python3 scripts/build_index.py" % domain["id"])
    rules = K.load_json(index_path)["rules"]

    enriched = []
    for rule in rules:
        enriched.append({
            "id": rule["id"], "pack": rule["pack"], "parent": rule["parent"],
            "text": rule["text"], "topics": set(rule["topics"]),
            "terms": content_terms(rule["text"]), "pol": polarity(rule["text"]),
        })

    candidates, compared = [], 0
    for i, a in enumerate(enriched):
        for b in enriched[i + 1:]:
            if a["pack"] == b["pack"] or not (a["topics"] & b["topics"]):
                continue
            compared += 1
            shared = a["terms"] & b["terms"]
            if len(shared) < args.min_overlap:
                continue
            opposed = a["pol"] * b["pol"] < 0
            union = len(a["terms"] | b["terms"]) or 1
            score = (len(shared) / union) * (2.0 if opposed else 1.0)
            candidates.append((score, opposed, sorted(shared), a, b))

    candidates.sort(key=lambda c: (-c[0], c[3]["id"]))
    top = candidates[:args.limit]

    n_opp = sum(1 for c in top if c[1])
    out = ["# Registry candidates — %s" % domain.get("title", domain["id"]), "",
           "Machine-proposed, **not confirmed**. %d cross-pack pairs shared a topic; %d cleared the "
           "overlap threshold; the %d strongest are below (%d opposed, %d aligned)."
           % (compared, len(candidates), len(top), n_opp, len(top) - n_opp), "",
           "- **opposed** — one rule prohibits where the other prescribes. Candidate *conflict*: "
           "write it up with a resolution saying *what determines which applies*. A resolution that "
           "merely picks a winner is not useful, because the loser was written by someone who had "
           "a reason.",
           "- **aligned** — both point the same way from different books. Candidate *convergence*: "
           "worth recording, because agreement reached by two independent routes is better "
           "supported than either source alone.", "",
           "Promote real ones into `domains/%s/conflicts.md`; discard the rest." % domain["id"], ""]

    for score, opposed, shared, a, b in top:
        out.append("### %s ⟷ %s · **%s**"
                   % (a["id"], b["id"], "opposed → conflict?" if opposed else "aligned → convergence?"))
        out.append("")
        out.append("- `%s` (%s) — %s" % (a["id"], a["pack"], K.strip_md(a["text"])[:180]))
        out.append("- `%s` (%s) — %s" % (b["id"], b["pack"], K.strip_md(b["text"])[:180]))
        out.append("")
        out.append("<sub>score %.2f · shared: %s</sub>" % (score, ", ".join(shared[:8])))
        out.append("")

    text = "\n".join(out) + "\n"
    out_path = args.out or os.path.join(domain["root"], "registry.candidates.md")
    K.write_text(out_path, text)

    print("%d cross-pack pairs compared · %d above threshold · %d shortlisted"
          % (compared, len(candidates), len(top)))
    print("shortlist: %d opposed (conflict candidates) · %d aligned (convergence candidates)"
          % (sum(1 for c in top if c[1]), sum(1 for c in top if not c[1])))
    print()
    for score, opposed, shared, a, b in top[:8]:
        print("%.2f %-14s %-14s %s" % (score, a["id"], b["id"],
                                       "opposed" if opposed else "aligned"))
    print()
    print("written: %s" % os.path.relpath(out_path, K.ROOT))
    print("Review and promote real ones into conflicts.md — nothing is written there for you.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
