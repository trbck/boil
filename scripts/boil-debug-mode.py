#!/usr/bin/env python3
"""Create a systematic-debugging worksheet for a failing iteration/ticket."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--iteration", required=True)
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--failure", default="", help="short failure summary")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = root / ".boil" / "debug" / args.iteration
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.ticket}-debug.md"
    verify = root / ".boil" / "iterations" / args.iteration / "verify.log"
    retest = root / ".boil" / "iterations" / args.iteration / "retest.log"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out.write_text(
        f"""# Debug Worksheet — {args.ticket}

**Created:** {now}
**Iteration:** {args.iteration}
**Failure:** {args.failure or "(fill exact symptom)"}

## Reproduce
- Command:
- Expected:
- Actual:

## Isolate
- Smallest failing input:
- First bad boundary:
- Logs/artifacts:
  - `{verify}` if present
  - `{retest}` if present

## Hypotheses
1. <hypothesis and falsifying check>
2. <hypothesis and falsifying check>

## Minimal Fix
- Target file(s):
- Risk:

## Regression Proof
- RED proof:
- GREEN proof:
- Adversarial retest:

## Next Ticket Proposal
Write `.boil/tickets/proposals/{args.ticket}-debug-fix.md` if this needs a new routed ticket.
""",
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
