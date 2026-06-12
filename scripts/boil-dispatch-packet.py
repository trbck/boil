#!/usr/bin/env python3
"""Generate a compact dispatch packet for one boil ticket."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _read(path: Path, missing: str = "") -> str:
    if not path.exists():
        return missing
    return path.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket", help="ticket id T-0001 or ticket path")
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--out-dir", default=".boil/dispatch")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    ticket_path = Path(args.ticket)
    if not ticket_path.exists():
        ticket_path = root / ".boil" / "tickets" / f"{args.ticket}.md"
    if not ticket_path.exists():
        print(f"dispatch-packet: missing ticket {args.ticket}", file=sys.stderr)
        return 2

    ticket_id = ticket_path.stem
    goal = _read(root / ".boil" / "goal.md", "(missing .boil/goal.md)")
    memory = _read(root / ".boil" / "memory.md", "(missing .boil/memory.md)")
    ticket = _read(ticket_path)
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{ticket_id}.md"
    out.write_text(
        f"""# Dispatch Packet — {ticket_id}

## Goal Context

{goal}

## Codebase Memory

{memory}

## Ticket

{ticket}

## Required Return Shape

- Changed files
- Proof / tests with fresh output
- Confidence gate: requirements, implementation, verification all >=99 or explain why not
- New ticket proposals
- Blockers
- Demo notes
""",
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
