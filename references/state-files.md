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
- Reviewer resolution: pass the selected reviewer explicitly with `roborev --agent`; Claude/Claude Code implementations prefer `codex`, and Codex implementations prefer `claude-code`.
- Fallback if no different reviewer is available: log as skipped, file/keep a P2 tooling ticket, and do not claim cross-LLM review ran.
```

At the start of each iteration, set `Iteration start SHA` before dispatch. If the iteration creates a checkpoint commit, Pass 4 reviews the range from that SHA to HEAD. If no commit exists and no working-tree review mode exists, the summary must say review was unavailable rather than pretending Pass 4 ran. Do not let repo-local roborev defaults choose the reviewer implicitly; they may route Claude work back to `claude-code` or Codex work back to `codex`.

## `.boil/goal.md`

The contract, and the termination condition. Written in Phase 0, edited only when the
user explicitly refines scope.

**Hard size limits, enforced by `ticket-lint.py`:** max 7 checkboxes, max 2500 bytes
(warning above 1800), and a demo target is required. A goal is ONE ladder criterion, not
a project — measured across 15 projects, a 976-byte goal went 7/7 green while every goal
between 4.6 KB and 8.3 KB landed at 0/7, 0/13 or 2/7. If it does not fit, the excess
belongs on the ladder (`references/outer-loop.md`), to be boiled one criterion at a time.

Keep the working detail out of this file: the proof map lives in `.boil/proof-map.md`,
constraints and stack notes in `.boil/memory.md`. Those can be as long as they need to be.

```markdown
# Goal

**One-line:** <restate the goal in one sentence>

## Success checklist
<every box must be green AND carry an EVIDENCE line to finish>

- [ ] <criterion 1, observable — a command, a URL, a number. Not a feeling.>
- [ ] <criterion 2, observable>

## Requirements understanding

| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---:|---|
| <user requirement> | <what boil will build> | <how it is observed> | <0-100> | <none or question> |

## How the user will see this works
<concrete: which page, which command, which screenshot. Every demo points here.>

## Out of scope
- <the fence>
```

A checked box carries its evidence inline, in ladder format, so one green goal is
paste-ready for the ladder:

```markdown
- [x] POST /orders returns 201 — EVIDENCE: `pytest tests/api -q` -> 12 passed | 2026-08-28 | auto
```

`boil-doctor.py --final` refuses to declare the goal done unless **every** checked box
matches that shape. An unfinished goal gets `HANDOFF.md`, never `FINAL.md`.

A checkbox that a frozen milestone measures ends with `{#<milestone id>}`:

````markdown
- [ ] latest run clears the Sharpe floor {#sharpe_floor}
````

`boil-check.py verify --write` ticks tagged boxes whose check passes now and stamps the auto
EVIDENCE line itself; it never un-ticks and never touches an untagged box or a `| human` line.
`ticket-lint.py` warns on a tag with no frozen milestone and on a must-have milestone with no
tag. A `| human` line expires after 30 days — `boil-doctor.py --final` refuses older ones.

---

## `.boil/proof-map.md`

Split out of `goal.md` so the goal stays under its size limit. Fill before Phase 2
dispatch; every checkbox needs a proof path.

```markdown
| Goal checkbox | Tier | Proof strategy | Pre-change proof | GREEN proof | Browser proof | Story/rubric |
|---|---|---|---|---|---|---|
| <criterion 1> | T1 | `red-green` | `<cmd/test>` | `<cmd/output>` | `<spec or n/a>` | `<or n/a>` |
| <criterion 2> | T3 | `rendered-doc` | `<build target>` | `<cmd/output>` | `<spec or n/a>` | `<or n/a>` |
```

Semantic criteria (behavior, intent, subjective quality) carry an inline rubric block —
see `references/rubrics.md` for the YAML shape and the judge dispatch protocol.
Deterministic criteria (exit codes, latency, schema checks) do **not** need a rubric;
direct verification covers them.

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
- Confidence: requirements <0-100>, implementation <0-100>, verification <0-100>; uncertainty <none | list>

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

## `.boil/milestones.json` → `.boil/checks/frozen.json` (verifier-first)

The goal's checkboxes compiled into checks. One LLM call **drafts** `milestones.json`;
`boil-check.py compile` **validates** every entry and writes `checks/frozen.json` — the
only file the loop reads. A drafted spec without a frozen counterpart is a lint error.

```json
{
  "budget_usd": 25.0,          "cap": 4,               "stall": 2,   "determinism_runs": 2,
  "milestones": [
    {"id": "M1", "title": "POST /orders returns 201 with an order_id",
     "check": "pytest -q tests/api/test_orders.py::test_create_returns_201",
     "kind": "test",            "tier": "T1",
     "after": [],               "protect": ["tests/api/test_orders.py"],
     "gold": "",                "already_green": false,
     "proxy_gap": "status code and id shape; not idempotency, not auth",
     "must_have": true}
  ]
}
```

| Field | Meaning |
|---|---|
| `check` | the command whose exit code IS the verdict; the implementer never sees or runs it |
| `kind` | `test` \| `metric` \| `artifact` \| `rubric` \| `human` — the last two are advisory + human-gated |
| `tier` | `T1` greenfield · `T2` mechanical oracle (port/migration) · `T3` undocumented brownfield · `T4` non-testable / high blast radius — `references/effort-tiers.md` |
| `after` | dependency edges; `next` walks them topologically, passed nodes are never re-run |
| `protect` | files or directories hashed together with the check; any drift is `TAMPER` |
| `gold` | a command that must pass on a known-good state (gold-sanity) |
| `already_green` | this is a regression guard (PASS→PASS); the falsifiability gate is skipped |
| `proxy_gap` | one line: what the check does **not** measure. Required in spirit, linted as a warning |
| `must_have` | `false` marks nice-to-have nodes that never block completion |

`compile` rejects: a check that already passes (not falsifiable), a failing `gold`, an
outcome that differs across `determinism_runs`. The controller's ledger is
`checks/attempts.jsonl` — one record per attempt with `result`, `signature`,
`counterexample`, `spent_usd` — and `boil-check.py status` renders it as one line.
A recompile carries an unchanged frozen check (same hash) forward without re-validating
it, and archives only the attempts of checks that changed.

Two more commands complete the ruler. `boil-check.py verify` re-runs **every** frozen check now
(no attempt recorded, no cap, no budget) and reports MET / GAP / TAMPER — `boil-doctor.py --final`
runs it, so a green box is re-measured, never remembered. A data check is just a command:
`boil-assert-db.py --db runs/x.duckdb --query "select …" --assert "n >= 1"` exits 0/1/2. And
`boil-guard.py` (a PreToolUse hook, `--settings-json` prints the wiring) blocks the worker from
editing `tests/`, any `protect` path, the frozen ruler, or a `| human` evidence line.

### `review` — milestone-wise second-model review (optional, top-level in `milestones.json`)

```json
"review": {"enabled": true, "agent": "codex", "every_lines": 150, "fix_min_severity": "high",
           "always_tiers": ["T3", "T4"], "risk_paths": ["**/auth/**", "**/migrations/**"],
           "cost_usd": 0.0, "timeout_s": 900, "reasoning": ""}
```

| Field | Meaning |
|---|---|
| `every_lines` | fire once this many unreviewed *source* lines have accumulated since the last review (docs, lockfiles, `.boil/` never count); `0` = every milestone with a diff |
| `always_tiers` / `risk_paths` | milestones that are always reviewed regardless of size; globs are matched against changed paths |
| `fix_min_severity` | findings at or above this become the `<M>-fix` node; lower ones are deferred into `.boil/log.md` |
| `agent` | the reviewer — pick a different model family from the implementer |
| `cost_usd` | charged per review against `budget_usd`; a review that would overrun is skipped |

`compile` also records `base_sha` (HEAD at first freeze — the accumulator's origin, never
moved by a recompile) and keeps `<M>-fix` nodes across recompiles. The reviewer's ledger is
`checks/reviews.jsonl`: `SKIP` (with the reason), `CLEAN`, `DEFERRED`, `FIX-NODE`,
`PENDING`, `CLOSED`, `OPEN`. The final milestone is always reviewed once, so a goal never
finishes without a second model having read its whole diff.
