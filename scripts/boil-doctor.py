#!/usr/bin/env python3
"""Validate a boil workspace before or during an agentic loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _check(path: Path, ok: bool, code: str, message: str) -> dict[str, str | bool]:
    return {"ok": ok, "file": str(path), "code": code, "message": message}


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    skill_root = Path(args.skill_root).resolve()
    boil = root / ".boil"
    checks: list[dict[str, str | bool]] = []

    checks.append(_check(boil, boil.exists(), "boil-dir", ".boil directory exists"))
    for rel in ("goal.md", "memory.md", "implementation.md", "bugs.md", "routing.md"):
        p = boil / rel
        checks.append(_check(p, p.exists(), f"state-{rel}", f".boil/{rel} exists"))
    checks.append(_check(boil / "tickets", (boil / "tickets").is_dir(), "tickets-dir", ".boil/tickets exists"))

    gitignore = skill_root / ".gitignore"
    ignored_bridge = False
    if gitignore.exists():
        ignored_bridge = ".susi-human-blockers/" in gitignore.read_text(encoding="utf-8", errors="replace")
    checks.append(_check(gitignore, ignored_bridge, "bridge-ignored", ".susi-human-blockers is ignored"))

    bridge = skill_root / ".susi-human-blockers" / "add_blocker.py"
    checks.append(_check(bridge, bridge.exists(), "bridge-present", "local Susi blocker bridge exists"))

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
