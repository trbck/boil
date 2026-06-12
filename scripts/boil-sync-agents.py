#!/usr/bin/env python3
"""Write project-local agent instructions for Codex, Cursor, and boil."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


AGENTS = """# Agent Instructions

This project uses `boil` for agentic looped development.

Follow these rules:
- Read `.boil/goal.md`, `.boil/memory.md`, and the assigned ticket before editing.
- Do not implement until requirements are understood at >=99/100 confidence.
- Use proof-first development: RED proof before implementation for behavior/bug work.
- Do not mark tickets done unless `confidence.requirements_understood`,
  `confidence.implementation_matches`, and `confidence.verification_working`
  are each >=99 with concrete evidence and empty uncertainty.
- Run the verification commands named in `.boil/memory.md` or the ticket.
- If blocked on user action, create/update a `human-action` ticket with a
  secret-free `safe_summary`.
- Keep changes scoped to the ticket. File proposals for unrelated work.
"""

CURSOR_RULE = """---
description: Boil agentic loop guardrails
alwaysApply: true
---

Use the project `.boil/` workspace as the source of truth. Confirm
requirements, write proof first, implement second, verify with real output,
and keep `Done` claims backed by ticket confidence >=99 with no uncertainty.
"""

ROUTING = """platform: codex
dispatch_field: agent_type
routes:
  frontend: worker
  backend: worker
  fullstack: worker
  qa: worker
  verification: worker
  debugger: worker
  error-detective: worker
  code-review: explorer
  review: explorer
  research: explorer
  brainstorm: default
  parallel-dispatch: default
  orchestrator: default
  ticket-triage: default
  general: worker
"""


def _write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"kept {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"wrote {path}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--force", action="store_true", help="overwrite existing instruction files")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    skill_root = Path(args.skill_root).resolve()
    outputs: list[str] = []
    outputs.append(_write(root / "AGENTS.md", AGENTS, args.force))
    outputs.append(_write(root / ".cursor" / "rules" / "boil.mdc", CURSOR_RULE, args.force))

    routing = root / ".boil" / "routing.md"
    if not routing.exists() or args.force:
        routing.parent.mkdir(parents=True, exist_ok=True)
        routing.write_text(ROUTING, encoding="utf-8")
        outputs.append(f"wrote {routing}")

    print("\n".join(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
