# Iteration 1

Implemented the minimal guardrail fixture.

**Tests:** guardrail scripts passed with exit=0.

**Demo (30 seconds to verify):**
Run `bash scripts/boil-verify-iteration.sh iter-001 <tmp>`.

## Suggested next steps

1. Copy `boil-state/` to `.boil/` in a temporary directory and run the guardrail scripts.
2. Extend the fixture with a human-action blocker if testing Susi/Pushover locally.
