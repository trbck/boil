#!/usr/bin/env python3
"""The three convergence brakes: stall, ticket WIP, and budget.

These exist because boil's prose rules never fired in practice. Measured across
15 projects: ttengine ran 65 iterations and moved 2 of 7 checkboxes; trtools2
ran 69 and moved 0 of 13 before being archived. Neither run stopped itself.
A brake that lives in a script executes; a brake that lives in SKILL.md does not.

Usage:
    boil-brakes.py tick  --root R --iteration iter-003 [--spent-usd 1.20]
    boil-brakes.py check --root R [--wip 5] [--stall 3] [--json]

check exit codes:  0 = CONTINUE   2 = RESTRICT (T1 only)   3 = STOP (ask the user)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boil_common import by_status, checkbox_counts, open_tickets, state_dir  # noqa: E402

PROGRESS = "progress.jsonl"
BUDGET = "budget.json"


def _records(root: Path) -> list[dict]:
    path = state_dir(root) / PROGRESS
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _budget(root: Path) -> dict:
    path = state_dir(root) / BUDGET
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def tick(root: Path, iteration: str, spent_usd: float | None) -> int:
    """Append one progress record. Call once per iteration, after verification."""
    boil = state_dir(root)
    boil.mkdir(parents=True, exist_ok=True)
    green, total = checkbox_counts(boil / "goal.md")
    rec = {
        "iteration": iteration,
        "green": green,
        "total": total,
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
    }
    if spent_usd is not None:
        rec["spent_usd"] = spent_usd
        budget = _budget(root)
        budget["spent_usd"] = round(float(budget.get("spent_usd", 0.0)) + spent_usd, 4)
        (boil / BUDGET).write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")
    with (boil / PROGRESS).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(f"tick {iteration}: {green}/{total} checkboxes green")
    return 0


def _milestone_verdicts(root: Path) -> dict[str, str]:
    """Last controller result per milestone from `.boil/checks/attempts.jsonl`
    (written by boil-check.py). Empty when the project is not in verifier-first mode."""
    path = state_dir(root) / "checks" / "attempts.jsonl"
    if not path.is_file():
        return {}
    last: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("milestone") and rec.get("result"):
            last[str(rec["milestone"])] = str(rec["result"])
    return last


def evaluate(root: Path, wip_limit: int, stall_limit: int) -> dict:
    """Run all three brakes. Returns a verdict dict; never raises."""
    green, total = checkbox_counts(state_dir(root) / "goal.md")
    recs = _records(root)
    tickets = open_tickets(root)
    actionable = by_status(tickets, "open", "in-progress")
    blocked = by_status(tickets, "blocked")
    budget = _budget(root)

    findings: list[dict] = []
    verdict = "CONTINUE"

    # Brake 1 — stall. N consecutive iterations with no checkbox moving.
    # A fully green goal is not a stall — it is a finished goal awaiting termination.
    complete = total > 0 and green == total
    # Backfilled records (from boil-migrate.py) carry green=None: they mark that an
    # iteration happened without claiming what it achieved. Only measured ticks count.
    measured = [r for r in recs if r.get("green") is not None]
    flat = 0
    if not complete and len(measured) >= stall_limit:
        tail = measured[-stall_limit:]
        if len({r.get("green") for r in tail}) == 1:
            flat = stall_limit
    if flat:
        verdict = "STOP"
        findings.append({
            "brake": "stall",
            "level": "stop",
            "message": (
                f"{flat} consecutive iterations at {green}/{total} checkboxes — the loop is not "
                "converging. Split the criterion, re-scope the goal, or park the project."
            ),
        })

    # Brake 2 — ticket WIP. The pool must not outrun the consumer.
    if len(actionable) > wip_limit:
        verdict = "STOP" if verdict == "STOP" else "RESTRICT"
        findings.append({
            "brake": "wip",
            "level": "restrict",
            "message": (
                f"{len(actionable)} actionable tickets exceeds the WIP limit of {wip_limit}. "
                "Move the excess to .boil/icebox.md; file no new tickets until it is back under."
            ),
        })

    # Brake 4 — the controller's verdict (verifier-first mode). When
    # `.boil/checks/attempts.jsonl` exists, the last record per milestone is a
    # decision: STALL / CAP / TAMPER / BUDGET hand the loop to the user until a
    # later PASS clears it. This is the brake that would have stopped a 65-iteration
    # run at iteration ten: nothing external was measuring per-milestone progress.
    for mid, last in _milestone_verdicts(root).items():
        if last in ("STALL", "CAP", "TAMPER", "BUDGET"):
            verdict = "STOP"
            findings.append({
                "brake": "milestone",
                "level": "stop",
                "message": (
                    f"milestone {mid} is at {last} — "
                    + {"STALL": "split it into 2-4 sub-checks (once), then ask the user",
                       "CAP": "the attempt ceiling is spent; split or ask the user, never attempt again",
                       "TAMPER": "a frozen check or protected file changed; a human decides",
                       "BUDGET": "the goal budget is spent; stop and report cost against progress"}[last]
                ),
            })

    # Brake 3 — budget.
    cap = budget.get("goal_usd")
    spent = float(budget.get("spent_usd", 0.0))
    if cap:
        frac = spent / float(cap)
        if frac >= 1.0:
            verdict = "STOP"
            findings.append({
                "brake": "budget",
                "level": "stop",
                "message": (
                    f"spent ${spent:.2f} of the ${float(cap):.2f} goal budget for {green}/{total} "
                    "checkboxes. Stop and report cost against progress."
                ),
            })
        elif frac >= 0.6:
            if verdict == "CONTINUE":
                verdict = "RESTRICT"
            findings.append({
                "brake": "budget",
                "level": "restrict",
                "message": (
                    f"spent ${spent:.2f} of ${float(cap):.2f} ({frac:.0%}) — drop to tier T1 only "
                    "and file no new tickets."
                ),
            })

    return {
        "verdict": verdict,
        "green": green,
        "total": total,
        "iterations": len(recs),
        "measured_iterations": len(measured),
        "actionable_tickets": len(actionable),
        "blocked_tickets": len(blocked),
        "spent_usd": spent,
        "budget_usd": cap,
        "findings": findings,
    }


EXIT = {"CONTINUE": 0, "RESTRICT": 2, "STOP": 3}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tick", help="record this iteration's progress")
    t.add_argument("--root", default=".")
    t.add_argument("--iteration", required=True)
    t.add_argument("--spent-usd", type=float, default=None)

    c = sub.add_parser("check", help="evaluate the brakes")
    c.add_argument("--root", default=".")
    c.add_argument("--wip", type=int, default=5)
    c.add_argument("--stall", type=int, default=3)
    c.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "tick":
        return tick(root, args.iteration, args.spent_usd)

    result = evaluate(root, args.wip, args.stall)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"brakes: {result['verdict']} — {result['green']}/{result['total']} green, "
              f"{result['iterations']} iterations, {result['actionable_tickets']} actionable tickets")
        for f in result["findings"]:
            print(f"  {f['level'].upper()} [{f['brake']}] {f['message']}")
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
