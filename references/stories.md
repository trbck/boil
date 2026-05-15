# User Stories — BPM-style acceptance contracts

A boil iteration that ends "all tests green" but doesn't survive a real user opening the thing is a known failure mode of agentic dev work. Mechanical assertions pass; the user-experienced behavior fails. The stories layer closes that gap by making each user-perceivable behavior a first-class artifact, written **before** the code, and replayed end-to-end by a runner that asserts functional + quant + UX in one pass — no human in the inner loop.

This is the boil adaptation of BDD / acceptance-test-driven-development, fused with the existing rubrics layer for the unavoidably-soft "feels right" checks.

---

## When to use stories (and when NOT to)

**Use a story when** the work creates or changes something a user (operator, end-user, downstream system) can *observe* — a button, an endpoint response, a CLI output, a stream emission, a generated artifact. The story is the contract: code is shipped to make the story green.

**Skip stories for** pure-internal refactors, dependency bumps, infra-only changes, doc-only commits. Those still go through Step 2d Pass 1 (direct verification); they just have no user-perceivable surface to story-test.

Rule of thumb: if a goal.md checkbox would make sense to read aloud to a non-engineer (operator, PM, end-user), it needs a story.

---

## Story file shape

One file per story in `.boil/stories/STORY-NNN.md`. Frontmatter is structured so the runner can parse it; the body is narrative + assertions.

```markdown
---
id: STORY-001
title: <one-line user-perceived behavior>
actor: <role — operator | end-user | downstream-consumer | …>
trigger: <event that starts the flow>
frequency: <how often this happens — per-deploy | weekly | daily | …>
closes_checkboxes:                    # which goal.md items this story proves
  - "<verbatim checkbox text>"
closed_by_tickets: [T-XXXX]           # auto-updated by the loop when tickets land
last_green_sha: ""                    # auto-updated by the runner
last_green_at: ""
last_red_reason: ""
last_red_lane: ""                     # functional | quant | ux — which lane failed
---

# Narrative

As a <actor>, when <trigger>, I expect <outcome>, so that <value>.

# Steps the runner replays

1. <action> → <expected observable>
2. <action> → <expected observable>
3. …

# Functional assertions (deterministic — runner asserts directly)

```yaml
- name: dashboard responds
  kind: http
  url: ${BASE_URL}/api/strategies
  expect:
    status: 200
    body_contains: ["STRATEGY_ID"]
- name: signal lands on the right stream
  kind: redis_xadd
  stream: signals.intake
  within_s: 5
  expect:
    body_contains: ["strategy=...", "side=buy"]
- name: DB row updated
  kind: sql
  driver: questdb            # project's adapters/functional.sh resolves the driver
  sql: SELECT status FROM strategies WHERE id='${STRATEGY_ID}'
  expect: "paper"
```

# Quant assertions (deterministic — runner calls project's gate evaluator)

```yaml
- name: promotion gates 7/7
  kind: gate
  bridge: .boil/stories/adapters/quant.sh
  args: [${STRATEGY_ID}]
  expect_exit: 0
- name: p95 latency under 200ms over a 1k-request run
  kind: latency
  endpoint: ${BASE_URL}/api/strategies
  n: 1000
  p95_ms: 200
```

# UX assertions (hybrid — properties hard, vibes via rubric)

```yaml
- name: promote button is present and enabled
  kind: dom
  selector: "[data-test=promote-btn]"
  expect:
    visible: true
    disabled: false
- name: promote button color in brand range
  kind: css_property
  selector: "[data-test=promote-btn]"
  property: background-color
  expect_in: ["#0066cc", "#0a78d4"]
- name: screenshot baseline (after step 3)
  kind: screenshot_diff
  step: 3
  baseline: baselines/STORY-001-step3.png
  threshold_pct: 2.0
- name: dialog clearly conveys risk
  kind: rubric
  rubric_id: R-STORY-001-dialog-risk     # defined inline below OR in .boil/rubrics/
```

# Rubric (inline; uses references/rubrics.md eval mechanism)

```yaml
id: R-STORY-001-dialog-risk
criterion: The confirmation dialog makes the risk of promotion obvious to a first-time operator.
eval_steps:
  - Look at iterations/iter-NNN/artifacts/STORY-001-step4-screenshot.png.
  - Extract every visible label/sentence in the dialog.
  - Verify the dialog names: (a) the strategy being promoted, (b) the sizing (% gross), (c) at least one risk word ("risk", "exposure", "live", "real money"), (d) a confirmable action button.
  - Return PASS if all four are present, FAIL otherwise.
artifacts_required:
  - iterations/iter-NNN/artifacts/STORY-001-step4-screenshot.png
pass_rule: all 4 steps return PASS
```
```

---

## Directory layout

```
.boil/stories/
├── STORY-001.md
├── STORY-002.md
├── …
├── MATRIX.md                    # auto-generated story status table
├── baselines/                   # screenshot baselines, one subfolder per story
│   └── STORY-001-step3.png
└── adapters/                    # optional project bridges (see below)
    ├── functional.sh
    ├── quant.sh
    └── ux.sh
```

Each story owns its own baselines directory. Baselines are committed.

---

## Adapters (project-supplied bridges)

The default runner handles HTTP, screenshot-diff, and DOM/CSS assertions out of the box (Playwright + curl). Anything project-specific — how to query *this* project's DB, how to invoke *this* project's gate evaluator, how to start *this* project's dev server — goes into `.boil/stories/adapters/`:

| Adapter | What it does | Story `kind`s it backs |
|---|---|---|
| `functional.sh` | Resolves project-specific drivers: SQL connection strings, Redis URLs, custom HTTP auth. | `sql`, `redis_*`, `http` with auth |
| `quant.sh` | Calls the project's gate evaluator (e.g. `python -m engine.controls audit`, `pytest engine/gates/`). Takes story args, exits 0/non-zero. | `gate`, `latency` |
| `ux.sh` | Starts/stops the dev server, configures Playwright with project-specific selectors or auth cookies. | `dom`, `css_property`, `screenshot_diff` |

Adapters are optional. A greenfield project starts with none and only adds them when a story needs a project-specific call. Default contract: stdin = JSON args from the story step, stdout = JSON result with `{status: "pass"|"fail", details: "…"}`, exit code = 0 (pass) / 1 (fail) / 2 (infra error).

---

## The runner

`scripts/story-run.sh STORY-NNN` (or `--all`) runs one story (or all) end-to-end and updates frontmatter + `MATRIX.md`. It is installed alongside the boil skill — generic, no project config required for the default cases.

Four lanes, one binary:

1. **Functional** — execute each `Functional assertions` entry. HTTP via curl, Redis via redis-cli, SQL via the project adapter. Each entry pass/fail captured.
2. **Quant** — invoke `adapters/quant.sh` per entry. Project's gate yaml + controls catalogue feed in here.
3. **UX (mechanical)** — Playwright headless. DOM presence + CSS properties + screenshot diff vs baseline.
4. **UX (rubric)** — for every `kind: rubric` entry, dispatch a `judge` subagent per the rubrics layer (`references/rubrics.md`). Verdict ∈ {PASS, FAIL, UNCERTAIN}. **UNCERTAIN is treated as FAIL** — no silent passes; if the judge can't tell, the story is red.

Story green iff all four lanes green.

Runner writes:
- `iterations/iter-NNN/stories/STORY-NNN.json` — full run record, lane-by-lane.
- Story frontmatter — `last_green_*` / `last_red_*` fields updated.
- `.boil/stories/MATRIX.md` — regenerated index.

Exit codes: 0 (all green), 1 (one or more red), 2 (infra error — couldn't start dev server, missing baseline, missing adapter).

---

## MATRIX.md (auto-generated)

Same shape as the controls matrix from the trading-platform integration — at-a-glance view of which stories are green, rotted, or never confirmed.

```markdown
# Stories matrix — auto-generated by scripts/story-run.sh

Last regenerated: <ISO ts>

| ID | Title | Last green SHA | Last green at | Status | Last red reason |
|----|-------|----------------|---------------|--------|------------------|
| STORY-001 | operator promotes a strategy to paper | a1b2c3d | 2026-05-15 14:22Z | ✓ green | — |
| STORY-002 | operator sees per-strategy fills | (never) | (never) | ✗ red | ux/screenshot_diff 8.3% > 2.0% |
| STORY-003 | crons emit weekly digest | e4f5g6h | 2026-05-08 09:00Z | ⚠ rotted (14d+) | — |
```

"Rotted" = last green > 14 days ago AND no story file edits since. Surfaces stories that haven't been replayed against current code in a while — common failure mode in long-lived projects.

---

## Integration with the boil loop

### Phase 0 — Goal crystallization (unchanged)

Goal.md continues to drive everything. New: every goal checkbox that names a user-perceivable behavior gets one or more stories in Phase 1.

### Phase 1 — Bootstrap (extended)

Two new bootstrap artifacts:

1. **Initial stories.** Before writing tickets, write one `.boil/stories/STORY-NNN.md` per goal checkbox that's user-perceivable. The story is the spec the tickets implement. A story without a matching goal checkbox is a smell — either the checkbox is missing or the story is out of scope.
2. **Adapter stubs (only if needed).** If the default runner can't reach the project's DB / gate evaluator / dev server, write the three adapter scripts. Keep them small: one `case`-style dispatcher per kind is usually enough.

The orchestrator must read every story file before dispatching tickets. Tickets that touch user-perceivable code reference stories via a `closes_stories` field:

```yaml
---
id: T-0042
title: Add promote button + confirm dialog to strategies page
specialty: frontend
closes_stories: [STORY-001, STORY-014]
status: open
priority: P0
---
```

### Phase 2 — The loop (Step 2d gets Pass 0)

A new pass slots in **before** Pass 1, because mechanical tests are downstream of the story contract:

**Pass 0 — Story replay (NEW).** For every story listed in any ticket's `closes_stories` that's completed this iteration, run `scripts/story-run.sh STORY-NNN`. If the story isn't green after the iteration's code lands, the iteration is **not** done — file a `demo-prep` ticket and loop. A story that was green before and is red now is a regression — file a `regression` ticket and loop.

The existing Passes 1–4 (direct verification, adversarial re-test, rubric judges, roborev) remain unchanged. Pass 0 sits on top: if the story doesn't replay, none of the other passes matter — the user experience is broken.

### Phase 2e — Demo (replaced)

The iteration's demo is no longer a hand-curated artifact. **The green story runner output IS the demo.** `iterations/iter-NNN/demo.md` is generated from:

- The MATRIX.md diff this iteration produced (red → green stories).
- Each story's `iterations/iter-NNN/stories/STORY-NNN.json` summary line.
- Direct links to the screenshot artifacts each green story produced.

A demo without an underlying story is forbidden for user-perceivable work. (Internal refactor iterations are exempt — they have no story to anchor to.)

### Phase 3 — Termination (extended)

Add to the termination conditions: every goal checkbox attached to a story must have at least one green story since the last code touch in the goal area. Stories rotted >14 days but still attached to a checked checkbox count as "not green" — they must be re-replayed (and pass) before termination.

---

## Hard rules

1. **No user-perceivable code change without a story.** If a ticket touches the UI, an endpoint shape, a CLI output, or a stream contract, it must list `closes_stories: [...]`. Tickets that fail this check don't get dispatched. (Internal refactor / dependency / infra work is exempt — but state so explicitly in the ticket body.)
2. **Stories are written before code.** The story is the spec. Writing the story after the code is just transcribing what happened, which defeats the purpose. The orchestrator drafts stories during Phase 1; ticket-filing agents may propose new stories but the orchestrator routes and approves them, same as tickets.
3. **UNCERTAIN rubric verdicts fail.** The runner does NOT pass a story whose UX rubric judge said "uncertain." The whole point of the rubrics layer is to refuse to vibe-check — if the judge can't decide, the story owes a clearer assertion or a better artifact.
4. **No silent baseline updates.** A screenshot baseline change is a story-level change. Bump it in a ticket whose body says *why* the UX is allowed to look different now. CI / pre-commit hooks can refuse silent updates to `.boil/stories/baselines/`.
5. **Adapters fail loud.** If `adapters/quant.sh` exits non-zero with no JSON body, the runner treats it as exit code 2 (infra error), not a failed assertion. Infra errors block the iteration too — don't paper over a missing adapter by calling it a story failure.
6. **The runner is the same in dev and CI.** Same script, same baselines, same adapter contracts. A green story locally must be green in CI. Divergence is a runner bug, never accepted as flakiness.

---

## What this trades

You're slowing the loop's outer cadence to harden the inner contract. A ticket now needs a story before it gets dispatched; an iteration now needs a green story replay before it claims done. In exchange, the "panel passes Playwright but shows empty data" failure mode goes away — empty data is a `body_contains` assertion that fails.

The trade is worth it when you have at least one of:
- Looped autonomous work where the user isn't watching every iteration.
- A UI surface where mechanical tests reliably miss real failures.
- Quant or numeric correctness that downstream consumers depend on.

The trade is *not* worth it for:
- Single-iteration one-shot work (just demo it).
- Pure-internal refactors with no user surface.
- Throwaway prototypes where the cost of writing the story exceeds the cost of re-doing the work.

If you find the stories layer slowing a project without catching anything for several iterations, remove it — but only after explicit user agreement. Don't silently skip pass 0.
