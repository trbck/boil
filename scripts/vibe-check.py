#!/usr/bin/env python3
"""Detect progress-theater summaries that lack proof, demo, or next actions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IMPLEMENTED_RE = re.compile(r"\b(implemented|built|done|fixed|completed|shipped)\b", re.I)
TEST_RE = re.compile(r"\b(Tests?|Verification|Proof)\b", re.I)
DEMO_RE = re.compile(r"\b(Demo|How to see it works|30 seconds|screenshot|localhost|curl)\b", re.I)
NEXT_RE = re.compile(r"\b(Suggested next steps|Next:|Next focus)\b", re.I)
OUTPUT_RE = re.compile(r"\b(passed|failed|exit=|HTTP\s+\d{3}|ok\b|green)\b", re.I)


def check_text(text: str, path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        issues.append({"file": str(path), "code": code, "message": message})

    claims_done = bool(IMPLEMENTED_RE.search(text))
    if claims_done and not TEST_RE.search(text):
        add("missing-tests", "summary claims progress but has no tests/proof section")
    if claims_done and not DEMO_RE.search(text):
        add("missing-demo", "summary claims progress but has no demo artifact/action")
    if not NEXT_RE.search(text):
        add("missing-next", "summary has no explicit next-step section/footer")
    if TEST_RE.search(text) and not OUTPUT_RE.search(text):
        add("weak-proof", "proof/test section lacks concrete output words like passed/failed/exit")
    if re.search(r"\bshould (work|pass|be|now)\b", text, re.I):
        add("speculative-language", "uses speculative completion language")
    return issues


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="summary/demo/final markdown to check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        issues = [{"file": str(path), "code": "missing-file", "message": "file does not exist"}]
    else:
        issues = check_text(path.read_text(encoding="utf-8", errors="replace"), path)

    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    else:
        if not issues:
            print("vibe-check: ok")
        for item in issues:
            print(f"{item['file']}: {item['code']}: {item['message']}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
