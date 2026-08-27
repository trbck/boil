# Ch 26 — MLOps and Governance

**Governs:** keeping a live system correct after launch — detection, response, and automated safety.
**Thesis:** every deployed model decays. **The diagnostic split is the whole chapter: technical failure means the same inputs produce different outputs; statistical failure means the same inputs produce the same outputs that no longer predict returns. Conflating them wastes time and capital.**

---

## 1. The failure taxonomy

| Type | Diagnosis | Response |
|---|---|---|
| **Technical** | Same inputs → **different** outputs | **Fix the bug** |
| **Statistical** | Same inputs → same outputs → **poor returns** | **Retrain, redesign, or retire** |

> **Treating statistical decay as a bug leads to futile debugging. Treating bugs as statistical decay leads to unnecessary model changes. The first step in any investigation is determining which category applies.**

**Four mechanisms of statistical decay:**

- **Overfitting** — backtest performance reflected in-sample noise. **Multiple hypothesis testing inflates backtested performance across finance research, and the same risk applies to individual strategy development**
- **Look-ahead bias** — features computed with data unavailable in real time; survivorship bias excluding delisted securities
- **Regime change** — volatility regimes changed, correlations broke down, or the feature-return relationship evolved
- **Alpha decay** — the strategy became crowded. **Once anomalies became public their profitability fell sharply, consistent with a mix of data-mining bias and post-publication arbitrage**

> **The question is not whether performance will degrade, but when — and whether detection arrives in time to respond.** The framework assumes decay will happen and builds systematic detection accordingly.

---

## 2. Performance monitoring

### Data integrity gates come first

> **A large fraction of apparent drift incidents in live trading are silent data defects: stale prices, corporate action mishandling, broken joins, timezone misalignment, missing bars, duplicated rows. These are technical failures that surface first as statistical anomalies in downstream metrics.**

**Enforce at ingest, before propagation to features, inference, or execution:** type constraints, null bounds, monotonic timestamp ordering, uniqueness keys.

> **The key design choice is a fail-closed policy for execution-critical feeds: if market data fails validation, do not trade on it.** Non-critical analytics can fail open with warnings. **A schema violation on a primary feed is a critical alert; a minor anomaly on a secondary feed is watch-level.**

### Rolling metrics

> **Point-in-time metrics hide trends. A strategy with an acceptable overall Sharpe may show alarming decay in recent windows.**

| Metric | What its movement means |
|---|---|
| **Rolling Sharpe** (30/60/90d) | **Persistent underperformance — live Sharpe consistently 0.5 or more below expectation — signals either backtest overfitting or regime change** |
| **Rolling IC** | **Catches prediction decay before it manifests in returns.** A strategy may maintain returns on favorable conditions while IC declines; **when conditions normalize, degraded predictions produce losses** |
| **Hit rate vs. win/loss ratio** | **Declining hit rate with stable win/loss → directional predictions weakening. Stable hit rate with deteriorating win/loss → correct direction, poor magnitude estimation or worsening execution** |
| **Drawdown depth and duration** | Beyond historical norms suggests **the strategy has entered unfamiliar territory — a regime it wasn't trained for** |

**Compute consistently on live, net-of-cost returns and compare against the same quantities from validation.**

### Tiered alerts

| Tier | Condition | Action |
|---|---|---|
| **Watch (yellow)** | Outside normal range, not alarming | Log for review |
| **Warning (orange)** | Significantly deteriorated | Investigate promptly; consider reducing exposure |
| **Critical (red)** | Hard limits breached | Protective action; may trigger automated response |

**Calibrate empirically from the backtest: what metric levels preceded historical degradation episodes? What values would have given sufficient warning to act?**

> **Threshold design must prevent alert fatigue. A monitoring system that pings the team every day trains them to ignore it.** Stick to alerts with a defined action, measure false-positive rates from history, and review thresholds when adding metrics.
>
> **If a threshold fires often but never changes exposure, retraining cadence, or diagnostic priority, it is noise masquerading as rigor.**

### Dashboard — five panels

Real-time PnL with backtest overlay · **rolling metrics across multiple windows** (short-window drops with stable long windows = temporary noise; all windows declining = persistent decay) · drawdown tracker with historical-max and breaker-threshold lines · color-coded alert status · **live equity overlaid on backtested equity, the gap being a central visual diagnostic.**

### The realization ratio

**Track backtested value, live value, deviation, and whether the deviation exceeds estimation noise.**

> **A strategy backtested at Sharpe 2.0 running live at 1.5 has a 0.75 realization ratio. Track it over time — a declining ratio suggests ongoing degradation even while absolute performance remains acceptable.**

### Execution quality can masquerade as model decay

> **Widening spreads, declining fill rates, increasing slippage, or broker throttling all reduce realized returns without changing the model's predictions.**

**Monitor alongside model metrics:** slippage vs. backtest assumptions · spread paid vs. quoted · fill ratio and partial-fill behavior · latency from signal to fill. **Compute a realized-versus-simulated cost ratio analogous to the return realization ratio.**

> **If execution costs consistently exceed backtest assumptions, the problem is microstructure or infrastructure, not the model — and retraining would be the wrong response.**

**The operational sequence:** monitor the metric gap → determine technical or statistical → diagnose the mechanism → **only then adjust exposure or start a model update.** *A mild rolling-Sharpe drop may justify observation; a sustained drop paired with worse IC, deeper drawdowns, or cost inflation justifies intervention.*

---

## 3. Drift detection

> **Performance monitoring tells you that something changed. Drift detection tells you what changed.**

### Data drift — input distributions

**PSI thresholds:** < 0.1 no significant shift · 0.1–0.25 moderate, investigate · **> 0.25 significant, predictions likely unreliable.**

> **Spikes in PSI often precede performance degradation, providing warning before returns deteriorate.**

**K-S test complements PSI for continuous features** — no binning assumptions, directly testing whether two samples came from the same distribution. **Preferred where binning would discard information.**

### Feature drift — importance shift

Even with stable input distributions, feature importance changes. **Three SHAP summaries matter:** mean absolute SHAP (magnitude) · SHAP variance (stability) · **relative ranking.**

> **Persistent rank changes and a collapsing contribution from a core feature are early warnings that the model is leaning on a relationship the market no longer rewards.**

### Concept drift — the relationship itself

> **The most insidious form: inputs look similar but no longer predict outcomes the same way.** *When markets transition from trending to mean-reverting, the same momentum signal that predicted positive returns now predicts negative ones. The feature distribution may be unchanged; the feature-target relationship has inverted.*

**Four types requiring different detection and adaptation:** sudden, gradual, incremental, recurring.

| Detector | Mechanism | Trade-off |
|---|---|---|
| **ADWIN** | Variable-length window continuously testing whether recent observations differ statistically from older ones; **shrinks to post-drift data on detection** | More adaptive |
| **DDM** | Monitors error rate with running mean and standard deviation; **warning on moderate increase, drift on substantial** | **Simpler, less adaptive — the lightweight choice when compute is the binding constraint** |

**Apply to prediction errors — the difference between predicted and realized returns.**

### Monitoring cadence

| Method | Frequency | Trigger |
|---|---|---|
| PSI on key features | Daily | PSI on high-importance inputs |
| K-S on continuous features | Daily/weekly | p-value vs. reference sample |
| **SHAP importance** | **Weekly** | **Rank reordering or large drop in a core feature** |
| **ADWIN/DDM on errors** | **Continuous** | Warning or drift state on the live error stream |

**What to monitor:** high-SHAP features · **historically volatile features** · domain-sensitive features (volatility, correlation, liquidity).

> **The detector itself needs monitoring.** Track alert frequency and warning streaks to recalibrate sensitivity before false positives overwhelm operators. **Treat detector health like any other production metric: if it pages constantly without changing decisions, it has stopped being useful.**

### Detection → diagnosis

| Drift? | Decay? | Interpretation | Response |
|---|---|---|---|
| Yes | No | **Robust model — distribution shifted but the relationship holds** | Monitor; no action |
| **No** | **Yes** | **Incomplete drift coverage or gradual concept drift** | **Expand monitoring; check untracked features** |
| Yes | Yes | Feature drift explains decay | Retrain on recent data or switch to a regime-specific model |
| No | No | Healthy | Continue |

> **Detect drift, correlate with performance, hypothesize a mechanism, validate with targeted analysis. This prevents both under-reaction (ignoring real problems) and over-reaction (changing models based on noise).**

---

## 4. Safe model updates

> **The replacement may perform worse than the decayed original.**

**Scheduled** retraining is predictable but **may update unnecessarily or too late if decay accelerates. Triggered** retraining responds to conditions but **requires robust monitoring to avoid false triggers. Combine: scheduled as baseline, triggered for exceptional conditions.**

### Shadow mode

**Deploy candidate alongside incumbent; both receive identical live feeds; only the incumbent trades.**

**Three comparison metrics:** prediction agreement (**disagreement is not necessarily bad, but its source should be understood before promotion**) · hypothetical returns under realistic execution assumptions · **risk characteristics — unexpected risk-profile changes warrant investigation.**

**Duration:** a 60-day default is long enough for multiple regimes and short enough to maintain velocity, **but a monthly strategy needs at least two rebalance cycles in shadow.**

> **A candidate that looks better during trending markets may fail in choppy conditions.**

### Statistical testing and effect size

> **Visual inspection is not sufficient.** A paired test on daily return differences establishes higher mean return; **Sharpe comparisons require methods accounting for mean, volatility, and the correlation between the two series.**

**The Jobson-Korkie framework relies on restrictive IID-normal assumptions;** later corrections relax some. **The Deflated Sharpe Ratio is especially useful when the candidate was selected after many experiments** because it adjusts for estimation error, multiple testing, and non-normality. **Block bootstrap on paired returns is the practical alternative when returns are serially dependent.**

> **A statistically significant 0.05 Sharpe improvement may not justify deployment risk. Define a minimum effect size for promotion — for example 0.2–0.3 Sharpe — below which you do not promote regardless of significance.**

> **Statistical power matters as much as the test. Short shadow windows can neither confirm nor reject modest improvements, especially with noisy, autocorrelated, or fat-tailed returns. If the effect size of interest is small, extend the shadow period or run bootstrap power analysis before declaring the candidate better.**

### Phased rollout

**Capital-capped A/B (5–10%)** → gradual increase through gates (10→25→50→100%) → **complete transition typically 60–90 days depending on rebalancing frequency.**

> **A/B testing with real capital reveals issues shadow mode misses: the candidate's signals may cluster in illiquid names, or its sizing may create market impact. These effects only appear when capital is actually deployed.**

> **The candidate need not dominate every day; what matters is that disagreement becomes observable, attributable, and reviewable at each stage before its capital share grows.**

**Explicit promotion criteria rather than discretionary judgment** — *illustrative: Sharpe exceeding incumbent by ≥0.2, significant at 10%, no drawdown exceeding historical maximum at any stage.* **Calibrate to the strategy's turnover and signal noise.**

### Rollback

**Archive the incumbent with full versioning** · define explicit triggers · **test the mechanism before deploying the candidate — a theoretical rollback that fails under pressure is useless** · **automatic for lower-level triggers (system errors, feed failures) where speed matters more than nuance; manual confirmation for performance degradation to avoid over-reacting to noise.**

---

## 5. Circuit breakers

**Four independent levels, each halting the relevant scope without higher-level intervention:** per-trade (order validation) · per-strategy (single-strategy exposure) · portfolio (aggregate risk) · **system (infrastructure health and latency).**

| Breaker type | Examples |
|---|---|
| **Loss-based** | Daily drawdown (−2%), weekly (−5%), **max from peak (−10% to −15%)** |
| **Position-based** | Max per asset (5%), max sector (20%), max correlation |
| **Anomaly-based** | Extreme volatility (VIX > 40), **liquidity collapse (spreads 3× normal)**, price dislocations (10%+ intraday) |

> **Fixed drawdown cutoffs are blunt instruments — drawdown breakers work best combined with exposure, liquidity, and market-stress signals. But when losses breach genuinely hard limits, halt immediately. Don't wait for human review. Don't try to "trade out" of the hole.**

> **Position limits catch situations where the model becomes overconfident in specific bets. Even if each trade looks reasonable individually, aggregate exposure may be dangerous.**

> **During market stress, normal relationships break down. Models trained on normal conditions may produce nonsense in extreme conditions. Stepping aside during anomalies is often the prudent response.**

> **Two different things share the name.** Trading circuit breakers are **risk controls** — when to stop trading based on PnL, positions, or conditions. The software circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) is **infrastructure resilience**, preventing cascading failures when data feeds or execution APIs become unreliable. **Both are necessary; they protect against different failure modes.**

### Recovery

**Immediate:** acknowledge the alert → assess what triggered it and current exposure → **secure the position, deciding whether to close or hedge.**

**Diagnostic:** technical or model failure? Unusual market conditions? **What was the sequence of events leading to the trigger?**

**Resume criteria:** all components healthy · feeds validated · conditions normalized if anomaly-triggered · **root cause identified and either fixed or determined nonthreatening.**

> **Don't resume at full capacity. Start with reduced position sizes or paper trading; verify behavior before scaling back up.**

**Override discipline:** log every override (who, when, why) · require explicit risk acknowledgment · **time-limit it (e.g. one hour unless renewed)** · review after the fact.

> **Making overrides too easy defeats the purpose; making them impossible prevents response to genuine false positives.**

---

## 6. MLOps infrastructure — right-sized

### Feature stores prevent training-serving skew

> **The core problem: in research you compute features from historical data with complete freedom. In production you compute the same features in real time, from streaming data, under latency constraints. Subtle differences — date handling, normalization windows, defaults for missing data — create skew that silently degrades performance.**

**Offline store** (Parquet, BigQuery, Redshift) holds historical values for training; **online store** (Redis, DynamoDB) holds only the most recent values for low-latency inference, materialized automatically from offline.

> **For trading this solves a specific problem: rolling features computed during backtesting with pandas and full hindsight must be computed incrementally as new data arrives in production. Feature definitions make the computation identical; the online store keeps serving latency in milliseconds.**

### Data versioning answers a different question

> **Feature stores ensure training-serving consistency, but they do not answer: which exact dataset produced this model? When a model fails and you need to distinguish data corruption from genuine regime shift, you must reproduce the exact training data. Without versioning, diagnosis is guesswork and rollback is risky.**

**Minimum viable: a run manifest per training run** logging git commit hash, dataset snapshot identifier (content hash or partition version), feature set version, model registry version, configuration hash. **Attach it as a tagged artifact so any deployed model traces back to its exact inputs.**

### Maturity tiers

| Tier | Stack |
|---|---|
| **Starting** | Manual deployment with a checklist; simple dashboards (Streamlit, basic Grafana) |
| **Growing** | Feature store · experiment tracking + data versioning · **workflow orchestration with retries and observability** · automated testing · Prometheus/Grafana · **structured logs with consistent correlation IDs (run, strategy, order) for incident diagnosis** |
| **Mature** | Full store with real-time serving · **registry with approval workflows** · Kubernetes · **OpenTelemetry for correlated logs, metrics, and traces across the full signal-to-execution pipeline** |

*Prometheus scrapes custom metrics (`strategy_sharpe_30d`, `signal_ic_rolling`) at 15–30s intervals; Alertmanager routes breaches with configurable escalation.*

> **Start simpler than you think you need. Infrastructure serves the trading system, not the reverse. Monitoring and safety matter more than tooling choices — get those right first and optimize infrastructure as constraints demand.**

---

## Transferable rules

1. **Classify the failure before responding.** Same inputs → different outputs is a bug; same outputs → poor returns is decay.
2. **Validate data at ingest with a fail-closed policy on execution-critical feeds.** Most apparent drift is a silent data defect.
3. **Compute metrics on rolling windows across several lengths,** because point-in-time aggregates hide trends and multi-window agreement distinguishes noise from decay.
4. **Decompose Sharpe into hit rate and win/loss** — the two move differently and point to different causes.
5. **Track the backtest-to-live realization ratio over time,** not just absolute performance.
6. **Monitor execution quality alongside model metrics.** Cost inflation looks like model decay and retraining is the wrong fix.
7. **Calibrate alert thresholds from historical degradation episodes,** and delete any threshold that fires without changing a decision.
8. **Use PSI for binned features and K-S for continuous ones,** and treat PSI spikes as leading indicators.
9. **Watch SHAP rank stability, not just magnitude** — a collapsing core-feature contribution is an early warning.
10. **Run ADWIN or DDM continuously on the prediction-error stream,** and monitor the detector's own alert frequency.
11. **Read the drift-vs-decay cross-tab.** Drift without decay means a robust model; decay without drift means your monitoring has gaps.
12. **Combine scheduled and triggered retraining** rather than choosing one.
13. **Shadow every candidate long enough to span multiple regimes,** with at least two rebalance cycles.
14. **Define a minimum effect size for promotion** and check statistical power before concluding the candidate is better.
15. **Phase capital in through explicit gates** — A/B testing with real money reveals illiquidity clustering and market impact that shadow mode cannot.
16. **Test the rollback mechanism before deploying the candidate.**
17. **Automate low-level rollbacks and require confirmation for performance-based ones.**
18. **Halt immediately on hard loss limits.** Do not wait for review; do not trade out of the hole.
19. **Restart gradually at reduced size after any breaker trip.**
20. **Time-limit and log every manual override.**
21. **Record a run manifest for every training run** so any deployed model traces to its exact inputs.
22. **Right-size the MLOps stack.** Monitoring and safety outrank tooling.

---

## Notebooks

`01_drift_monitoring` (PSI, K-S, prediction-distribution drift, rolling IC and hit rate, alert states — **on the real `us_equities_panel` holdout stream, reference slice from the last pre-holdout year**) · `02_online_drift_detection` (**ADWIN-style vs. DDM on real chronological error streams from the final validation year before promotion, with alerts related to a market-stress proxy rather than synthetic change points**) · `03_safe_model_rollout` (shadow mode, A/B, staged promotion on real incumbent-candidate artifacts) · `04_circuit_breakers` (**drawdown, daily-loss, consecutive-loss, and latency breakers driven by the real SPY 2020 H1 path through the COVID crash**) · `05_feast_feature_store` and `05b_feast_live` (point-in-time joins, online-style as-of snapshots, **measured skew from an incorrect timestamp rule**) · `06_mlflow_experiments` (tracking, artifact logging, registry-style promotion through the local SQLite registry)

> **Only the infrastructure-latency stream is synthetic**, scoped to make the latency breaker's rolling-average trip inspectable. Broker connectivity is out of scope; alert logic, lineage, and promotion gates are grounded in actual workflow outputs.

---

## Cross-references

Ch. 7 §7.4 multiple testing, the mechanism behind overfitting decay · Ch. 11 §11.4 SHAP, used here for importance monitoring · Ch. 16 Deflated Sharpe and backtest-overfitting probability, reused in promotion testing · Ch. 19 §19.8 kill switches and drift detection as risk governance · Ch. 20 the case-study artifacts these notebooks monitor · Ch. 24 §24.9 observability, replay, and release process for agent systems · Ch. 25 §25.6 the parity verification that rules out technical failure before decay is diagnosed; the deployment-loop invariants this chapter audits · Ch. 27 the systematic edge arising from the pipeline as a coherent whole

---

## Citations

Bailey & López de Prado (2014), Deflated Sharpe Ratio · Bifet & Gavaldà (2007), ADWIN · Capponi et al. (2025), nonstationarity and model reliability · Gama et al. (2004), DDM · Harvey, Liu & Zhu (2016), multiple testing in finance · Hinder, Vaquet & Hammer (2023), drift detection survey · Korn, Möller & Schwehm (2022), drawdown-based rules · López de Prado, Lipton & Zoonekynd (2025), Sharpe comparison instability over short samples · Lu et al. (2018), concept drift taxonomy · Lundberg & Lee (2017), SHAP · McLean & Pontiff (2016), post-publication decay · Paleyes, Urma & Lawrence (2023), ML deployment challenges · Sculley et al. (2015), hidden technical debt in ML systems · Varma (2025), drawdown-rule critique

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 26.*
