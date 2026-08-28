# Goal

**One-line:** Demonstrate a minimal boil loop fixture.

## Success checklist
- [x] Ticket schema validates. EVIDENCE: `ticket-lint.py --root .` -> exit 0 | 2026-06-10 | auto
- [x] Iteration summary includes proof, demo, and next steps. EVIDENCE: `boil-verify-iteration.sh iter-001 .` -> exit 0 | 2026-06-10 | auto

## Requirements understanding

**Confidence target:** >=99/100 before implementation starts.

| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---:|---|
| Demonstrate a minimal boil loop fixture | Provide a tiny state tree that guardrail scripts can validate | Doctor, ticket lint, and iteration verifier exit 0 | 99 | none |

## How the user will see this works
Run the guardrail scripts from the skill repo.
