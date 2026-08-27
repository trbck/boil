# Rules — Optimal stopping — when to look and when to leap

`21` rules · ~498 words · ~672 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-01 — Optimal Stopping

<sub>Algorithms to Live By</sub>

- **ATLB-01-R1** — **Ask "how many options should I consider?" before "which option should I pick?"** The second question is downstream of the first, and only the first has a closed-form answer.
- **ATLB-01-R2** — **Name both failure modes — stopping early and stopping late — before choosing a policy.** A rule that only guards against one is not a solution.
- **ATLB-01-R3** — **With ordinal information only, use Look-Then-Leap at ~37%.** Anything between 35% and 40% performs nearly identically, so do not over-tune the constant.
- **ATLB-01-R4** — **Expect to fail ~63% of the time and do not treat that as evidence the method is broken.** Optimal play still misses the best option most of the time.
- **ATLB-01-R5** — **Prefer any objective yardstick to a subjective one.** Converting a no-information game into a full-information one raises the success rate from 37% to 58% — a far larger gain than better judgement inside the no-information game.
- **ATLB-01-R6** — **With full information, drop the look phase entirely and use a declining threshold.** Standards should fall as options run out, and by a computable amount — never below average until you are genuinely out of options.
- **ATLB-01-R7** — **When maximising value rather than finding the best, set the threshold from the cost of waiting alone**, and note it depends on the *spread* of outcomes, not their level.
- **ATLB-01-R8** — **A value-maximising threshold never declines with bad luck.** If the odds and the search cost are unchanged, a run of poor offers is not information.
- **ATLB-01-R9** — **Never reconsider an option you passed on.** What you spent searching is sunk; if it was below threshold then, it is below threshold now.
- **ATLB-01-R10** — **If offers can be rejected, start offering much earlier** (25% rather than 37%) and keep offering to every best-yet candidate.
- **ATLB-01-R11** — **If passed options can be recalled, look longer** (61%) and keep an explicit fallback to the best one that got away.
- **ATLB-01-R12** — **Stop pressing a repeatable gamble at roughly (success odds ÷ failure odds) attempts.**
- **ATLB-01-R13** — **Do not target full utilisation of a contended resource.** The last 5% of occupancy can double everyone's search time; slack is what makes the system usable.
- **ATLB-01-R14** — **When the optimal policy under a model implies certain ruin, reject the model.** Some problems are better avoided than solved.
- **ATLB-01-R15** — **Before calling behaviour suboptimal, check for an unmodelled cost of time.** A 1% per-observation search cost fully explains apparently premature stopping.

### ATLB-02 — Explore/Exploit

<sub>Algorithms to Live By</sub>

- **ATLB-02-R12** — **Watch for over-exploration in recurring choices** — the empirical bias runs opposite to the stopping bias, and people observe far longer than the math warrants.

### ATLB-09 — Randomness

<sub>Algorithms to Live By</sub>

- **ATLB-09-R8** — **Commit in advance to publishing what the random sample returns**, whatever it says — the pre-commitment is what makes it evidence.

### ATLB-10 — Networking

<sub>Algorithms to Live By</sub>

- **ATLB-10-R2** — **Accept that confirmation is never complete** and fix a practical stopping point, rather than pursuing certainty that provably cannot exist.
- **ATLB-10-R10** — **Increase commitment additively, cut it multiplicatively.** Ramp gently, retreat by half — asymmetry is what makes a shared system stable.

### ATLB-11 — Game Theory

<sub>Algorithms to Live By</sub>

- **ATLB-11-R14** — **Bind yourself deliberately.** Contracts, schedules, closing times and commitments are equilibrium-shifting devices, not just restrictions.
- **ATLB-11-R15** — **Treat involuntary commitment as an asset.** A reputation for responding disproportionately deters exploitation; predictability of feeling substitutes for external enforcement.

