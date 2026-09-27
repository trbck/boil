# Ch 1 — Optimal Stopping

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 1.
**Governs:** when to stop searching and commit, in any process where options arrive one at a time and passing means losing them.
**Thesis:** the hard part of a search is not *which* option to pick — it is *how many* to consider before picking. That question has a closed-form answer, and the answer depends almost entirely on what information you have and what waiting costs.

---

## 1. The two ways to fail

Every stopping problem fails in exactly two directions:

- **Stop too early** — you leave the best option undiscovered.
- **Stop too late** — you hold out for a better option that does not exist.

The optimal strategy is whatever balances these. Naming both failure modes is the whole analytical move; most bad stopping decisions come from optimising against only one.

---

## 2. The secretary problem — the no-information case

Setup: interview applicants in random order, one at a time. You can rank any two against each other but have **no absolute scale** (ordinal information only, never cardinal). An offer is always accepted. A rejected applicant is gone forever. Goal: pick the single best.

**The Look-Then-Leap Rule.** Set a fixed looking period during which you commit to nobody, no matter how impressive. Then leap for the first candidate who beats everyone seen in the look phase.

| Quantity | Value |
|---|---|
| Optimal look phase | **37%** of the pool (precisely 1/*e*; anything from 35–40% is near-identical) |
| Probability of getting the best | **37%** |
| Behaviour as pool grows | **Invariant** — 37% at n=100 and at n=1,000,000 |

Two consequences that are easy to miss:

- **A 63% failure rate is optimal play.** Acting perfectly still fails most of the time. Any process judged by whether it found the best option will look broken even when correctly run.
- **The bigger the pool, the more the algorithm is worth.** Random choice degrades as 1/n; optimal stopping does not degrade at all. *"Optimal stopping is your best defence against the haystack, no matter how large."*

Why a look phase exists at all: with no absolute scale you must spend observations calibrating what "good" means. The look phase is the price of ignorance, not of caution.

---

## 3. Variants — each assumption relaxed changes the constant, not the shape

| Variant | Changed assumption | Strategy | Success |
|---|---|---|---|
| **Classical** | — | Look 37%, then leap | 37% |
| **Rejection** (offers refused 50% of the time) | Offers not always accepted | Start leaping at **25%**; keep offering to every best-yet | 25% |
| **Recall** (late offers accepted half the time) | Passed options not gone forever | Look to **61%**, then leap; if still unmatched, **go back to the best one that got away** | 61% |
| **Full information** (percentile known) | Cardinal scale available | **Threshold Rule** — no look phase at all | **58%** |

The recurring symmetry: **the optimal look fraction and the success probability are the same number.** Worth remembering as a sanity check.

**On recall:** restlessness and doubt are not character defects when second chances exist — they are part of the optimal policy. The strategy is a *longer* non-committal period plus a fallback.

---

## 4. Full information — the Threshold Rule

Once you can place an option against the whole population (a percentile, not just a comparison), everything changes: *"No buildup of experience is needed to set a standard, and a profitable choice can sometimes be made immediately."*

Accept immediately anything above a threshold — but the threshold **declines as options run out**, because it depends entirely on how much looking remains:

| Position | Accept if above |
|---|---|
| 4th from last | 78th percentile |
| 3rd from last | 69th percentile |
| 2nd from last | 50th percentile |
| Last | anything |

> **In the face of slim pickings, lower your standards; with more fish in the sea, raise them — and the math says by exactly how much.** Never accept below-average unless you are out of options.

The uncomfortable corollary: **an objective criterion beats a subjective one**, because it converts a no-information game (37%) into a full-information one (58%). Judging partners on income percentile is *mathematically* easier than judging on love, which needs experience to calibrate.

---

## 5. When the goal is value, not the best — house selling

Change two things: you know cardinal values, and you want **maximum money overall**, not the single best offer. Waiting has a per-offer cost.

Now there is no look phase whatsoever. Set a threshold before starting, ignore everything below it, take the first thing above it.

**The threshold depends only on the cost of search** — not on the price level, only on the spread between best and worst likely offers. For a $400k–$500k range:

| Cost per offer | Accept at |
|---|---|
| $1 | $499,552.79 |
| $2,000 | $480,000 |
| $10,000 | $455,279 |
| $50,000 (half the range) | **the first offer** — no advantage to holding out |

**Two rules follow, and both are counterintuitive:**

1. **The threshold never moves.** Since the odds of the next offer and the cost of finding out never change, a run of bad luck is not a reason to lower it. Set it once, then hold.
2. **Never go back to a passed offer, even if it is still available.** If it was below threshold then, it is below threshold now. What you spent searching is a sunk cost. *"Don't compromise, don't second-guess. And don't look back."*

This is the same algorithm economists use to model job search — and it explains the otherwise paradoxical coexistence of unemployed workers and unfilled vacancies.

---

## 6. Parking — the whole problem is one number

Parking is optimal stopping under forward-only motion. The controlling variable is the **occupancy rate**.

| Occupancy | Start taking the first free spot at |
|---|---|
| 99% | ~70 spaces out (over a quarter mile) |
| 85% | ~half a block |

Shoup's policy argument, which generalises well beyond parking: **targeting near-100% utilisation is a mistake.** Going from 90% to 95% occupancy accommodates 5% more cars but **doubles everyone's search time**. Empty spots on desirable blocks are a sign the system is working, not failing.

> Utilisation is not the objective. A resource whose queue consumes attention, time and fuel is not being managed by maximising its occupancy.

---

## 7. When to quit while ahead — the burglar problem

Sequence of opportunities, each paying out, each carrying a chance of losing everything accumulated.

```
optimal number of attempts ≈ (chance of success) / (chance of failure)
```

- 90% success per attempt → stop after **9**
- 50/50 → the first is free, but **do not push your luck more than once**

## 8. The problem with no answer

"Triple or nothing": bet everything, 50% chance of tripling, 50% chance of losing it all. Expected value rises every round, so **the math says always keep playing** — and following that guarantees eventual ruin. There is no optimal stopping rule.

> **Some problems are better avoided than solved.** When the optimal policy under a model leads to certain ruin, the model is the thing to reject, not the ruin to accept.

---

## 9. What people actually do

About a dozen studies agree: **people stop early.** In Seale & Rapoport's experiments (40 or 80 applicants), subjects found the best option **31%** of the time against an optimal 37% — respectable — but **leapt too soon in more than four-fifths of trials**.

The explanation is not irrationality. Modelling a search cost of just **1% of the prize per applicant** makes the optimal strategy align exactly with observed behaviour. The classical problem has no time cost; **people's lives do**. As Bearden puts it: *"After searching for a while, we humans just tend to get bored. It's not irrational to get bored, but it's hard to model that rigorously."*

**The lesson is not that the models are wrong but that the cost term is usually missing.** Before concluding someone is behaving suboptimally, check whether they are paying a cost your model omits.

---

## 10. Why this generalises

The secretary problem's least believable assumption — strict one-way seriality — is simply **the nature of time**. You must decide on possibilities not yet seen; hesitation is as irrevocable as action; no choice recurs.

> *"The flow of time turns all decision-making into optimal stopping."*

---

## Transferable rules

1. **Ask "how many options should I consider?" before "which option should I pick?"** The second question is downstream of the first, and only the first has a closed-form answer.
2. **Name both failure modes — stopping early and stopping late — before choosing a policy.** A rule that only guards against one is not a solution.
3. **With ordinal information only, use Look-Then-Leap at ~37%.** Anything between 35% and 40% performs nearly identically, so do not over-tune the constant.
4. **Expect to fail ~63% of the time and do not treat that as evidence the method is broken.** Optimal play still misses the best option most of the time.
5. **Prefer any objective yardstick to a subjective one.** Converting a no-information game into a full-information one raises the success rate from 37% to 58% — a far larger gain than better judgement inside the no-information game.
6. **With full information, drop the look phase entirely and use a declining threshold.** Standards should fall as options run out, and by a computable amount — never below average until you are genuinely out of options.
7. **When maximising value rather than finding the best, set the threshold from the cost of waiting alone**, and note it depends on the *spread* of outcomes, not their level.
8. **A value-maximising threshold never declines with bad luck.** If the odds and the search cost are unchanged, a run of poor offers is not information.
9. **Never reconsider an option you passed on.** What you spent searching is sunk; if it was below threshold then, it is below threshold now.
10. **If offers can be rejected, start offering much earlier** (25% rather than 37%) and keep offering to every best-yet candidate.
11. **If passed options can be recalled, look longer** (61%) and keep an explicit fallback to the best one that got away.
12. **Stop pressing a repeatable gamble at roughly (success odds ÷ failure odds) attempts.**
13. **Do not target full utilisation of a contended resource.** The last 5% of occupancy can double everyone's search time; slack is what makes the system usable.
14. **When the optimal policy under a model implies certain ruin, reject the model.** Some problems are better avoided than solved.
15. **Before calling behaviour suboptimal, check for an unmodelled cost of time.** A 1% per-observation search cost fully explains apparently premature stopping.

---

## Cross-references

Ch. 2 explore/exploit — the same tension where options *can* be revisited · Ch. 5 scheduling — what to do once you have committed · Ch. 6 Bayes's Rule — predicting how much better the next option might be · Ch. 7 overfitting — why more deliberation is not always better.

**Named references:** Merrill Flood (first known discovery of the 37% rule, 1958) · Martin Gardner, *Scientific American* (1960) · Seale & Rapoport (experimental studies) · Neil Bearden (endogenous time costs) · Donald Shoup, *The High Cost of Free Parking* · Johannes Kepler (the recall variant, lived) · Michael Trick (the rejection variant, lived).
