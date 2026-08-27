# Ch 15 — Causal Machine Learning

**Governs:** the multivariate estimation machinery that features surviving Ch. 7's bivariate triage require, plus the refutation tests every causal claim must pass.
**Thesis:** a sophisticated estimator cannot rescue an identification failure. The pipeline runs DAG → adjustment set → estimand → estimation → refutation, and the goal is not to prove causation from observational data but to **distinguish robust claims from those that collapse under scrutiny.**

---

## 1. Method selection

| DAG known? | Treatment type | Method | Library |
|---|---|---|---|
| Yes | Binary/continuous | Backdoor adjustment | DoWhy |
| Yes | **Continuous** | **DML** | EconML |
| Yes | **Binary (event)** | **BSTS** | tfp-causalimpact |
| No | Discovery, time series | **PCMCI** | Tigramite |
| No | Discovery, cross-section | NOTEARS | causal-learn |
| No | Discovery, time series | VAR-LiNGAM | causal-learn |

> **The assumption-fragility ordering is the selection rule.** Where a DAG and valid adjustment set are defensible, DML has the strongest finite-sample guarantees. Where the treatment is a discrete event, BSTS shifts the burden onto control-series stability and spillover testing. Where neither holds, discovery methods generate candidates whose credibility scales with their stationarity and confounding assumptions. **DML with a well-specified DAG on a clean panel produces more credible results than PCMCI on a short noisy series, even though PCMCI is technically more ambitious.**

---

## 2. Defining the causal question

**Fix treatment, outcome, estimand, target population, and timing before fitting any model.** Without this, causal analysis degenerates into post-hoc rationalization — another form of the selection bias it aims to eliminate.

| Term | Definition |
|---|---|
| **ATE** | Average marginal effect across the target population, under specified controls |
| **Subgroup ATE** | The ATE re-estimated within a stratum (e.g. a volatility regime) |
| **CATE** | Covariate-conditional effect from a **single heterogeneity model** (causal forest, X-learner) |
| **Effect modifier** | A variable along which the effect is allowed to vary |
| **Confounder (control)** | A pre-treatment variable adjusted for to block a backdoor path |
| **Refutation** | A diagnostic that can **weaken** a claim but cannot prove it |

> **Two distinctions that are routinely conflated and change what you're estimating.** Splitting the sample by regime and re-estimating yields **subgroup ATEs** — it does not fit a model of how the effect varies with covariates; a **CATE requires a heterogeneity estimator that learns the effect surface directly.** And a confounder is adjusted for to remove bias while an effect modifier defines how the effect changes — **EconML exposes these as separate arguments (`W` vs. `X`), and using the wrong one changes the quantity being estimated.**

**Four assumptions before any estimand is causal:** consistency · **overlap** (both treated and untreated observations available across relevant covariates) · **no interference / SUTVA** · **conditional exchangeability.**

> These are demanding in markets: prices aggregate information quickly, assets interact through common factors and portfolio flows, and treatment timing is often ambiguous. **The point is not to pretend they hold — it's to state the question precisely enough that they can be inspected.**

**The estimand fixes the horizon too.** The effect of a funding-rate shock on *next-period premium reversion* is not the same estimand as its effect on *multi-day forward returns* — the first asks whether the premium mean-reverts, the second whether the shock survives all other return drivers.

---

## 3. Adjustment sets — why more controls is not safer

**Backdoor criterion:** an admissible set blocks every noncausal path from treatment to outcome beginning with an arrow into treatment, **and contains no descendants of treatment.**

> **Admissibility depends on causal structure, not predictive power. Statistical significance, feature importance, and predictive accuracy do not determine the adjustment set.**

| Bad control | Damage |
|---|---|
| **Mediator** | Removes part of the pathway through which treatment acts — **changes the estimand** |
| **Collider** | **Opens a noncausal path that was previously closed** |
| **Treatment descendant** | Post-treatment bias |

> **This is why kitchen-sink regression is dangerous in causal work.** Adding variables does not automatically make an estimate safer; it may do the opposite.

**Timing discipline is the most practical screen** — every control should be known before treatment is realized. Event studies must avoid variables reacting contemporaneously to the event (especially with macro announcements that move broad markets instantly); factor studies must avoid realized performance, portfolio outcomes, or anything mechanically built from future returns.

> **But timing discipline is necessary, not sufficient.** A variable observed before treatment can still be a **collider, a selection variable, or a proxy for a conditioning event that changes the population.** Filtering on liquidity, analyst coverage, or fund flows looks harmless because they precede the outcome horizon — yet they bias results if they are common effects of prior performance, attention, and treatment exposure. **The DAG remains the governing object.**

**Write the DAG before choosing the estimator.** DoWhy makes this operational by requiring the graph, treatment, and outcome to be declared before deriving the estimand. **It doesn't remove judgment; it exposes where judgment enters.** If identification fails, the problem is the research design, not a weak estimator.

---

## 4. Alternative identification designs

Each replaces broad unconfoundedness with a **narrower assumption about the source of identifying variation.**

| Design | Identifying variation | Hardest assumption |
|---|---|---|
| **Backdoor adjustment** | Observed confounders | Admissibility without post-treatment or selection bias |
| **Instrumental variables** | External shifter of treatment | **Exclusion** — instrument affects outcome *only* through treatment |
| **Difference-in-differences** | Differential change over time, treated vs. control | **Parallel trends** absent treatment |
| **Regression discontinuity** | Assignment rule near a threshold | **Continuity** of potential outcomes through the cutoff |
| **Event-study counterfactual** | Event timing + uncontaminated controls | **No spillover** to control series |

> **IV's exclusion restriction is usually the hardest to defend in finance.** A policy announcement, index rule, or market-structure change may shift the treatment — but it may also affect attention, liquidity, risk appetite, and funding conditions, each a direct path to the outcome. **When effects vary across units, IV identifies a *local* effect for units the instrument actually moves, not a population average. State that explicitly.**

> **RD's strength is its locality — and that's also its limit.** The estimate applies to the margin around the threshold. Credibility collapses if units can manipulate position around the cutoff, if other rules change at the same cutoff, or if too few observations sit near the boundary.

**No design is superior; each exchanges one set of assumptions for another.** Choose the comparison whose assumptions are most defensible, state the corresponding estimand, then test whether the claim is fragile under plausible perturbations.

---

## 5. The refutation toolkit

Three separable questions:

| Question | Tool |
|---|---|
| Does the method detect effects where none should exist? | **Placebo and negative controls** |
| How much omitted confounding would overturn the result? | **Sensitivity analysis** |
| Does the effect persist across samples, specifications, outcomes? | **Stability checks** |

**Placebo treatment** — randomize, shift, or otherwise falsify the treatment assignment. **Placebo date** — apply the same counterfactual model to non-event dates. **Negative control outcome** — an outcome that should not respond; if it does, you have residual confounding, timing leakage, or misspecified adjustment.

> **The goal is not exactly zero in finite samples — it's verifying the method does not systematically discover effects where the design says none exist.**

**Sensitivity interpretation should be conservative:** if a *small* omitted-confounder perturbation changes sign, magnitude, or significance, **the result is not separable from the assumed confounder structure. Treat it as a hypothesis, not evidence.**

**Three stability dimensions:** subsample (a funding effect appearing only in one short volatility regime may be real, but **the estimand is then regime-specific, not general**) · specification (vary nuisance learners, adjustment sets, control series, model windows) · **outcome triangulation** — do effects appear where the mechanism predicts, weaken where it's indirect, and **disappear for outcomes that should not respond?**

> **A claim passing these checks is not proven causal — it is credible under the stated assumptions and tested perturbations. A claim failing them should be downgraded to a research hypothesis requiring a stronger design, not automatically discarded.**

---

## 6. Double Machine Learning

**Identification checklist:** treatment timing fixed, covariates strictly pre-treatment · estimand declared · unconfoundedness argued · **cross-fitting respects time ordering** · sensitivity analysis run.

**Three steps** (the ML analogue of Frisch–Waugh–Lovell): predict outcome from controls, take residual · predict treatment from controls, take residual · regress residual on residual.

> **Residualization alone is not what makes DML work.** The key is the **orthogonal score** — an estimating equation constructed so small errors in the nuisance models have only **second-order** effect on the target parameter. That's what permits flexible ML for nuisances without regularization bias dominating inference.

> **Cross-fitting must respect temporal ordering: expanding or rolling windows, never random folds, with a temporal gap where forward returns overlap.**

### Nuisance-model sensitivity is a diagnostic, not a footnote

> **On ETF momentum, the DML ATE spans roughly a 2× range across nuisance learners** — linear, shallow gradient boosting, and deep gradient boosting give materially different estimates. **Large changes across reasonable nuisance learners are evidence the causal conclusion is unstable.** Mitigate with flexible learners, CV tuning, and comparison across **at least two model classes.**

### Confounding bias runs in both directions

> **ETF momentum:** naive OLS slope is negative with a HAC interval; after orthogonalization the DML estimate is **more negative**, excluding zero. **The naive slope *understates* the magnitude by roughly a third — naive factor research misses part of the effect rather than overstating it.** (HAC bandwidth must match the 21-day forward outcome; a shorter bandwidth understates the overlap-induced autocorrelation.)
>
> **Crypto funding rates:** the reverse. Naive and DML keep the same sign, but **confounders suppress ~90% of the effect magnitude.** A block-permutation test shuffling treatment in **seven-day blocks passes (p ≈ 0.00)**; shortening to **one-day blocks inflates the statistic** — too-short blocks understate the autocorrelation null. Yet **neither estimate is statistically significant: even DML cannot guarantee robustness when the underlying signal is weak.**

### Outcome choice shapes causal credibility

Same treatment (funding-rate z-score above 2), two outcomes:

| Outcome | Mechanism | OOS drift | Placebo ratio |
|---|---|---|---|
| Forward returns | Broad market outcome exposed to sentiment, positioning, risk appetite | **85%** | **12.7%** |
| Premium reversion | Mechanism-adjacent: funding incentives and arbitrage pressure | **51%** | **5.7%** |

> **The broad outcome is substantially more fragile on both diagnostics.** But the mechanism-adjacent outcome is **not conclusive either** — 51% drift is not small, and the outcome is mechanically close to the treatment definition, so reversion may partly reflect ordinary mean reversion after an extreme observation.

> **The methodological lesson: begin with the treatment–outcome pair, not the estimator.** A narrow mechanism-consistent outcome is not automatically valid and a broad market outcome is not automatically invalid — **but broad outcomes require stronger assumptions, richer controls, and more careful sensitivity analysis. A simple estimator on a well-chosen outcome supports a more credible claim than a sophisticated estimator on a weakly connected one.**

### Regime-conditional sizing — the honest result

CausalForestDML with volatility and regime indicators as **effect modifiers** (`X`) and the volatility panel plus yield-curve slope as **controls** (`W`). Strict temporal split; regime thresholds, CATE estimates, and position rules fixed before the test period.

CATE **varies in sign across regimes**. Sizing rule: regime multiplier from the within-regime signal-to-noise ratio, **clipped so imprecise estimates shrink toward neutral exposure** — halving exposure where the effect reverses sign, raising it where the signal is strong and precisely estimated.

> **Sharpe ratios are positive in training for all three strategies (naive, causal, heuristic) and negative in holdout for all three.** Causal is best of the three in holdout but **does not deliver positive risk-adjusted returns.** The reason: **momentum IC inverts post-2022.** No sizing rule rescues a treatment whose relationship to forward returns flips sign.
>
> **The transferable claim is narrow and worth stating precisely: causal analysis reduces out-of-sample degradation when training-period heterogeneity carries information. It does not guarantee alpha when the underlying signal breaks down.**

### Post-double-selection LASSO for factor-zoo validation

> Among four managed-portfolio factors, **only MeanRev clears the naive significance bar — and that signal collapses to insignificance once the first ten principal components of the asset universe are included as controls.** The BCH/FGX correction substantively changes the inferential conclusion.

---

## 7. BSTS for discrete events

**Identification checklist:** estimand is the post-period counterfactual difference (ATT on the treated series) · control-selection rule defined and **spillover risk assessed** · pre-period relationship stability verified · **placebo dates tested** · robustness across alternative control sets.

**Two assumptions:** the pre-period target–control relationship holds in the post-period absent the event, and **the event does not affect the controls.**

> **Spillover is the most common failure mode in financial event studies.** Mitigate by choosing controls from asset classes with weak fundamental linkage to the event. **Useful diagnostic: run BSTS with each control as the target — any control showing a "significant" effect is contaminated.**

### The worked example is a negative result, and that's the point

FOMC announcements on IEF, controls VEA/EFA/DBC, 60-day pre-period, 20-day post-period, log-price indexes.

**All four events produced 95% credible intervals excluding zero** — signs plausibly matching macro context (March 2023 hike amid banking stress positive, consistent with flight-to-quality; July 2023 hike negative — same policy action, opposite response).

> **Then the validation rejected the design. Seven of twelve placebo dates yielded intervals excluding zero — a ~58% false-positive rate.** The model finds "significant" effects on arbitrary non-event dates at over half the rate it finds them on FOMC dates. **Under that condition the apparent significance of the four events cannot be attributed to the announcements.**
>
> **The spillover check confirms it: all three control ETFs respond on three of the four FOMC dates.** The same policy shock propagates across global equities, developed-market bonds, and commodities through dollar and risk-appetite channels — **so the counterfactual absorbs the announcement effect rather than isolating it.** A more conservative design would use duration-matched non-US sovereign bonds or a local-level model with no cross-asset controls.

> **Run the spillover check per event rather than transferring the verdict from a single date** — DBC alone responded in July 2023 while all three responded on the other dates.

> **Posterior probability vs. credible interval.** A true posterior probability is the integral of the posterior above or below zero — a Bayesian tail probability **over the parameter, not over time.** The fraction of point-effect *rows* whose mean is positive is a **sample frequency over the post-period** that can be high or low for reasons unrelated to whether the effect is real. **The reliable diagnostic is whether the cumulative-effect credible interval excludes zero, supported by placebo tests with a low false-positive rate. When the placebo rate is high, neither the interval nor any derived sign frequency is trustworthy.**

---

## 8. Causal discovery — hypotheses, not signals

**Shared assumptions:** causal sufficiency (no unobserved common causes) · faithfulness · **stationarity.** All demanding in markets with omitted macro drivers, regime changes, simultaneous feedback, and evolving structure.

| Method | Typical use | Strength | Key limitation |
|---|---|---|---|
| **Granger** | Preliminary screening | Simple, intuitive | **Pairwise and predictive rather than causal** |
| **PCMCI** | Multivariate lagged discovery | Controls autocorrelation and indirect links via relevant parent sets | Strong assumptions; can be conservative |
| **VAR-LiNGAM** | Temporal discovery with structural assumptions | **Uses non-Gaussianity for identification** — often more plausible in finance than Gaussianity | Linear; assumes no hidden common causes |
| **NOTEARS** | **Cross-sectional/contemporaneous** DAG learning | Converts combinatorial DAG search into differentiable continuous optimization | Original formulation linear, **not time-series specific** |

### The comparison result is the lesson

> **Seven ETFs, daily, 2015–2024, identical data:** Granger finds **26** FDR-significant edges · PCMCI **42** lagged links · NOTEARS **5** contemporaneous edges · VAR-LiNGAM **1 edge via causal-learn but 11 from scratch.** **The spread from one edge to 42 on the same data is the central finding.** Each method operationalizes different assumptions and responds differently to noise, dimensionality, and weak dependence.

**What survives is what agrees.** XLF (financials) leading the broad market by one day appears in the PCMCI graph as a dominant driver, survives **both** VAR-LiNGAM implementations, and appears in NOTEARS as a within-day edge stable in 69% of bootstrap resamples. **Edges confirmed by multiple methods carry more weight than those depending on a specific specification.**

> **Effect size, not just p-value.** PCMCI's 42 links have **median absolute partial correlation ≈ 0.06** — statistically distinguishable from zero but not necessarily economically meaningful. Only a few exceed 0.10.

> **Universe composition drives the result.** A four-asset macro panel (SPY, IEF, GLD, VIX) finds **zero** significant lagged links, with the most stable edge appearing in only **37% of block-bootstrap resamples** — below a 50% robustness threshold. Adding sector ETFs introduces genuine dependencies. **Interpret discovery results conditionally on assets, frequency, and sample period.**

> **The same algorithm under different estimation and pruning strategies produces radically different graphs** — VAR-LiNGAM from scratch (VAR via Ridge, raw ICA on residuals) finds 11 edges; the library version with DirectLiNGAM and statistical pruning retains 1.

> **On the ADIA Lab challenge:** supervised methods dramatically outperformed classical discovery baselines, but the result is narrow — it shows that **with many labeled dataset–graph pairs from a stable simulator family**, a supervised model learns the mapping from statistical patterns to causal-role labels well. That is amortized inference under a known synthetic regime, **not transferable causal competence.** In practice researchers rarely have labeled true graphs, and market data carry latent confounding, structural breaks, simultaneity, and endogenous sampling. **Benchmark success may reflect the benchmark's own structure.**

---

## 9. Case study causal evidence — the two gates

One primary treatment per case study, DML with HAC inference plus a block-permutation refutation. **Gate 1: HAC significance p < 0.05. Gate 2: refutation p < 0.05.**

| Case | Treatment | DML effect | HAC t | p | Bias | Refut. | Gates |
|---|---|---|---|---|---|---|---|
| **ETFs (21d)** | momentum | −0.058 | −9.84 | <0.001 | +33.2% | 0.00 | **both** |
| **US Firms (1m)** | factor | +0.007 | +1.98 | 0.048 | +42.8% | 0.03 | **both** |
| **S&P 500 Options** | VRP, HTM | −0.123 | −4.69 | <0.001 | +49.8% | 0.03 | **both** |
| **US Equities (1d)** | momentum | −0.001 | −2.16 | 0.031 | +68.8% | 0.00 | **both** |
| NASDAQ-100 (15m) | microstructure | ~0.00 | +2.52 | 0.012 | −9.9% | 0.11 | HAC only |
| Crypto (8h) | premium z | −0.001 | −1.03 | 0.303 | +68.3% | 0.00 | refutation only |
| S&P 500 Eq+Opt (5d) | IV–RV spread | −0.002 | −1.50 | 0.135 | +86.5% | 0.00 | refutation only |
| FX Pairs (1d) | momentum | +0.0004 | +0.42 | 0.675 | **−213.5%** | 0.30 | neither |
| CME Futures (5d) | carry | +0.0003 | +0.75 | 0.454 | −59.7% | 0.19 | neither |

> **The gates rarely agree, and the disagreement is informative because they probe different properties.** Refutation asks whether the estimate is distinguishable from a **placebo-generated artifact**; HAC asks whether it is distinguishable from **zero** under inference robust to heteroskedasticity and serial correlation. **NASDAQ-100 is HAC-significant but does not separate from placebo — the pattern expected when autocorrelation or specification structure carries part of the apparent signal. Crypto and Eq+Opt are the reverse: they reproduce above the placebo background but their HAC errors are too wide. Neither gate alone suffices.**

> **Orthogonalization moves the estimate substantially: median absolute naive-vs-DML gap is 59.7%, exceeding 50% in five of nine case studies.** FX is the only sign reversal, and there the reversed estimate is itself indistinguishable from noise. **A factor evaluation that skips orthogonalization draws its conclusions from systematically distorted coefficients — which is how much of the backtesting literature reports factor premia.**

> **Label engineering is a first-order causal decision, not preprocessing.** ETF momentum at five days is **positive and HAC-significant**; at 21 days it is **negative and larger in magnitude**, and only the longer horizon clears both gates. S&P 500 Options reports five horizons, all negative, but **only the hold-to-maturity variant clears both** — the raw ten-day horizon is HAC-significant without refutation, and shorter and delta-hedged variants overlap zero. Winsorizing the US Firms monthly label **raises the HAC t-statistic but then the estimate fails refutation.**

### Causal effect and predictive signal are different objects

> **A feature can carry one without the other, in both directions.** S&P 500 Eq+Opt extracts a small cross-sectional IC from the IV–RV spread while the causal estimate's HAC interval overlaps zero; Crypto reaches a credibly positive predictive IC while the causal premium-z interval includes zero. **These support continued predictive use without a causal claim of the naive coefficient's magnitude.**
>
> **And the reverse: a treatment clearing both causal gates is not a tradable signal.** Alpha generation needs the cross-sectional ranking machinery of Ch. 11–14, and **the strategy stack consumes predictions, not causal coefficients.**

---

## Transferable rules

1. **Identification precedes estimation.** No estimator rescues a design that cannot justify a causal interpretation.
2. **Write the DAG before choosing the method,** and let structure — not significance or feature importance — determine the adjustment set.
3. **More controls is not safer.** Mediators change the estimand, colliders open closed paths, treatment descendants introduce post-treatment bias.
4. **Timing discipline is necessary but insufficient** — a pre-treatment variable can still be a collider or selection variable.
5. **Start with the treatment–outcome pair, not the estimator.** Mechanism-adjacent outcomes support more credible claims than broad market outcomes.
6. **Declare the estimand precisely,** including horizon — different horizons are different causal questions, not robustness checks.
7. **Distinguish subgroup ATEs from CATEs, and confounders from effect modifiers.** Both distinctions change what is being estimated.
8. **Cross-fit on expanding or rolling windows with a temporal gap,** never random folds.
9. **Sweep nuisance learners and treat large variation as instability,** not as a menu to pick from.
10. **Report the naive-vs-orthogonalized gap.** It is often above 50%, and it can run in either direction.
11. **Size permutation blocks to the autocorrelation.** Too-short blocks understate the null and inflate apparent significance.
12. **Run placebo dates before believing any event study,** and reject the design if the false-positive rate is high — no individual finding survives a broken design.
13. **Test every control as a target for spillover, per event.** For macro events, truly unaffected controls may not exist.
14. **A cumulative-effect credible interval is the diagnostic; a fraction of positive rows is not a posterior probability.**
15. **Treat discovered edges as hypotheses.** Method outputs on identical data ranged from 1 to 42 edges.
16. **Weight edges by cross-method agreement and effect magnitude,** not by p-value or by any single implementation.
17. **Causal analysis reduces out-of-sample degradation when heterogeneity carries information; it does not manufacture alpha when the signal inverts.**
18. **Causal credibility and predictive signal are separable in both directions** — neither licenses the other.

---

## Notebooks

`01_library_overview` (DoWhy, EconML, tfcausalimpact, Tigramite, causal-learn) · `02_dowhy_causal_graph` (full validation workflow: DAG, identification, temporal splits, placebo and refutation, two-outcome crypto contrast) · `03_econml_dml` (manual and EconML DML for ETF momentum, nuisance sensitivity sweep, block-permutation refutation) · `04_dml_crypto_regime` (regime-stratified estimates, block-length sensitivity) · `05_momentum_causal_trading` (CausalForestDML, regime-scaled sizing, three-strategy holdout comparison with 10 bp costs and a 5–20 bp sweep) · `06_fed_announcement_bsts` (spillover diagnostics, four FOMC events, twelve placebo dates) · `07_tigramite_time_series` (PCMCI on four-asset macro panel — the null result) · `08_neural_causal_discovery` (seven-asset panel: PCMCI, NOTEARS, VAR-LiNGAM, Granger side by side) · `09_adia_causal_benchmark` · `10_case_study_insights` (cross-case DML, refutation distributions, bias decomposition) · `11_factor_zoo_validation` (post-double-selection LASSO with PC controls)

For IV estimation, the `linearmodels` library provides standard estimators — not implemented in this chapter.

---

## Cross-references

Ch. 7 §7.5 the bivariate plausibility screen this chapter's multivariate machinery follows; timing placebo and shared-driver checks as single-feature versions of the same logic · Ch. 8 the features whose survivors reach this stage · Ch. 11–14 the predictive machinery that generates tradable rankings — **causal coefficients are not signals** · Ch. 14 double-selection LASSO for factor-zoo testing as a special case of the debiased-ML framework here · Ch. 16 strategy simulation, which consumes predictions · Ch. 17 portfolio construction weighting factors by causal confidence · Ch. 19 risk management accounting for effect uncertainty in sizing

---

## Citations

Belloni, Chernozhukov & Hansen (2014), post-double-selection LASSO · Brodersen et al. (2015), BSTS causal impact · Chernozhukov et al. (2018), double/debiased ML · Feng, Giglio & Xiu (2020), factor-zoo testing · Hyvärinen et al. (2010), VAR-LiNGAM · Olivetti et al. (2026), ADIA Lab causal discovery challenge · Reisach, Seiler & Weichwald (2021), benchmark artifacts in structure learning · Runge et al. (2019b), PCMCI · Shojaie & Fox (2022), Granger causality review · Spirtes, Glymour & Scheines (2000), causation prediction and search · Zheng et al. (2018), NOTEARS

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 15.*
