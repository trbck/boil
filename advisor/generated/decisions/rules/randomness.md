# Rules — Deliberate randomness and sampling

`20` rules · ~415 words · ~560 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-00 — Introduction: Algorithms to Live By

<sub>Algorithms to Live By</sub>

- **ATLB-00-R4** — **Do not equate rigour with exhaustiveness.** For hard problems the best available methods use approximation, randomness and early stopping *by design*.

### ATLB-07 — Overfitting

<sub>Algorithms to Live By</sub>

- **ATLB-07-R2** — **Test stability under perturbation.** Re-fit with slight noise or a different sample; a model that swings wildly is overfitted regardless of its fit statistics.
- **ATLB-07-R6** — **Cross-validate on held-out data**, and additionally **cross-validate the metric itself** against a different, harder-to-game evaluation applied to a small sample.

### ATLB-09 — Randomness

<sub>Algorithms to Live By</sub>

- **ATLB-09-R1** — **Sample when the possibility space is too large to enumerate.** An estimate with known error beats an exact answer you will never compute.
- **ATLB-09-R2** — **Judge sampling by whether it returns an answer at all**, not by whether it beats exhaustive analysis for precision.
- **ATLB-09-R3** — **Simulate the process rather than deriving it** when outcomes branch — play the game, run the trial, count what happens.
- **ATLB-09-R4** — **Use repeated random tests to drive uncertainty arbitrarily low.** Each independent check multiplies down the error; near-certainty is usually cheap.
- **ATLB-09-R5** — **Decide explicitly what error rate you need** rather than assuming you need none — cryptography settles for one in 10²⁴, and that is a choice.
- **ATLB-09-R6** — **Trade certainty for time and space deliberately.** Error probability is a third design axis, not a defect.
- **ATLB-09-R7** — **Prefer random samples to both anecdotes and aggregates.** Selected stories carry no information *because* they were selected; aggregates hide the heterogeneity that matters, and you rarely know which statistic to ask for.
- **ATLB-09-R8** — **Commit in advance to publishing what the random sample returns**, whatever it says — the pre-commitment is what makes it evidence.
- **ATLB-09-R9** — **Treat a large quantitative gap as a qualitative one.** "Possible in principle" is not a defence when the cost is astronomically large.
- **ATLB-09-R10** — **Recognise the local maximum**: nothing nearby improves matters, yet you suspect something far better exists. Nearby-optimal is not optimal.
- **ATLB-09-R11** — **Accept a temporary worsening to escape.** Some traps require moving *away* from the exit before you can reach it.
- **ATLB-09-R12** — **Match the escape to the landscape** — jitter for small perturbations, full random restart where local maxima are dense, Metropolis-style occasional bad moves for continuous search.
- **ATLB-09-R13** — **Anneal: be most random early and least random late**, and slow down as you approach a decision rather than after it.
- **ATLB-09-R14** — **Never decline a clear improvement**, however random your process otherwise is.
- **ATLB-09-R15** — **Scale willingness to try a bad option inversely to how bad it is** — this keeps exploration cheap rather than reckless.
- **ATLB-09-R16** — **Engineer serendipity deliberately.** Random inputs — cards, articles, unfamiliar ingredients — break context and are a reliable technique, not a happy accident.

### ATLB-10 — Networking

<sub>Algorithms to Live By</sub>

- **ATLB-10-R6** — **Break symmetry with randomness** when two parties keep colliding through polite deference.

