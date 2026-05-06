# Brainstorm Questions — Phase 0

Read this when the user's `boil X till Y` request is missing a piece. Don't ask everything — only the gaps. The goal is to write a `goal.md` you and the user both believe in, in under 5 minutes of dialogue.

## When to skip these questions entirely

If the request already gives you all five elements below, skip the questions and go straight to writing `goal.md`. Read it back to the user in 3–5 lines for confirmation.

The five elements:

1. **A concrete artifact** — which page / command / endpoint / file
2. **An observable stop condition** — something demoable, not a feeling
3. **Scope boundaries** — what's in, what's out
4. **A quality bar** — prototype | personal | production
5. **A demo target** — *how* the user will see it works

If 4 of 5 are clear, ask only about the missing one. If 2+ are missing, do a brief structured pass.

## The question pool

Pick the 2–5 most relevant. Ask them in one message; don't drip-feed. Adapt wording to the user's tone.

### Artifact clarity

> "When you say `<thing>`, are you pointing at a specific file/page/command, or do I need to pick one? If I should pick, what would convince you I picked right?"

Use this when the target object is ambiguous. ("the dashboard" — which one?)

### Demo / stop condition

> "How will you, in person, *see* this is done? An open URL you click, a command you run, a test that turns green, a screenshot, a number that drops?"

This one is almost always worth asking. The user often has a clear picture and just hasn't said it. The answer becomes the skill's hard target — every iteration's demo points at this.

### Done definition

> "What's the smallest set of checkboxes that, if all green, means I can stop? Three to five things, each one I can verify."

Drives the `Success checklist` section of `goal.md`. If the user gives you something fluffy ("it should feel snappy"), gently push for an observable form ("under 200ms p95? Loads without a spinner? Pick the one you'd actually measure").

### Scope / off-limits

> "Anything I should *not* touch — files, services, deploy steps, third-party APIs? Anything that, if I changed it, would be the wrong move even if it 'worked'?"

Skip if the project is small or greenfield. Critical on existing codebases.

### Quality bar

> "Throwaway prototype, personal tool, production for a team, or production for paying users? This sets how much testing, error handling, and polish I bake in."

The honest answer matters — overbuilding for a prototype wastes loops, underbuilding for production wastes trust.

### Iteration / time budget

> "Any cap on how long I should run? E.g., 'stop after 5 cycles', 'stop by 6pm', or 'just go until done'?"

Useful for unattended `/loop` wraps. Skip for normal interactive runs.

### Existing baseline

> "Is there current behavior I should preserve, or are we replacing this from scratch? If preserving — anywhere I can run the old version to compare against?"

Critical when the goal is a rewrite or refactor. Surfaces the regression test angle for Pass 2 (adversarial re-test).

### Verification access

> "What can I run to verify changes — test command, lint command, dev server start command? Any credentials/setup needed for end-to-end checks?"

If the project doesn't have an obvious test or run setup, ask now. You'll need it every iteration; better to know up front than to fake demos because you can't run anything.

### User-facing demo capability

> "When I demo, can I open a localhost URL on your machine? Take screenshots? Run shell commands you can see the output of? I want to know which demo formats actually reach you."

Especially relevant when the user is remote, on Cowork, or in a constrained environment. Pick demo formats from `demo-formats.md` that match what actually reaches them.

---

## After the user answers

1. Write `.boil/goal.md` using the template in `state-files.md`.
2. Read it back in 3–5 lines: "Here's what I'm working toward — does this match?"
3. **Wait for confirmation.** Don't start Phase 1 until the user signs off (explicit "yes", "looks right", "go", or equivalent).

If the user pushes back on any element, edit `goal.md`, re-read, re-confirm. The 30 seconds you spend here saves hours of misdirected iteration.

---

## Anti-patterns

- **Don't ask all eight questions.** That's an interrogation, not a brainstorm.
- **Don't accept "make it good".** Push gently for an observable form, but only once. If the user genuinely doesn't have a metric, default to "matches a reasonable interpretation that I'll demo each iteration so you can correct me."
- **Don't write goal.md before asking.** That feels like you ignored the user.
- **Don't start the loop without confirmation.** Even if you're sure the goal is right, the read-back-and-confirm step is what makes the user feel in control of the firm.
