# Ticket System

The ticket pool is how the firm coordinates. Agents write tickets to each other; the orchestrator routes them to the right specialist. This file defines the ticket schema, the dispatch prompt template, and the inter-agent handoff rules.

## Why tickets (not just a TODO list)

A flat TODO list collapses under parallel work. Tickets are durable, addressable units that carry their own context. Two properties matter:

1. **Specialty + routing.** Each ticket declares what kind of expertise it needs (`frontend`, `backend`, `qa`, `debugger`, …). The orchestrator looks up the matching subagent type in `routing.md` and dispatches accordingly. An agent never picks its own work — that prevents specialty thrash.
2. **Agent-to-agent handoff.** When an agent discovers work outside its specialty mid-task ("the test fails because the API returns 500"), it doesn't try to do it itself — it files a new ticket and returns. The orchestrator picks up the new ticket on the next iteration and routes it to the right specialist.

## Ticket schema

One file per ticket: `.boil/tickets/T-NNNN.md`. Use 4-digit zero-padded IDs.

```markdown
---
id: T-0042
title: Fix dashboard chart not refreshing on filter change
type: bug | feature | test | research | refactor | demo-prep | docs
specialty: frontend | backend | qa | debugger | code-review | design | devops | data | docs | general
status: open | in-progress | blocked | done | wontfix
priority: P0 | P1 | P2 | P3
opened_by: orchestrator | T-0040 | agent:frontend
opened_at: 2026-05-05T14:32:00Z
blocked_by: []                       # list of ticket IDs that must be done first
closes_goal_checkbox: ["criterion 2"]  # which goal.md checkbox(es) this closes (optional)
working_on: ""                       # ONE line: what the LLM is actively doing
                                     # (orchestrator sets on dispatch, agent updates
                                     # on return). E.g. "writing failing tests for
                                     # refetch hook" / "fixing 500 on date param"
                                     # / "done — closed by commit a4b5c6d". Empty
                                     # when ticket is `open` and not yet picked.
demo: |
  User opens http://localhost:3000/admin/metrics, changes the date filter,
  chart re-renders within 200ms with new data.
proof:
  red_test: "tests/dashboard/filter-refresh.test.ts::refetches on date change"
  green_test: ""                      # filled after implementation
  full_suite: ""                      # command + final stdout line
  playwright: "tests/e2e/filter-refresh.spec.ts"
  demo_artifact: ".boil/iterations/iter-NNN/artifacts/filter-refresh.png"
acceptance:
  - Filter change triggers refetch within 100ms
  - Chart re-renders without flicker
  - No console errors
  - Unit test covers the refetch logic
  - Playwright test covers the user-visible flow
---

## Context
<what's known, links to relevant files/lines, prior attempts if any>

## Working notes (append-only by agents — short status updates)
<empty until an agent picks it up. Append a one-paragraph "what I'm
doing right now / blockers / next step" so the operator can answer
"what is the LLM working on?" by reading this section.>

## Notes (append-only by agents — final reports)
<empty until an agent finishes>
```

### `working_on` field — purpose and contract

The `working_on` field is the operator's at-a-glance answer to "what
is the LLM working on right now?". One line, kept current.

**State transitions:**
- `open`, never picked → `working_on: ""` (empty).
- Orchestrator dispatches → orchestrator sets `working_on` to a tight
  one-liner describing the dispatch (e.g. "implementing T-0042
  refetch hook"). Status flips to `in-progress`.
- Agent makes meaningful progress → agent updates `working_on` (e.g.
  "writing failing tests" → "implementing fix" → "running test suite").
- Agent returns → agent sets `working_on` to a one-line summary of
  the return state (e.g. "done — tests green, awaiting orchestrator
  verify" or "blocked on T-0XXXX").
- Orchestrator closes → orchestrator sets `working_on` to e.g.
  "done — closed by commit <sha> on <date>".

A ticket file should answer "what is happening with this work?" by
reading the first 12 lines — `status`, `priority`, `working_on`,
`opened_at`. Detailed history goes in `## Working notes`.

### Field guidance

- **`type`** — Use `demo-prep` when an iteration's work needs more user-visible polish before it can be demoed (a real, common situation). This keeps the demo requirement honest.
- **`specialty`** — Match against `routing.md`. Use `general` only when nothing else fits.
- **`priority`** — P0 = blocker (loop can't make progress without it). P1 = critical to goal. P2 = needed for goal but flexible. P3 = nice-to-have.
- **`opened_by`** — Lets you trace agent-to-agent chains. Useful when the loop produces a chain of tickets and you want to debug the cascade.
- **`closes_goal_checkbox`** — Optional but powerful. Lets the orchestrator pick tickets that move the needle on `goal.md`.
- **`demo`** — How the user will see this specific ticket worked. The orchestrator uses this to assemble the iteration demo.
- **`proof`** — The TDD proof map. Fill `red_test` before implementation. Fill `green_test`, `full_suite`, and `demo_artifact` after verification. For frontend/user-visible tickets, `playwright` is mandatory; if the repo lacks Playwright, this ticket should either add it or depend on a setup ticket.
- **`acceptance`** — Concrete, checkable. The implementing agent must satisfy these; the orchestrator verifies.

## Dispatch prompt template

When dispatching a ticket to a specialist, use a self-contained prompt. The agent has none of your conversation context — give them everything they need.

```
You are working on ticket T-NNNN inside a `boil` dev-firm loop.

## The ticket
<paste ticket file contents>

## Goal context (relevant slice of .boil/goal.md)
<paste the relevant lines from goal.md — the one-liner and the success-checklist items this ticket touches>

## Codebase context (relevant slice of .boil/memory.md)
<paste the relevant lines: stack, where the goal-relevant code lives, run/test commands>

## Your job — strict TDD order

Work in this order. Do not skip steps. Do not interleave them.

1. **Write the failing test(s) FIRST.** For every acceptance
   criterion, write the test that would prove it. Run them; confirm
   they fail with a clear "feature not yet implemented" message (not
   import errors / syntax errors — those are tooling bugs you fix
   before counting the test as "failing"). Update `proof.red_test`
   with the test name + command + failing stdout line. Update
   `working_on:` to "writing failing tests for <area>".
2. **Implement the change** to make the failing tests pass. Update
   `working_on:` to "implementing <thing>".
3. **For frontend/user-visible behavior, add or update the Playwright
   test before claiming UI correctness.** The Playwright test must
   exercise the actual user flow, not just assert that a component
   rendered. Update `proof.playwright` with the spec path and command.
4. **Run the project's full test suite** (not just your new tests).
   Update `working_on:` to "running test suite".
5. **Fix any failures until ALL tests pass — yours AND the regression
   set.** If a regression appears, you broke something — fix or
   revert. Do not commit / stage code with red tests.
6. **Re-run + capture the test output line** (e.g. `47 passed in
   2.3s`). Fill `proof.green_test` and `proof.full_suite`. Set
   `working_on:` to "done — N tests green, awaiting orchestrator
   verify".
7. If you discover work outside your specialty, DO NOT try to do it.
   File a new ticket at `.boil/tickets/T-XXXX.md` (next free ID after
   T-NNNN) with `specialty:` set and `opened_by: T-NNNN`. Append to
   `## Working notes` of your own ticket. Continue with what you
   CAN do.
8. If you hit a blocker that needs operator input, set
   `status: blocked` + `working_on: "blocked on <reason>"` and
   describe the blocker in `## Working notes`.

**`working_on:` field is mandatory.** Update it at every state
transition. The operator reads it to answer "what is the LLM working
on right now?" without diving into the iteration log.

## Constraints
- Only modify files needed for this ticket.
- Don't refactor unrelated code, even if you see something messy — file a refactor ticket instead.
- Don't change test infrastructure unless the ticket asks you to.
- If the demo target requires running a dev server or producing a screenshot, leave
  the server running (note the port) so the orchestrator can demo it.
- If this is frontend work and no Playwright/browser harness exists, file a
  P0/P1 setup ticket instead of pretending unit tests prove the user flow.
- **No completion claim without paste-the-test-output evidence.** The
  Return section's `Tests:` line must contain the actual stdout (e.g.
  `47 passed in 2.3s`, not "should be green").

## Return
Return a structured report:

### Changed files
- <path> — <one-line>
- <path> — <one-line>

### Tests
- Added: <test names + file:line>
- RED first: <command + failing output line>
- GREEN: <command + passing output line>
- Full suite: <command + passing output line>
- Playwright/browser: <spec + command + result, or "not applicable — non-UI">
- Status: <green | N failures (list)>

### New tickets filed
- T-XXXX — <title> — specialty: <…>  (or "none")

### Blockers
- <description>  (or "none")

### Demo notes
- <how to see this works — URL, command, file:line of the diff, etc.>

### Acceptance criteria
- [ ] <criterion 1> — <met / not met / how to verify>
- [ ] <criterion 2> — <met / not met / how to verify>
```

Adjust the language to the agent type — a `qa-expert` and a `frontend-developer` care about different things, but the structure stays the same.

## Routing in code

Each iteration, after picking the batch:

```
For each ticket in batch:
    specialty = ticket.specialty
    subagent_type = routing[specialty]   # from .boil/routing.md
    Dispatch via Agent tool with subagent_type=<that>, prompt=<filled template above>

ALL dispatches go in ONE assistant message (multiple Agent tool blocks)
so they execute concurrently.
```

If `routing.md` has no entry for the ticket's specialty, fall back to `general-purpose` and log a TODO to add the routing entry.

## Inter-agent handoff rules

These rules keep the firm from devolving into chaos.

1. **Agents don't pick their own next work.** When an agent finishes, it returns and waits. The orchestrator picks the next batch.
2. **Agents file tickets, they don't dispatch them.** Filing = writing a `.md` file. Dispatching = invoking another subagent. Only the orchestrator dispatches.
3. **Agents don't edit other agents' tickets.** They can append to the `## Notes` section of their own ticket, and they file new tickets — but they don't modify the metadata or notes of other tickets.
4. **Status changes are the orchestrator's job.** When an agent returns, the orchestrator (you) reads the report, verifies, and sets `status: done` (or `blocked`). Agents themselves only ever leave their ticket in `in-progress` or note a blocker.
5. **No two agents on the same ticket.** Before dispatching, mark `status: in-progress` so a future cycle's pick logic can't double-book.
6. **Bug-discovery → ticket.** If an agent's verification reveals a bug elsewhere, file it as a ticket AND append it to `bugs.md`. Both: the bug log is for human review, the ticket is for the loop.

## Worked example

Iteration 3 picks `T-0007 (frontend, P1)` — "Make filter change refetch chart data".

Orchestrator dispatches to `voltagent-core-dev:frontend-developer` with the prompt template.

Agent returns:
- Implemented the refetch hook, added a unit test (green)
- BUT: discovered the API endpoint at `/api/metrics?range=...` returns 500 on the new query param shape
- Files `T-0011 (backend, P0)` — "Fix /api/metrics 500 on date-range param" — `opened_by: T-0007`
- Sets own ticket `status: blocked`, `blocked_by: [T-0011]`
- Returns its report

Orchestrator:
- Verifies the changed files via `git diff`
- Updates `T-0007` status to `blocked` (matches what agent reported)
- Adds `T-0011` to the pool
- Iteration 3's demo shows: the refetch hook works in the unit test, but the user-visible flow blocks on T-0011 (which is now P0 and will be picked in iteration 4)
- Iteration 4 picks T-0011, routes to backend specialist; once T-0011 closes, T-0007 unblocks

This pattern — file a ticket, mark blocked, return — is the firm's coordination mechanism. It scales.
