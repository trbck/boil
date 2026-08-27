# Conflict & convergence registry

Curated by hand. The build does not generate this file, because deciding that two rules genuinely
disagree requires reading both in context.

**Why it exists.** An advisor that averages opposed rules into one confident voice produces mush
and hides the disagreement exactly where it matters. When a question touches an entry below,
present both positions with their IDs and say which applies here and why.

**A note on this domain's shape.** `decisions` currently holds a single pack, so there are no
cross-book conflicts to register. What it has instead are **internal tensions**: rules from
different chapters of *Algorithms to Live By* that point opposite ways in the same situation. The
book states each in its own chapter's context and does not always reconcile them, so the
reconciliation is the work done here. `suggest_conflicts.py` cannot generate these — it requires
two packs by design, on the reasoning that a book rarely contradicts itself. Within one book the
contradictions are between *chapters*, and finding them takes reading.

**Convergences across domains matter too.** Where a rule here and a rule in `trading` reach the
same conclusion from unrelated evidence — computer science on one side, market practice on the
other — that is stronger support than either alone.

---

## Internal tensions

### T1 — Explore more, or stop looking and commit?

| | Position | Rules |
|---|---|---|
| **Ch. 1 (stopping)** | Fix the look phase, then commit to the first option beating your baseline, and **never reconsider what you passed on**. Continuing to search past the threshold is the failure mode. | `ATLB-01-R3`, `ATLB-01-R9` |
| **Ch. 2 (explore/exploit)** | In a non-stationary world, **never stop exploring entirely** — revisit options you wrote off, because the world may have changed. Regret accrues most heavily from not trying. | `ATLB-02-R13`, `ATLB-02-R9` |

**Resolution — one decision or many?** Optimal stopping governs a *single* irrevocable choice from
a stream of options; the bandit problem governs a *repeated* choice you will face again. Ask which
you are in. Ch. 1's "never look back" applies within one search, not across a lifetime of them —
and `ATLB-02-R3` is explicit that treating a recurring decision as isolated is the error. The
tie-breaker is `ATLB-02-R1`: establish the interval first. A short interval makes Ch. 1's
commitment discipline right; a long one makes Ch. 2's standing exploration right.

### T2 — Is more deliberation better?

| | Position | Rules |
|---|---|---|
| **Ch. 7 (overfitting)** | Bound deliberation in advance and decide when the bound is reached. More time means more factors and more overfitting, not a better decision. Trust the first factors you generate. | `ATLB-07-R11`, `ATLB-07-R12`, `ATLB-07-R13` |
| **Ch. 9 (randomness)** | Anneal — be most random early and least random late, **slowing down as you approach a decision**. Sampling more drives error arbitrarily low. | `ATLB-09-R13`, `ATLB-09-R4` |

**Resolution — what are you spending the time on?** These are not the same activity. Ch. 7 warns
against *elaborating the model* — adding factors, refining weights against unreliable estimates.
Ch. 9's slow cooling is about *reducing the variance of your search*, not adding structure to the
answer. Extra sampling of a fixed question is cheap and safe; extra reasoning about a question you
cannot estimate well is where overfitting enters. `ATLB-07-R10` gives the test: are the quantities
I rely on hard to estimate? If yes, Ch. 7 governs and you should stop early. If the quantity is
measurable and the only obstacle is noise, Ch. 9 governs and more samples help.

### T3 — Keep it, or throw it away?

| | Position | Rules |
|---|---|---|
| **Ch. 4 (caching)** | Build a hierarchy rather than discarding: small-and-fast backed by large-and-slow beats either alone. Evict by recency, and treat the reversed past as your substitute for clairvoyance. | `ATLB-04-R1`, `ATLB-04-R3`, `ATLB-04-R5` |
| **Ch. 3 (sorting)** | Never sort what you will not search; erring toward mess is cheaper than erring toward order. As search gets cheaper, filing loses value. | `ATLB-03-R5`, `ATLB-03-R7` |

**Resolution — they answer different questions and agree more than they appear to.** Ch. 3 is about
*imposing order*; Ch. 4 is about *what to retain and where*. Both point away from effortful
curation: the LRU pile and the unsorted-but-recent stack are the same object. The genuine tension
is only about whether to keep a second tier at all, and `ATLB-04-R2` settles it — have a cache even
if you manage it badly. Keep, but do not sort.

### T4 — Push to capacity, or leave slack?

| | Position | Rules |
|---|---|---|
| **Ch. 1 / Ch. 10** | Do not target full utilisation; the last 5% of occupancy can double everyone's search time. Keep queues small and drain them to empty. Refuse work whose working set will not fit. | `ATLB-01-R13`, `ATLB-10-R15`, `ATLB-05-R18` |
| **Ch. 10 (congestion)** | Push to the point of failure — that is how a system discovers its ceiling and how feedback is generated at all. | `ATLB-10-R13`, `ATLB-10-R16` |

**Resolution — `ATLB-10-R13` carries its own condition.** Push to failure *only when your response
to failure is sharp and resilient*: additive increase, multiplicative decrease, and a real
mechanism for shedding load. Absent that response, the system does not degrade — it thrashes
(`ATLB-05-R16`), which is failure with no information returned. Deliberate probing of the ceiling
requires an already-working retreat; slack is the default until you have built one.

### T5 — Assert your preferences, or defer to the group?

| | Position | Rules |
|---|---|---|
| **Ch. 12 (kindness)** | State your preferences. "I'm flexible" passes the cognitive buck and forces others into the most expensive computation there is. | `ATLB-12-R9`, `ATLB-12-R7` |
| **Ch. 11 (game theory)** | Do not out-level your opponent, and beware consensus assembled from mutual inference — but also, seek games where honesty is dominant rather than assuming it is safe. | `ATLB-11-R2`, `ATLB-12-R11` |

**Resolution — check whether the game rewards honesty first.** Ch. 12's advice assumes a
cooperative setting where everyone's stated preference is used to find a joint answer. Ch. 11's
warning is that in a game with opposed interests, revealed preferences are exploitable. The
practical rule is `ATLB-11-R19`: where you set the rules, design so honesty is dominant, then be
straightforward inside them. Where you do not, asserting preferences is a concession, not a
kindness — price it accordingly.

---

## Convergences with `trading`

Cross-domain. Cite both IDs when one of these comes up; independent derivation is the point.

| # | Shared conclusion | `decisions` | `trading` |
|---|---|---|---|
| V1 | **Judge the process, not the outcome.** A good method still fails often, and scoring the process is what survives a bad run. | `ATLB-12-R1`, `ATLB-00-R9` | `ASSP-10-R9` |
| V2 | **Unbounded search overfits.** Deliberation is a complexity knob; search you did not count cannot be corrected for. | `ATLB-07-R11`, `ATLB-07-R12` | `ML4T-01-R2` |
| V3 | **Prefer graceful degradation to an optimal point estimate.** Robustness to being wrong beats precision you have not earned. | `ATLB-07-R9`, `ATLB-07-R14` | `ML4T-01-R4` |
| V4 | **Anything measured and rewarded gets optimised, including in ways you did not intend** — so cross-validate the metric, not only the model. | `ATLB-07-R5`, `ATLB-07-R6` | `ML4T-11-R8` |
| V5 | **Retreat faster than you advance.** Additive increase, multiplicative decrease — asymmetry is what keeps exposure survivable. | `ATLB-10-R10`, `ATLB-10-R11` | `ASSP-09-R9` |
| V6 | **Fit quality on data you already hold is not evidence.** Only held-out results arbitrate. | `ATLB-07-R1`, `ATLB-07-R6` | `ML4T-05-R1` |

---

## Adding an entry

Add a conflict when you find two rules that would lead to different actions in the same situation.
Include both positions with IDs, and a resolution that says *what determines which one applies* —
a resolution that just picks a winner is not useful, because the loser was written by someone who
had a reason.

For this domain, an internal tension between chapters is a legitimate entry and should be labelled
`T<n>`; reserve `C<n>` for genuine cross-pack conflicts once a second book is added. Cross-domain
convergences carry IDs from both domains and should be qualified (`trading:ML4T-01-R2`) when quoted
outside this file.
