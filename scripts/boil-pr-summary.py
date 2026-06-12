#!/usr/bin/env python3
"""Generate a PR body from boil run state and iteration summaries."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    base = args.base or _git(root, "merge-base", "HEAD", "origin/main") or "HEAD~1"
    diffstat = _git(root, "diff", "--stat", base, "HEAD")
    goal = root / ".boil" / "goal.md"
    iterations = sorted((root / ".boil" / "iterations").glob("iter-*/summary.md")) if (root / ".boil" / "iterations").exists() else []

    lines = ["# PR Summary", ""]
    if goal.exists():
        lines.extend(["## Goal", "", goal.read_text(encoding="utf-8", errors="replace").split("\n\n", 1)[0], ""])
    lines.extend(["## Iterations", ""])
    if iterations:
        for path in iterations:
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            lines.append(f"- `{path.parent.name}` — {first.lstrip('# ').strip()}")
    else:
        lines.append("- No boil iteration summaries found.")
    lines.extend(["", "## Verification", "", "- [ ] Direct verification output included", "- [ ] Adversarial retest included", "- [ ] Demo included", "- [ ] Confidence gates >=99 with no uncertainty", ""])
    lines.extend(["## Diff Stat", "", "```", diffstat or "(no diffstat available)", "```", ""])
    body = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
        print(args.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
