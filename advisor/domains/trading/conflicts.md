# Conflict & convergence registry

Curated by hand. The build does not generate this file, because deciding that two rules genuinely
disagree requires reading both in context.

**Why it exists.** Two books written by different practitioners for different mandates will
contradict each other. An advisor that averages them into one confident voice produces mush and
hides the disagreement exactly where it matters. When a question touches an entry below, present
both positions with their IDs and say which applies here and why.

**Convergences matter too.** When two independent sources reach the same conclusion by different
routes, that is stronger evidence than either alone — and worth saying so.

---

## Conflicts

### C1 — Should volatility and covariance drive allocation?

| | Position | Rules |
|---|---|---|
| **ML4T** | Yes, carefully. Allocators are models with tunable hyperparameters; judge covariance models by the portfolios they generate and validate out of sample. | `ML4T-17-R1`, `ML4T-17-R6`, `ML4T-17-R8`, `ML4T-19-R13` |
| **ASSP** | No. Recent volatility is actively misleading — left-skewed strategies are calmest immediately before they fail, so variance-based allocators increase weight precisely when survivability demands the opposite. | `ASSP-09-R4`, `ASSP-09-R6` |

**Resolution — scope by skew.** ASSP's objection is specifically about portfolios mixing left- and
right-skewed strategies, where variance misprices the left tail. ML4T's machinery is sound for
cross-sectional equity portfolios of broadly similar payoff shape. Ask first: *are the components
skew-heterogeneous?* If yes, follow ASSP and cap by failure geometry (`ASSP-09-R7`). If no, ML4T's
allocator discipline applies — but `ML4T-17-R9` still says clear equal weight before believing any
of it.

### C2 — Is survivorship bias disqualifying?

| | Position | Rules |
|---|---|---|
| **ML4T** | It is one of the systematic defects that manufacture false alpha; design validation around it. | `ML4T-02-R2` |
| **ASSP** | For a **short** backtest it is conservative, not disqualifying — you are testing against the fittest survivors, so the real universe including deletions would score better. | `ASSP-03-R5` |

**Resolution — direction-dependent, and both are right.** Long backtests on surviving constituents
are inflated. Short backtests on the same set are deflated. State which direction the bias runs for
the strategy in hand rather than reciting "survivorship bias" as a blanket disqualifier.

### C3 — How much authority should max drawdown carry?

| | Position | Rules |
|---|---|---|
| **ML4T** | Never read max drawdown as a standalone quality measure — it is an extreme statistic that grows with sample length. Measure duration and recovery too. | `ML4T-16-R10`, `ML4T-19-R9` |
| **ASSP** | Make max drawdown tolerance **the single control parameter**; leverage becomes a consequence, not an input. | `ASSP-09-R12`, `ASSP-09-R1` |

**Resolution — different jobs.** ML4T is talking about *evaluation* (comparing strategies), where
MaxDD is a poor statistic. ASSP is talking about *control* (deciding today's exposure), where
drawdown-from-peak is the one quantity investors actually react to. Use ML4T's caution when
ranking; use ASSP's when sizing. Note that both insist on duration alongside depth
(`ML4T-19-R9`, `ASSP-09-R1`), so there is no disagreement there.

### C4 — Mechanical drawdown cutoffs

| | Position | Rules |
|---|---|---|
| **ML4T** | Prefer graduated escalation to a binary cutoff — mechanical drawdown rules lock in losses that would have recovered. | `ML4T-19-R22` |
| **ASSP** | Cites the "−5% cut AUM by half, −7.5% stop to zero" rule approvingly as the origin of its risk oscillator. | `ASSP-09` §5 layer 3 |

**Resolution — ASSP's implementation already satisfies ML4T's objection.** The `risk_appetite`
oscillator is continuous and EWM-smoothed, i.e. graduated, not binary. The hard −5%/−7.5% rule it
descends from is exactly what `ML4T-19-R22` warns against. Recommend the oscillator, not the
ancestor.

### C5 — Reusing ASSP chapter-6 code

Not a disagreement between books — a trap in the corpus itself. `ASSP-06` ships **deliberate**
lookahead bias for teaching (signals unshifted, P&L computed after resizing). Every other relevant
rule contradicts it: `ASSP-06-R4`, `ASSP-05-R7`, `ML4T-16-R4`.

**Resolution — always fix both defects before reuse, and say you did.**

---

## Convergences

Where the two books agree from different starting points, treat the conclusion as well supported.

| # | Conclusion | ML4T | ASSP |
|---|---|---|---|
| V1 | **Clear equal weight before believing any allocator.** Estimation error usually swamps theoretical gains. | `ML4T-17-R9` | `ASSP-09-R6` |
| V2 | **Full Kelly is an upper bound, not a target.** Trade a fraction of it. | `ML4T-17-R13` | `ASSP-06-R12` |
| V3 | **Separate signal computation from execution in time.** | `ML4T-16-R4` | `ASSP-05-R7` |
| V4 | **Beat a simple baseline before adding complexity.** | `ML4T-11-R19`, `ML4T-05-R6` | `ASSP-01-R7` |
| V5 | **Report costs against returns; proximity to break-even is fragility.** | `ML4T-16-R8`, `ML4T-16-R9`, `ML4T-17-R17` | `ASSP-05` cost caveats |
| V6 | **Calibrate stops from the strategy's own excursion distribution (MAE/MFE).** | `ML4T-19-R19` | `ASSP-10` MAE/MFE section |
| V7 | **Drawdown duration matters as much as depth — investors redeem before recovery.** | `ML4T-19-R9` | `ASSP-09-R1` |

---

## Adding an entry

Add a conflict when you find two rules that would lead to different actions in the same situation.
Include both positions with IDs, and a resolution that says *what determines which one applies* —
a resolution that just picks a winner is not useful, because the loser was written by someone who
had a reason.

Derived rules from `notes` can appear here, clearly labelled. A derived rule contradicting a
primary one is a prompt to investigate, not grounds to overrule it.
