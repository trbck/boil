# The outer loop — charter, ladder, portfolio

> **Load when:** running init, an audit, or a portfolio review; writing a charter or ladder; or any time a brake fired and you need the rule behind it.

Absorbed from the `gate` skill on 2026-08-28. gate was correct and unused: it
was a separate skill, so running it was voluntary, and voluntary governance is
not governance. Measured that day — 4 of 15 projects with `.boil/` state had a
`.gate/` directory at all, and `PORTFOLIO.md` had been sitting on an unresolved
"WIP limit breached" for five weeks.

boil now owns three scopes. This file covers the outer two; `SKILL.md` covers
the run loop.

| Scope | Question | When | Where |
|---|---|---|---|
| Portfolio | should I be in this project at all? | session start, automatic | `PORTFOLIO.md` |
| Ladder | is the project converging? | end of every iteration | `.boil/ladder.md`, `.boil/log.md` |
| Run | is this one thing built and proven? | the loop | `.boil/goal.md` |

## The maturity ladder

Every project climbs the same six levels. `ladder.md` customises the criteria;
the meaning of each level is fixed.

| Level | Name | The gate question |
|---|---|---|
| **L0** | Spark | Charter written. Deliberate decision this beats the alternatives. |
| **L1** | Skeleton | Core loop works end-to-end once, on the dev machine. |
| **L2** | Usable by me | I use it for its real purpose, repeatedly (>=3 times in a week). No data-loss bugs. Setup documented. |
| **L3** | Survives a stranger | Deployed/installable without me. Errors handled, restarts clean, secrets out of code, a stranger onboards from the README. |
| **L4** | Valuable to others | Business: >=1 external user, unprompted, feedback captured. Life-tool: 30 consecutive days of real use. |
| **L5** | Profitable / load-bearing | Business: recurring revenue >= the charter's target. Life-tool: removing it would hurt. |

Rules:

- **Levels are sequential.** L3 work does not matter while L2 criteria are open.
  Exception: a security or data-loss fix is always in scope.
- **The most important criteria are not code.** L4/L5 force distribution, users
  and money — the things a coding loop never reaches on its own. An LLM cannot
  do these for you; the ladder's job is to keep putting them in front of you as
  `human-action` tickets instead of permitting another refactor.
- **Criteria must be observable.** "Improve reliability" is not a criterion.
  "Survives `docker restart` with zero data loss, verified by test X" is.

## Evidence

A checkbox — on the ladder or in `goal.md` — flips only with an evidence line on
the same line:

```
- [x] Core loop runs end-to-end — EVIDENCE: `pytest tests/e2e -q` -> 4 passed | 2026-08-28 | auto
```

Format: `EVIDENCE: <command -> result | URL | number | path> | <YYYY-MM-DD> | <auto|human>`

- `auto` — re-verifiable by re-running the command. Goes **stale after 14 days**:
  the box stays ticked, the audit flags it, and it does not count toward the gate
  until re-verified.
- `human` — requires a human observation ("3 users recruited", "Stripe shows
  €147"). Expires after 30 days for usage and revenue criteria.
- No fresh verification, no claim. Run the command, paste the result, then tick.

**This is the merge seam.** `boil-doctor.py --final` refuses to declare a goal
done unless every checked box carries this line — so one green boil goal emits
evidence that is already in ladder format, and ticking the ladder is a copy, not
a re-derivation. That hand-off used to be prose, which is why it never happened.

## The ticket pool replaces gate's todo.md

gate had NOW (<=5) / NEXT / ICEBOX. boil's ticket pool does the same job, and the
WIP brake enforces the same limit mechanically:

1. **Max 5 actionable tickets** (`open` + `in-progress`). `boil-brakes.py check`
   reports RESTRICT above that; the overflow goes to `.boil/icebox.md` and is not
   routed. This exists because the pool is a *generator*: passes 2-4 file tickets
   rather than fixing, so without a ceiling it outruns the consumer. Measured:
   ttengine 156 done / 40 open; trtools2 173 done / 104 open.
2. **New ideas go to the icebox by default.** The exception is work that unblocks
   a current-gate criterion.
3. **Bugs beat features.** A bug breaking a previously-passed criterion reopens
   that checkbox and goes to the top.
4. **Items are outcomes, not activities.** "signup returns 200 and sends mail"
   not "work on auth".
5. **Human-action tickets are first-class.** "Email 5 potential users", "set up
   Stripe" sit in the pool like any other ticket. If the top item is a human
   action, the loop's job is to *prepare* it — draft the post, the email, the
   checklist — and surface it, never to quietly pick a code ticket instead.

## The three brakes

`boil-brakes.py check` runs all three and returns CONTINUE (0), RESTRICT (2), or
STOP (3). `boil-now.py` embeds the result, so the session sees it at start.

1. **Stall** — three consecutive *measured* iterations with no checkbox moving.
   The loop exits and asks: split the criterion, re-scope the goal, or park the
   project. This is the brake that would have stopped trtools2 at iteration 10
   instead of 69. A fully green goal is completion, not a stall, and does not
   trigger it. Backfilled records from `boil-migrate.py` carry `green: null` and
   do not count.
2. **WIP** — more than 5 actionable tickets. Drops to RESTRICT: no new tickets
   until the pool is back under.
3. **Budget** — `.boil/budget.json` holds `goal_usd`. At 60% spent: RESTRICT,
   meaning T1 work only and no new tickets. At 100%: STOP and report spend
   against checkboxes closed. Record spend with
   `boil-brakes.py tick --spent-usd <n>`.

## Portfolio

`boil-portfolio.py` regenerates `PORTFOLIO.md` from every `<project>/.boil/charter.md`
in the workspace (falling back to a pre-migration `.gate/charter.md`).

Hard rules:

1. **Max 3 projects `status: active`.** Everything else is `parked` with an
   explicit re-entry condition, or `killed` with a three-line post-mortem in its
   charter. `boil-now.py` exits 3 in a parked project: an agent asked to work
   there says so and stops.
2. **Weekly review.** Regenerate, then per active project ask only: did the score
   move? Two consecutive weeks without movement forces recommit (saying what
   changes), park, or kill. No silent limbo.
3. **Kill criteria are set at charter time**, before the sunk cost exists. Killing
   a project that met its kill criteria is the system working.
4. **New ideas do not get a directory.** They get a charter draft and enter as
   `candidate`. A candidate becomes active only by displacing a named active
   project.

### Health flags

`status: active` is a claim; commit activity is evidence. The generator compares
them, which the gate version did not:

| Flag | Meaning |
|---|---|
| `OK` | fresh audit, recent delta |
| `UNAUDITED` | >=20 commits in 30 days but no ladder delta in >30 days — **effort is not converting into gate progress.** This is the failure the whole system exists to catch. Measured on ttengine: 297 commits, 53 days without a delta. |
| `ZOMBIE` | active, little activity, no delta in >30 days |
| `DECLARED-DEAD` | `status: active` with **0** commits in 30 days — park it or recommit |
| `UNGOVERNED` | >=20 commits in 30 days, `.boil/` present, no charter — real work outside the portfolio entirely |
| `STALE-EVIDENCE` | current-level `auto` evidence past its 14-day TTL |

## Audit

Run on demand, every ~5 sessions, or weekly. The auditing agent:

1. Reads `.boil/` and `git log --oneline -20`.
2. **Re-runs every `auto` evidence command for the current level.** Marks stale
   ones; unticks broken ones.
3. **Drift check:** last 20 commits against the charter's goal and non-goals.
   Work serving no criterion is drift; name it.
4. Applies the 14-day challenge: any pool item untouched for 14 days must be
   done, deleted, or iceboxed.
5. Writes `scorecard.md` (template in `templates/`) with exactly **one**
   recommended next action.
6. Regenerates `PORTFOLIO.md`.

Score = `<current level> + <fraction of the next level's criteria with fresh
evidence>`, e.g. `L2 + 3/7 -> 2.43`.

## Bootstrapping (`/boil init`)

1. Read the project's README, CLAUDE.md, docs, and recent git history **first**.
2. Interview the user with <=10 questions to fill `charter.md`. Push on: who is
   the user, what is the north-star metric, what are the kill criteria, what is
   explicitly out of scope.
3. Draft `ladder.md`; mark plausibly-met criteria `[?]`, then **verify each with
   real evidence before ticking**. Most months-old projects land at L1-L2 with
   holes. That is the useful truth, not a failure.
4. Seed the ticket pool with the <=5 tickets that close the current gate.
5. Add `templates/claude-md-snippet.md` to the project's CLAUDE.md/AGENTS.md.
6. Log the init and run a first audit.
7. **Portfolio update is part of init, never a separate step.** Set
   `status: active`, run `boil-portfolio.py --check`, and if the WIP limit is now
   breached resolve it *inside the init*: ask which active project this displaces,
   park it with a one-line re-entry condition, re-run. Init is not complete until
   `--check` exits 0 or the user has explicitly acknowledged the remainder.
