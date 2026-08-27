# Ch 8 — Financial Feature Engineering

**Governs:** turning a strategy narrative into a specified, testable feature set — and keeping the search space from exploding while doing it.
**Thesis:** the distinction that matters is between *meaning-changing* choices (which create a new hypothesis and a new trial) and *noise-reduction* choices (which trade variance for bias). Conflating them is how feature research becomes indicator sprawl.

---

## 1. The three-step filter

| Step | Question | Failure if skipped |
|---|---|---|
| **Horizon alignment** | Do lookback, sampling cadence, and aggregation match the label horizon and execution lag? | Feature/label horizon mismatch — a leading cause of unstable estimates |
| **Driver hypothesis** | Which economic mechanism does this claim? | Without a nameable mechanism you have a data pattern, not a feature hypothesis |
| **Role separation** | Signal (predicts conditional mean/direction) or state (conditions *when* signals work, how aggressively to trade, how costly)? | State variables often have weak marginal association and only earn their keep through interactions |

**Four driver mechanisms cover most return-predicting features:**

- **Persistence** — information incorporated gradually (attention limits, slow institutional flows)
- **Reversion** — predictable flows (hedging, rebalancing, inventory) create transient pressure then reversal
- **Risk compensation** — returns paid for exposures others avoid (liquidity, tail, funding)
- **Predictable clocks** — calendars, roll schedules, funding resets, scheduled events

> **Patterns without a mechanism need a higher evidentiary bar,** because they offer no guidance on failure modes or regime dependence. Treat as provisional: stricter multiple-testing discipline, untouched holdouts *beyond* CV folds, robustness across related instruments and definition variants, and post-deployment decay monitoring with a pre-committed retirement trigger.

**Three configuration choices apply to nearly every family:**

| Choice | Options | Determines |
|---|---|---|
| **Reference frame** | Time-series (own dynamics) vs. cross-sectional (relative positioning) | Which hypothesis is being tested |
| **Representation** | Raw vs. ranks, vol-scaling, winsorization, residualization | What "extreme" means |
| **Aggregation** | Window and smoothing | Effective bandwidth; responsiveness vs. variance |

### Feature specification template

Record for every candidate; if you can't fill these in, you have an input awaiting a hypothesis, not a feature:

- [ ] Name, family, **signal vs. state role**
- [ ] Driver hypothesis and edge source
- [ ] Inputs and observability constraints
- [ ] Lookback and aggregation
- [ ] Reference frame and representation
- [ ] **Expected failure modes**

In production this is a feature-registry entry supporting versioning, auditability, and reuse across trials.

---

## 2. Price-derived families

| Family | Economic claim | Role | Typical horizons |
|---|---|---|---|
| Trend/momentum | Recent performance persists | Signal | Hours–months |
| Reversal | Prices revert to an anchor | Signal | Seconds–days |
| Volatility/tail risk | Risk conditions sizing and gating | **State** | All |
| Liquidity/tradability | Costs and capacity gate signals | **State** | All |
| Microstructure/order flow | Informed flow moves prices | Signal or state | Seconds–hours |

Most price features reduce to four primitives: changes over a window, distance to an anchor, gain–loss asymmetry, cross-sectional comparison. Recognizing that many named technical indicators are parameterizations of the same claim is what prevents indicator sprawl.

### Trend and momentum

| Distinction | Effect |
|---|---|
| **Time-series vs. cross-sectional** | Predicting an asset from its own past vs. relative performance in a peer set — different hypotheses |
| **Return-based vs. moving-average** | Net displacement vs. path persistence. **Not interchangeable** — they diverge in choppy markets and during trend acceleration/exhaustion |

Lookback too short → captures noise that decays before the label resolves. Too long → smooths away the variation the label targets.

- **Meaning-changing:** TS vs. XS framing, lookback and holding horizon, decay profile, benchmark/sector residualization, vol scaling and risk targeting
- **Failure modes:** regime concentration (trend vs. mean-reverting), lookback/label horizon misalignment, **search inflation from scanning many windows without correction**

### Reversal and mean reversion

**The anchor defines the economic content.** Short-horizon reversal is usually microstructure-driven (bid–ask bounce, inventory, short-lived overreaction) with an implicit fair-mid anchor. Longer-horizon reversion needs an economically grounded anchor: VWAP, moving average, peer mean, spread equilibrium, parity level.

> Keep the **anchor window** and the **deviation window** separate — they control different parts of the hypothesis and collapsing them into one parameter hides which one you're actually tuning.

- **Failure modes:** edges that vanish after costs and execution delay; unstable poorly-estimated anchors; **"reversion" signals that are actually liquidity proxies**

### Volatility and tail-risk state

Primarily state variables. If the label *is* a volatility target, the same measurements become signals — evaluate them against a volatility label, not returns.

Converting volatility levels to percentiles (historical or cross-sectional ranks) usually improves stability, since downstream models want a relative high/low state rather than a drifting level.

**Range-based estimator efficiency vs. close-to-close:**

| Estimator | Inputs | Relative efficiency | Best when |
|---|---|---|---|
| Close-to-close | Close | 1× | Only closes available |
| **Parkinson** | High, Low | **~5×** | Daily bars, negligible overnight effects |
| **Garman–Klass** | OHLC | **~7×** | Full OHLC, small gaps |
| **Yang–Zhang** | OHLC | **~8–14×** | **Overnight gaps material** |

Efficiency = precision gain per observation. 5× means roughly one-fifth the observations for the same target variance — which is why range estimators let you use shorter windows without paying in noise. Yang–Zhang decomposes into overnight (close-to-open), intraday, and a Rogers–Satchell term.

> **ATR is not a variance estimator.** Use range-based *variance* estimators to measure volatility, and ATR for price-denominated sizing and gating (stop distances, dollar-risk scaling, breakout filters). Mixing the two roles produces sizing rules calibrated on the wrong quantity.

**Regime indicators:** variance ratio (long-horizon variance vs. scaled short-horizon — below 1 suggests mean reversion, above 1 persistence) · fractal efficiency (net displacement / path length) for trending vs. choppy · VaR/CVaR and downside deviation for tail asymmetry.

**Estimator choice by market structure** (worth copying as defaults):

| Case | Choice | Why |
|---|---|---|
| 24/7 crypto, 8h bars | Close-to-close | No overnight decomposition needed |
| ETFs, US equities panel | Close-to-close + NATR | NATR for gating/sizing, not variance measurement |
| FX, equity-option analytics | Garman–Klass + close-to-close | Full OHLC exploitable, gaps small at that cadence |
| CME futures | **Yang–Zhang** + close-to-close | Overnight moves around the US open are material |
| Minute-frequency equities | Realized vol from intraday returns | Daily OHLC estimators don't apply |

### Microstructure and order flow

Most "price+volume" indicators reduce to two operations: aggregate signed flow over a window, normalize by a liquidity scale.

**The binding constraint is delay sensitivity — test whether the effect survives realistic execution latency before optimizing anything else.**

- **Trade-signing rule** is meaning-changing: tick rule, quote-midpoint (Lee–Ready-style), venue aggressor flags
- **Aggregation structure:** simple OFI sums signed trades; order-book OFI (Cont, Kukanov & Stoikov, 2014) uses changes in best-bid/ask quantities — cleaner with full depth, but requires LOB reconstruction
- **Normalization** determines portability: by total volume (fraction), by depth (liquidity-scaled), or z-score vs. own history (rarity). Volume- and depth-normalized OFI **diverge sharply in thin markets, and the divergence is itself informative**

> **Calibration anchor from the worked example:** TSLA shows the highest Kyle's lambda (**0.003**) — greatest price impact per unit volume. But contemporaneous OFI–return correlation (**+0.053**) far exceeds lagged (**−0.011**). Order flow that looks strongly predictive contemporaneously can be near-useless one step out. Measure the lagged relationship before building anything on it.

**Venue structure constrains what's expressible:** CLOBs (CME, major crypto) expose depth and queue state; RFQ/dealer markets expose flow only through transactions; AMMs expose pool state but no order book. "Informed flow moves prices" must be written in the venue's data structure.

---

## 3. Structural and cross-instrument families

### Carry, funding, term structure

Roll yield = annualized price difference between two futures maturities. **The maturity pair selects the hypothesis:**

- Front vs. second month → very front of the curve, most sensitive to short-term supply/demand
- Front vs. deferred back → broader term-structure slope, more persistent conditions

Annualize by days between expirations to compare across contracts. Curve level, slope, and curvature (butterfly) are three independent dimensions driven by different forces.

> **Crypto perpetuals are a distinct carry regime, not roll yield by another name.** Roll yield is a *known mechanical* cost; funding is *market-determined and can swing 100 bps within hours* during volatility. Features assuming stable funding regimes fail precisely during the transitions that matter.

Three perpetuals design choices:

1. **Clock alignment** — most major venues use 8-hour funding (00:00/08:00/16:00 UTC), but some use 4h or 1h. **Verify per venue**; 8-hour windows on 4-hour funding data mix settlements.
2. **Basis–funding decomposition** — basis reflects immediate supply-demand imbalance; funding reflects cost of maintaining positions. Separate features, distinct horizons, distinct failure modes.
3. **Signal vs. state dual role** — as *signal*, extreme funding predicts mean reversion (high positive funding precedes perp underperformance as longs pay shorts); as *state*, funding proxies crowding (persistently elevated funding → directional signals less reliable because one-sided positioning creates fragility). **Log both roles explicitly.**

- **Failure modes:** roll discontinuities when contract definitions change; calendar misalignment between roll dates and feature windows; **hidden assumptions about which contract month is "front"**

### Cross-asset structure and relative value

Three distinct questions: what exposure should be removed as common, whether one market leads another, and how relationships change over time.

> **Neutralization is not cleanup — it defines the hypothesis.** Sector peers, factor-model residuals, and statistical clusters encode different theories of what "common" means and produce different residuals. Peer-set stability and refresh cadence are first-order: a shifting peer set changes the hypothesis mid-backtest.

**Lead-lag features** require careful handling of time zones, trading hours, settlement conventions, and stale prices. Main failure mode: mistaking delayed price discovery, low liquidity, or nonsynchronous trading for genuine information flow.

> **Instructive negative result:** testing SPY → sector-ETF lead-lag at daily frequency finds **uniformly negative lag-1 correlations, roughly −0.06 to −0.13** — short-term *reversal*, not continuation. Highly liquid instruments on the same venue show no exploitable daily lead-lag; the negative values likely reflect bid–ask bounce, ETF rebalancing, or short-horizon flow reversal. Lead-lag claims need validation before promotion, not after.

**Relationship-change features are often the more robust class**, and read better as state variables than signals. Example: 63-day rolling SPY–TLT correlation. Negative → diversification working, flight-to-safety operative. Toward zero or positive → the usual stock-bond hedge is failing (as in 2022) and other signals may behave differently.

> **Empirical weight of this state variable:** across 120 fold × config observations on a 21-day momentum label, `corr_spy_tlt_63d` has the **highest stable fold-normalized importance among 27 inputs (mean 0.73)** — ahead of yield-curve z-score and momentum-slope features. This doesn't isolate standalone predictive content, but a tree model repeatedly selecting it as a split criterion is consistent with the state-variable reading: when the stock-bond hedge weakens, the relative attractiveness of momentum vs. reversal shifts.

- **Failure modes:** universe drift; moving targets from frequent peer-set redefinition; **estimation noise introduced by the neutralization step itself**

### Options-implied features

More forward-looking than realized measures — but only if the surface is built consistently. **A stable surface policy is a prerequisite:** moneyness definition, quote acceptance rules, mid vs. last, interpolation across strikes and maturities, mapping to standardized horizons (e.g. 30 days). If the policy drifts, the feature tracks construction artifacts rather than beliefs.

| Feature | Measures | Primary use |
|---|---|---|
| **ATM IV** (usually constant-maturity 30d) | Baseline expected dispersion | Primary volatility-regime state variable |
| **Implied − realized spread** | Variance risk premium | Direct signal for vol-selling; conditioning variable otherwise |
| **Risk reversal** (25Δ put IV − 25Δ call IV) | Downside/upside pricing asymmetry | Perceived fragility; larger spread = stronger protection demand |
| **Term-structure slope** (front vs. 3-month) | Near-term stress vs. persistent uncertainty | **Inversion often signals imminent event or stress** |
| **Put–call skew** (OTM put vs. OTM call IV) | Tail pricing asymmetry, independent of ATM level | Isolates tail demand from overall vol level |

- **Meaning-changing:** ATM convention (spot / forward / delta-based), delta choice for skew, quote filters, mid vs. last, interpolation and extrapolation, constant-maturity mapping, levels vs. changes vs. z-scores vs. ranks
- **Failure modes:** stale or wide quotes on illiquid strikes distorting the surface; inconsistent moneyness conventions across vendors; survivorship bias as series expire or delist; **lookahead when the "realized" leg of IV−RV overlaps the label horizon**; regime-dependent meaning — a given risk reversal carries different information at VIX 15 than at VIX 35

---

## 4. Contextual and slow-moving families

Shared properties: low update frequency, strict PIT requirements, primary role as state variables conditioning faster signals. **The limiting factor is data integrity, not modeling.**

### Fundamentals

> **The sample-size illusion, quantified.** Repeating a quarterly value across daily rows inflates nominal sample size without adding information. Quarterly book equity repeated over ~63 trading days multiplies nominal N by **~63**. Apply the Ch. 7 effective-sample-size and uniqueness-weighting logic or repeated values will dominate fold-level diagnostics.

The assumed reporting lag **is meaning-changing** — a 60-day vs. 90-day lag defines a different feature with different lookahead risk.

Four characteristic categories: value (book-to-market, earnings yield) · profitability (operating profitability, gross margins) · investment (asset growth, capex) · quality (accruals, leverage).

- **Failure modes:** lookahead via revised fundamentals; inflated nominal N from repeated values; **stale fundamentals treated as fresh daily observations**

### Calendar and event encodings

**Encode phase and proximity, not outcomes.** Time-to-event and post-event decay indicators — never realized post-event quantities in pre-event windows.

- Compute time-to-event in the **same time zone and trading calendar** used for bar construction, with the same session boundaries and holiday rules
- For earnings, use **confirmed** announcement dates from a PIT calendar; treating estimated dates as confirmed creates lookahead
- Periodic patterns → cyclical sin/cos or low-order Fourier terms to preserve circular structure. **Number of harmonics is noise control; which clocks to encode is meaning-changing.**
- Post-event decay is a *separate hypothesis* about information absorption, not a variant of the pre-event feature

### Macro and policy state

Yield-curve slope is the standard example. **The maturity choice is meaning-changing** (10Y−2Y vs. 10Y−3M vs. a PC representation select different aspects of the term structure); smoothing and standardization horizons are noise control.

- **Failure modes:** lookahead via revised data (use vintage series — ALFRED or equivalent); incorrect release timestamping; stale values treated as daily-fresh; **unstable expectations proxies** for surprise features

---

## 5. Breadth vs. skill

> Across the nine case studies, feature counts range from **39 to 66** with deliberate per-asset-class specialization, and **past-return windows are the only family universal to every case study.** Plotting universe size against best in-sample |IC| with bubble area ∝ Grinold's IR estimate (IC·√N) makes the point: `us_firm_characteristics` is the dominant outlier at an estimated **IR near 4 on a 2,483-stock universe**. Breadth, not a marginally higher IC, is what separates a thin signal from an investable one.

### When direct aggregation is not enough

Every feature above is a deterministic formula over a trailing window. Four kinds of structure are invisible to that approach:

| Hidden structure | Question a rolling statistic can't answer | Requires |
|---|---|---|
| **Conditional dynamics** | How fast does a volatility shock decay? | Fitted GARCH |
| **Latent states** | Trending or mean-reverting regime? | HMM / Markov-switching |
| **Cyclical structure** | Is the weekly pattern real or noise? | Spectral decomposition (FFT) |
| **Path geometry** | Two windows, identical return, different paths | Sequential encoding (path signatures) |

---

## 6. Signal × state interactions

Much of the practical improvement comes from combining a signal with a state, not from better individual features.

| Template | Mechanism | Strategy effect |
|---|---|---|
| **Gating** | Trade only when state is favorable, else flat | Changes the **active sample** — and therefore turnover and capacity |
| **Scaling** | Adjust signal strength continuously by state | Changes position size conditionally |
| **Conditional variant** | Log "signal in regime" as a separate versioned feature | Turns the interaction into **separately testable hypotheses** |

**Prioritize interactions where** the state is economically relevant, the interaction is **asymmetric** (conditional IC genuinely differs across state values rather than being a constant rescaling), and the state is **observable at decision time** (not contemporaneous or revised).

**Three diagnostics per interaction**, computed within fold, summarized by median and worst fold:

1. **Structure** — conditional IC varies systematically with state; irregular patterns suggest overfitting or unstable binning
2. **Fold stability** — conditional effects don't repeatedly flip sign
3. **Real-time robustness** — noisy, delayed, or revised state estimates degrade transfer to live, **especially for hard gates**

**Ratio features** (signal ÷ positive state): risk-adjusted momentum (mom/vol), carry-to-vol (carry/IV), momentum-to-spread (cost-adjusted).

> Ratio definitions implicitly assume a strictly positive, well-estimated denominator. Handle edge cases explicitly: clip near-zero volatility, set the ratio to zero or missing where the denominator is undefined. Skipping this produces occasional enormous feature values that silently dominate tree splits or linear coefficients.

### Worked example — momentum × volatility terciles

126-day momentum signal, 42-day SPY realized volatility as market-wide state, **expanding-window percentile thresholds** (avoids lookahead), 20-day forward return label:

| Volatility tercile | Momentum IC | HAC t | p |
|---|---|---|---|
| Low (<33rd) | **+0.071** | 2.8 | 0.006 |
| Medium (33–67th) | +0.025 | 1.3 | 0.21 |
| High (>67th) | **−0.034** | −1.1 | 0.26 |

**The monotonic decay across terciles is the relevant pattern**, not any single cell's significance. The 10.5pp swing between low and high vol is the empirical basis for a gating rule: take momentum only when volatility is not in the top tercile.

**Search cost:** 5 signals × 3 states × 3 templates = **45 interactions.** Report the count, apply BH-FDR, treat best-in-search as exploratory until confirmed on held-out folds.

### Event studies as falsification

Define an event date, estimate normal returns on a window ending *before* the event window, compute abnormal returns, aggregate to CAR/CAAR. In feature research the "event" is usually a rule-based signal (momentum breakout, transition into top decile, regime change), not a corporate announcement. **The event definition must use only decision-time information or the study inherits lookahead.**

Because feature-generated events overlap and assets share risk exposures, use **HAC or clustered standard errors** — never assume independent event returns.

> **Worked result and why it's a falsification tool.** ETF momentum breakouts, window −3 to +10: mean CAR **1.11%** (t = 3.28, p = 0.001), with CAAR building through the window and **no pre-event reversal** — consistent with continuation rather than mechanical rebound. But signal-conditioned analysis shows an asymmetry: **long signals validate (CAAR 0.87%, t = 3.30), short signals do not (CAAR −0.25%, t = −1.31).** A candidate feature should not merely produce a significant average effect — it should exhibit the correct *event-time shape*, survive reasonable benchmark choices, and behave consistently in the direction it claims.

---

## 7. Degrees-of-freedom discipline

**Three controls:**

1. **Budget by family and role** — allocate variants within a hypothesis class (momentum signals) separately from state features (volatility, liquidity)
2. **One choice at a time** — fix driver and representation, vary one choice (usually lookback), keep a small survivor set, then consider a second
3. **Deduplicate within families first** — before modeling, not after

### Deduplication procedure

- **Pairwise dependence** — rank correlations within each fold's training window → p × p matrix
- **Clustering** — hierarchical, distance √(1−|ρ|), which groups features similar *up to sign*. Cut level is a tuning choice; **0.6–0.8 are common starting points**
- **Representative selection** — one per cluster by a transparent rule: highest median IC with low fold-to-fold dispersion, simplest construction, or lowest implementation burden. **Where criteria conflict, favor fold stability over a small gain in a single summary metric.**

> **Calibration for what a full selection pipeline actually removes.** ETF case study: 57 candidates → correlation filter at 0.9 removes 14 → IC ranking retains 18 above threshold → final selection yields **10 features, an 82.5% reduction.** Strongest single feature is distance-to-52-week-low at IC 0.076. After BH-FDR, **4 of the 34 features significant at the raw 5% level no longer survive.**

> **And the importance methods disagree more than people assume: MDI and permutation importance agree on only ~49% of rankings.** The choice of importance method materially changes which features get selected. Deduplication reduces within-family redundancy; it does not replace model-stage selection.

### Three implementation choices that change the hypothesis

| Choice | Why it's meaning-changing |
|---|---|
| **Residualization** | Defines a different question *and* introduces a fitted model that must live inside the walk-forward protocol |
| **Winsorization level** | 1st/99th vs. 5th/95th changes which observations drive the signal. Fit bounds on training data, apply to the matched validation window. |
| **Stationarity–memory trade-off** | First differencing removes long-range dependence; fractional differencing with d < 1 preserves memory while improving stationarity. **d = 0.4 encodes a different hypothesis than d = 1.** |

**Operational rule:** any transform with learned parameters is fit on walk-forward training splits and applied to the matched validation split. When a feature depends on a fitted object (neutralization model, scaler, learned representation), **log the fitted parameters and the training window.**

---

## Transferable rules

1. **Separate meaning-changing choices from noise-reduction choices.** The first create new hypotheses and new trials; the second trade variance for bias within one hypothesis.
2. **If you cannot name the economic mechanism, you have a data pattern.** Hold it to a higher evidentiary standard or drop it.
3. **Classify every feature as signal or state before evaluating it.** State variables legitimately show weak marginal association and only earn their place through interactions.
4. **Match lookback, cadence, and smoothing to the label horizon.** Horizon mismatch is the most common source of unstable estimates.
5. **Use range-based estimators for variance and ATR for sizing** — they answer different questions.
6. **Test delay sensitivity before optimizing any flow-based feature.** Contemporaneous correlation routinely exceeds lagged by an order of magnitude.
7. **The anchor, the peer set, and the maturity pair *are* the hypothesis.** Changing them is not tuning.
8. **Verify venue-specific clocks** (funding intervals, roll schedules, session boundaries) rather than assuming the common convention.
9. **Repeating slow data across fast rows inflates N without adding information.** Weight by uniqueness.
10. **Encode event proximity and phase, never event outcomes,** in pre-event windows.
11. **Breadth beats marginal IC.** A slightly better signal on a small universe loses to a thin signal on a large one.
12. **Deduplicate within families before the model stage,** and prefer fold stability over single-metric wins when picking cluster representatives.
13. **Every interaction is a separate trial** and enters the multiple-testing budget — 5 × 3 × 3 is 45 tests, not one experiment.
14. **Demand the right event-time shape, not just a significant average.** Correct sign, correct timing, correct asymmetry.
15. **Log fitted parameters and training windows for any feature that depends on a fitted object.**

---

## Notebooks

| Notebook | Covers |
|---|---|
| `01_price_volume_features` | Trend, reversal, volatility families |
| `02_microstructure_features` | Trade-sign OFI, Kyle's lambda, Amihud illiquidity, Roll spread, delay-sensitivity test |
| `03_structural_cross_instrument_features` | Rolling beta, relative value, SPY→sector lead-lag test, options-implied constructions |
| `04_fundamentals_macro_calendar` | Book-to-market with simulated reporting lags, cyclical encodings, time-to-event, yield-curve slope, VIX regimes |
| `05_feature_selection` | Full pipeline: correlation filter → IC ranking → final selection; MDI vs. permutation comparison |
| `06_robustness_sensitivity` | Vol-tercile conditional IC with HAC adjustment; lookback sweeps; interaction stability |
| `07_event_studies` | ETF momentum breakouts, benchmark model, CAAR with clustered inference |
| `case_study_feature_summary` | Cross-case breadth-vs-skill diagnostic |
| `13_model_analysis` | Fold-normalized feature importance (source of the SPY–TLT correlation evidence) |

---

## Cross-references

Ch. 3 order-flow imbalance, LOB reconstruction, volume/information bars · Ch. 4 PIT pipelines for fundamentals, macro vintages, alternative and on-chain data · Ch. 6 strategy families and edge sources that motivate each feature family; trial taxonomy · Ch. 7 §7.2 effective sample size and uniqueness weighting; §7.3 fold-aware IC diagnostics; §7.4 multiple-testing controls for interaction search · Ch. 9 model-based extraction for hidden structure (§9.1 fractional differencing, §9.5 regime models) · Ch. 13 transformer architectures behind foundation-model embeddings · Ch. 14 factor zoo and characteristic families · Ch. 16 backtest-overfitting penalties · Ch. 18 cost models that determine which features survive

---

## Citations

Amihud, illiquidity ratio · Cont, Kukanov & Stoikov (2014), order-book OFI · Garman & Klass, OHLC volatility estimator · Kyle (1985), price impact per unit flow · Lee & Ready, trade signing · MacKinlay (1997), event study methodology · Parkinson, range-based volatility · Rogers & Satchell, drift-independent estimator · Roll, effective spread from serial covariance · Yang & Zhang, gap-inclusive volatility estimator

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 8.*
