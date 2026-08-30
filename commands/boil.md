---
description: "Run a boil loop, or manage the project/portfolio gates"
argument-hint: "GOAL [till|until CONDITION] | init | status | report | audit | review | migrate"
---

# /boil

boil owns three scopes: the **portfolio** (should I be in this project?), the
**ladder** (is it converging?), and the **run loop** (is this one thing proven?).

## Subcommands

| Command | Does |
|---|---|
| `/boil <goal> till <condition>` | run the loop on a goal |
| `/boil init` | interview → charter, ladder, verified current level, portfolio update |
| `/boil status` | read-only: print NOW.md — where the project is and the one next action |
| `/boil report` | one page for the current goal: attempts per milestone, first-attempt pass rate, $ per green box |
| `/boil audit` | re-run every frozen check (`verify`), drift check, regenerate the scorecard |
| `/boil review` | weekly portfolio review: moved / recommit / park / kill |
| `/boil migrate` | fold a legacy `.gate/` into `.boil/` and bootstrap the new state files |

## Running a goal

**A goal is one ladder criterion, not a project** — max 7 checkboxes, max 2500
bytes, and it must say how you will see it works. This is enforced, because goal
size predicts failure: a 976-byte goal in this workspace went 7/7 green, while
every goal over 4.6 KB landed at 0/7, 0/13, or 2/7. Bigger intent goes on the
ladder and gets boiled one criterion at a time.

**Examples:**

    /boil the /api/orders endpoint until POST returns 201 with a real order_id
    /boil the failing test suite until 100% green
    /boil the conversion chart until it loads under 200ms

If the goal is fuzzy, the skill inspects the workspace first, then asks only what
the workspace cannot answer.

## What each iteration costs

One LLM call drafts a deterministic check per checkbox; `compile` validates it (it
must fail now, pass on a known-good state, repeat, and bind to its box) and freezes
it. Then, per milestone, the loop is two commands and one dispatch:

    boil-check.py prepare   → the packet for the next milestone
    <one implementer subagent, holding only the packet>
    boil-check.py score     → audit, the check once, the box ticked by the script, one status line

The implementer never sees or runs the check; the guard denies it. One attempt, up to
two feedback rounds seeded with a single counterexample line, one fresh resample, then
stop. Nothing in between is an LLM call.

## What you get back

One status line per iteration —
`milestones 5/13 green | delta 8 | current M07 att 2/4 last=FAIL | spent $3.18/$25` —
a demo per passed milestone, and the goal's boxes ticked by the controller with the
evidence line it measured. `/boil report` is the page that says how it went.

## When it stops on its own

The script hands the decision to you rather than pressing on:

- **STALL** — the same failure twice → the milestone is split once, then it asks
- **CAP** — four attempts on one milestone
- **TAMPER** — a frozen check or protected file changed
- **BUDGET** — the goal's `budget.json` cap is spent
- **REVIEW** — a second model's must-fix findings survived their one fix round
- the ladder brakes: three flat iterations, or too many open tickets

It also stops when every box is green **and re-measured** (`boil-doctor.py --final`
re-runs every check), when you say stop, or when something only you can do is
blocking. An unfinished goal produces `HANDOFF.md`, never a `FINAL.md`.

---

Start now with: $ARGUMENTS

Use the `boil` skill to do this.
