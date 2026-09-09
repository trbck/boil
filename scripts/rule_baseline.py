#!/usr/bin/env python3
"""Guard the one contract the whole skill rests on: a rule ID means one thing forever.

Every compliance manifest, every citation in a past answer, and every note that
quotes `ASSP-05-R7` is a pointer into this corpus. Nothing about those pointers
is self-validating — a re-distillation that renumbers a chapter, or an edit that
rewrites a rule while keeping its number, leaves every one of them resolving
cleanly to the wrong thing. That failure is silent by construction, which is why
it needs a baseline rather than a reviewer.

Two checks, with deliberately different severities:

  * An ID in the baseline that no longer exists is BREAKING. Something was
    deleted or renumbered, and citations to it are now dangling.
  * A `primary` (book) rule whose text changed under a stable ID is BREAKING.
    The number kept its promise and the words did not, which is worse than a
    dangling pointer because it still looks right.
  * A `derived` (notes) rule whose text changed is fine and expected — research
    notes get corrected. Only their existence is guarded.

New IDs are always fine. The corpus is meant to grow.

Usage:
    python3 scripts/rule_baseline.py            # check; non-zero exit on breakage
    python3 scripts/rule_baseline.py --update   # accept the current corpus as the baseline
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

BASELINE = os.path.join(K.ROOT, "tests", "rule-ids.baseline")

HEADER = [
    "# advisor rule-ID baseline.",
    "#",
    "# Every ID listed here must still resolve, and every `primary` rule must still",
    "# say what it said, because citations elsewhere point at these numbers.",
    "# Lines are `ID` or `ID<TAB>text-hash`; a bare ID is existence-checked only.",
    "#",
    "# Regenerate deliberately, never to make a failure go away:",
    "#     python3 scripts/rule_baseline.py --update",
]


def text_hash(text):
    return hashlib.sha1(re.sub(r"\s+", " ", (text or "").strip())
                        .encode("utf-8")).hexdigest()[:8]


def current_rules():
    """Every rule in every generated domain index, by ID."""
    rules = {}
    for path in sorted(glob.glob(os.path.join(K.ROOT, "generated", "*", "index.json"))):
        for rule in K.load_json(path).get("rules", []):
            rules[rule["id"]] = rule
    return rules


def load_baseline(path=BASELINE):
    """Both formats: `ID` alone, or `ID<TAB>hash`. Missing hash means 'do not check'."""
    entries = {}
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rule_id, _, digest = line.partition("\t")
            entries[rule_id.strip()] = digest.strip() or None
    return entries


def write_baseline(rules, path=BASELINE):
    lines = list(HEADER) + [""]
    for rule_id in sorted(rules):
        rule = rules[rule_id]
        # Only book rules get a content hash. A note is expected to be corrected;
        # holding it to a hash would train everyone to run --update reflexively,
        # and a baseline nobody trusts guards nothing.
        if rule.get("authority") == "primary":
            lines.append("%s\t%s" % (rule_id, text_hash(rule.get("text"))))
        else:
            lines.append(rule_id)
    K.write_text(path, "\n".join(lines) + "\n")
    return len(rules)


def check(path=BASELINE):
    """Returns (breaking, added) — breaking is a list of human-readable strings."""
    baseline, rules = load_baseline(path), current_rules()
    breaking = []
    for rule_id, digest in sorted(baseline.items()):
        rule = rules.get(rule_id)
        if rule is None:
            breaking.append("%s no longer exists — every citation of it now dangles"
                            % rule_id)
            continue
        if digest and rule.get("authority") == "primary":
            now = text_hash(rule.get("text"))
            if now != digest:
                breaking.append(
                    "%s changed text under a stable ID (%s → %s) — past citations still "
                    "resolve, but to different words: %r"
                    % (rule_id, digest, now, (rule.get("text") or "")[:80]))
    return breaking, sorted(set(rules) - set(baseline))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true",
                    help="rewrite the baseline from the current corpus")
    ap.add_argument("--baseline", default=BASELINE)
    args = ap.parse_args()

    if args.update:
        n = write_baseline(current_rules(), args.baseline)
        print("baseline updated: %d rules" % n)
        return 0

    breaking, added = check(args.baseline)
    for problem in breaking:
        print("  ✗ %s" % problem)
    if added:
        print("  + %d new rule(s) since the baseline: %s%s"
              % (len(added), ", ".join(added[:6]), " …" if len(added) > 6 else ""))
    print()
    print("%d breaking change(s), %d addition(s)" % (len(breaking), len(added)))
    if breaking:
        print("If a renumbering was deliberate, run --update — and fix the citations "
              "that pointed at the old IDs first.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
