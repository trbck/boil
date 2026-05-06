---
description: "Start a boil dev-firm loop on the goal you provide"
argument-hint: "GOAL [till|until CONDITION]"
---

# /boil

Start a `boil` loop in the current session.

The `boil` skill (loaded by this command) runs a production-grade iterative dev-firm loop:
parallel skilled subagents, an inter-agent ticket pool, mandatory verification both directly
and from a different angle, and — every iteration — a user-visible demo so you can verify
the work in 30 seconds.

**Arguments:** Pass the goal as natural-language text. Use "till" or "until" to express the
stop condition.

**Examples:**

    /boil a better dashboard till the conversion chart loads under 200ms
    /boil the /api/orders endpoint until POST returns 201 with a real order_id
    /boil the failing test suite until 100% green
    /boil the docs site until every public function has an example

If the goal is fuzzy, the skill will ask 2–5 brainstorming questions before starting (it
won't ask everything — only the gaps). Otherwise it goes straight to writing
`.boil/goal.md`, confirms with you, and starts iterating.

**At the end of every iteration**, you'll get:

- A 10-line summary (what changed, goal progress, tests, next focus)
- A 30-second demo: an URL to open, a command to run, a screenshot to view, a diff to read,
  or a green test where there was a red one
- An open question: continue, refine the goal, pivot, or stop

**Stops when:** all `goal.md` checkboxes are green AND the latest demo passes user check, OR
you say stop, OR a hard blocker needs your input.

---

Start now with this goal: $ARGUMENTS

Use the `boil` skill to do this.
