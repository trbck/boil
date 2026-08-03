### Changed files
- .boil/iterations/iter-001/summary.md — iteration summary with demo + next steps
- .boil/iterations/iter-001/demo.md — the user-visible demo

### Proof / tests
- Strategy: verification-only
- Final proof: `bash scripts/boil-run-iteration.sh iter-001 <root>` → exit 0

### Confidence gate
- Requirements understood: 99 — ACCEPTANCE.md lists five checkable conditions
- Implementation matches: 99 — all five present in the fixture
- Verification working: 99 — the runner exits 0
- Remaining uncertainty: none
