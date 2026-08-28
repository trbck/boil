# Paste into the project's CLAUDE.md / AGENTS.md

```markdown
## Project governance (boil)

This project is governed by `.boil/` (spec: ~/.claude/skills/boil/SKILL.md).

- BEFORE any work, run ONE command and read its output:
  `python3 ~/.claude/skills/boil/scripts/boil-now.py --root . --write`
  It prints project status, ladder position, goal progress, the brakes, and the
  actionable tickets in ~40 lines. Do not read charter/ladder/log separately —
  NOW.md is derived from them and is the single session-start read.
- It exits 3 when the project is PARKED or a brake fired. On exit 3: stop, put
  the decision to the user, do not start work.
- Work that serves no open ladder criterion: stop and ask — icebox it, or amend
  the ladder with explicit user confirmation.
- Charter non-goals are a fence. Do not build past it.
- Checkboxes only flip with a fresh EVIDENCE line on the same line:
  `EVIDENCE: <command -> result | URL | number> | YYYY-MM-DD | auto|human`
  Run the command, paste the result, then tick. Never tick from memory.
- AFTER work, append one entry to `.boil/log.md` (did / delta / next) and run
  `boil-brakes.py tick --root . --iteration iter-NNN`. A session that did not
  tick did not happen.
```
