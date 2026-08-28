# Ladder — mentordrop (example of evidence discipline)

## L0 — Spark
- [x] Charter written and confirmed — EVIDENCE: .boil/charter.md confirmed in session | 2026-07-03 | human
- [x] Portfolio decision: displaces `braini` (parked, re-entry: mentordrop hits L4 or dies) | 2026-07-03 | human

## L1 — Skeleton
- [x] Visitor can book+pay end-to-end — EVIDENCE: story-01 booking flow, Stripe test-mode
      charge `ch_3Rf…` visible | 2026-07-03 | auto
- [x] Repeatable from clean checkout — EVIDENCE: `make demo` → page on :3000, README §Quickstart | 2026-07-03 | auto
- [ ] Governance pointer in CLAUDE.md

## L2 — Usable by me
- [ ] 3 real (friend) bookings completed in one week — EVIDENCE: booking log | human
- [ ] No data-loss bug open (booking without payment / payment without booking)
- [ ] Happy paths as stories — EVIDENCE: `python3 scripts/story-run.py .boil/stories` → green | auto

## L3 — Survives a stranger
- [ ] Live at mentordrop.example — EVIDENCE: `curl -s https://… | grep -q book` | auto
- [ ] Survives `docker compose restart` with zero booking loss — EVIDENCE: restart story | auto
- [ ] Stripe webhook failure ≠ lost booking (retry/alert path) — EVIDENCE: chaos story | auto
- [ ] Uptime alert reaches Pushover before a user notices — EVIDENCE: kill server → alert screenshot | human

## L4 — Valuable to others
- [ ] [human-action] 3 Reddit posts published — EVIDENCE: URLs | human
- [ ] ≥200 unique visitors — EVIDENCE: analytics number | human
- [ ] ≥3 PAID bookings from strangers — EVIDENCE: Stripe live-mode dashboard | human
- [ ] Post-session survey answered by ≥3 buyers — EVIDENCE: responses doc | human

## L5 — Profitable
- [ ] ≥10 paid bookings in a 30-day window (≥€390 net) — EVIDENCE: Stripe | human
- [ ] Mentor supply loop: ≥5 vetted mentors, ≥1 referred by another mentor | human
- [ ] Ops ≤3h/week documented (vetting, matching, support)
