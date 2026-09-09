#!/usr/bin/env python3
"""Resolve every citation in a piece of advisor output. Fabrications are the point.

The skill's central promise is that a claim carries an ID you can look up. That
promise is only worth something if somebody looks. A fabricated ID is a worse
defect than a missing one — it survives review, because diligence is exactly what
it imitates — and it is also the single most mechanically checkable failure this
skill has: an ID either resolves against the index or it does not.

So this reads an answer, a spec, a compliance manifest, or a source file, pulls
out everything ID-shaped that starts with a known pack prefix, and says which
ones exist.

    python3 scripts/check_citations.py answer.md
    claude -p "..." | python3 scripts/check_citations.py
    python3 scripts/check_citations.py --json answer.md

Exit status is 1 if anything was fabricated, so it can gate a test or a hook.

Only prefixes this corpus actually defines are considered, so ordinary prose
("COVID-19", "GPT-4") is never mistaken for a citation. The cost of that choice
is that an ID invented under a *made-up* prefix reads as ordinary text; it is
`--strict` that catches those.
"""

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402


def load_universe():
    """Every citable identifier: rules, chapters and sections, plus the prefixes."""
    rules, chapters, sections, prefixes = set(), set(), set(), set()
    for path in sorted(glob.glob(os.path.join(K.ROOT, "generated", "*", "index.json"))):
        index = K.load_json(path)
        for pack in index.get("packs", []):
            if pack.get("prefix"):
                prefixes.add(pack["prefix"])
        for rule in index.get("rules", []):
            rules.add(rule["id"])
        for chapter in index.get("chapters", []):
            chapters.add(chapter["id"])
            for section in chapter.get("sections", []):
                sections.add("%s§%s" % (chapter["id"], section["key"]))
    return rules, chapters, sections, prefixes


def find_citations(text, prefixes, strict=False):
    """Candidate identifiers in document order, de-duplicated.

    A citation is `PREFIX-` followed by the id body: digits or a slug, optionally
    a section marker, optionally a rule suffix. NOTE ids carry a whole slug, so
    the body cannot be assumed numeric.
    """
    if strict:
        # Any all-caps token that looks like an identifier, whoever minted it.
        pattern = r"\b([A-Z][A-Z0-9]{2,5})-((?:[A-Za-z0-9]+-)*[A-Za-z0-9]+)(§\d+)?\b"
    else:
        pattern = (r"\b(%s)-((?:[A-Za-z0-9]+-)*[A-Za-z0-9]+)(§\d+)?\b"
                   % "|".join(sorted(map(re.escape, prefixes))))
    seen, out = set(), []
    for match in re.finditer(pattern, text):
        ident = match.group(0)
        if ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def classify(idents, rules, chapters, sections):
    resolved, fabricated = [], []
    for ident in idents:
        kind = ("rule" if ident in rules else
                "chapter" if ident in chapters else
                "section" if ident in sections else None)
        (resolved if kind else fabricated).append((ident, kind))
    return resolved, fabricated


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="file to check; omit to read stdin")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--strict", action="store_true",
                    help="also flag identifiers minted under prefixes this corpus "
                         "does not define — an invented pack is still an invented cite")
    ap.add_argument("--quiet", action="store_true", help="summary line only")
    ap.add_argument("--require-citations", action="store_true",
                    help="fail when nothing was cited at all — for measuring whether "
                         "an agent retrieved or answered from recall")
    args = ap.parse_args()

    text = K.read_text(args.path) if args.path else sys.stdin.read()
    rules, chapters, sections, prefixes = load_universe()
    idents = find_citations(text, prefixes, strict=args.strict)
    resolved, fabricated = classify(idents, rules, chapters, sections)

    total = len(idents)
    rate = (len(fabricated) / total) if total else 0.0
    summary = {
        "cited": total,
        "resolved": len(resolved),
        "fabricated": len(fabricated),
        "fabrication_rate": round(rate, 3),
        "fabricated_ids": [i for i, _ in fabricated],
    }

    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        if not args.quiet:
            for ident, kind in resolved:
                print("  ok  %-12s %s" % (kind, ident))
            for ident, _ in fabricated:
                print("  ✗   %-12s %s — does not resolve" % ("unknown", ident))
            print()
        if total == 0:
            print("no citations found — an ungrounded answer is its own finding")
        else:
            print("%d cited · %d resolved · %d fabricated (%.0f%%)"
                  % (total, len(resolved), len(fabricated), rate * 100))
    if fabricated:
        return 1
    return 1 if (args.require_citations and total == 0) else 0


if __name__ == "__main__":
    sys.exit(main())
