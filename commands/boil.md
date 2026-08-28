---
description: "Run a boil loop, or manage the project/portfolio gates"
argument-hint: "GOAL [till|until CONDITION] | init | status | audit | review | migrate"
---

# /boil

boil owns three scopes: the **portfolio** (should I be in this project?), the
**ladder** (is it converging?), and the **run loop** (is this one thing proven?).

## Subcommands

| Command | Does |
|---|---|
| `/boil <goal> till <condition>` | run the loop on a goal |
| `/boil init` | interview → charter, ladder, verified current level, first tickets, portfolio update |
| `/boil status` | read-only: print NOW.md — where the project is and the one next action |
| `/boil audit` | re-run every `auto` evidence command, drift check, regenerate the scorecard |
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

Work is dispatched at the **tier its blast radius earns**, not at a fixed
ceremony: T1 direct (most tickets — edit, test, show the diff), T2 delegated (one
builder subagent plus independent verification), T3 adversarial (frozen answer
key, isolated judge in a different model family, deterministic manager,
cross-LLM review) for money, auth, data-loss and production paths — or anything
that has already failed twice.

## What you get back

One block per iteration: what changed, goal progress, the real proof output, a
30-second demo, and the next concrete actions. The same result is appended to
`.boil/log.md` as a ladder EVIDENCE line — written once, used twice.

## When it stops on its own

Three brakes are binding and hand the decision to you rather than pressing on:

- **stall** — three iterations with no checkbox moving
- **WIP** — more than 5 actionable tickets
- **budget** — the goal's `budget.json` cap is spent

It also stops when every checkbox is green **and evidenced** (`boil-doctor.py
--final`), when you say stop, or when something only you can do is blocking. An
unfinished goal produces `HANDOFF.md`, never a `FINAL.md`.

---

Start now with: $ARGUMENTS

Use the `boil` skill to do this.
