# State Files — Templates

The core files in `.boil/`. Treat these as living state — agents read and update them, the orchestrator (you) curates them.

## `.boil/run.md`

Loop metadata. Written in Phase 1 and updated at each iteration boundary.

```markdown
# Boil Run State

**Started:** <ISO timestamp>
**Start SHA:** <short git SHA | (not-a-git-repo)>
**Current iteration:** iter-001
**Iteration start SHA:** <short git SHA | (not-a-git-repo)>

## Commit Policy

<checkpoint-commits | user-managed-commits | no-git>

- `checkpoint-commits`: after an iteration verifies green, create one checkpoint commit so roborev can review `--since <iteration_start_sha>`.
- `user-managed-commits`: do not commit automatically; use diff artifacts for demos and run roborev only if the repo/client supports reviewing an uncommitted diff.
- `no-git`: skip commit-scoped review and record why in the iteration summary.

## Review Policy

- Implementation agent/model: <codex | claude | mixed | unknown>
- Preferred roborev reviewer: <agent name different from implementation agent/model>
- Fallback if no different reviewer is available: log as skipped, file/keep a P2 tooling ticket, and do not claim cross-LLM review ran.
```

At the start of each iteration, set `Iteration start SHA` before dispatch. If the iteration creates a checkpoint commit, Pass 4 reviews the range from that SHA to HEAD. If no commit exists and no working-tree review mode exists, the summary must say review was unavailable rather than pretending Pass 4 ran.

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

## Proof map
<fill before Phase 1 dispatch; every checkbox needs a proof path>

| Goal checkbox | Proof strategy | Pre-change proof | GREEN proof | Playwright/browser proof | Story/rubric |
|---|---|---|---|---|---|
| <criterion 1> | `red-green` | `<cmd/test>` | `<cmd/output>` | `<spec or n/a>` | `<story/rubric or n/a>` |
| <criterion 2> | `rendered-doc` | `<section/build target>` | `<cmd/output>` | `<spec or n/a>` | `<story/rubric or n/a>` |

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

## Human-action blocker state

Human-action blockers live as normal tickets, not as a separate public state file. Use `type: human-action`, `status: blocked`, and the `human_action` frontmatter block defined in `references/ticket-system.md`.

Keep tracked state safe:

- Store only secret-free wording in `.boil/tickets/T-NNNN.md`.
- Do not copy credentials, cookies, `.env` values, personal account IDs, or private URLs into `.boil/`.
- If the optional Susi sync runs, write back only the resulting task id/status and Pushover delivery status.
- The Susi bridge and its config live under the boil skill repo's ignored `.susi-human-blockers/` directory, not in a user project and not in Git.

---

## `.boil/iterations/iter-NNN/` layout

Every iteration produces a directory:

```
iter-NNN/
├── summary.md      # the 10-line summary you posted to chat
├── demo.md         # THE user-visible demo (links + paste-able commands)
├── verify.log      # full output of the direct-verification commands (Pass 1)
├── retest.log      # full output of the adversarial re-test (Pass 2)
├── stories/        # story-run JSON records for Pass 0
├── judges/         # rubric verdicts consumed by stories and Pass 3
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
- Proof strategy: <red-green | characterization | rendered-doc | research-artifact | perf-baseline | verification-only>
- New: <test names>
- Pre-change proof: <RED test output | characterization baseline | rendered target | perf baseline | research questions>
- Final proof: <test command + passing output line | artifact path | before/after numbers>
- Playwright/browser: <spec + result, or "not applicable">

**Tickets touched:** <T-00XX done, T-00YY in-progress>
**New tickets filed:** <T-00ZZ (frontend), T-00AA (qa)>  — or "none"

**Bugs surfaced:** <B-XXX, B-YYY>  — or "none"

**Next focus:** <which ticket(s) next iteration will pick>

## Suggested next steps

1. <best next action for the user/operator, concrete>
2. <best next ticket or verification action if continuing>
3. <optional choice: refine/pivot/stop when relevant>
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
- Pre-change proof: `<test name or artifact>` — <what it asserts/proves> — `<cmd>` — <failing output line, baseline, or artifact path>
- Final proof: `<test name or artifact>` — `<cmd>` — <passing output line or artifact path>
- Full suite: `<cmd>` — <passing output line>
- Playwright/browser: `<spec>` — `<cmd>` — <passing output line, or "not applicable">

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

## Suggested next steps

1. <single handoff/confirmation action if complete, or the exact unblock action if blocked>
2. <optional follow-up verification/review action>
```
