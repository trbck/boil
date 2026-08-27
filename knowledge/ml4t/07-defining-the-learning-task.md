# Ch 7 — Defining the Learning Task

**Governs:** label definition, split-aware preprocessing, and the triage gates every candidate feature must clear before it reaches a model.
**Thesis:** most apparent predictability is manufactured by the label — misaligned anchors, overlapping horizons, and uncounted search. Fix the learning problem before touching an algorithm.

---

## 1. Five protocol invariants (every run must satisfy)

| Invariant | Requirement |
|---|---|
| **Observability** | Every raw input observable at decision time. Reporting lags, update times, eligibility rules, calendar conventions are *part of the definition*. |
| **Train-only fitting** | Any transform estimating parameters from data is fit on the training portion of each fold only |
| **Overlap-aware evaluation** | Overlapping horizons induce dependence — handle in split design, report overlap diagnostics alongside metrics |
| **Versioned metadata** | A feature/label is a fully specified recipe; log it. Definition changes create new trial families. |
| **Auditable masks** | Store the mask *definition*, not just surviving rows; report effective sample size by fold and asset group |

**Rule of thumb:** if a step computes a summary statistic from a population of observations, it is *fitted* and must be split-aware. Stateless steps (dropping invalid rows, fixed unit conversion, boolean calendar flags) are exempt. When in doubt, treat it as fitted.

> Leakage from full-panel scaler fitting is *quiet*, not dramatic. The worked demo shows test mean 0.110 under train-only fitting vs. 0.101 with full-panel fit — small enough to survive review, large enough to shift a marginal decision. Don't expect leakage to announce itself with an implausible Sharpe.

---

## 2. Preprocessing decisions

**Outliers — the first cut is invalid vs. rare, not big vs. small.**

| Class | Examples | Treatment |
|---|---|---|
| **Invalid** | Negative volume, impossible timestamps, crossed quotes | Remove |
| **Single-interval spike + immediate reversion** | Print errors | Field-aware spike check comparing move magnitude *and* reversion pattern against the field's distribution |
| **Valid tail** | Genuine extreme moves | Winsorize/clip at fixed percentile; prefer robust scaling (median / IQR) over mean-σ when skewed or leptokurtic |

> **The exception that matters:** when the label targets extreme moves or barrier events, clipping returns deletes exactly the outcomes the model is supposed to learn. Preserve tails when tails are the target.

**Representation choices** (treat as fixed parts of the definition, not tunables):

- Level-like series (prices, yields, spreads) → model changes, not levels
- Risk scaling (divide by realized vol) stabilizes across regimes — fix the vol estimator's definition *and* lookback rather than tuning it between trials
- Ranks/percentile ranks are the most robust cross-sectional encoding; **specify and freeze** whether ranking is cross-sectional (across assets at each *t*) or time-series (within an asset's history)
- Categoricals: one-hot for low cardinality, ordinal where order is meaningful (rating tiers), hashing/learned embeddings for high-cardinality IDs — encoder fit on train split

**Missing data is three problems, not one:**

| Type | Mechanism | Response |
|---|---|---|
| **Noise** | Absent for reasons unrelated to asset/time/value | Robust default fill (cross-sectional median), or leave missing if model accepts it |
| **Observed coverage rules** | Missingness explained by fields you *do* observe (size, exchange, region, listing age) | Impute from observed fields **+ "was missing" indicator**, or native-missing model + indicator |
| **Informative** | Absence linked to the unobserved value (non-reporting when metrics are poor; sparse prints when liquidity is low) | Preserve explicitly as indicator or "not reported" category. **Imputation here is a modeling assumption, not a default.** |

**Never allow silent imputation that erases missingness without a trace.**

---

## 3. Label engineering

### Execution convention — the highest-leverage single choice

| Convention | Definition | Use when |
|---|---|---|
| **Close-to-close** | Signal at close of bar *t*; return measured close *t* → close *t+h* | Academic comparability; simplest |
| **Next-open-to-open** | Signal at close *t*; enter at open *t+1*, exit at open *t+h+1* | Realistic for most end-of-bar signals |

> **Calibration anchor:** on daily US equity data the two conventions differ by **50–100 bps per trade**, in either direction, depending on overnight moves and opening gaps. This is not cosmetic — over the past ~30 years nearly all US equity market return has accrued **overnight rather than intraday** (Glasserman et al., 2025). Choosing close-to-close silently hands the strategy a return stream it cannot capture.

Keep the convention identical between label computation and backtest PnL.

### Fixed-horizon labels

Simple vs. log returns: near-identical for small moves; log is additive across periods, simple aligns with PnL arithmetic. Pick one, record it. Horizon need not be calendar-based — bar counts over volume or information bars make *h* adapt to activity.

**Discretization thresholds control two things at once: the magnitude of the labeled event and the base rate.** Too tight → near-50/50 split labeling noise. Too wide → rare-event problem implying infeasible trading frequency.

| Threshold rule | Behavior | Best for |
|---|---|---|
| **Fixed absolute** (e.g. 1%) | Simple, interpretable; implied base rate drifts with volatility | Stable-vol single asset |
| **Volatility-scaled** (multiple of past-only σ estimate) | Stabilizes base rate across regimes | Single-asset strategies |
| **Time-series percentile** (e.g. 75th pct of trailing 252 bars) | Adapts to asset-specific vol | Single-asset; **must be estimated within the training fold** |
| **Cross-sectional percentile** (quantile membership at each *t*) | Class proportions stable *by construction* | Most multi-asset strategies |

> Global (full-sample) time-series percentiles leak information about the future return distribution. This one is easy to ship by accident because the code looks innocuous.

### Variable-horizon labels

**Trend scanning** — evaluate candidate horizons (typically 5–60 bars) per observation, select the one with the highest t-statistic for a linear trend fit.

> Trend scanning has selection bias baked in: picking the best horizon per observation systematically selects extreme outcomes that won't persist. Mitigate with Bonferroni correction on the selected t-stat (divide by number of candidate horizons) or by constraining the horizon range to match turnover constraints. And because horizons vary, **you cannot compute a single IC** — report the distribution of selected horizons and verify it's stable across folds.

**Triple-barrier labels** — upper barrier, lower barrier, vertical (time) barrier from the tradable price at anchor. Label +1 / −1 / 0 by which is touched first.

- Resolution time is **variable**, which drives the overlap analysis below
- With bar data, when both barriers cross in the same bar, **specify and log a tie-break rule** (e.g. treat as loss — conservative; or exclude ambiguous bars)
- Barrier widths use the same vol-scaling logic; asymmetric multipliers where there's directional conviction

**Calibrate barrier widths with MFE/MAE**, not intuition:

| Width | Effect |
|---|---|
| Narrow | Fast resolution, but noise-dominated |
| Wide | Longer resolution, fewer usable observations, **more overlap** |

Target: workable class balance, plausible upper/lower hit rates, reasonable resolution-time distribution.

---

## 4. Overlap and effective sample size

Adjacent *h*-bar labels share most of the same price increments; any shock affects every label alive at that moment. **Average uniqueness** = mean of 1/concurrency over the label's lifetime; effective sample size ≈ nominal × average uniqueness. For fixed-horizon labels sampled every bar, uniqueness ≈ 1/*h*.

> **The number that should change your standard errors.** SPY over ~10 years: **248,436 nominal observations collapse to ~11,830 effective**. Confidence intervals built on the nominal count are too narrow by roughly √21 ≈ 4.6×. Standard errors must use the effective count.

Overlap creates three separable problems, each with its own fix:

| Problem | Fix |
|---|---|
| Train/test labels share price increments → leakage across split | Purge gaps (Ch. 6 protocol) — **non-negotiable**, ≥ *h* bars |
| Gradients and metrics overweight high-concurrency periods | Uniqueness-based sample weighting |
| Serial dependence inflates apparent significance | Report effective sample size; block-bootstrap standard errors |

**Four remedies, most setups combine at least two:**

1. **Protocol-correct splits** — mandatory, not optional
2. **Sample weighting** by uniqueness — retains all data
3. **Subsampling** (every *h* bars, or start a new label only after the previous resolves) — simpler, discards information
4. **Sequential bootstrap** — updates draw probabilities after each selection so observations with higher expected uniqueness become more likely; yields lower redundancy without discarding data

### Label audit record (close every definition with this)

- [ ] Anchor convention
- [ ] Horizon definition
- [ ] Resolution-time rule, including bar-data tie-breaking
- [ ] Overlap summary (uniqueness, effective sample size)
- [ ] Base-rate summary and stability across regimes
- [ ] Implied trading intensity — **if infeasible, revise the label before modeling**

### Meta-labeling

Two-stage decomposition of direction and confidence: a primary model (often a simple rule or existing strategy) generates entries; the secondary label records only whether each signal was profitable *after costs*; a meta-model learns when the primary is trustworthy, and its calibrated probability maps to size (e.g. sigmoid → fraction of max bet).

> Worth knowing, but note the book's case studies deliberately **do not** use it — each trains a single model on a single horizon and sizes via an allocator. Meta-labeling earns its keep when a directional model already exists and the goal is filtering weak signals, not re-engineering entries.

---

## 5. Univariate triage — four screens in order

A feature must clear each before advancing. **All diagnostics computed within fold, aggregated across folds** — medians, IQRs, worst-fold views, never a single pooled statistic.

1. **Correctness** — can you trust the definition at decision time?
2. **Association** — does it carry information about the label?
3. **Shape** — is the relationship compatible with a plausible score→position mapping?
4. **Feasibility** — could anything implementable survive costs and capacity?

### Correctness screens (non-negotiable first pass)

- [ ] **Coverage** — fraction of eligible (asset, decision-time) pairs with non-null values; sparse coverage changes effective sample size and may indicate stale inputs
- [ ] **Timing/lag consistency** — reporting lags for fundamentals, publication times for third-party signals, update schedules for derived quantities
- [ ] **Mask alignment** — identical mask applied to feature computation, label computation, *and* evaluation
- [ ] **Staleness** — infrequently-updating features (quarterly fundamentals) may be dominated by asset-specific intercepts rather than time-varying signal

These establish no economic value. They prevent the costliest failure: promoting a definition you cannot trust.

### Information Coefficient

Rank IC (Spearman) is the conservative default — aligns with ranking-based construction, robust to heavy tails and monotone nonlinearity. Pearson IC only when linear association on raw values matters. **Keep representation and metric consistent:** store as ranks → evaluate with rank IC.

IC is a *learnability* diagnostic for the bundle (feature, label, masks) under the protocol. It is not a claim about tradable performance.

**Summarize at the fold level, never pooled.** Report median and IQR of fold means, plus worst fold. ICIR = fold mean / fold dispersion. **Sign consistency — the fraction of folds sharing the sign of the overall median — is the key stability gate.**

> **Why pooling destroys information, with numbers.** ETF universe, 21-day momentum: **pooled IC = 0.001** (indistinguishable from zero) but **fold-level mean IC = 0.064, ICIR 0.79, 75% of folds positive**. The pooled statistic hides a signal that is real in most regimes and cancelled by a few adverse episodes. The mirror-image trap: a feature with mean IC 0.04 across five folds achieving 0.08 in two trending folds and −0.02 in three mean-reverting folds — the aggregate conceals a regime switch that would destroy a static allocation.

**Two patterns to watch in the IC time series:** (i) IC concentrated in a single episode → transient shock or protocol artifact; (ii) IC flipping sign across folds → usefulness depends on unmodeled state variables.

**IC decay curve across horizons** reveals useful life. Peaks at 5 days and halves by 10 → don't hold a month. Flat from 5 to 21 days → rebalancing flexibility.

### Inference at triage

Apply to fold summaries, not daily IC values: (1) block bootstrap within fold, block length reflecting horizon overlap; (2) within-time permutation shuffling asset–label assignment inside each cross-section (preserves cross-sectional dependence, breaks feature–label pairing). Treat p-values as descriptive here.

> **HAC correction is not a rounding adjustment.** On 21-day ETF momentum IC, HAC inflates the naive standard error by **2.54×** and effective sample size falls from **4,989 to 773 — an 85% efficiency loss.** That number is what should anchor minimum-track-record planning.

### Grinold's Fundamental Law as a triage lens

IR ≈ IC × √breadth. Not a performance forecast — bets are rarely independent, and 100 ETFs with shared sector exposure may offer **effective breadth of only 20–30**.

**Triage lesson: small but persistent ICs matter when breadth is genuinely large. Peak IC is less informative than stable IC across folds.**

### When to use something other than rank IC

| Measure | Use when | Caveat |
|---|---|---|
| **Rank IC (Spearman)** | Default for large cross-sections with monotone prior | — |
| **Kendall's τ** | Small cross-sections; built from pairwise orderings so more stable | Numerically smaller than Spearman for the same relationship — **not interchangeable** |
| **Mutual information** | Only when quantile plots show clear nonlinear/non-monotone structure | Hard to estimate in finite samples; needs discretization choices; **non-negative so gives no direction** |

### Discrete labels

Threshold-dependent: precision, recall, specificity. In trading terms, **false positives are costly entries** (round-trip cost + adverse move); false negatives are foregone gains.

Threshold-free: ROC AUC *and* PR AUC, both fold-by-fold with median and IQR.

> Under strong class imbalance a feature can post a healthy ROC AUC while producing many false positives relative to true positives at practically relevant thresholds. The PR curve exposes the precision collapse at high-recall operating points that ROC hides. With rare positives, PR AUC is the more informative of the two.

For multi-class event labels (profit / stop / time-out), report base rates by class *and* fold — they shift across regimes. If collapsing to binary actions, record the collapse rule and verify it matches the intended action set.

### Quantile/decile analysis — validating shape

Sort assets by feature within the eligibility mask at each *t*, bin, compute mean label per bin, track the top-minus-bottom spread, summarize within folds.

- **Monotone increasing** → compatible with ranking approaches (top-N, long–short spreads)
- **Non-monotone (e.g. U-shaped)** → a monotone mapping will miss signal in one extreme; implies either a nonlinear mapping or a confounder

At this stage you are validating shape, not designing the mapping.

### Feasibility screens

Use the simplest mapping (rank, take top-N) as a stress test:

| Check | Warning sign |
|---|---|
| **Turnover proxy** | Top-N set turning over completely each rebalance. Persistent positions have a structural cost advantage. |
| **Break-even cost sanity** | Median fold spread 20 bps vs. round-trip cost 15 bps → **net 5 bps, barely above noise**. Gross spread not clearing estimated cost is a **stop**. |
| **Capacity** | Recompute IC/spread by liquidity bucket. Signal confined to the least liquid bucket → stop for this setup. Smooth degradation liquid→illiquid suggests a broad-based signal. |

### Triage decision standard

| Decision | Condition | Action |
|---|---|---|
| **Proceed** | Correctness passes; primary diagnostic directionally consistent across folds; quantile/confusion evidence supports a plausible mapping | Hand to modeling chapters |
| **Revise** | Idea plausible, definition flawed (anchor mismatch, horizon mismatch, unstable base rates) | Change definition, re-run triage, **record the delta** |
| **Stop** | Sign unstable across folds; spread too small to survive costs; signal confined to untradeable liquidity | Archive **and document the failure mode** |

Read output strictly in order: correctness → association → shape and feasibility → search accounting.

---

## 6. Multiple testing

### Define the searched set

Record everything evaluated under the same decision rules: label-definition variants (anchor, horizon, threshold, barrier rules), feature-family variants (lookbacks, transforms, reference frames), conditioning templates. Log searched-set size *and* generation rules (grid, deduplication, exclusions).

**Worked arithmetic:** 5 label horizons × 3 threshold rules × 10 feature variants = **150 bundles**. At a naive 5% test under the null, expect **~7–8 false positives**. The number 150 must accompany any reported p-value.

> **Calibration for what pure noise produces.** Among 100 noise factors (50 assets, 252 days), the best achieves **IC = 0.020** against a theoretical maximum of 0.023. Across 200 simulations the median best-factor IC is **0.022** — a spurious signal that would pass most screens. Naive testing at α = 0.05 yields ~5 false discoveries per simulation; BH-FDR reduces this to near zero. If your best-of-many IC is around 0.02, you have found nothing.

### Exploration vs. confirmation

- **Exploration pass** — evaluate many candidates, promote on **fold stability** (sign consistency, absence of single-episode dominance, robustness to timing and coverage checks) rather than peak performance
- **Confirmation pass** — freeze promoted candidates, re-run triage with a minimized comparison set, produce the summaries you will cite

**Mixing the two — promoting on peak performance, then "confirming" on the same data — is the most common multiple-testing failure.**

### Correction family choice

| Family | Controls | Use when | Procedure |
|---|---|---|---|
| **FWER** | P(≥1 false positive) across all tests | Promoting a *small* number from a large pool; each false positive is expensive | **Holm–Bonferroni** — sort p ascending, reject *i* only if p₍ⱼ₎ ≤ α/(m−j+1) for all j ≤ i. Uniformly more powerful than plain Bonferroni at the same error rate. |
| **FDR** | Expected fraction of false positives among rejections | Large screens expecting many true positives; e.g. screening 200 variants to advance 20–30 | **Benjamini–Hochberg** — reject if p₍ᵢ₎ ≤ (i/m)·q |

Decision rule keyed to downstream cost: expensive modeling/backtesting per promoted feature → FWER. Building a feature pool where model selection will weed out a few false positives → FDR.

> **Sobering empirical anchor:** applied to 13 ETF features, **zero survive** BH-FDR or Holm–Bonferroni at α = 0.05. RVol-10d leads under HAC and is still rejected after correction. Expect this outcome to be normal, not a sign your pipeline is broken.

**Harvey, Liu & Zhu (2016)**, surveying 300+ published factors, recommend raising the discovery threshold to **t > 3.0** (from 2.0) for new factors — a practical shortcut accounting for accumulated search across the literature.

> When candidates are correlated (lookback variants, parameter sweeps around one factor), independence-based corrections **overstate** the penalty. Rademacher complexity gives sharper bounds by measuring the effective richness of the hypothesis class (Ch. 16).

### Report effect sizes, not only significance

- [ ] Searched-set size and generation rules
- [ ] Fold-level summaries (median **and worst fold**) for the primary diagnostic
- [ ] Stability indicator — sign consistency, time concentration
- [ ] Whether numbers come from the exploration or confirmation pass

> **The single most common accounting failure:** tuning a threshold, lookback grid, missingness rule, or interaction *after* reviewing results, and not counting it as a trial. These are legitimate research moves. They are also additional trials and must enter the search-set accounting as a new trial family.

**Strategy-level analogues** when the outcome is a Sharpe rather than an IC: Deflated Sharpe Ratio (probability the best Sharpe exceeds chance) · Probability of Backtest Overfitting (how often the in-sample best-ranked config becomes the out-of-sample worst) · Minimum Track Record Length (data required before promotion).

---

## 7. Causal sanity checks as a falsification filter

The goal is **not** to prove causality. It is to rule out stories that fail their own basic implications before committing to heavier modeling. These test one feature at a time and **cannot detect multivariate confounding** — that's Ch. 15.

### Three traps

| Trap | Mechanism |
|---|---|
| **Confounding** | Feature and label share a common driver; correlation vanishes when the driver shifts (momentum and forward returns both responding to vol regime) |
| **Conditioning traps** | Wrong control creates spurious relationships (collider) or removes the effect (mediator). Inclusion depends on causal structure, **not statistical significance**. |
| **Construction artifacts** | Pipeline encodes selection or timing rather than market information — e.g. a rolling window overlapping the label horizon |

### Three structural roles — decide before controlling for anything

| Role | Structure | Conditioning effect |
|---|---|---|
| **Confounder** | Common cause → both feature and label (VIX regime → momentum strength *and* return dispersion) | **Condition on it** — blocks the spurious path, isolates any direct relationship |
| **Mediator** | Feature → mediator → label (momentum → flows → liquidity → further appreciation) | **Do not condition** unless specifically testing for effect beyond the mediated path — you'd delete the signal |
| **Collider** | Feature → common effect ← label (momentum and returns both drive fund flows) | **Do not condition.** Unconditionally harmless; conditioning (e.g. restricting to high-flow funds) *induces* spurious correlation |

> **The collider is the counterintuitive one, with a number:** in the synthetic simulation, conditioning on fund flows creates an approximately **−0.25 correlation between two genuinely independent variables**. This is why "add more controls" is not a safe default. If you can't assign a role, flag the feature for the Ch. 15 toolkit rather than guessing.

DAGs in finance are small — three to five nodes, one hypothesis about one feature. The point is that "momentum predicts returns" is untestable while a DAG placing an arrow from momentum to returns and specifying that vol regime affects both commits you to checkable implications.

### The four checks

| Check | Protocol | Expected if mechanism real |
|---|---|---|
| **Timing placebo** | Shift feature back by 5, 21, 63, 126, 252 bars; recompute IC at each lag | IC strongest near lag 0, decaying as feature goes stale |
| **Shared-driver** | Replace label with an unrelated outcome (Treasury returns for an equity microstructure feature) + cross-sectional permutation null | IC indistinguishable from zero on the control; observed IC far outside the permutation null |
| **Regime heterogeneity** | Partition by state variable (VIX terciles), recompute IC within each | Magnitude may attenuate; **sign and rough magnitude should hold** |
| **Event-time alignment** | For event-motivated features, IC in event-time windows | IC concentrates where the mechanism predicts |

> A mechanical floor exists on the timing placebo: for a rolling feature with lookback *L*, a *k*-shifted version shares roughly (L−k)/L of its inputs with the original. Focus on decay at lags **beyond the lookback window**, not near it. Flat or *increasing* IC at distant lags means the feature is proxying a slow-moving state variable rather than carrying timely information.

### Plausibility scorecard

| Check | Pass | Caution | Stop |
|---|---|---|---|
| Timing placebo | IC significant (HAC) **with meaningful decay** | IC persists without clear decay | No timely signal; IC increases at distant lags |
| Shared-driver | IC ≈ 0 on control outcome (HAC) | IC small but nonzero | IC significant on control (HAC) |
| Regime heterogeneity | IC stable across partitions | IC varies; sign flip not HAC-significant | **Sign flip HAC-significant AND unconditional IC ≈ 0** |
| Event-time alignment | IC concentrates post-event | IC spread across windows | IC peaks **pre**-event (anticipation, leakage, or confound) |

> **REVISE is the expected outcome, not a disappointment.** In efficient markets cross-sectional ICs are small and few single features cleanly pass every check. REVISE tells you *where and when* a feature works — which is exactly what downstream model design needs.

### Worked contrast

| | 12-1 Momentum → **REVISE** | 1-day Reversal → **STOP** |
|---|---|---|
| Timing placebo | IC peaks at lag 0 (**0.053**), persists to lag 252d (**0.034**) — partly mechanical for a 231d lookback, but timely | Near-zero IC at all lags — no information to decay |
| Shared-driver | No Treasury association; IC well above permutation null — **passes cleanly** | IC indistinguishable from shuffled noise |
| Regime heterogeneity | Sign stable, magnitude varies **~5×** across VIX regimes; concentrates in low-vol | **Sign flips** (HAC-significant) with near-zero unconditional IC |

Momentum's regime concentration is consistent with documented momentum crashes and is an *actionable* finding motivating regime-conditional modeling downstream. Reversal's profile is a textbook **aggregation artifact** — opposite information in low- and high-VIX markets averaging to nothing.

---

## Transferable rules

1. **Define the label before selecting an algorithm.** Label misalignment manufactures predictability that no model choice can fix.
2. **Match the execution convention to the actual execution assumption** and keep it identical in label computation and backtest PnL — the gap is 50–100 bps per trade on daily equities.
3. **Any step estimating parameters from data is fit train-only, refit per fold.** When unsure, treat it as fitted.
4. **Preserve tails when tails are the prediction target;** winsorize only when they aren't.
5. **Treat missingness as three distinct mechanisms** and never let imputation erase it without an indicator.
6. **Compute standard errors on effective sample size, not row count.** Overlap can shrink 248k observations to 12k.
7. **Summarize diagnostics by fold, never pooled.** Sign consistency across folds is the stability gate; pooled IC can read 0.001 while fold-level reads 0.064.
8. **Thresholds set both event magnitude and base rate simultaneously** — choose them against the turnover and cost budget, and estimate percentiles within-fold.
9. **Log the searched-set size with every p-value.** Without it, significance claims are uninterpretable.
10. **Separate the exploration pass from the confirmation pass,** and never confirm on the data used to promote.
11. **Post-hoc parameter changes are new trials.** Count them.
12. **Assign a causal role (confounder / mediator / collider) before conditioning on any variable.** More controls is not safer — conditioning on a collider fabricates correlation.
13. **A gross spread that doesn't clear estimated costs is a stop, not a revise.**
14. **Expect most candidates to fail correction.** Zero of 13 surviving BH-FDR is a normal result, not a broken pipeline.

---

## Notebooks

| Notebook | Covers |
|---|---|
| `01_data_quality_diagnostics` | Distribution characteristics across all datasets, tail statistics informing scaling choice |
| `02_preprocessing_pipeline` | `SplitAwarePreprocessor`, leakage demonstration, winsorization, coverage by column/asset/period |
| `03_label_methods` | Execution conventions, fixed/variable horizons, trend scanning, uniqueness, meta-labeling |
| `04_maximum_favorable_adverse_excursion` | MFE/MAE visualization, barrier calibration, hit fractions, resolution-time distributions |
| `05_signal_evaluation` | Correctness screens, fold-level IC/ICIR, IC decay, ROC/PR AUC with Wilson CIs, turnover, break-even |
| `06_ic_inference` | HAC inference, stationary block bootstrap, minimum track record planning |
| `07_multiple_testing` | HAC p-values, BH-FDR, Holm–Bonferroni on a simulated factor zoo; previews Rademacher and DSR |
| `08_causal_sanity_checks` | Feature × horizon scan, timing placebo, shared-driver, regime heterogeneity, collider simulation |

---

## Cross-references

Ch. 2 / Ch. 4 PIT correctness and corporate actions (prerequisite to §1) · Ch. 3 volume and information bars for activity-based horizons · Ch. 6 walk-forward protocol, purge/embargo, run logging and trial taxonomy · Ch. 8–10 the candidate features this framework screens · Ch. 11–12 multivariate model selection, which makes the decisive judgments triage cannot · Ch. 12 tree models with native missingness handling · Ch. 15 multivariate causal toolkit for features flagged here · Ch. 16 §16.7 Rademacher complexity for correlated candidates; Deflated Sharpe in depth · Ch. 17 allocator-based sizing (the book's alternative to meta-labeling) · Ch. 20 stop-loss design and risk-management context for barrier labels

---

## Citations

Asness, Moskowitz & Pedersen (2013), cross-asset momentum · Bailey & López de Prado (2014), Deflated Sharpe Ratio · Bailey et al. (2015), Probability of Backtest Overfitting · Benjamini & Hochberg, FDR control · Daniel & Moskowitz (2016), momentum crashes · Glasserman et al. (2025), overnight vs. intraday return accrual · Grinold (1989), Fundamental Law of Active Management · Harvey, Liu & Zhu (2016), t > 3.0 threshold for factor discovery · Holm, sequentially rejective Bonferroni · López de Prado (2018), trend scanning, triple barrier, uniqueness, sequential bootstrap, meta-labeling

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 7.*
