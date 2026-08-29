#!/usr/bin/env python3
"""Generate `.boil/NOW.md` — the ONE file a session reads at start.

Replaces the old session-start ritual (charter + ladder + todo + last 3 log
entries + goal.md + the ticket pool). Everything below is derived, so NOW.md is
never hand-edited and never drifts.

Usage:
    boil-now.py --root R [--write] [--wip 5] [--stall 3]

Without --write it prints to stdout. Exit code mirrors the brakes:
0 = CONTINUE, 2 = RESTRICT, 3 = STOP (parked project, or a brake fired).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util  # noqa: E402

from boil_common import (  # noqa: E402
    by_status, charter_path, checkbox_counts, ladder_path, open_tickets,
    parse_frontmatter, state_dir,
)

_spec = importlib.util.spec_from_file_location("brakes", Path(__file__).resolve().parent / "boil-brakes.py")
_brakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_brakes)


def _open_criteria(root: Path) -> tuple[int, int, list[str]]:
    """(green, total, first few open criterion texts) from the ladder."""
    path = ladder_path(root)
    green, total = checkbox_counts(path)
    open_items: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                open_items.append(stripped[5:].strip())
    return green, total, open_items


def _clip(text: str, limit: int) -> str:
    """NOW.md is a ~40-line orientation file, not an archive. Clip hard."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def _last_log(root: Path, n: int = 1) -> list[str]:
    path = state_dir(root) / "log.md"
    if not path.is_file():
        path = Path(root) / ".gate" / "log.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = [b.strip() for b in text.split("\n## ") if b.strip()]
    return blocks[-n:] if blocks else []


def _goal_headline(root: Path) -> str:
    path = state_dir(root) / "goal.md"
    if not path.is_file():
        return "(no goal.md — run Phase 0)"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("**One-line:**"):
            return _clip(s.replace("**One-line:**", ""), 160)
        if s and not s.startswith("#"):
            return _clip(s, 160)
    return "(goal.md has no one-line summary)"


def _measured(root: Path) -> str:
    """One line from `boil-check.py status` when the goal has frozen checks. Reads the
    attempt ledger only (cheap) — it never runs a check. Empty when nothing is frozen."""
    if not (state_dir(root) / "checks" / "frozen.json").is_file():
        return ""
    script = Path(__file__).resolve().parent / "boil-check.py"
    proc = subprocess.run([sys.executable, str(script), "status", "--root", str(root)],
                          text=True, capture_output=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def render(root: Path, wip: int, stall: int) -> tuple[str, int]:
    charter = parse_frontmatter(charter_path(root))
    status = charter.get("status", "unknown")
    lg, lt, open_items = _open_criteria(root)
    result = _brakes.evaluate(root, wip, stall)
    tickets = open_tickets(root)
    actionable = by_status(tickets, "open", "in-progress")
    blocked = by_status(tickets, "blocked")
    human = [t for t in tickets if str(t.get("type", "")).strip() == "human-action"]

    L = [f"# NOW — {charter.get('project', root.name)}", ""]
    L.append(f"**Project:** {status} · stage {charter.get('stage', '?')} · "
             f"north star: {charter.get('north_star', '(unset)')}")
    if status == "parked":
        L.append("")
        L.append("> **PARKED.** Do not start work here. Re-entry condition: "
                 f"{charter.get('reentry', '(unstated — ask the user)')}")
    L.append(f"**Ladder:** {lg}/{lt} criteria green" + (f" · next open: {open_items[0]}" if open_items else ""))
    L.append(f"**Goal:** {result['green']}/{result['total']} checkboxes — {_goal_headline(root)}")
    measured = _measured(root)
    if measured:
        L.append(f"**Measured:** {measured}")
    L.append(f"**Loop:** {result['iterations']} iterations · {result['actionable_tickets']} actionable tickets"
             + (f" · {result['blocked_tickets']} blocked" if result["blocked_tickets"] else ""))
    if result.get("budget_usd"):
        L.append(f"**Budget:** ${result['spent_usd']:.2f} of ${float(result['budget_usd']):.2f}")
    L.append("")
    L.append(f"## Brakes: {result['verdict']}")
    if result["findings"]:
        for f in result["findings"]:
            L.append(f"- **{f['brake']}** ({f['level']}): {f['message']}")
    else:
        L.append("- all clear")
    L.append("")

    if human:
        L.append("## Blocked on you")
        for t in human:
            L.append(f"- `{t.get('id', '?')}` {_clip(str(t.get('title') or '(untitled)'), 70)}"
                     f" — {_clip(str(t.get('working_on') or ''), 70)}")
        L.append("")

    L.append("## Actionable tickets")
    if actionable:
        for t in sorted(actionable, key=lambda x: str(x.get("priority", "P9")))[:wip]:
            L.append(f"- `{t.get('id', '?')}` [{t.get('priority', '?')}/{t.get('tier', 'T?')}] "
                     f"{_clip(str(t.get('title') or '(untitled)'), 70)}"
                     f" — {_clip(str(t.get('working_on') or 'not started'), 60)}")
    else:
        L.append("- none open — pick the next ladder criterion or close the goal")
    L.append("")

    log = _last_log(root)
    if log:
        L.append("## Last session")
        lines = [ln for ln in log[-1].splitlines() if ln.strip()]
        L.append(f"**{_clip(lines[0], 90)}**" if lines else "(empty)")
        for ln in lines[1:5]:
            L.append(_clip(ln, 110))
        if len(lines) > 5:
            L.append(f"_(+{len(lines) - 5} more lines in log.md)_")
        L.append("")

    L.append("---")
    if status == "parked":
        L.append("**Next:** this project is parked — confirm with the user before any work.")
    elif result["verdict"] == "STOP":
        L.append("**Next:** a brake fired. Stop and put the decision above to the user.")
    elif result["green"] == result["total"] and result["total"]:
        L.append("**Next:** goal is green — run `boil-doctor.py --final` and hand off.")
    else:
        L.append("**Next:** work the top actionable ticket at its declared tier.")

    exit_code = 3 if status == "parked" else _brakes.EXIT[result["verdict"]]
    return "\n".join(L) + "\n", exit_code


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--write", action="store_true", help="write .boil/NOW.md instead of stdout")
    ap.add_argument("--wip", type=int, default=5)
    ap.add_argument("--stall", type=int, default=3)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    text, code = render(root, args.wip, args.stall)
    if args.write:
        out = state_dir(root) / "NOW.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out} ({len(text.splitlines())} lines)")
    else:
        print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
