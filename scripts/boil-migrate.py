#!/usr/bin/env python3
"""Fold a project's `.gate/` outer-loop state into `.boil/`.

gate and boil were separate skills, so the outer loop had to be invoked
voluntarily — and measurably was not: on 2026-08-28, 4 of 15 boil projects had
`.gate/` at all and PORTFOLIO.md had been stale for five weeks. After migration
there is one state directory, and `boil-now.py` reads it automatically at
session start.

Non-destructive by default: `.gate/` is copied, not moved, and left in place
unless --remove-gate is passed. Dry-run unless --apply.

Usage:
    boil-migrate.py --root <project> [--apply] [--remove-gate]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boil_common import checkbox_counts  # noqa: E402

# gate files that become boil files verbatim. `todo.md` is deliberately absent:
# its NOW/NEXT/ICEBOX role is taken over by the ticket pool plus icebox.md, which
# the WIP brake already enforces.
GATE_FILES = ("charter.md", "ladder.md", "log.md", "scorecard.md")
ITER_DIR = re.compile(r"^iter-(\d+)")


def backfill_progress(root: Path, apply: bool) -> tuple[int, str]:
    """Seed progress.jsonl from existing iteration dirs.

    Without this the stall brake sees `0 iterations` on a project that has run
    65 of them, and cannot fire until three more go by.
    """
    boil = root / ".boil"
    iterations = boil / "iterations"
    target = boil / "progress.jsonl"
    if target.exists():
        return 0, "progress.jsonl already exists — left alone"
    if not iterations.is_dir():
        return 0, "no iterations/ to backfill"
    dirs = sorted((d for d in iterations.iterdir() if d.is_dir() and ITER_DIR.match(d.name)),
                  key=lambda d: int(ITER_DIR.match(d.name).group(1)))
    if not dirs:
        return 0, "no iter-NNN directories found"
    green, total = checkbox_counts(boil / "goal.md")
    # Historical per-iteration greens are not recoverable; record the count and
    # today's standing so the brake has a baseline without inventing history.
    records = [{"iteration": d.name, "green": None, "total": total,
                "ts": dt.datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds"),
                "backfilled": True} for d in dirs]
    records.append({"iteration": "migrate", "green": green, "total": total,
                    "ts": dt.datetime.now().isoformat(timespec="seconds"), "backfilled": True})
    if apply:
        target.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return len(records), f"backfilled {len(records)} progress records from iterations/"


def migrate(root: Path, apply: bool, remove_gate: bool) -> int:
    gate = root / ".gate"
    boil = root / ".boil"
    actions: list[str] = []

    if not boil.is_dir():
        actions.append("CREATE .boil/")
        if apply:
            boil.mkdir(parents=True)

    if gate.is_dir():
        for name in GATE_FILES:
            src, dst = gate / name, boil / name
            if not src.is_file():
                continue
            if dst.is_file():
                actions.append(f"SKIP  .boil/{name} (already exists)")
                continue
            actions.append(f"COPY  .gate/{name} -> .boil/{name}")
            if apply:
                shutil.copy2(src, dst)
        # gate sharded its log in busy projects; carry the shards over too.
        shards = gate / "log.d"
        if shards.is_dir() and not (boil / "log.d").exists():
            actions.append(f"COPY  .gate/log.d/ -> .boil/log.d/ ({len(list(shards.glob('*.md')))} files)")
            if apply:
                shutil.copytree(shards, boil / "log.d")
    else:
        actions.append("NOTE  no .gate/ — this project had no outer loop; charter.md must be written")

    icebox = boil / "icebox.md"
    if not icebox.is_file():
        actions.append("CREATE .boil/icebox.md (overflow for the WIP brake)")
        if apply:
            icebox.write_text(
                "# Icebox\n\nTickets beyond the WIP limit live here. They are not routed.\n"
                "Promote one only when an actionable slot frees up.\n\n", encoding="utf-8")

    budget = boil / "budget.json"
    if not budget.is_file():
        actions.append("CREATE .boil/budget.json (unset caps — fill goal_usd to arm the brake)")
        if apply:
            budget.write_text(json.dumps({"goal_usd": None, "iteration_usd": None, "spent_usd": 0.0},
                                         indent=2) + "\n", encoding="utf-8")

    n, msg = backfill_progress(root, apply)
    actions.append(f"{'BACKFILL' if n else 'NOTE '} {msg}")

    if remove_gate and gate.is_dir():
        actions.append("REMOVE .gate/ (copies verified above)")
        if apply:
            shutil.rmtree(gate)

    print(f"{'APPLYING' if apply else 'DRY RUN'} — {root}")
    for a in actions:
        print(f"  {a}")
    if not apply:
        print("\nNothing was written. Re-run with --apply.")
    else:
        print("\nDone. Next: `boil-now.py --root <project> --write`, then check goal.md size "
              "with `ticket-lint.py`.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--remove-gate", action="store_true", help="delete .gate/ after copying")
    args = ap.parse_args(argv)
    return migrate(Path(args.root).resolve(), args.apply, args.remove_gate)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
