#!/usr/bin/env python3
"""Check every pack against the contracts in FORMAT.md.

Reports drift; never modifies anything. Exit code is non-zero when a hard
requirement fails, so this can gate a commit hook or CI.

Usage:
    python3 scripts/validate_pack.py [--pack ID] [--strict]
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

# Chapters this thin are usually a truncated paste rather than a deliberate summary.
MIN_RULES_WARN = 3
MIN_SECTIONS_WARN = 2


def collect(pack):
    base = pack["abs_path"]
    if not os.path.isdir(base):
        return []
    if pack.get("recursive"):
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            out += [os.path.join(dirpath, f) for f in filenames
                    if f.endswith(".md") and not f.startswith("_")]
        return sorted(out)
    return sorted(os.path.join(base, f) for f in os.listdir(base)
                  if f.endswith(".md") and not f.startswith("_"))


def check_book(pack, files):
    errors, warnings = [], []
    seen = {}
    for path in files:
        name = os.path.basename(path)
        rec = K.parse_chapter(path, pack["prefix"])
        for problem in rec["problems"]:
            errors.append("%s: %s" % (name, problem))
        if rec["number"] is not None:
            if rec["number"] in seen:
                errors.append("%s: duplicate chapter number %d (also %s)"
                              % (name, rec["number"], seen[rec["number"]]))
            seen[rec["number"]] = name
            if not name[:2].isdigit():
                warnings.append("%s: filename should start with the zero-padded chapter number"
                                % name)
            elif int(name[:2]) != rec["number"]:
                warnings.append("%s: filename number != H1 chapter number (%d)"
                                % (name, rec["number"]))
        if len(rec["rules"]) < MIN_RULES_WARN and not rec["problems"]:
            warnings.append("%s: only %d rules — thin for a chapter"
                            % (name, len(rec["rules"])))
        if len(rec["sections"]) < MIN_SECTIONS_WARN and not rec["problems"]:
            warnings.append("%s: only %d sections" % (name, len(rec["sections"])))
        # Absent **Source:** is tolerable: build_index synthesises a citation from
        # pack metadata. Only flag it when the pack cannot supply the fallback.
        if not rec.get("source") and not pack.get("author"):
            warnings.append("%s: no '**Source:**' line and pack declares no author — "
                            "citations will be vague" % name)

    if seen:
        lo, hi = min(seen), max(seen)
        missing = [n for n in range(lo, hi + 1) if n not in seen]
        if missing:
            warnings.append("chapter number gap(s): %s"
                            % ", ".join(str(m) for m in missing))
    return errors, warnings


def check_notes(pack, files):
    errors, warnings = [], []
    for path in files:
        name = os.path.relpath(path, K.ROOT)
        rec = K.parse_note(path, pack["prefix"], root=K.ROOT)
        for problem in rec["problems"]:
            warnings.append("%s: %s" % (name, problem))
        if rec.get("authority") not in ("derived", "primary"):
            errors.append("%s: authority must be 'derived' or 'primary', got %r"
                          % (name, rec.get("authority")))
        if not rec["sections"] and not rec["rules"]:
            warnings.append("%s: no sections and no findings — nothing retrievable" % name)
    return errors, warnings


def _git_tracked(path):
    """True if git currently tracks this path. Used to catch licence leaks."""
    try:
        out = subprocess.check_output(["git", "ls-files", "--error-unmatch", path],
                                      cwd=K.ROOT, stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except Exception:
        return False


def check_engine(pack):
    errors, warnings = [], []
    base = pack["abs_path"]
    sources = pack.get("sources", {})
    if not sources:
        errors.append("engine pack declares no 'sources'")
    for role, name in sources.items():
        path = os.path.join(base, name)
        if not os.path.exists(path):
            errors.append("missing %s source: %s (licensed files are gitignored by "
                          "default — see README)" % (role, name))
        elif os.path.getsize(path) == 0:
            errors.append("%s source is empty: %s" % (role, name))
        elif pack.get("license") == "proprietary" and _git_tracked(path):
            # A directory move silently un-ignores path-shaped rules, so assert
            # the outcome rather than trusting .gitignore to still match.
            errors.append("LICENCE LEAK: %s is proprietary and TRACKED BY GIT (%s). "
                          "Fix .gitignore and `git rm --cached` it before pushing."
                          % (name, os.path.relpath(path, K.ROOT)))
    return errors, warnings


RULE_REF_RE = re.compile(r'"([A-Z][A-Z0-9]*-\d+-R\d+)"')


def check_domain_config(domain):
    """Gates and checklists may cite rule IDs; every one must resolve.

    This is the mechanical half of "never invent an ID" -- config is written by
    hand, so without this a typo ships as a confident-looking citation.
    """
    errors, warnings = [], []
    index_path = os.path.join(domain["generated"], "index.json")
    if not os.path.exists(index_path):
        warnings.append("no built index yet — cannot verify rule references")
        return errors, warnings
    known = {r["id"] for r in K.load_json(index_path).get("rules", [])}
    for key in ("gates", "checklists"):
        cfg = K.load_optional(domain, key)
        if not cfg:
            continue
        for rid in sorted(set(RULE_REF_RE.findall(json.dumps(cfg)))):
            if rid not in known:
                errors.append("%s.json cites unknown rule %s" % (key, rid))
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain")
    ap.add_argument("--pack")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    domains = K.load_domains(args.domain)
    if not domains:
        sys.exit("no domains found")
    total_err = total_warn = 0
    packs = []
    for dom in domains:
        packs += K.load_domain_packs(dom)
        errors, warnings = check_domain_config(dom)
        if errors or warnings:
            print("%-10s %-8s %-7s %3s          %s"
                  % (dom["id"], "config", "-", "-", "FAIL" if errors else "ok"))
            for err in errors:
                print("   ✗ %s" % err)
            for warn in warnings:
                print("   ! %s" % warn)
            total_err += len(errors)
            total_warn += len(warnings)

    for pack in packs:
        if args.pack and pack["id"] != args.pack:
            continue
        files = collect(pack) if pack["kind"] != "engine" else []
        if pack["kind"] == "book":
            errors, warnings = check_book(pack, files)
        elif pack["kind"] == "notes":
            errors, warnings = check_notes(pack, files)
        elif pack["kind"] == "engine":
            errors, warnings = check_engine(pack)
        else:
            errors, warnings = ["unknown pack kind %r" % pack["kind"]], []

        status = "ok" if not errors else "FAIL"
        count = len(files) if pack["kind"] != "engine" else len(pack.get("sources", {}))
        print("%-10s %-8s %-7s %3d file(s)  %s"
              % (pack["domain"], pack["id"], pack["kind"], count, status))
        for err in errors:
            print("   ✗ %s" % err)
        for warn in warnings:
            print("   ! %s" % warn)
        total_err += len(errors)
        total_warn += len(warnings)

    print()
    print("%d error(s), %d warning(s)" % (total_err, total_warn))
    if total_err or (args.strict and total_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
