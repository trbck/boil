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
type: bug | feature | test | research | refactor | demo-prep | docs | human-action
specialty: frontend | backend | qa | debugger | code-review | design | devops | data | docs | general | brainstorm | verification | review | parallel-dispatch | orchestrator | ticket-triage | error-detective
status: open | in-progress | blocked | done | wontfix
priority: P0 | P1 | P2 | P3
proof_strategy: red-green | characterization | verification-only | rendered-doc | research-artifact | perf-baseline
opened_by: orchestrator | T-0040 | agent:frontend
opened_at: 2026-05-05T14:32:00Z
blocked_by: []                       # list of ticket IDs that must be done first
confidence:
  requirements_understood: 0          # 0-100; done tickets must be >=99
  implementation_matches: 0           # 0-100; done tickets must be >=99
  verification_working: 0             # 0-100; done tickets must be >=99
  evidence: []                        # concrete proof artifacts/commands/links
  uncertainty: []                     # must be empty for `done`
human_action:
  required: false                     # true only when progress needs the user/operator
  reason: ""                          # e.g. "provide Stripe API key"
  safe_summary: ""                    # secret-free wording safe for external tools
  susi_task_id: ""                    # filled by local/private Susi bridge if available
  susi_sync_status: ""                # pending | created | failed | skipped
  pushover_status: ""                 # sent | not_configured | failed | skipped
closes_goal_checkbox: ["criterion 2"]  # which goal.md checkbox(es) this closes (optional)
closes_stories: [STORY-001]          # required for user-perceivable behavior
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

- **`type`** — Use `demo-prep` when an iteration's work needs more user-visible polish before it can be demoed (a real, common situation). Use `human-action` when the only next step is outside the agent's control: the user must provide a credential, approve an account, make a product decision, grant access, run hardware, or do some other project-specific action.
- **`specialty`** — Match against `routing.md`. Use `general` only when nothing else fits. If using the superpowers-compatible routing profile, prefer `verification` for independent proof checks, `debugger` or `error-detective` for root-cause work, `parallel-dispatch` or `orchestrator` for coordination/tooling tickets, `brainstorm` for goal shaping, and `review` or `code-review` for review work.
- **`priority`** — P0 = blocker (loop can't make progress without it). P1 = critical to goal. P2 = needed for goal but flexible. P3 = nice-to-have.
- **`proof_strategy`** — Pick the proof shape before dispatch. Use `red-green` for behavior/bug tickets, `characterization` for refactors that preserve behavior, `verification-only` for dependency/tooling changes, `rendered-doc` for documentation, `research-artifact` for spikes, and `perf-baseline` for performance work.
- **`confidence`** — Evidence-backed confidence, not vibes. A ticket may only be marked `done` when `requirements_understood`, `implementation_matches`, and `verification_working` are all `>=99`, `evidence` lists concrete artifacts/commands, and `uncertainty` is empty. If any score is below 99 or uncertainty remains, keep the ticket `in-progress` or `blocked` and file the next ticket needed to close the gap.
- **`opened_by`** — Lets you trace agent-to-agent chains. Useful when the loop produces a chain of tickets and you want to debug the cascade.
- **`closes_goal_checkbox`** — Optional but powerful. Lets the orchestrator pick tickets that move the needle on `goal.md`.
- **`closes_stories`** — Required when the ticket changes a user-perceivable surface (UI, endpoint response, CLI output, stream/event contract, generated artifact). Internal-only tickets may omit it, but the ticket body must state why no story applies.
- **`demo`** — How the user will see this specific ticket worked. The orchestrator uses this to assemble the iteration demo.
- **`proof`** — The strategy-specific proof map. For `red-green`, fill `red_test` before implementation. For other strategies, capture the relevant baseline/artifact first. Fill `green_test`, `full_suite`, and `demo_artifact` (or their strategy-specific equivalents) after verification. For frontend/user-visible tickets, `playwright` is mandatory; if the repo lacks Playwright, this ticket should either add it or depend on a setup ticket.
- **`acceptance`** — Concrete, checkable. The implementing agent must satisfy these; the orchestrator verifies.
- **`human_action`** — Required for blocked human-action tickets. Keep `safe_summary` secret-free and GitHub-safe. Never write API keys, account IDs, personal tokens, private URLs, or copied `.env` values into ticket files. The optional Susi sync writes only the safe summary and local project label.

### Human-action blockers and Susi sync

When a ticket is blocked because the user must act, convert or file a dedicated `human-action` ticket instead of burying the need in notes. This gives the operator one canonical blocker and lets local tooling turn it into a Susi/Microsoft To Do task.

Use this flow:

1. Set `status: blocked`, `type: human-action`, `priority: P0` when the loop cannot continue without it, and `working_on: "blocked on user action: <safe summary>"`.
2. Fill `human_action.required: true`, `reason`, and `safe_summary`. The `reason` can be more specific but still must not contain secrets. The `safe_summary` is what external tools may see.
3. If the ignored local bridge exists at `<boil-skill-repo>/.susi-human-blockers/add_blocker.py`, run it from the project repo to add the Susi task. Record the returned task id in `human_action.susi_task_id` and `human_action.susi_sync_status: created`.
4. If the bridge reports a Pushover result, record it in `human_action.pushover_status`. Pushover sends only after the To Do item is created, and its message must use the same secret-free safe summary.
5. If the bridge is absent or fails, set `human_action.susi_sync_status: skipped` or `failed`, set `human_action.pushover_status: skipped` or `failed` as appropriate, keep the ticket blocked, and surface the action in the iteration summary.
6. Do not commit, paste, or push the bridge, its config, cookies, Pushover tokens, endpoint URL, or generated sync logs. `.gitignore` in the boil skill repo ignores `.susi-human-blockers/` for this reason.

Example:

```markdown
---
id: T-0043
title: Provide OpenAI API key for embeddings smoke test
type: human-action
specialty: general
status: blocked
priority: P0
proof_strategy: verification-only
opened_by: T-0042
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
human_action:
  required: true
  reason: "User needs to add the OpenAI API key to the project environment."
  safe_summary: "Add the missing OpenAI API key to the project environment, then ask boil to continue."
  susi_task_id: ""
  susi_sync_status: pending
  pushover_status: pending
working_on: "blocked on user action: add missing OpenAI API key"
demo: |
  After the key is available, run the smoke test named in the parent ticket.
proof:
  verification: "env check plus parent smoke test"
acceptance:
  - Required key is available to the local project process.
  - Parent ticket's smoke test runs without auth/config failure.
---

## Context
The implementation is ready, but verification cannot run until the operator supplies the credential locally.
```

## Ticket ID allocation

Canonical ticket IDs (`T-NNNN`) are owned by the orchestrator only. Parallel agents must not scan for "the next free ID" and create `.boil/tickets/T-XXXX.md` themselves; two agents can race and pick the same ID.

When an agent discovers new work, it writes a proposal instead:

```text
.boil/tickets/proposals/<source-ticket>-<short-slug>.md
```

Proposal files use this shape:

```markdown
---
title: <one-line>
type: bug | feature | test | research | refactor | demo-prep | docs
specialty: <suggested specialty>
priority: P0 | P1 | P2 | P3
opened_by: T-NNNN
blocked_by: []
closes_goal_checkbox: []
closes_stories: []
proof_strategy: <suggested proof strategy>
---

## Context
<what was found, with repro/artifacts>

## Suggested acceptance
- <checkable criterion>
```

After agents return, the orchestrator reads every proposal, assigns the next canonical `T-NNNN`, resolves priority/specialty, writes the real ticket, and either deletes or moves the proposal to `.boil/tickets/proposals/accepted/`.

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

## Your job — proof strategy order

Work in this order. Do not skip steps. Do not interleave them.

0. **Confirm requirements before implementation.** Restate the ticket's user requirement, acceptance criteria, and out-of-scope boundaries in `## Working notes`. If anything is ambiguous enough that you cannot be at least 99% confident you understand what the user wants, stop and file a `human-action`, `product`, or `brainstorm` proposal instead of coding.
1. **Read `proof_strategy` and produce the pre-change proof first.**
   - `red-green`: write the failing test(s) first. Run them; confirm
     they fail with a clear "feature not yet implemented" message (not
     import errors / syntax errors). Update `proof.red_test` with the
     test name + command + failing stdout line.
   - `characterization`: add or identify behavior-preservation tests
     before the refactor. Run them on the current code and capture the
     passing baseline.
   - `verification-only`: name the existing command or smoke check that
     proves the tooling/dependency change after implementation.
   - `rendered-doc`: identify the rendered preview/build command and
     the doc section that must appear.
   - `research-artifact`: create the findings artifact path and the
     questions it must answer.
   - `perf-baseline`: run the baseline workload first and capture the
     before numbers.
   Update `working_on:` to "building proof for <area>".
2. **Implement the change** to satisfy the ticket. Update
   `working_on:` to "implementing <thing>".
3. **For frontend/user-visible behavior, add or update the Playwright
   test before claiming UI correctness.** The Playwright test must
   exercise the actual user flow, not just assert that a component
   rendered. Update `proof.playwright` with the spec path and command.
4. **Run the ticket's proof command(s), then the project's full test
   suite** where a suite exists. Update `working_on:` to "running
   verification".
5. **Fix any failures until the ticket proof and regression set are
   green.** If a regression appears, you broke something — fix or
   revert. Do not commit / stage code with red tests.
6. **Re-run + capture the final output line** (e.g. `47 passed in
   2.3s`, docs build success, perf before/after table). Fill
   `proof.green_test` and `proof.full_suite` or the strategy-specific
   equivalent. Set `working_on:` to "done — proof green, awaiting
   orchestrator verify".
7. **Fill the confidence gate.** Before returning green, update
   `confidence.requirements_understood`, `confidence.implementation_matches`,
   and `confidence.verification_working`. Use `99` or `100` only when backed
   by concrete evidence listed in `confidence.evidence`. If any score is
   below 99 or `confidence.uncertainty` is non-empty, do not mark the ticket
   done; file the next ticket/blocker that would raise confidence.
8. If you discover work outside your specialty, DO NOT try to do it.
   File a proposal at `.boil/tickets/proposals/T-NNNN-<short-slug>.md`
   with `specialty:` set and `opened_by: T-NNNN`. Append to
   `## Working notes` of your own ticket. Continue with what you
   CAN do.
9. If you hit a blocker that needs operator input, set
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

### Proof / tests
- Strategy: <proof_strategy>
- Added: <test names + file:line, or "not applicable">
- Pre-change proof: <RED test, characterization baseline, rendered-doc target, perf baseline, etc.>
- Final proof: <command + passing output line / artifact path / before-after numbers>
- Full suite: <command + passing output line, or "not applicable">
- Playwright/browser: <spec + command + result, or "not applicable — non-UI">
- Status: <green | N failures (list)>

### Confidence gate
- Requirements understood: <0-100> — <evidence/why>
- Implementation matches: <0-100> — <evidence/why>
- Verification working: <0-100> — <evidence/why>
- Remaining uncertainty: <none | list concrete uncertainty/blockers>

### New ticket proposals filed
- `.boil/tickets/proposals/T-NNNN-<slug>.md` — <title> — specialty: <…>  (or "none")

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
    dispatch_field = routing.dispatch_field
    dispatch_target = routing.routes[specialty]
    Dispatch via the platform subagent tool with <dispatch_field>=<dispatch_target>,
    prompt=<filled template above>

ALL dispatches go in ONE assistant message (multiple subagent tool blocks)
so they execute concurrently.
```

If `routing.md` has no entry for the ticket's specialty, fall back to the platform default (`worker` on Codex, `general-purpose` on Claude-style rich-agent installs) and log a TODO to add the routing entry.

## Inter-agent handoff rules

These rules keep the firm from devolving into chaos.

1. **Agents don't pick their own next work.** When an agent finishes, it returns and waits. The orchestrator picks the next batch.
2. **Agents file ticket proposals, they don't dispatch or assign canonical IDs.** Filing = writing a proposal `.md` file in `.boil/tickets/proposals/`. Dispatching = invoking another subagent. Only the orchestrator dispatches and assigns `T-NNNN`.
3. **Agents don't edit other agents' tickets.** They can append to the `## Notes` section of their own ticket, and they file proposals — but they don't modify the metadata or notes of other tickets.
4. **Closure is the orchestrator's job.** When an agent returns, the orchestrator (you) reads the report, verifies, and sets `status: done` or canonicalizes blockers. Agents may set their own ticket to `blocked` only when they hit a real blocker and explain it in `working_on` + `## Working notes`.
5. **No two agents on the same ticket.** Before dispatching, mark `status: in-progress` so a future cycle's pick logic can't double-book.
6. **Bug-discovery → proposal + bug log.** If an agent's verification reveals a bug elsewhere, file it as a ticket proposal AND append it to `bugs.md`. Both: the bug log is for human review, the canonical ticket is for the loop after orchestrator acceptance.

## Worked example

Iteration 3 picks `T-0007 (frontend, P1)` — "Make filter change refetch chart data".

Orchestrator dispatches to the `frontend` route from `.boil/routing.md` with the prompt template.

Agent returns:
- Implemented the refetch hook, added a unit test (green)
- BUT: discovered the API endpoint at `/api/metrics?range=...` returns 500 on the new query param shape
- Files proposal `.boil/tickets/proposals/T-0007-metrics-date-range-500.md` — "Fix /api/metrics 500 on date-range param" — suggested `backend`, P0
- Sets own ticket `status: blocked`, `blocked_by: [T-0011]`
- Returns its report

Orchestrator:
- Verifies the changed files via `git diff`
- Updates `T-0007` status to `blocked` (matches what agent reported)
- Assigns canonical `T-0011 (backend, P0)` from the proposal and adds it to the pool
- Iteration 3's demo shows: the refetch hook works in the unit test, but the user-visible flow blocks on T-0011 (which is now P0 and will be picked in iteration 4)
- Iteration 4 picks T-0011, routes to backend specialist; once T-0011 closes, T-0007 unblocks

This pattern — file a ticket, mark blocked, return — is the firm's coordination mechanism. It scales.
