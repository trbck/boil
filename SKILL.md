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

Then **compile the goal into checks** — this is the one LLM call that drafts:

```bash
# one LLM call writes .boil/milestones.json: one milestone per goal checkbox, each with a
# deterministic `check` command, `after:` dependencies, `protect:` paths, a `proxy_gap`
python3 <skill>/scripts/boil-check.py compile --root <project> --spec <project>/.boil/milestones.json
```

`compile` validates before it freezes: a check that already passes is rejected as
unfalsifiable, a `gold` command must pass, the outcome must repeat across runs; on
brownfield milestones pair a new-behaviour assertion with an `already_green` regression
guard. Only validated checks get a hash. A drafted-but-unfrozen spec is a lint error.
Milestone schema: `references/state-files.md`.

Set `budget.json` `goal_usd` to arm the budget brake. A goal with no budget has
no cost ceiling, and that is how 65-iteration runs happen.

If the project has no charter, write one (`templates/charter.md`) — a run loop
inside an ungoverned project is how effort stops converting into progress.

---

## Phase 2 — The loop

The controller is `boil-check.py`; you are the driver. Per milestone the LLM is called for
exactly two things — **drafting the check** (Phase 1) and **attempting the milestone** —
and decides nothing. The script decides. Its exit code is the instruction:

| Exit | Meaning | You do |
|---|---|---|
| 0 | PASS — an `EVIDENCE:` line was printed | copy the line onto the goal checkbox; `next` |
| 10 | RETRY — new failure signature | one fresh implementer call with the packet (below) |
| 20 | STALL — identical failure twice | `split` the milestone into 2–4 sub-checks, once; then ask |
| 30 | CAP — attempt ceiling (4) spent | split or ask the user; **never attempt again** |
| 40 | BUDGET — goal budget spent | stop; report cost against progress |
| 50 | TAMPER — a frozen check or protected file changed | abort; the user decides |
| 70 | REVIEW — a second model's must-fix findings (from `boil-review.py`) | `next` returns the `<M>-fix` node; after it passes, `close`; if 70 again, the user decides |
| 71 | PENDING — the review is still running | continue the loop; re-run `review` later |

One iteration:

```bash
python3 <skill>/scripts/boil-check.py next --root <project>            # {"milestone": "M3", ...}
python3 <skill>/scripts/boil-dispatch-packet.py --milestone M3 --root <project>
#   → dispatch one implementer (T1: you, in a fresh context; T2+: one builder subagent)
#     with ONLY that packet: statement, proxy gap, last counterexample. Never the check.
python3 <skill>/scripts/boil-check.py audit --root <project> --diff <the attempt's diff>
python3 <skill>/scripts/boil-check.py run --root <project> --milestone M3 --spent-usd <n> --rerun \
        --note <sha of the diff>
python3 <skill>/scripts/boil-review.py review --root <project> --milestone M3     # only after exit 0
```

### 2a — The attempt ladder is the retry policy

1 fresh generation → up to 2 feedback rounds, each seeded with the single counterexample
line the controller returned → 1 fresh-context resample → stop. Attempt 3 runs only if the
failure signature changed. The implementer never holds the check's source and has no tool
that runs it; the controller runs it once, after the implementer declares done. Two
execution-feedback rounds capture 76–95% of the achievable gain; a third adds nothing, and
in-context retries reproduce the same wrong program 33–68% of the time — hence the fresh
context, and hence the cap.

### 2b — Never lower the bar, never edit the ruler

A failed attempt is not information about the check. Re-authoring a check happens only
through `compile` (validated again, hashed again) and only because the check was *wrong*
— it passed on the baseline, failed on gold, or flaked. `audit` findings (writes under
protected paths, skip markers, monkey-patching, git-history access) are logged and count
against the attempt; they are never explained away.

### 2c — Demo

One user-visible artifact per passed milestone. **Never skip it.** The demo is a real
invocation of the built thing — the command and its captured output, the curl and its
response, the screenshot — not a description. Recipes: `references/demo-formats.md`.

### 2d — Tick, then the status line

```bash
python3 <skill>/scripts/boil-brakes.py tick --root <project> --iteration iter-NNN --spent-usd <n>
python3 <skill>/scripts/boil-check.py status --root <project>
```

`status` prints the only report:
`milestones 5/13 green | delta 8 | current M07 att 2/4 last=FAIL | spent $3.18/$25 | <ts>`.
Append the milestone's `EVIDENCE:` line to `.boil/log.md` (ladder format,
`references/outer-loop.md`). Do not write a narrative, a next-steps block, or a footer:
the ledger is the report, and prose about work whose truth value the script already
holds is the most expensive output in the loop.

### 2f — A second model reads the code, when the script says so

`boil-review.py review` runs after a PASS and *decides* whether a roborev review is worth
its cost — it is not fired per commit. It fires on a T3/T4 milestone, a `risk_paths` hit,
the final milestone, or once `every_lines` (default 150) unreviewed source lines have
accumulated; docs and `.boil/` never count, a job the post-commit hook already enqueued
for HEAD is adopted, and a milestone gets **one review round and one fix round**, never
more. Findings at or above `fix_min_severity` (default high) become a `<M>-fix` node whose
gate is the parent's frozen check; lower ones are deferred into `.boil/log.md` and the job
is closed — never silently dismissed. When the fix node passes, `boil-review.py close
--milestone <M>-fix` re-reviews once: clean closes both jobs; anything left is `OPEN`, the
brakes say STOP, and the user decides. The reviewer never replaces a green check.

### 2e — Continue or stop

Auto-continue under `/loop` while `next` returns a milestone and `boil-brakes.py check`
says CONTINUE. Any non-zero controller code other than 10 hands the decision to the user;
the driver never grants itself another attempt. A brake that fires is a planned exit:
commit work in progress to a branch, write `HANDOFF.md`, stop.

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
4. **The implementer never runs the check.** The controller runs it once, after
   the implementer declares done, and returns one counterexample line. Not the
   suite, not the trace, not the check's source.
5. **No milestone without a demo.**
6. **Validate before you freeze; never lower the bar.** A check passes `compile` or it
   does not exist. A failed attempt is not a reason to change the check, and a stalled
   milestone is split, never retried a fifth time.
7. **The brakes are binding.** A STALL/CAP/TAMPER/BUDGET verdict, three flat
   iterations, >5 actionable tickets, or a spent budget stop the loop and hand the
   decision to the user. The driver never grants itself another attempt.
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
| `references/effort-tiers.md` | assigning a milestone's tier (T1–T4), or disputing a ticket's |
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
| `boil-check.py` | compile/next/run/split/audit/status, and `verify` — re-run every frozen check now; `--write` stamps evidence on `{#id}`-tagged boxes |
| `boil-now.py` | the session-start read; writes `NOW.md` |
| `boil-brakes.py` | `tick` per iteration; `check` the brakes, including the controller's and the reviewer's last verdict |
| `boil-review.py` | milestone-wise roborev: `review` (decide by risk score, one round, route findings), `close` (one re-review) |
| `boil-doctor.py` | state validation; `--final` is the termination gate |
| `boil-portfolio.py` | regenerate `PORTFOLIO.md`; `--check` exits 1 on violations |
| `boil-migrate.py` | fold `.gate/` into `.boil/`; bootstrap the new files |
| `ticket-lint.py` | ticket schema, tier, answer key, and goal-size lint |
| `boil-loop.py` | the T3 adversarial protocol — blast-radius milestones only |
| `boil-commit-guard.py` | no AI attribution in commits; run before any push |
| `boil-assert-db.py` | a data check as a command: `--db --query --assert`; exit 0/1/2 is the verdict |
| `boil-guard.py` | PreToolUse hook: the worker never edits tests/, `protect` paths, or the frozen ruler; `--settings-json` wires it |
| `boil-run-iteration.sh` | doctor + lint + stories + tests + iteration verify |

## Integration

- `superpowers:test-driven-development` for T2/T3 implementation tickets,
  `:verification-before-completion` for every done claim,
  `:systematic-debugging` when a failure is non-obvious,
  `:dispatching-parallel-agents` for the 2b mechanics.
- **helm** is a cockpit, nothing more: it lists projects with `.boil/`, drafts a goal, and
  launches ONE headless boil session per click with `boil-guard.py --settings-json` wired in.
  It measures nothing — `boil-check.py verify` is the ruler, and `boil-doctor.py --final`
  re-runs it before any FINAL. A `| human` evidence line is the operator's sign-off; a worker
  may never write one. Compile the ruler (`boil-check.py compile`) BEFORE wiring the guard: a
  guarded session can never write `.boil/milestones.json` or `.boil/checks/`; helm's
  goal-creation step owns draft → compile before the first Run.
- `/loop` wraps boil for unattended runs; `/schedule` for recurring ones.
- `hound` MCP over `WebFetch` for JS-heavy or bot-walled research fetches.

## Mental model

> One work-day at a small firm that knows what it costs. The team lead reads the
> board once, gives each job only as much process as its blast radius earns,
> proves the work with a demo the customer can check in 30 seconds, and writes
> the result down once. If three days pass with the board unmoved, the firm stops
> and asks whether this is the right job — instead of working a fourth.
