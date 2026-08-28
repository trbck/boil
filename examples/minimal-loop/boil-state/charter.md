---
project: minimal-loop
type: life
status: active
stage: L1
north_star: "the guardrail fixture stays runnable as the skill evolves"
kill_by: 2026-12-31
---

# Charter — minimal-loop

**Why:** a tiny, real `.boil/` tree the guardrail scripts can validate, so the skill's
own gates are exercised by CI rather than only by hand.

**User:** anyone changing boil's scripts.

**North star:** the fixture stays runnable — `boil-run-iteration.sh` exits 0 on it.

**Kill criteria:** delete this fixture if the guardrail scripts are ever covered
end-to-end by unit tests alone.

**Non-goals:**
- A realistic application. It is a fixture, not a demo app.
- Any real credentials, services, or network access.
