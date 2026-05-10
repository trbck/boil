# State Files — Templates

The four core files in `.boil/`. Treat these as living state — agents read and update them, the orchestrator (you) curates them.

## `.boil/goal.md`

The contract. Written in Phase 0, edited only when the user explicitly refines scope.

```markdown
# Goal

**One-line:** <restate the goal in one sentence>

**Created:** <ISO timestamp>
**Last refined:** <ISO timestamp, only update when user changes scope>

## Success checklist
<this is the termination condition — every box must be checked to finish>

- [ ] <criterion 1, observable>
- [ ] <criterion 2, observable>
- [ ] <criterion 3, observable>

<!--
  Semantic criteria (behavior, intent, subjective quality) should carry an
  inline rubric block right under the checkbox — see references/rubrics.md
  for the YAML shape and the judge dispatch protocol. Deterministic criteria
  (exit codes, latency, schema checks) do NOT need a rubric — Pass 1 covers them.
-->

## How the user will see this works (demo target)

<concrete: which page, which command, which test, which screenshot. This is what every iteration's demo points toward.>

## Out of scope
- <thing 1 we are NOT doing>
- <thing 2>

## Constraints
- **Quality bar:** <prototype | personal | production | paying-users>
- **Off-limits:** <files, services, APIs we don't touch>
- **Iteration budget:** <unlimited | N cycles | by <time>>
- **Verification access:** <test command, dev server command, credentials needed>
```

---

## `.boil/memory.md`

What's true about the codebase right now. Updated lazily — when an agent learns something useful for the next agent, they append a one-liner.

```markdown
# Memory

**Last updated:** <ISO timestamp>

## Stack
- Language(s): <…>
- Framework(s): <…>
- Test runner: <…>
- Build/run commands: <…>

## Project layout (relevant slices)
- `<path>/` — <what lives here>
- `<path>/` — <what lives here>

## Goal-relevant code
- `<path/file>:<line>` — <what this does, why it matters to the goal>
- `<path/file>:<line>` — <what this does>

## Run / test / build
- Run dev: `<cmd>`
- Run tests: `<cmd>`
- Lint: `<cmd>`
- Type-check: `<cmd>`
- Build: `<cmd>`

## Gotchas (append-only)
- <gotcha 1, who learned it, when>
- <gotcha 2>
```

Keep this tight (~30–60 lines). It's a quick-reference for incoming agents, not full documentation.

---

## `.boil/implementation.md`

The plan. Ordered slices toward the goal. Each slice maps to one or more tickets. Re-orderable as you learn.

```markdown
# Implementation Plan

**Last updated:** <ISO timestamp>

## Slices (ordered)

### Slice 1: <name>
**Closes goal checkbox(es):** <which ones>
**Tickets:** T-0001, T-0002
**Status:** in-progress | done | blocked

<one-paragraph description>

### Slice 2: <name>
…

## Done log
- <ISO date> — Slice 1 complete (T-0001 ✅, T-0002 ✅)
```

This is your sequencing memory across iterations. After each iteration, mark slices done and re-order remaining ones if priorities shifted.

---

## `.boil/bugs.md`

Append-only log of observed defects. Anything verification turned up that wasn't in scope of the current iteration's tickets.

```markdown
# Bugs

## Open

### B-001 — <one-line>
**Discovered:** <ISO timestamp> in <iter-NNN>
**Symptom:** <what was observed>
**Reproducer:** <command or steps>
**Filed as ticket:** T-00XX  (or "not yet")
**Severity:** P0 | P1 | P2 | P3

## Fixed
- B-000 — <one-line> — fixed in iter-NNN by T-00YY
```

When a bug becomes a ticket, link them. When a ticket fixes a bug, move it to Fixed with a back-link. Keeps both sides honest.

---

## `.boil/iterations/iter-NNN/` layout

Every iteration produces a directory:

```
iter-NNN/
├── summary.md      # the 10-line summary you posted to chat
├── demo.md         # THE user-visible demo (links + paste-able commands)
├── verify.log      # full output of the direct-verification commands (Pass 1)
├── retest.log      # full output of the adversarial re-test (Pass 2)
└── artifacts/      # screenshots, captured outputs, generated files
```

### `summary.md` template

```markdown
# Iteration N — <ISO timestamp>

**Done this cycle:**
- <bullet>
- <bullet>

**Goal progress:** <X / Y checkboxes green> — <which one(s) just turned green>

**Tests:** <e.g., "added 4, all 53 passing">
- New: <test names>

**Tickets touched:** <T-00XX done, T-00YY in-progress>
**New tickets filed:** <T-00ZZ (frontend), T-00AA (qa)>  — or "none"

**Bugs surfaced:** <B-XXX, B-YYY>  — or "none"

**Next focus:** <which ticket(s) next iteration will pick>
```

### `demo.md` template

```markdown
# Demo — Iteration N

## What changed (file-level)
- `<path>` — <one-line>
- `<path>` — <one-line>

## How to see it works (30 seconds)

**The action:** <ONE concrete thing the user does>

→ <URL | command | screenshot path | test command + expected output>

## Where this sits vs goal
- ✅ Closed: <goal checkboxes that just went green>
- 🟡 Moved forward: <checkboxes that progressed but aren't green yet>
- ⬜ Untouched: <checkboxes for future iterations>

## Tests added / run
- `<test name>` — <what it asserts> — verify with `<cmd>` — <pass/fail>
- `<test name>` — <what it asserts> — verify with `<cmd>` — <pass/fail>

## Adversarial angle (Pass 2)
**Angle:** <what the implementer DIDN'T test that you did>
**Result:** <pass / new bug B-XXX filed>
```

---

## `.boil/iterations/FINAL.md` (on termination)

```markdown
# Final — <ISO timestamp>

**Goal:** <one-liner from goal.md>
**Iterations run:** N
**Termination reason:** <goal complete | user stopped | hard blocker>

## Final demo
**The action:** <ONE concrete thing the user does to see it all working>
→ <URL | command | screenshot path>

## Goal checklist — final state
- [x] <criterion 1>
- [x] <criterion 2>
- [ ] <criterion 3 — left undone because…>

## Iteration index
- iter-001 — <one-liner from that summary> — demo: <link>
- iter-002 — <one-liner> — demo: <link>
- …

## Tests
- Added: N
- Total now passing: N
- Total still failing: N (see bugs.md)

## Open tickets (remaining)
- T-00XX — <title> — why left open: <reason>

## Diff stats vs start
- Files changed: N
- Lines added: N
- Lines removed: N
```
