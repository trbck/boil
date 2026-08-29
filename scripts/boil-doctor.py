#!/usr/bin/env python3
"""Validate a boil workspace before or during an agentic loop."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boil_common import checkbox_counts  # noqa: E402

# The merge seam: a checked goal box carries a gate-format EVIDENCE line, so one
# green boil checkbox is simultaneously paste-ready evidence for the gate ladder.
# Format: EVIDENCE: <command -> result | URL | number | path> | <YYYY-MM-DD> | <auto|human>
EVIDENCE = re.compile(r"EVIDENCE:\s*\S.*\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*(auto|human)\b")
HUMAN_EVIDENCE = re.compile(r"EVIDENCE:.*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*human\b")
HUMAN_MAX_AGE_DAYS = 30
CHECK_SCRIPT = Path(__file__).resolve().parent / "boil-check.py"


def _check(path: Path, ok: bool, code: str, message: str) -> dict[str, str | bool]:
    return {"ok": ok, "file": str(path), "code": code, "message": message}


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.strip()


def _goal_contract_ok(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing goal.md"
    text = path.read_text(encoding="utf-8", errors="replace")
    required = ("## Requirements understanding", "Confidence", "Acceptance signal")
    missing = [item for item in required if item not in text]
    if missing:
        return False, "goal.md missing requirements contract: " + ", ".join(missing)
    return True, "goal.md requirements contract present"


def _reverify(root: Path) -> list[str]:
    """Re-run every frozen check via `boil-check.py verify --json`. A ticked box whose check
    fails NOW is a stale claim, not evidence. Returns reasons (empty = all green)."""
    frozen = root / ".boil" / "checks" / "frozen.json"
    if not frozen.is_file():
        return []
    proc = subprocess.run([sys.executable, str(CHECK_SCRIPT), "verify", "--root", str(root), "--json"],
                          text=True, capture_output=True)
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [f"could not re-verify frozen checks (boil-check verify exit {proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:200]}"]
    if not isinstance(out, dict) or not isinstance(out.get("results"), list):
        return ["could not re-verify: malformed verify output"]
    reasons = []
    for r in out["results"]:
        if not isinstance(r, dict) or "milestone" not in r or "result" not in r or "must_have" not in r:
            reasons.append("could not re-verify: malformed verify output")
            continue
        if r["result"] == "TAMPER":
            reasons.append(f"milestone {r['milestone']} is TAMPER — its check or a protected file changed since freeze")
        elif r["result"] != "PASS" and r["must_have"]:
            ce = f" ({r['counterexample']})" if r.get("counterexample") else ""
            reasons.append(f"milestone {r['milestone']} is {r['result']} now{ce} — re-measured, not remembered")
    return reasons


def _stale_human(goal_text: str, today: dt.date) -> list[str]:
    reasons = []
    for line in goal_text.splitlines():
        s = line.strip()
        if not s.startswith(("- [x]", "- [X]")):
            continue
        m = HUMAN_EVIDENCE.search(s)
        if not m:
            continue
        box = s[5:].split("EVIDENCE:")[0].strip(" —-")
        try:
            evidence_date = dt.date.fromisoformat(m.group(1))
        except ValueError:
            reasons.append(f'human evidence on "{box[:60]}" has an unparseable date '
                           f'"{m.group(1)}" — fix the EVIDENCE line')
            continue
        age = (today - evidence_date).days
        if age < 0:   # dated in the future: not "fresh", just wrong
            reasons.append(f'human evidence on "{box[:60]}" has an unparseable date '
                           f'"{m.group(1)}" (it is in the future) — fix the EVIDENCE line')
            continue
        if age > HUMAN_MAX_AGE_DAYS:
            reasons.append(f'human evidence on "{box[:60]}" is {age} days old (max {HUMAN_MAX_AGE_DAYS}) — re-approve')
    return reasons


def audit_final(root: Path) -> tuple[bool, list[str], list[str]]:
    """Can this goal legitimately be declared done?

    Returns (ok, reasons_it_is_not, unevidenced_box_texts). boil wrote FINAL.md
    on unfinished goals before because nothing checked; this is the check.
    """
    goal = root / ".boil" / "goal.md"
    reasons: list[str] = []
    unevidenced: list[str] = []
    if not goal.is_file():
        return False, ["no .boil/goal.md"], []

    green, total = checkbox_counts(goal)
    if total == 0:
        reasons.append("goal.md has no success checklist — nothing to declare done")
    if green < total:
        reasons.append(f"{total - green} of {total} checkboxes are still open")

    for line in goal.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(("- [x]", "- [X]")) and not EVIDENCE.search(stripped):
            unevidenced.append(stripped[5:].strip())
    if unevidenced:
        reasons.append(
            f"{len(unevidenced)} checked box(es) carry no EVIDENCE line "
            "(`EVIDENCE: <cmd -> result> | YYYY-MM-DD | auto|human`)")
    reasons += _reverify(root)
    # UTC, to match the date boil-check.py stamps onto EVIDENCE lines
    reasons += _stale_human(goal.read_text(encoding="utf-8", errors="replace"),
                            dt.datetime.now(dt.timezone.utc).date())
    return (not reasons), reasons, unevidenced


def write_handoff(root: Path, reasons: list[str], unevidenced: list[str]) -> Path:
    """Honest artifact for an unfinished goal. The only thing writable when not green."""
    goal = root / ".boil" / "goal.md"
    green, total = checkbox_counts(goal)
    open_boxes = [
        ln.strip()[5:].strip()
        for ln in goal.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip().startswith("- [ ]")
    ] if goal.is_file() else []

    out = root / ".boil" / "HANDOFF.md"
    lines = [
        f"# HANDOFF — {root.name}",
        "",
        f"Written {dt.date.today().isoformat()}. **This goal is not done: {green}/{total} green.**",
        "",
        "## Why this is not a FINAL",
    ]
    lines += [f"- {r}" for r in reasons]
    if open_boxes:
        lines += ["", "## Still open"] + [f"- [ ] {b}" for b in open_boxes]
    if unevidenced:
        lines += ["", "## Checked but unevidenced"] + [f"- {b}" for b in unevidenced]
    lines += [
        "",
        "## Next",
        "Pick ONE of: (a) close the remaining boxes, (b) re-scope goal.md to what was actually",
        "achieved and move the rest onto the ladder, or (c) park the project in the charter.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--final", action="store_true",
                    help="termination gate: may this goal be declared done?")
    ap.add_argument("--write", action="store_true",
                    help="with --final, write HANDOFF.md when the goal is not green")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()

    if args.final:
        ok, reasons, unevidenced = audit_final(root)
        if ok:
            print("FINAL OK: every checkbox is green and carries an EVIDENCE line.")
            print("The evidence lines are paste-ready for the gate ladder.")
            return 0
        print("FINAL REFUSED — this goal may not be declared done:")
        for r in reasons:
            print(f"  - {r}")
        if args.write:
            path = write_handoff(root, reasons, unevidenced)
            print(f"\nWrote {path} instead. That is the honest artifact for an unfinished goal.")
        else:
            print("\nRe-run with --write to produce HANDOFF.md instead.")
        return 3
    skill_root = Path(args.skill_root).resolve()
    boil = root / ".boil"
    checks: list[dict[str, str | bool]] = []

    checks.append(_check(boil, boil.exists(), "boil-dir", ".boil directory exists"))
    for rel in ("goal.md", "memory.md", "implementation.md", "bugs.md", "routing.md"):
        p = boil / rel
        checks.append(_check(p, p.exists(), f"state-{rel}", f".boil/{rel} exists"))
    goal_ok, goal_msg = _goal_contract_ok(boil / "goal.md")
    checks.append(_check(boil / "goal.md", goal_ok, "goal-requirements-contract", goal_msg))
    checks.append(_check(boil / "tickets", (boil / "tickets").is_dir(), "tickets-dir", ".boil/tickets exists"))

    # Merged outer-loop state. Absence is reported but never fatal: a fresh run loop in a
    # project that has not been governed yet is legitimate, and blocking on it would just
    # teach people to skip the doctor.
    for rel, why in (
        ("charter.md", "outer loop: no charter means no ladder and no portfolio row"),
        ("icebox.md", "WIP overflow file (created by boil-migrate.py)"),
        ("budget.json", "budget brake is unarmed without goal_usd"),
        ("progress.jsonl", "stall brake has no history until the first tick"),
    ):
        present = (boil / rel).exists()
        checks.append(_check(boil / rel, True,
                             f"outer-{rel}",
                             f".boil/{rel} present" if present else f"optional: .boil/{rel} absent — {why}"))

    gitignore = skill_root / ".gitignore"
    ignored_bridge = False
    if gitignore.exists():
        ignored_bridge = ".susi-human-blockers/" in gitignore.read_text(encoding="utf-8", errors="replace")
    checks.append(_check(gitignore, ignored_bridge, "bridge-ignored", ".susi-human-blockers is ignored"))

    bridge = skill_root / ".susi-human-blockers" / "add_blocker.py"
    bridge_msg = "local Susi blocker bridge exists" if bridge.exists() else "optional local Susi blocker bridge absent"
    checks.append(_check(bridge, True, "bridge-present", bridge_msg))

    linter = skill_root / "scripts" / "ticket-lint.py"
    if (boil / "tickets").is_dir():
        code, out = _run([sys.executable, str(linter), "--root", str(root), "--json"], cwd=root)
        checks.append(_check(linter, code == 0, "ticket-lint", out[:500] or "ticket lint ok"))

    ok = all(bool(c["ok"]) for c in checks)
    if args.json:
        print(json.dumps({"ok": ok, "checks": checks}, indent=2))
    else:
        for c in checks:
            tag = "ok" if c["ok"] else "FAIL"
            print(f"{tag}: {c['code']}: {c['message']} ({c['file']})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
