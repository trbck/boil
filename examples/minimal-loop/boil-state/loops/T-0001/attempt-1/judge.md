# Judge — T-0001 — attempt 1

**Answer key:** document — ACCEPTANCE.md
**Key integrity:** VERIFIED (hash matches frozen_sha)
**Criterion:** the fixture satisfies all five acceptance conditions in ACCEPTANCE.md.

## Evidence trace

### Check 1: .boil/ carries the five state files
**Action:** listed `.boil/`
**Observation:** goal.md, memory.md, implementation.md, bugs.md, routing.md all present
**Evidence:** ACCEPTANCE.md:9 — "contains `goal.md`, `memory.md`, `implementation.md`, `bugs.md`, and `routing.md`"
**Result:** PASS

### Check 2: a ticket passes ticket-lint
**Action:** ran `python3 scripts/ticket-lint.py --root .`
**Observation:** clean
**Evidence:** `ticket-lint: ok`
**Result:** PASS

### Check 3: iter-001 carries summary.md and demo.md
**Action:** listed `.boil/iterations/iter-001/`
**Observation:** both files present
**Evidence:** ACCEPTANCE.md:11 — "contains both `summary.md` and `demo.md`"
**Result:** PASS

### Check 4: the summary names a demo action and a next step
**Action:** read summary.md
**Observation:** carries a "Demo (30 seconds to verify)" line and a "Suggested next steps" block
**Evidence:** summary.md — "Run `bash scripts/boil-verify-iteration.sh iter-001 <tmp>`"
**Result:** PASS

### Check 5: the iteration runner exits 0
**Action:** ran `bash scripts/boil-run-iteration.sh iter-001 <root>`
**Observation:** completed
**Evidence:** `boil-run-iteration: gates complete for iter-001`
**Result:** PASS

## Verdict
**Decision:** PASS
**Failure signature:** none
**Reason (one sentence):** every condition in ACCEPTANCE.md is satisfied with cited evidence.
