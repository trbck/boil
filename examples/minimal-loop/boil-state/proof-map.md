# Proof map — minimal-loop

Split out of `goal.md` so the goal stays under its size limit.

| Goal checkbox | Tier | Proof strategy | Pre-change proof | GREEN proof | Browser proof | Story/rubric |
|---|---|---|---|---|---|---|
| Ticket schema validates | T1 | `verification-only` | n/a (fixture) | `ticket-lint.py --root .` -> exit 0 | n/a | n/a |
| Iteration summary includes proof, demo, next | T1 | `verification-only` | n/a (fixture) | `boil-verify-iteration.sh iter-001 .` -> exit 0 | n/a | n/a |
