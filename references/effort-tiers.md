# Effort tiers — how much ceremony a ticket pays

> **Load when:** choosing a ticket's tier, or disputing one. This is the file that decides how much a ticket costs.

Before this layer existed, every ticket paid the full adversarial protocol:
dispatch packet → builder subagent → independent judge → manager decision → five
verification passes → demo → three separate report surfaces. That is roughly six
model calls with their own context loads, and it was charged equally to a
one-line config change and to a payment flow.

The cost of that uniformity is measurable. Across 15 projects on 2026-08-28,
ttengine had run 65 iterations and 205 tickets to move 2 of 7 checkboxes;
`_archive/trtools2` ran 69 iterations and 308 tickets to move 0 of 13 before
being archived. Meanwhile `escalation.md` — the artifact the adversarial loop
writes when it catches something — existed **zero** times across 86 loop
directories. Universal ceremony did not produce universal rigor. It produced
universal cost.

So ceremony is now chosen by **blast radius**: what does it cost if this ticket
is wrong and nobody notices?

## The three tiers

### T1 — direct (the default)

The orchestrator makes the change itself, runs the project's own test/lint/build,
and shows the diff. No subagent, no judge, no separate answer key beyond the test
that already exists.

Use for: config, copy, docs, dependency bumps, log lines, small refactors with
existing coverage, anything a competent developer would commit without review.

Proof: the command and its real output, pasted. That is all.

### T2 — delegated

One builder subagent does the work; the orchestrator verifies independently
(reads the diff, runs the suite, checks the claim against the ticket).

Use for: work that benefits from context isolation, parallelisable batches, or
anything large enough that doing it inline would crowd the orchestrator's window.

Proof: the builder's report **plus** the orchestrator's own re-run. A builder's
word is not proof — that rule predates the tiers and survives them.

### T3 — adversarial (reserved)

The full protocol: a frozen answer key authored outside the builder, a builder
subagent, an independent judge in a different model family that never sees the
builder's reasoning, the deterministic manager (`boil-loop.py`) deciding
revise/accept/escalate, and a cross-LLM review of the diff.

Use for — and `ticket-lint.py` warns when a T1/T2 ticket mentions these:

- money: payment, billing, invoicing, refunds
- identity: auth, login, sessions, credentials, tokens, secrets
- data at risk: migrations, schema changes, deletes, truncation
- reach: production deploys, DNS
- **and: anything that has already failed twice at T1 or T2**

That last trigger matters more than the keyword list. Two failures mean the
cheap path has been falsified for this ticket; escalating tier is the response,
not a third cheap attempt.

Full protocol: `references/self-correcting-loop.md`. Read it only when you are
actually running a T3 ticket.

## Declaring and enforcing

`tier:` is a required ticket field. `ticket-lint.py` errors on a missing or
invalid tier and warns on an under-scoped one. The orchestrator sets it at
routing time; a ladder criterion or the user may force T3 on anything.

Tier can be raised mid-ticket and never silently lowered. Lowering a tier after
a failure is the same class of move as editing the answer key to pass.

## Budget interaction

When the budget brake reports RESTRICT (60% of the goal's cap spent), new work
runs at T1 only and no new tickets are filed. T3 tickets already in flight
finish; they are the expensive ones, and abandoning them halfway wastes what was
already spent. See `references/outer-loop.md`.
