#!/usr/bin/env python3
"""Regenerate PORTFOLIO.md from every <project>/.boil/ in the workspace.

Absorbed from gate's `gate-portfolio.py`, with one addition that the gate
version lacked: a **reality check** against git. The declared portfolio drifts
from what is actually being worked on — measured 2026-08-28, two of four
declared-active projects had 0 commits in 30 days while two undeclared projects
had 61 and 48. `status: active` is a claim; commit activity is evidence.

Reads `.boil/charter.md` (falling back to a pre-merge `.gate/charter.md`), so it
works before and after migration.

Usage:
    boil-portfolio.py [--root ~/workspace] [--wip 3] [--out PORTFOLIO.md] [--check]

--check exits 1 on any rule violation (usable from CI, cron, or a hook).
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boil_common import charter_path, parse_frontmatter  # noqa: E402

SKIP_PREFIXES = ("_", ".")


def days_since(datestr: str, today: dt.date) -> int | None:
    try:
        return (today - dt.date.fromisoformat(datestr)).days
    except (ValueError, TypeError):
        return None


def commits_since(project: Path, days: int = 30) -> int | None:
    """Commits in the last `days`. None when the project is not a git repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(project), "log", f"--since={days}.days", "--oneline"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return len([ln for ln in proc.stdout.splitlines() if ln.strip()])


def collect(root: Path, today: dt.date) -> list[dict]:
    rows = []
    for project_dir in sorted(root.iterdir()):
        if not project_dir.is_dir() or project_dir.name.startswith(SKIP_PREFIXES):
            continue
        cpath = charter_path(project_dir)
        if not cpath.is_file():
            # Ungoverned: real boil work happening with no charter at all.
            if (project_dir / ".boil").is_dir():
                c30 = commits_since(project_dir)
                if (c30 or 0) >= 20:
                    rows.append({
                        "project": project_dir.name, "type": "?", "status": "ungoverned",
                        "stage": "—", "score": "—", "health": "UNGOVERNED", "north_star": "—",
                        "kill_by": "—", "delta_days": None, "commits30": c30,
                        "kill_breached": False,
                    })
            continue
        charter = parse_frontmatter(cpath)
        score = parse_frontmatter(cpath.parent / "scorecard.md")
        row = {
            "project": charter.get("project", project_dir.name),
            "type": charter.get("type", "?"),
            "status": charter.get("status", "?"),
            "stage": score.get("stage", charter.get("stage", "?")),
            "score": score.get("score", charter.get("score", "?")),
            "health": score.get("health", "no-audit"),
            "north_star": charter.get("north_star", "?"),
            "kill_by": charter.get("kill_by", "?"),
            "delta_days": days_since(score.get("last_gate_delta", ""), today),
            "commits30": commits_since(project_dir),
        }
        # Health taxonomy. Stale ladder + busy repo is a *different* failure from a
        # dead project: the work is happening, the outer loop just is not recording it.
        d = row["delta_days"]
        c30 = row["commits30"] or 0
        stale = d is None or d > 30
        if row["status"] == "active":
            if c30 == 0:
                row["health"] = "DECLARED-DEAD"
            elif stale and c30 >= 20:
                row["health"] = "UNAUDITED"
            elif stale:
                row["health"] = "ZOMBIE"
        kb = days_since(row["kill_by"], today)
        row["kill_breached"] = kb is not None and kb >= 0 and row["status"] in ("active", "parked")
        rows.append(row)
    return rows


def render(rows: list[dict], wip: int, today: dt.date) -> tuple[str, list[str]]:
    violations: list[str] = []
    active = [r for r in rows if r["status"] == "active"]
    if len(active) > wip:
        violations.append(
            f"WIP limit breached: {len(active)} active projects (max {wip}): "
            + ", ".join(r["project"] for r in active)
        )
    for r in rows:
        if r["health"] == "DECLARED-DEAD":
            violations.append(
                f"DECLARED-DEAD: {r['project']} is `status: active` with 0 commits in 30 days — "
                "park it or recommit."
            )
        elif r["health"] == "UNAUDITED":
            violations.append(
                f"UNAUDITED: {r['project']} has {r['commits30']} commits in 30 days but no ladder "
                f"delta in {r['delta_days'] if r['delta_days'] is not None else '>30'} days — "
                "effort is not converting into gate progress. This is the failure the loop exists to catch."
            )
        elif r["health"] == "ZOMBIE":
            violations.append(f"ZOMBIE: {r['project']} is active with no ladder delta in >30d (or never audited)")
        elif r["health"] == "UNGOVERNED":
            violations.append(
                f"UNGOVERNED: {r['project']} has {r['commits30']} commits in 30 days and a .boil/ "
                "directory but no charter — it is real work outside the portfolio entirely."
            )
        if r["kill_breached"]:
            violations.append(f"KILL-BY reached: {r['project']} ({r['kill_by']}) — decide: recommit / park / kill")
    undeclared = [r for r in rows
                  if r["status"] not in ("active", "ungoverned") and (r["commits30"] or 0) >= 20]
    for r in undeclared:
        violations.append(
            f"UNDECLARED WORK: {r['project']} is `{r['status']}` but has {r['commits30']} commits in "
            "30 days — the portfolio does not describe what you are doing."
        )

    order = {"active": 0, "ungoverned": 1, "candidate": 2, "parked": 3, "killed": 4, "?": 5}
    rows = sorted(rows, key=lambda r: (order.get(r["status"], 4), str(r["project"])))

    lines = [
        "# PORTFOLIO",
        "",
        f"Generated {today.isoformat()} by boil-portfolio.py — do not hand-edit the table.",
        f"WIP limit: {wip} active. Weekly review notes go below the table.",
        "",
        "| Project | Type | Status | Stage | Score | Health | Commits 30d | North star | Kill by | Δ days |",
        "|---|---|---|---|---|---|---:|---|---|---:|",
    ]
    for r in rows:
        delta = "—" if r["delta_days"] is None else str(r["delta_days"])
        c30 = "—" if r["commits30"] is None else str(r["commits30"])
        lines.append(
            f"| {r['project']} | {r['type']} | {r['status']} | {r['stage']} | {r['score']} "
            f"| {r['health']} | {c30} | {r['north_star']} | {r['kill_by']} | {delta} |"
        )
    lines.append("")
    if violations:
        lines.append("## ⚠️ Rule violations")
        lines.extend(f"- {v}" for v in violations)
        lines.append("")
    lines.append("## Weekly review notes")
    lines.append("<!-- appended by `/boil review`: date, per-active verdict (moved / recommit / park / kill) -->")
    lines.append("")
    return "\n".join(lines), violations


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.home() / "workspace"))
    ap.add_argument("--wip", type=int, default=3)
    ap.add_argument("--out", default=None, help="default: <root>/PORTFOLIO.md")
    ap.add_argument("--check", action="store_true", help="exit 1 on rule violations")
    ap.add_argument("--dry-run", action="store_true", help="print instead of writing")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    today = dt.date.today()
    rows = collect(root, today)
    if not rows:
        print(f"No <project>/.boil/charter.md (or .gate/charter.md) found under {root}", file=sys.stderr)
        return 2

    content, violations = render(rows, args.wip, today)
    out = Path(args.out) if args.out else root / "PORTFOLIO.md"
    if out.is_file():  # preserve appended review notes
        old = out.read_text(encoding="utf-8", errors="replace")
        marker = "## Weekly review notes"
        if marker in old:
            content = content.split(marker, 1)[0] + marker + old.split(marker, 1)[1]
    if args.dry_run:
        print(content)
    else:
        out.write_text(content, encoding="utf-8")
        print(f"Wrote {out} ({len(rows)} projects, {len(violations)} violations)")
    for v in violations:
        print(f"  !  {v}")
    return 1 if (args.check and violations) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
