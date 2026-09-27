#!/usr/bin/env python3
"""boil advise — the advisor corpus (advisor/) as a boil subcommand.

  lookup|check|ingest|build ARGS…   forward verbatim to advisor/scripts/<same>.py (same flags, same exit)
  retire ID --reason R [--by B]      tombstone a rule: hidden from search, still resolvable
  unretire ID                        undo it
  decide --question Q [--project .]  print a decision packet: question, goal excerpt, candidate rules
  record --question Q --verdict V    accept a cited verdict into .boil/decisions.md, or reject it
  sweep [--project .]                apply the vetoes written into .boil/decisions.md

Exit codes: 0 ok · 2 usage / unknown id · 3 rejected or advisor unavailable (the caller escalates
to the human exactly as it would have without the advisor).

BOIL_ADVISOR_ROOT overrides the corpus location (tests point it at a copy).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ADVISOR = Path(os.environ.get("BOIL_ADVISOR_ROOT") or SKILL_ROOT / "advisor")
FORWARD = {"lookup": "lookup.py", "check": "check_citations.py",
           "ingest": "ingest.py", "build": "build_index.py"}
EXIT_OK, EXIT_USAGE, EXIT_REJECT = 0, 2, 3


def _k():
    """advisor's ka_common, imported from the corpus ADVISOR points at (its ROOT follows its file)."""
    path = str(ADVISOR / "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)
    import ka_common as K  # noqa: E402
    return K


def _index_rules(K) -> dict[str, str]:
    """Rule id (upper-case) → domain, across every built index, retired rules included."""
    out = {}
    for dom in K.load_domains():
        path = Path(dom["generated"]) / "index.json"
        if path.exists():
            for r in K.load_json(str(path)).get("rules", []):
                out[r["id"].upper()] = dom["id"]
    return out


def _stored(K, dom: str) -> dict:
    """retired.json as stored: load_retired adds a `domain` key that is not part of the file."""
    return {rid: {k: v for k, v in meta.items() if k != "domain"}
            for rid, meta in K.load_retired(dom).items()}


def cmd_retire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    if not dom:
        print(f"boil advise: unknown rule id {args.id}", file=sys.stderr)
        return EXIT_USAGE
    data = _stored(K, dom)
    data[rid] = {"reason": args.reason, "date": dt.date.today().isoformat(), "by": args.by}
    K.save_retired(dom, data)
    print(f"retired {rid} ({dom}): {args.reason}")
    return EXIT_OK


def cmd_unretire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    data = _stored(K, dom) if dom else {}
    if rid not in data:
        print(f"boil advise: {args.id} is not retired", file=sys.stderr)
        return EXIT_USAGE
    del data[rid]
    K.save_retired(dom, data)
    print(f"unretired {rid}")
    return EXIT_OK


def main(argv: list[str]) -> int:
    if argv and argv[0] in FORWARD:
        script = ADVISOR / "scripts" / FORWARD[argv[0]]
        return subprocess.run([sys.executable, str(script), *argv[1:]]).returncode
    ap = argparse.ArgumentParser(prog="boil advise", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("retire", help="tombstone a rule")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.add_argument("--by", default="cli")
    p.set_defaults(fn=cmd_retire)
    p = sub.add_parser("unretire", help="undo a retire")
    p.add_argument("id")
    p.set_defaults(fn=cmd_unretire)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
