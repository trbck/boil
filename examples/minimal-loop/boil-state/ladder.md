# Ladder — minimal-loop

Levels are sequential. A box flips only with an EVIDENCE line on the same line:
`EVIDENCE: <command -> result> | YYYY-MM-DD | auto|human`

## L0 — Spark
- [x] Charter written. EVIDENCE: `.boil/charter.md` exists | 2026-06-10 | auto

## L1 — Skeleton
- [x] Guardrail scripts run end-to-end on this tree. EVIDENCE: `boil-run-iteration.sh iter-001 .` -> exit 0 | 2026-06-10 | auto
- [ ] The fixture covers the merged outer-loop state (charter, ladder, budget, progress).

## L2 — Usable by me
- [ ] CI runs the fixture on every push. EVIDENCE: <workflow run URL> | | auto
