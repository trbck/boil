# Acceptance — minimal guardrail fixture

This file is T-0001's **answer key** (`kind: document`). It was written by the
orchestrator before any builder was dispatched, and it is read-only to the builder:
the judge measures the work against the lines below, not against the builder's report.

A conforming fixture satisfies all of:

1. `.boil/` contains `goal.md`, `memory.md`, `implementation.md`, `bugs.md`, and `routing.md`.
2. `.boil/tickets/` contains at least one ticket that passes `scripts/ticket-lint.py`.
3. `.boil/iterations/iter-001/` contains both `summary.md` and `demo.md`.
4. The iteration summary names a demo action and a suggested next step.
5. `bash scripts/boil-run-iteration.sh iter-001 <root>` exits 0.
