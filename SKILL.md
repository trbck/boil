---
name: boil
description: Iterative dev loop to a verifiable goal, with project-level quality gates, a maturity ladder, and portfolio discipline. Use ANY time the user says "boil X till/until Y", or asks for sustained looped development toward a goal — "keep iterating until", "loop until done", "run a dev firm on this", "build X with full verification", "self-correct until X is true", "ralph this". ALSO use when the user asks to gate a project, audit a project, review the portfolio, decide what to work on, init project governance, or starts a coding session in any project containing a `.boil/` directory. Do not wait for the exact word "boil" — if the shape matches (a desired end-state + repeated try-test-fix cycles + wanting proof at each step), invoke this skill.
---

# boil — build one thing until it is proven, inside a project that is converging

**Announce at start:** "Using boil — I'll read NOW.md, work the loop, and show you a demo each cycle."

boil owns three scopes. Most of what used to be resident in this file now lives
behind the router at the bottom: read a reference when its trigger fires, not
before.

| Scope | Question | When |
|---|---|---|
| **Portfolio** | should I be in this project at all? | session start, automatic |
| **Ladder** | is the project converging? | end of every iteration |
| **Run** | is this one thing built and proven? | the loop |

The scopes rhyme on purpose: the ladder says *no checkmark without fresh
evidence*, the run loop says *never edit the answer key to pass a ticket*.
**Whoever is being measured never owns the ruler.**

---

## Step 0 — Session start: ONE read

```bash
python3 <skill>/scripts/boil-now.py --root <project> --write
```

`NOW.md` is ~40 derived lines: project status, ladder position, goal progress,
the brakes, blocked-on-you tickets, actionable tickets, last session. **Do not
read charter/ladder/log/goal/tickets separately** — NOW.md is derived from them.

Exit code is the instruction:

| Exit | Meaning | What you do |
|---|---|---|
| 0 | CONTINUE | work the top actionable ticket at its declared tier |
| 2 | RESTRICT | T1 work only, file no new tickets, say why in your first message |
| 3 | STOP | the project is parked or a brake fired — **put the decision to the user before any work** |

If there is no `.boil/` yet, this is a new project: go to Phase 0.

---

## Phase 0 — Crystallize the goal

Read-only discovery first: README, manifests, structure, tests, prior `.boil/`
state, the files the request names. Ask the user only what the workspace cannot
answer.

**A goal is ONE ladder criterion, not a project.** This is the highest-leverage
rule in the skill. Measured across 15 projects on 2026-08-28: susi's 976-byte
goal went 7/7 green; every goal between 4.6 KB and 8.3 KB landed at 0/7, 0/13,
or 2/7 — including one that ran 69 iterations and 308 tickets before being
archived. Goal size predicts failure better than anything else measured.

`ticket-lint.py` enforces it: **max 7 checkboxes, max 2500 bytes, a demo target
required.** Larger intent goes on the ladder (`references/outer-loop.md`), and
gets boiled one criterion at a time.

Write `.boil/goal.md`:

```markdown
# Goal
**One-line:** <what will be true that isn't now>

## Success checklist
- [ ] <observable — a command, a URL, a number. Not a feeling.>

## Requirements understanding
| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---:|---|

## How the user will see this works
<the exact action: open this URL, run this command, look at this file>

## Out of scope
- <the fence>
```

Model it on `examples/minimal-loop/boil-state/goal.md`. Interview until the
goal, constraints, tradeoffs, and success criteria are clear — but the output of
that interview is a *small* file. Completeness of understanding, brevity of goal.

The working detail goes elsewhere and may be as long as it needs to be: the
per-checkbox proof map in `.boil/proof-map.md`, stack and constraints in
`.boil/memory.md`. Templates for both: `references/state-files.md`.

**goal.md is sacred.** Scope changes get edited into it and confirmed with the
user first, never silently re-interpreted because an agent suggested it.

---

## Phase 1 — Bootstrap

```bash
python3 <skill>/scripts/boil-migrate.py --root <project> --apply   # existing project
```

Creates `.boil/` with `icebox.md`, `budget.json`, and `progress.jsonl`, and folds
in any legacy `.gate/`. Then write `memory.md`, `implementation.md`, `bugs.md`,
`routing.md`, and `tickets/`. Templates: `references/state-files.md`.

Set `budget.json` `goal_usd` to arm the budget brake. A goal with no budget has
no cost ceiling, and that is how 65-iteration runs happen.

If the project has no charter, write one (`templates/charter.md`) — a run loop
inside an ungoverned project is how effort stops converting into progress.

---

## Phase 2 — The loop

One iteration: pick → dispatch at tier → verify → demo → tick → ask.

Record `Iteration start SHA` (`git rev-parse --short HEAD`) in `.boil/run.md`.
That is the diff boundary for demos and review.

### 2a — Pick

From `NOW.md`'s actionable list: unblocked, highest priority, preferring tickets
that would close a `goal.md` checkbox. Pick 1–4. **If the WIP brake says
RESTRICT, close tickets before opening any.**

### 2b — Dispatch at the declared tier

`tier:` is a required ticket field, chosen by blast radius — what it costs if
this is wrong and nobody notices.

| Tier | What runs | Use for |
|---|---|---|
| **T1** direct *(default)* | you edit, you run the test, you show the diff. No subagent. | config, copy, docs, deps, small covered refactors |
| **T2** delegated | one builder subagent + **your own** independent verification | needs isolation, or parallelisable |
| **T3** adversarial | frozen answer key + builder + isolated judge in another model family + manager + cross-LLM review | money, auth, data loss, production — **or anything that failed twice at T1/T2** |

Most tickets are T1. Paying T3 everywhere is what produced 205 tickets for 2
checkboxes — and zero escalations across 86 loop directories, so it was not
buying rigor either. Full contract: `references/effort-tiers.md`.

**Only T3 tickets carry a frozen `answer_key`.** At T1 and T2 the proof is the
project's own suite via `proof_strategy` — a one-line fix does not need an
externally-authored, hash-protected ruler. `ticket-lint.py` enforces the key at
T3 and treats a *missing* tier as T3, so a ticket cannot dodge the key by
omitting the field.

Dispatch parallel tickets in **one message with multiple tool calls**. Agents may
*propose* tickets; you route them. Proposals beyond the WIP limit go to
`icebox.md` unrouted.

### 2c — Verify

**Always:** run the project's own tests/lint/build. Capture exit codes and real
output. Never "should pass". For each closed ticket, confirm its `proof_strategy`
evidence exists — RED→GREEN for behavior and bugs, characterization for
refactors, before/after numbers for performance.

**Always:** re-test from an angle the implementer did not. They wrote a unit test
→ you write an integration test. They tested the happy path → you test empty,
malformed, concurrent. They fixed a bug → you reproduce the symptom on the prior
commit, then on HEAD.

**Conditionally** — each of these is real work, so run it only on its trigger:

| Pass | Trigger |
|---|---|
| Story replay | the project has stories AND a closed ticket names one → `references/stories.md` |
| Rubric judge | a moved checkbox has a rubric attached → `references/rubrics.md` |
| Manager loop | the ticket is T3 → `references/self-correcting-loop.md` |
| Cross-LLM review | the ticket is T3 and roborev has a *different* reviewer available |
| Playwright proof | the goal touches a visible UI |
| Debug worksheet | the same ticket failed verification twice → `boil-debug-mode.py` |

If a conditional pass finds problems, file tickets and loop. Do not try to fix
everything in one iteration — that is what looping is for.

### 2d — Demo

One user-visible artifact. **Never skip it.** If you cannot produce one, the work
is not done from the user's point of view: file a `demo-prep` ticket and loop.

| Work type | Demo |
|---|---|
| Web UI | dev server + screenshot + the localhost URL |
| API | a `curl` one-liner **and its real captured response** |
| CLI | the command and its real output |
| Library | a ≤30-line diff with `file:line`, plus the now-passing test |
| Bug fix | the failing test before, green now, one-line root cause |
| Performance | before/after numbers, same workload |

Recipes: `references/demo-formats.md`.

### 2e — Tick, then report ONCE

```bash
python3 <skill>/scripts/boil-brakes.py tick --root <project> --iteration iter-NNN --spent-usd <n>
```

Then **one** block in chat. Not a machine summary *and* a narrative *and* a
next-steps block *and* a footer — those were four restatements of one state:

```
## Iteration N — <what a returning human needs to know in one line>

**Changed:** <2-3 bullets, file-level>
**Goal:** <X/Y checkboxes> — <which moved, or "none moved — <why>">
**Proof:** <the actual command output line, e.g. `47 passed in 2.3s`>
**Demo (30s):** → <the single action: open http://…, run `cmd`, view path>
**Next:** <1-3 concrete actions, most important first — an unblock action first if one exists>
```

Then append the same result as one line in `.boil/log.md` in EVIDENCE format
(`references/outer-loop.md`). That line is simultaneously the boil proof and the
ladder evidence — write it once, use it twice.

If the iteration made no real progress, or regressed, **say so plainly**. The
loop is only worth running while it tells the truth.

### 2f — Continue or stop

Auto-continue when invoked under `/loop` and the goal is not done — but always
emit the demo and pause. The demo is the user's interrupt window. If a brake
fired, stop and ask; do not decide on the user's behalf that the work is nearly
there.

---

## Phase 3 — Termination

```bash
python3 <skill>/scripts/boil-doctor.py --final --root <project> --write
```

The gate, not a promise: it refuses unless every checkbox is green **and** each
carries a fresh `EVIDENCE:` line. If it refuses, `--write` produces `HANDOFF.md`
— X of Y done, what is left, why — which is the honest artifact for an
unfinished goal.

Also stop when: the user says stop, or a human-action blocker cannot be resolved
without them (file the ticket, surface it, do not claim done).

On a clean FINAL: copy the evidence lines onto the ladder, append the session to
`log.md`, and regenerate the portfolio. For production work, prefer a branch and
a PR body from `boil-pr-summary.py` over pushing to `main`.

---

## Hard rules

Eight, each mechanically checkable. Everything else lives in the reference that
owns it.

1. **One read at session start.** `boil-now.py`. Exit 3 means stop and ask.
2. **A goal is one ladder criterion** — ≤7 checkboxes, ≤2500 B, a demo target.
   Enforced by `ticket-lint.py`.
3. **No claim without fresh output in the same message.** Run it, paste the
   line, then claim. Never from memory.
4. **Always re-test from an angle the implementer did not.**
5. **No iteration without a demo.**
6. **Tier by blast radius; raise it after two failures, never lower it.**
   Lowering a tier to get past a failure is the same move as editing the answer
   key.
7. **The brakes are binding.** Three flat iterations, >5 actionable tickets, or a
   spent budget stop the loop and hand the decision to the user. The manager
   never grants itself another attempt.
8. **Protect the user's work.** Never reset, stash, overwrite, or amend without
   explicit authorization. Never merge a PR without it — a plan, a green key, or
   an accepted loop is not merge authority. Never add AI attribution trailers or
   commit as an AI identity (`boil-commit-guard.py`; run before any push).

Baseline conduct is the Clanker Constitution — honor the request, act with
judgment, finish the job, protect existing work, verify reality, communicate for
humans, learn in the right place. It is a floor and never an excuse: "scale
process to the task" does not authorize skipping the clarity gate, the demo, or
a T3 ticket's answer key. Full text and mapping:
`references/clanker-constitution.md`.

Never write credentials, tokens, session cookies, or private IDs into `.boil/`.

---

## Router — read these only when the trigger fires

| Read | When |
|---|---|
| `references/outer-loop.md` | init, audit, portfolio review, writing a ladder or charter, or any brake fired |
| `references/effort-tiers.md` | choosing or disputing a ticket's tier |
| `references/ticket-system.md` | writing a ticket or a dispatch prompt |
| `references/state-files.md` | bootstrapping `.boil/` state files |
| `references/self-correcting-loop.md` | running a **T3** ticket |
| `references/demo-formats.md` | the demo format for this work type is not obvious |
| `references/stories.md` | the project has stories and this iteration touches one |
| `references/rubrics.md` | a moved checkbox has a rubric attached |
| `references/specialty-routing.md` | setting up `routing.md`, or a dispatch target is missing |
| `references/brainstorm-questions.md` | Phase 0 and the goal is genuinely fuzzy |
| `references/clanker-constitution.md` | a conduct question the eight rules do not settle |
| `references/helm-status.md` | this session is driven by a helm contract |
| `references/lsdf-codebase-index.md` | dispatch context is the cost driver |
| `references/plain-english-output.md` | wiring plain-English operator output |

## Scripts

| Script | Does |
|---|---|
| `boil-now.py` | the session-start read; writes `NOW.md` |
| `boil-brakes.py` | `tick` per iteration; `check` the three brakes |
| `boil-doctor.py` | state validation; `--final` is the termination gate |
| `boil-portfolio.py` | regenerate `PORTFOLIO.md`; `--check` exits 1 on violations |
| `boil-migrate.py` | fold `.gate/` into `.boil/`; bootstrap the new files |
| `ticket-lint.py` | ticket schema, tier, answer key, and goal-size lint |
| `boil-loop.py` | the T3 manager (builder/judge/decide/escalate/audit) |
| `boil-commit-guard.py` | no AI attribution in commits; run before any push |
| `boil-run-iteration.sh` | doctor + lint + stories + tests + iteration verify |

## Integration

- `superpowers:test-driven-development` for T2/T3 implementation tickets,
  `:verification-before-completion` for every done claim,
  `:systematic-debugging` when a failure is non-obvious,
  `:dispatching-parallel-agents` for the 2b mechanics.
- **helm** is the controller between the ladder and the run loop: a criterion
  contract turns a goal into machine-checkable subgoals, and `helm gate-sync
  --write` ticks the ladder box from a MET goal. Link a session with
  `boil-helm-log.py link --stem <contract>`.
- `/loop` wraps boil for unattended runs; `/schedule` for recurring ones.
- `hound` MCP over `WebFetch` for JS-heavy or bot-walled research fetches.

## Mental model

> One work-day at a small firm that knows what it costs. The team lead reads the
> board once, gives each job only as much process as its blast radius earns,
> proves the work with a demo the customer can check in 30 seconds, and writes
> the result down once. If three days pass with the board unmoved, the firm stops
> and asks whether this is the right job — instead of working a fourth.
