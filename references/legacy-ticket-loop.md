# The legacy ticket loop (parked 2026-08-30)

> **Load when:** the project has `.boil/tickets/` or `.boil/iterations/` and **no**
> `.boil/checks/frozen.json`. New goals do not use this loop; they compile checks and run
> `boil-check.py prepare` / `score` (SKILL.md Phase 2).

Before the controller, a boil iteration was a ticket: an orchestrator routed tickets to
specialists by `routing.md`, each iteration wrote `.boil/iterations/iter-NNN/` (summary,
demo, verify/retest logs), `boil-run-iteration.sh` ran doctor + lint + `boil-loop.py audit`
+ stories + `boil-verify-iteration.sh`, and `boil-brakes.py tick --iteration iter-NNN`
recorded progress. T3 tickets ran the builder / judge / manager protocol in
`self-correcting-loop.md`.

Why it was parked: measured on 2026-08-28, two projects ran 65 and 69 iterations with 205
and 308 tickets for 2 of 7 and 0 of 13 checkboxes. Throughput was never the problem;
nothing external measured per-ticket progress, and the LLM that judged its own progress
kept going. The controller replaces the judge with a frozen check, the manager with a
script, and the ticket pool with a milestone DAG.

What still works, unchanged, for a project mid-flight on tickets:

- `ticket-lint.py`, `boil-doctor.py`, `boil-now.py`, the brakes (`tick --iteration iter-NNN`
  keeps accumulating spend into `budget.json` when no ledger exists)
- `boil-run-iteration.sh iter-NNN` (it takes the legacy path when no checks are frozen)
- `boil-loop.py` for a T3 ticket's builder / judge / manager cycle
- `references/ticket-system.md` for the ticket schema and dispatch prompt

Migrating a ticket project: write `.boil/milestones.json` from the open checkboxes,
`boil-check.py compile`, close or icebox the tickets. `boil-review.py` covers what the
manager's cross-LLM review pass did.
