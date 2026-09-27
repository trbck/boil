# Ch 9 — Model-Based Feature Extraction

**Governs:** features produced by *fitted procedures* rather than deterministic formulas — filtered states, conditional variances, regime probabilities, uncertainty summaries — and the PIT discipline that keeps them honest.
**Thesis:** a fitted object is a feature generator with an estimation window attached. Every estimate must be refit inside the walk-forward training fold, use **filtered** rather than smoothed output, and be versioned with the features it produces.

---

## 1. When a fitted procedure earns its place

Direct aggregation (Ch. 8) fails when the structure is hidden. Four cases:

| Hidden structure | Rolling statistic can't answer | Method |
|---|---|---|
| **Conditional dynamics** | How fast does a volatility shock decay? | GARCH family |
| **Latent state** | Trending or mean-reverting regime? | HMM, Markov-switching |
| **Cyclical structure** | Real weekly pattern or noise? | Spectral (FFT), wavelets |
| **Path geometry** | Same start/end/vol, different path | Path signatures |

**Organizing principle: one fitted procedure generates several feature types.** A Kalman filter yields level, trend, innovation, *and* uncertainty. GARCH yields a conditional variance path *and* persistence parameters. A regime model yields probabilities, expected durations, *and* transition structure.

> The PIT obligation tightens here relative to Ch. 8. A GARCH parameter or HMM state probability depends on an estimation window, and that window must be confined to the training fold, versioned, and monitored for drift. Model selection — ARIMA order, number of HMM states, fractional differencing order *d* — is itself a fitted step and must be repeated inside each training window.

---

## 2. Diagnostics that double as features

### Stationarity tests

ADF and KPSS begin from **opposite nulls**, which is why running both is worth the cost:

| ADF (null: unit root) | KPSS (null: stationary) | Reading |
|---|---|---|
| Rejects | Doesn't reject | Evidence favors stationarity under the chosen specifications |
| Doesn't reject | Rejects | Evidence favors non-stationarity |
| **Both reject** | | **Conflicting** — deterministic trend, structural breaks, nonlinear mean reversion, or changing volatility not cleanly captured by either |
| **Neither rejects** | | **Inconclusive** — short window, high persistence, or limited power |

**The test outputs matter as much as the verdict.** Track statistics and p-values over rolling windows: ADF statistic moving toward zero (or p rising) → weakening evidence against a unit root. Rising KPSS statistic → weakening evidence for stationarity. These become **lagged inputs** measuring how stable the process appears at decision time — not a binary stationary/non-stationary label.

> In cross-sectional settings these tests are most informative on **spreads, valuation ratios, volatility proxies, residualized returns, and slow firm characteristics** — not raw daily equity returns, which are already close to stationary in level while still violating strict stationarity through vol clustering and liquidity shifts.

### Structural breaks

| Method | Use when |
|---|---|
| **Zivot–Andrews** | One plausible major discontinuity; distinguishing a true unit root from a broken but stable process. Break chosen endogenously. |
| **Bai–Perron** | Longer samples where multiple breaks are realistic — identifies several candidate dates rather than forcing one-or-none |
| **CUSUM** | **Online monitoring** — accumulates deviations, triggers on sustained drift. Useful even though the exact break date is only clear in hindsight. |
| **Supervised classification** | Combine weak signals (shifts in location, scale, dependence, distributional shape); best when labeled break examples exist and no classical test is decisive across regimes |

**Feature outputs:** break dates, **time since most recent break**, pre/post-break means, CUSUM statistics, classifier probabilities.

> A break marks a discrete change in the data-generating process. A **regime** model assumes states *recur*. Don't use break machinery for recurring conditions or regime machinery for one-way structural change.

### Fractional differencing

First differencing removes the low-frequency component in one blunt step. Fractional differencing with real order *d* applies slowly decaying lag weights, occupying the continuum between no differencing and first differencing. For the stationary long-memory case (roughly 0 < d < 0.5) autocorrelations decay **hyperbolically** rather than exponentially.

**Boundary convention is part of the feature definition** — two defensible choices:

| Convention | Behavior |
|---|---|
| **Full-window** (fixed-width, López de Prado style) | First observations unavailable until lookback accumulates → warmup period + validity mask |
| **Boundary-partial** (truncated weights) | Applies whatever weights are available near the start → preserves row count, but early observations come from a **shorter effective filter** |

> Whichever you pick, downstream models must know which observations rely on a partial filter and how many rows the full-window convention would have cost. Changing *d* changes how slowly weights decay; changing the truncation rule changes how much history must be retained. **Both simultaneously affect how much persistence remains and how many observations are usable.**

**Selection workflow (walk-forward safe):** evaluate a bounded *d* grid over the *training window* → compute a stationarity diagnostic (ADF) for each → assess retained correlation with the original series → **take the smallest *d* that yields an acceptable diagnostic while preserving maximum memory.** Not a globally "optimal" *d* computed on the full sample.

---

## 3. Signal transforms

### Kalman filter

Unlike an EMA or rolling OLS trend, the filter **does not commit to a fixed lookback** — its gain adapts to the estimated signal-to-noise ratio. Predict step projects the state forward; update step revises with the new observation. Smooth series relative to assumed noise → state moves steadily; erratic observations → filter becomes cautious.

**Four features from one fit:**

| Output | Interpretation |
|---|---|
| **Level** | Filtered underlying level — adaptive trend anchor |
| **Trend** (slope) | Momentum feature **without a fixed lookback** |
| **Innovation** | Prediction error — natural surprise variable |
| **State uncertainty** | Estimated state variance — how confident the filter is in itself |

> These carry more information than a moving-average crossover because they separate **direction, surprise, and confidence** rather than collapsing all three into one smoothed line.

**Calibration anchor:** on SPY, the Kalman slope achieves an IC with 5-day forward returns roughly **9× stronger** than a 20-day rolling OLS slope. Both are negative (consistent with short-term mean reversion) — the adaptive filter separates signal from noise far more effectively at the same nominal task. The innovation feature spikes around earnings seasons and macro releases, i.e. when the smooth model is repeatedly surprised, which makes it a useful conditioner for triaging *other* signals.

The same state-space logic extends to **dynamic hedge-ratio estimation**, letting beta evolve rather than treating it as a fixed constant.

### Spectral features

| Feature | Measures |
|---|---|
| **Spectral energy** | Total power, or power in a target band — strength of cyclical structure |
| **Dominant period** | Period of the largest peak in the rolling spectrum |
| **Spectral entropy** | Concentration vs. diffusion of normalized power — low = few strong periodic components, high = noise-like |
| **Low-frequency ratio** | Fraction of energy below a cutoff (e.g. 1/21) — slow trend-like vs. fast noisy variation |

> **Compute causally.** At time *t* the transform uses only a trailing window, never the full sample. **Window length sets frequency resolution** — a quarterly cycle cannot be resolved in a short window. Use several lengths; 21, 63, and 126 days capture different cycles in daily data.

**How this differs from Ch. 8 calendar features:** cyclical sin/cos encodings *impose* known cycles. Spectral features ask whether a cycle is **actually present** and whether its strength is rising, stable, or fading. That distinction matters whenever cyclical structure is itself time-varying.

### Wavelets — research diagnostic, not a deployable feature

Fourier says *which* frequencies are present; wavelets also say *when*. Multi-resolution decomposition separates coarse (slow) from fine (short-lived) components while retaining temporal localization — detail bands map roughly from 2–4 day fluctuations through 32–64 day components, with the approximation term capturing slower trend.

> **Standard wavelet decompositions are usually not causal.** Coefficients at time *t* can depend on observations on *both sides* of *t*. Excellent for offline horizon discovery; **not automatically safe for live pipelines.** The correct workflow: use wavelets to find which scale carries the informative structure, then **build a causal proxy at that horizon** — don't deploy the offline coefficients.

### Path signatures

Two windows with identical start, end, and realized volatility can differ materially in *how* the path got there. A steady rise then sharp reversal is not the same pattern as an early selloff then gradual recovery — but endpoint-and-dispersion summaries treat them as near-identical.

- Depth-1 records total displacement (net change)
- Depth-2 begins to capture interactions between coordinates, including **lead–lag structure**
- Higher depths capture finer geometry, but term count grows rapidly

> **Time augmentation is essential for financial series.** Without an explicit monotone time coordinate, two paths with the same geometric trace but different ordering look too similar at low depth. Adding it lets the signature distinguish "rose early then faded" from "fell early then recovered" — which is often the whole point.

**Use log-signatures, not full signatures** — the full version carries algebraic redundancy; the log version is more compact while preserving expressive information. **Depth-2 log-signatures are the sensible default for daily applications;** higher depths inflate dimensionality fast and are defensible only when path shape is central.

Signatures complement return/volatility/momentum features rather than displacing them. The same principle reappears in learned form in later chapters — TCNs, RNNs, and transformer encoders also convert raw sequences into richer internal representations exposed as features.

---

## 4. Volatility models as feature extractors

Fitted models add three things direct aggregation cannot: conditional estimates that update as shocks arrive, separation of short/medium/long-horizon contributions, and **parameters describing persistence and asymmetry that are informative in their own right.**

### ARIMA — mostly a preprocessing tool

For liquid daily returns, low-order ARIMA adds little as a standalone predictor. Its value is elsewhere:

- **Residual** — de-meaned/de-trended input for the volatility model that follows (prewhitening). Usually the more useful of the two outputs.
- **One-step forecast** — usable directly for series with clearer serial structure: realized volatility, bid–ask spreads, funding rates, futures basis

Keep order selection conservative — ARIMA(1,0,1) or (2,0,1) for stationary inputs. **Any automated order search must be repeated inside each walk-forward training window,** or the lag structure itself is chosen with knowledge of later data.

### GARCH family

| Feature | Source | Meaning |
|---|---|---|
| `cond_vol` | Fitted conditional σ | Volatility state at *t*; **more responsive than fixed-window realized vol** because it updates recursively |
| `shock_impact` | α | How strongly volatility reacts to recent shocks |
| `vol_persistence` | β | Persistence of the volatility process |
| Half-life | ln(0.5)/ln(α+β) | How slowly a volatility shock decays |
| `long_run_vol` | ω/(1−α−β) | Unconditional variance level — **conditional on stationarity** |

> **Calibration anchor:** SPY GARCH(1,1) gives an implied shock **half-life of about 23 trading days.** This is why volatility models contribute useful features even when mean-return models don't — volatility clusters, and the clustering is parsimoniously summarizable.

> **Guard on `long_run_vol`:** if α+β ≥ 1 the model behaves like IGARCH and implies **no finite unconditional variance**. The long-run level is then not a valid feature. Either constrain estimation to stationary fits or explicitly flag non-stationary estimates — silently emitting the ratio produces garbage exactly when volatility is most extreme.

**Asymmetry:** standard GARCH is symmetric because it depends on squared innovations. EGARCH models log variance with an asymmetry parameter — negative values mean negative shocks raise future volatility more than equal-magnitude positive shocks. That parameter is the natural `leverage_effect` feature. GJR-GARCH achieves the same via an indicator for negative shocks; **the choice between them is empirical.**

Read the leverage parameter as a **conditioning variable**, not a forecast: a strongly negative value says downside shocks have disproportionate consequences, which matters for risk controls, for interactions with momentum/carry, and for judging whether a volatility rise is generic turbulence or specifically downside stress.

### HAR — the strongest simple baseline

Regresses next-day volatility on daily, weekly, and monthly averages of realized volatility. The horizon-specific measures are Ch. 8 inputs; **HAR adds a fitted layer that weights them.** Larger monthly coefficient → more persistent conditions; larger daily coefficient → greater sensitivity to recent shocks.

> **HAR beats GARCH decisively on SPY out-of-sample: RMSE 0.061 vs. 0.111 — roughly half.** The weekly component dominates, consistent with institutional-frequency dynamics driving index volatility. The multi-horizon decomposition captures persistence structure a single-lag recursion misses. If you fit only one volatility model, this is the one.

Specify HAR on daily realized volatility, ideally from intraday returns. With only daily OHLC, Garman–Klass or Yang–Zhang serve as proxies — same model, different input.

### Re-estimation cadence — two separate decisions

**How often to refit parameters** vs. **how to update features between refits.**

| Model | Refit cadence | Between refits |
|---|---|---|
| GARCH | Weekly–monthly (parameters move slowly) | Conditional variance recursion updates **daily** on fixed parameters |
| EGARCH asymmetry | Not daily | Same recursion logic |
| HAR | Rolling schedule, somewhat more regime-sensitive | Daily/weekly/monthly RV inputs update as new observations arrive |
| Stochastic volatility (MCMC) | **Monthly or less** — posterior sampling is expensive | Filtering updates refresh latent state without rerunning the posterior |

**Panel workflow:** re-estimate parameters overnight across the universe, update recursive features during the next trading day. Where even that is too expensive, exponential smoothing is a defensible operational substitute at the cost of a less interpretable parameterization.

### Rough volatility and the Hurst exponent

Volatility can be **persistent in level yet rough in increments** — GARCH and HAR impose relatively smooth dynamics that miss this.

H = 0.5 → Brownian scaling · H > 0.5 → persistent increments · H < 0.5 → anti-persistent increments.

> **The empirical picture, with numbers:** Gatheral et al. (2014) document log-volatility Hurst exponents around **0.1** for equity indices — far below 0.5. SPY confirms: **returns give H ≈ 0.5** (random walk) while **log-volatility increments give H between 0.12 and 0.23** depending on estimator — squarely rough.

**Treat H as a slow-regime descriptor, never a high-frequency signal.** When it falls well below 0.5, standard volatility recursions may understate how abruptly volatility can spike and decay. This doesn't invalidate GARCH features; it changes how to read them.

> Estimates are noisy. Use a **252-day rolling window refreshed weekly**, not daily re-estimation. Large one-day moves in the estimate are estimation noise, not structural breaks. On return series rather than log-volatility, interpret more cautiously still.

---

## 5. Uncertainty as a feature

Two distinctions that get conflated:

- **State uncertainty ≠ forecast uncertainty.** An SV model can be uncertain about the *current* volatility state before being asked to predict. An ARIMA model can be confident about the current level while uncertain about the next step.
- **Bayesian** methods yield posteriors directly; **frequentist** models yield forecast standard errors and prediction intervals. Both are usable.

Available features once a model produces a distribution: posterior standard deviations · credible-interval widths · tail probabilities · forecast standard errors · prediction-interval widths.

> **The principle in one comparison:** a volatility forecast of 20% with a *narrow* interval means something operationally different from the same 20% with a *wide* one. The first is a well-identified state; the second is material ambiguity. The uncertainty summary is a valid conditioning feature **even when the central estimate is already in the model.**

### Stochastic volatility

GARCH treats conditional volatility as a deterministic recursion given parameters and data. SV treats volatility as a **latent process with its own shock term**, so estimation yields a distribution over the state rather than a single path.

Features: posterior mean of current volatility · posterior SD and credible-interval width · vol-of-vol (innovation variance of log-volatility) · persistence.

> Together these separate three cases a single volatility number conflates: **low and well identified / high and well identified / high but poorly identified.** Uncertainty about volatility matters most when it rises *independently of the level* — a large posterior SD means the model is not only detecting elevated risk but is unsure where the risk state sits. That can be a stronger warning than high volatility alone.

**Use filtered posteriors, never smoothed full-sample state estimates** — smoothing borrows from the future.

### ARIMA forecast uncertainty

More useful on volatility-like series than on returns, since realized volatility, spreads, and funding rates have clearer serial structure.

> **Model log volatility, not the level, when the target is strictly positive.** The log transform stabilizes scale, prevents negative back-transformed forecasts, and yields **asymmetric** intervals on the original scale — realistic for volatility, where downside is bounded near zero while upside spikes are large.

Three practical features: forecast standard error (modeled scale) · prediction-interval width (original scale) · **their ratio** (width ÷ forecast level) as a *relative* uncertainty measure. High relative uncertainty flags a weakly identified forecast even when the point forecast looks large.

---

## 6. Regime features

### Observable rules first

Deterministic threshold rules (VIX above a level, price vs. long moving average, choppiness index, trend efficiency) are transparent, need no latent-state estimation, and are auditable in production.

> **They fail transparently, which is their real advantage.** If VIX stops being informative for a universe or horizon, the failure is easy to diagnose. A latent-state model represents richer dynamics but adds assumptions and failure modes. Deterministic indicators are good baselines even after more elaborate models arrive.

**A regime feature encodes market context, not a forecast.** A volatility threshold doesn't predict returns; it tells the downstream model whether to interpret other features in a calm or stressed environment. This conditioning role is the primary function of regime features generally.

### Hidden Markov models

| Output | Use |
|---|---|
| **Filtered probability** P(state \| info through *t*) | **The central object.** Preserves uncertainty — more useful than a hard state label. |
| *Smoothed* probability | Uses future observations — **retrospective analysis only** |
| Transition matrix | e.g. probability of moving low-vol → high-vol next step |
| Expected duration | 1/(1−p_ii) — regime persistence |
| Entropy of the filtered vector | Classification uncertainty — low when one state dominates |

> **Two implementation traps.** (1) **States are unlabeled.** What one estimation window calls "state 0" may be "state 1" in the next. Relabel using a stable characteristic — variance, if states differ mainly in volatility — or your feature is scrambled across refits. (2) **Keep the state count modest.** Two-state specifications are usually more interpretable and more stable out-of-sample than richer models that fit historical noise.

### Markov-switching autoregressive

HMM with simple emissions suffices when regimes differ in the *unconditional distribution*. MS-AR lets the **autoregressive process itself vary by state**, yielding regime-specific AR coefficients that summarize whether persistence, mean reversion, or short-horizon momentum differs across states.

**Decision rule:** regimes differ mainly in volatility → plain HMM. Regimes also differ in persistence or directional dynamics → MS-AR.

### Distribution-based regimes

Moment-based models distinguish states by mean and variance, missing cases where the difference is in **shape** — skewness, tail behavior, downside concentration. Treating each rolling window as an empirical distribution and clustering with **Wasserstein distance** (in 1D, distance between quantile functions) is sensitive across the whole distribution.

Features: cluster assignment (regime label) · **distance from current window to its assigned centroid** (how typical/atypical this regime instance is — a window far from every centroid flags an unusual environment even when assigned to the nearest cluster) · **disagreement between distribution-based and moment-based labels**, which is itself informative that tails or skewness matter more than mean and variance.

> **The gap is large, not marginal:** on a synthetic two-regime benchmark, Wasserstein K-means achieves an **adjusted Rand index of 0.87 vs. 0.31 for moment-based K-means.** Summary statistics genuinely miss regime structure that the distributional metric captures.

### Conditioning, not hard switching

> **Regime inference is most uncertain exactly when regime information matters most.** Near transitions the model assigns meaningful probability to several states. A hard-switching system must still commit to one regime-specific model, so small changes in regime probability produce large changes in the active predictor — instability at precisely the boundary cases that matter in live trading.

A single model receiving regime features as *inputs* degrades gracefully: filtered probabilities, entropy, durations, and regime-conditioned interactions let it learn that a signal behaves differently in calm and stressed states, and as regime certainty falls the regime inputs naturally become less decisive.

Separate regime-specific models remain defensible when there is a **strong economic reason** to believe distinct mechanisms operate and each regime has enough data for separate estimation — at the cost of sample size, operational complexity, and fragility near boundaries.

---

## 7. Panel layer — from temporal to cross-sectional

A conditional volatility of 25% annualized means something different for a utility than a biotech. Same for a Kalman trend, regime probability, or spectral energy.

| Transform | What it produces |
|---|---|
| **Cross-sectional rank / percentile / z-score** | Kalman trend → universe-relative momentum; conditional vol → volatility percentile; regime probability → relatively stressed vs. peers |
| **Benchmark adjustment** | Subtract market/sector momentum → idiosyncratic component; divide conditional vol by market vol → asset-specific vs. market-wide stress |
| **Pairwise** | Cointegration diagnostics, Kalman time-varying hedge ratio, spread z-score, half-life |
| **Universe aggregation** | Cross-sectional mean of conditional vol (overall state), dispersion (differentiation), fraction with elevated stress probability (breadth) |

**Choosing among rank / z-score / percentile:** ranking is most robust (least outlier-sensitive, comparable across heterogeneous assets); z-scores retain cross-sectional *distance* and are preferable when dispersion itself matters; percentiles are a bounded, interpretable compromise.

**Benchmark choice follows the economic question** — a market index for broad equity universes; sector, country, duration-bucket, or commodity-sleeve benchmarks when separating local structure from a narrower common factor. Benchmark mappings must be the ones **known at decision time**, not later reclassifications.

> Read pairwise quantities as **state summaries, not trading rules.** A short half-life does not by itself justify a trade, and a cointegration test does not guarantee a robust spread after costs.

**Aggregate interpretation:** high average stress probability → pressure is broad rather than idiosyncratic. High breadth → many assets simultaneously stressed. **High dispersion → disagreement across the universe**, often accompanying rotation, segmentation, or selective risk-taking. The combination beats any single asset-level regime label.

> **The order of operations is non-negotiable:** compute each asset's temporal feature from its own trailing history → align asset-level outputs at the decision date → *only then* apply cross-sectional rank, benchmark adjustment, pairwise transform, or universe aggregation. **Reversing it leaks across assets or across time.**

> Universe composition is a second-order leak: when assets enter or leave the tradable set, **cross-sectional ranks shift even though no underlying signal changed.** Use fixed-composition checks, pre-declared eligibility filters, and explicit missing-value handling to separate genuine signal movement from composition effects.

---

## Transferable rules

1. **A fitted object is a feature generator with an estimation window attached.** Refit inside the training fold, version the parameters, log the window.
2. **Always use filtered output, never smoothed.** Smoothed states and full-sample posteriors borrow from the future.
3. **Model selection is a fitted step.** ARIMA order, HMM state count, fractional *d* — all must be re-selected within each training window.
4. **Diagnostics are features.** Rolling ADF/KPSS statistics, CUSUM values, and time-since-break are conditioning variables, not just gates.
5. **Take the smallest differencing order that achieves stationarity,** preserving maximum memory — and record the boundary convention as part of the definition.
6. **Prefer methods that separate direction, surprise, and confidence** over methods that collapse them into one smoothed line.
7. **Compute spectral features causally on trailing windows,** and remember window length sets frequency resolution.
8. **Treat non-causal transforms (wavelets) as horizon-discovery diagnostics,** then build causal proxies at the discovered scale.
9. **Time-augment path signatures** or ordering information is lost; default to depth-2 log-signatures.
10. **HAR is the strongest simple volatility baseline** — roughly half the out-of-sample RMSE of GARCH on index data.
11. **Guard parameter-derived features against their own validity conditions** — long-run variance is meaningless under IGARCH.
12. **Separate refit cadence from between-refit update logic.** Most recursions update daily on fixed parameters.
13. **Uncertainty is a feature even when the point estimate is already included.** Identical forecasts with different interval widths are different states.
14. **Relabel latent states by a stable characteristic across refits,** or the feature is incoherent over time.
15. **Feed regime probabilities as continuous inputs rather than hard-switching between models** — inference is least certain exactly at the transitions that matter.
16. **Compute temporal features first, then apply the panel layer.** Never the reverse.
17. **Keep the set compact.** One or two volatility features, one regime feature, one signal-transform feature, and a limited set of cross-sectional transforms are usually enough to establish what fitted methods add over Ch. 8 directs.

---

## Notebooks

| Notebook | Covers |
|---|---|
| `01_visual_diagnostics` | ACF/PACF/Q-Q workflow, rolling ADF and KPSS, time-varying stationarity features |
| `02_structural_breaks` | Classical break tests, online CUSUM monitoring, classification-based detection |
| `03_fractional_differencing` | Fixed-width fdiff, bounded *d* grids, walk-forward-safe selection, validity masks |
| `04_kalman_filter` | MLE noise covariance estimation, walk-forward refitting, dynamic hedge ratio for pairs |
| `05_spectral_features` | Rolling FFT, Welch PSD, time-frequency heatmap; wavelet MRA as diagnostic + causal proxy translation |
| `06_path_signatures` | Iterated integrals, log-signatures, time augmentation, `esig`, head-to-head vs. lag features |
| `07_arima_features` | Order selection, residual extraction, walk-forward evaluation |
| `08_garch_volatility` | GARCH / EGARCH / GJR estimation, ARCH-effect testing, conditional vol extraction |
| `09_har_rough_volatility` | HAR estimation, rolling coefficients, GARCH comparison; R/S and DFA Hurst, cross-asset roughness |
| `10_uncertainty_features` | Student-t SV filtered posteriors in walk-forward; rolling ARIMA on log GK realized vol |
| `11_hmm_regimes` | Forward filtering, filtered vs. smoothed, transition/duration/entropy features, MS-AR alongside |
| `12_wasserstein_regimes` | Distributional clustering on S&P 500 returns via stream-lift methodology |
| `13_regime_as_feature` | Unified vs. regime-conditioned designs feeding a gradient-boosting workflow |
| `14_panel_features` | Cross-sectional ranks, market-relative momentum, Engle–Granger/Johansen pair screens, `universe_crisis_prob` / `crisis_breadth` / `regime_dispersion` |

---

## Cross-references

Ch. 5 stochastic volatility models and MCMC estimation · Ch. 6 walk-forward protocol and refit cadence commitments · Ch. 7 §7.1 train-only fitting invariant, which every model here inherits; §7.4 search accounting for order/state-count selection · Ch. 8 direct volatility estimators these models sit on top of; §8.6 signal × state interactions, where regime features do their work · Ch. 11 the ML pipeline that consumes these features · Ch. 12 gradient boosting with regime features as inputs · Ch. 13 learned sequence representations (TCN, RNN, transformer) as the learned analogue of §3 · Ch. 17 portfolio construction where regime conditioning affects allocation · Ch. 19 risk management use of conditional volatility and tail features

---

## Citations

Ang & Bekaert (2002); Ang & Timmermann (2011), regime models in finance · Bai & Perron (1998), multiple structural breaks · Bollerslev (1986), GARCH · Chevyrev et al. (2016), path signatures · Corsi (2009), HAR · Engle (1982), ARCH · Garman & Klass (1980) · Gatheral, Jaisson & Rosenbaum (2014), rough volatility · Glosten, Jagannathan & Runkle (1993), GJR-GARCH · Granger & Joyeux (1980); Hosking (1981), fractional integration · Hamilton (1989), Markov-switching AR · Horvath et al. (2021), stream-lift distributional regimes · Kalman (1960) · Marra (2023), volatility estimator comparison · Moreira & Muir (2017), volatility-managed portfolios · Nelson (1991), EGARCH · Parkinson (1980) · Rabiner (1989), HMM tutorial · Shu & Mulvey (2025), continuous regime features for factor allocation · Taylor (1982), stochastic volatility · Uysal & Mulvey (2021), HMM regimes in finance · Yang & Zhang (2000) · Zivot & Andrews (1992), endogenous break unit-root test

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 9.*
