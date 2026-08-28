# Ladder — <project>

<!-- Customize criteria per level; keep them observable. Do NOT weaken level
meanings (see SKILL.md). Tick only with EVIDENCE lines:
- [x] <criterion> — EVIDENCE: <cmd → result | URL | number> | YYYY-MM-DD | auto|human
Evidence TTL: auto=14d, human(usage/revenue)=30d. `[?]` = plausibly met, unverified. -->

## L0 — Spark
- [ ] Charter written and confirmed by user
- [ ] Portfolio decision made: which project this displaces (or `candidate`)

## L1 — Skeleton (core loop works once)
- [ ] Core loop end-to-end on dev machine — EVIDENCE: <demo cmd/story>
- [ ] The demo is repeatable from a clean checkout (documented in README)
- [ ] `.boil/` governance pointer added to CLAUDE.md/AGENTS.md

## L2 — Usable by me
- [ ] I used it for its REAL purpose ≥3 times within one week — EVIDENCE: log/dates | human
- [ ] No data-loss or corrupting bug open
- [ ] Setup from scratch documented and re-tested — EVIDENCE: <cmd> | auto
- [ ] Core happy paths covered by tests/stories — EVIDENCE: <test cmd → green> | auto

## L3 — Survives a stranger
- [ ] Deployed / installable without me present — EVIDENCE: <URL or install cmd> | auto
- [ ] Survives restart with zero data loss — EVIDENCE: <restart test> | auto
- [ ] Errors handled: bad input, network down, empty state (no raw tracebacks to user)
- [ ] Secrets out of code; config documented
- [ ] A stranger can onboard from README alone — EVIDENCE: fresh-eyes run (person or clean-env agent) | human
- [ ] Basic monitoring: I find out it broke before a user tells me

## L4 — Valuable to others  <!-- life-tools: see alt block below -->
- [ ] ≥1 external user used it without me prompting — EVIDENCE: <analytics/log> | human
- [ ] Structured feedback from ≥3 users captured in docs
- [ ] North-star metric moved from zero — EVIDENCE: <number + source> | human
- [ ] Distribution channel tested: <channel> produced <N> signups — EVIDENCE | human

<!-- L4 alternative for type: life -->
<!-- - [ ] 30 consecutive days of real use — EVIDENCE: usage log | human -->
<!-- - [ ] The targeted behavior measurably changed — EVIDENCE: <before/after number> | human -->

## L5 — Profitable / load-bearing
- [ ] Business: recurring revenue ≥ <charter target> — EVIDENCE: Stripe/bank number | human
- [ ] Life: removing it for a week would visibly hurt — EVIDENCE: deprivation note | human
- [ ] Maintenance loop defined: what runs weekly, who is paged (me), time cost ≤ <X h/week>
