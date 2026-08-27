# Rules — Features, labels & horizons

`109` rules · ~1812 words · ~2446 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R5** — Zero-lag records on delayed data are a red flag, always.

### ML4T-04 — Fundamental and Alternative Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-04-R2** — Conservative default for equities: use filing acceptance as availability; track the earlier 8-K separately only if event precision matters.
- **ML4T-04-R3** — Crypto needs a **confirmation policy** in the PIT contract — block time alone permits reorg lookahead.
- **ML4T-04-R4** — Never interpolate macro series onto a decision grid.
- **ML4T-04-R6** — Identifier match ≠ correct resolution. Pick the layer (entity / security / contract) explicitly.
- **ML4T-04-R7** — Precision over recall in entity matching; the failure is asymmetric.
- **ML4T-04-R8** — All joins constrained by both availability time and identifier effective-date range.
- **ML4T-04-R9** — Detect leakage by running as-known vs. latest-available and comparing.
- **ML4T-04-R10** — Legal and PIT integrity are hard gates; score comparisons happen only after.
- **ML4T-04-R11** — For text: accession number as key, `accepted_at` for timing, store raw + cleaned + extraction metadata.

### ML4T-06 — Strategy Research Framework

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-06-R6** — **Test admissibility with one question:** at decision time *t*, were the features computable and was the label already resolved?

### ML4T-07 — Defining the Learning Task

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-07-R1** — **Define the label before selecting an algorithm.** Label misalignment manufactures predictability that no model choice can fix.
- **ML4T-07-R2** — **Match the execution convention to the actual execution assumption** and keep it identical in label computation and backtest PnL — the gap is 50–100 bps per trade on daily equities.
- **ML4T-07-R5** — **Treat missingness as three distinct mechanisms** and never let imputation erase it without an indicator.
- **ML4T-07-R6** — **Compute standard errors on effective sample size, not row count.** Overlap can shrink 248k observations to 12k.
- **ML4T-07-R7** — **Summarize diagnostics by fold, never pooled.** Sign consistency across folds is the stability gate; pooled IC can read 0.001 while fold-level reads 0.064.
- **ML4T-07-R8** — **Thresholds set both event magnitude and base rate simultaneously** — choose them against the turnover and cost budget, and estimate percentiles within-fold.
- **ML4T-07-R9** — **Log the searched-set size with every p-value.** Without it, significance claims are uninterpretable.
- **ML4T-07-R10** — **Separate the exploration pass from the confirmation pass,** and never confirm on the data used to promote.
- **ML4T-07-R11** — **Post-hoc parameter changes are new trials.** Count them.
- **ML4T-07-R13** — **A gross spread that doesn't clear estimated costs is a stop, not a revise.**
- **ML4T-07-R14** — **Expect most candidates to fail correction.** Zero of 13 surviving BH-FDR is a normal result, not a broken pipeline.

### ML4T-08 — Financial Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-08-R2** — **If you cannot name the economic mechanism, you have a data pattern.** Hold it to a higher evidentiary standard or drop it.
- **ML4T-08-R3** — **Classify every feature as signal or state before evaluating it.** State variables legitimately show weak marginal association and only earn their place through interactions.
- **ML4T-08-R4** — **Match lookback, cadence, and smoothing to the label horizon.** Horizon mismatch is the most common source of unstable estimates.
- **ML4T-08-R5** — **Use range-based estimators for variance and ATR for sizing** — they answer different questions.
- **ML4T-08-R6** — **Test delay sensitivity before optimizing any flow-based feature.** Contemporaneous correlation routinely exceeds lagged by an order of magnitude.
- **ML4T-08-R8** — **Verify venue-specific clocks** (funding intervals, roll schedules, session boundaries) rather than assuming the common convention.
- **ML4T-08-R9** — **Repeating slow data across fast rows inflates N without adding information.** Weight by uniqueness.
- **ML4T-08-R10** — **Encode event proximity and phase, never event outcomes,** in pre-event windows.
- **ML4T-08-R11** — **Breadth beats marginal IC.** A slightly better signal on a small universe loses to a thin signal on a large one.
- **ML4T-08-R12** — **Deduplicate within families before the model stage,** and prefer fold stability over single-metric wins when picking cluster representatives.
- **ML4T-08-R14** — **Demand the right event-time shape, not just a significant average.** Correct sign, correct timing, correct asymmetry.
- **ML4T-08-R15** — **Log fitted parameters and training windows for any feature that depends on a fitted object.**

### ML4T-09 — Model-Based Feature Extraction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-09-R1** — **A fitted object is a feature generator with an estimation window attached.** Refit inside the training fold, version the parameters, log the window.
- **ML4T-09-R2** — **Always use filtered output, never smoothed.** Smoothed states and full-sample posteriors borrow from the future.
- **ML4T-09-R4** — **Diagnostics are features.** Rolling ADF/KPSS statistics, CUSUM values, and time-since-break are conditioning variables, not just gates.
- **ML4T-09-R5** — **Take the smallest differencing order that achieves stationarity,** preserving maximum memory — and record the boundary convention as part of the definition.
- **ML4T-09-R6** — **Prefer methods that separate direction, surprise, and confidence** over methods that collapse them into one smoothed line.
- **ML4T-09-R7** — **Compute spectral features causally on trailing windows,** and remember window length sets frequency resolution.
- **ML4T-09-R8** — **Treat non-causal transforms (wavelets) as horizon-discovery diagnostics,** then build causal proxies at the discovered scale.
- **ML4T-09-R9** — **Time-augment path signatures** or ordering information is lost; default to depth-2 log-signatures.
- **ML4T-09-R10** — **HAR is the strongest simple volatility baseline** — roughly half the out-of-sample RMSE of GARCH on index data.
- **ML4T-09-R11** — **Guard parameter-derived features against their own validity conditions** — long-run variance is meaningless under IGARCH.
- **ML4T-09-R12** — **Separate refit cadence from between-refit update logic.** Most recursions update daily on fixed parameters.
- **ML4T-09-R13** — **Uncertainty is a feature even when the point estimate is already included.** Identical forecasts with different interval widths are different states.
- **ML4T-09-R14** — **Relabel latent states by a stable characteristic across refits,** or the feature is incoherent over time.
- **ML4T-09-R16** — **Compute temporal features first, then apply the panel layer.** Never the reverse.
- **ML4T-09-R17** — **Keep the set compact.** One or two volatility features, one regime feature, one signal-transform feature, and a limited set of cross-sectional transforms are usually enough to establish what fitted methods add over Ch. 8 directs.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R1** — **The timestamp contract, not the model, decides whether a text feature is tradable.** Publication ≠ scrape ≠ vendor timestamp; pick the one you could have acted on.
- **ML4T-10-R2** — **Verify the model's training cutoff predates the backtest period** — for the encoder, the topic model, and every other fitted component.
- **ML4T-10-R3** — **Always run the TF-IDF baseline.** Failure to beat it points at labels, alignment, or task definition rather than capacity.
- **ML4T-10-R4** — **Benchmark accuracy does not transfer across text distributions.** Run a cross-dataset evaluation; expect drops of tens of points when label conventions differ.
- **ML4T-10-R5** — **"FinBERT" names several incompatible checkpoints.** Match corpus *and* label definition to your task.
- **ML4T-10-R6** — **Snapshot documents at first availability and reject revisions by default.**
- **ML4T-10-R7** — **Deduplicate syndicated and revised content within (ticker, date)** before aggregation, or you count the same information many times.
- **ML4T-10-R8** — **Sizing the purge gap is a function of the signal's decay horizon,** not a fixed constant.
- **ML4T-10-R9** — **Pin embedding model versions and key caches by document hash + model ID.** Vector meaning changes when models change.
- **ML4T-10-R10** — **Chunk within documents, never across them,** and never fit global transforms on the full corpus.
- **ML4T-10-R11** — **Coverage is endogenous** — evaluate IC conditional on coverage, and consider modeling coverage as its own signal.
- **ML4T-10-R12** — **Test the signal against a realistic availability delay.** IC that dies with a one-hour lag is a speed edge, not an information edge.
- **ML4T-10-R13** — **Attention weights are routing, not explanation.**
- **ML4T-10-R14** — **Prefer abstention to a low-confidence record,** and validate at the pipeline boundary.
- **ML4T-10-R15** — **Separate extraction from aggregation** so models can be upgraded without rebuilding feature history.
- **ML4T-10-R16** — **Reserve LLMs for ambiguous, rare, or schema-rich tasks;** high-volume daily features should use encoders or distilled models unless the LLM adds measurable value after latency, cost, and validation constraints.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R18** — **Check sign stability before concluding a flat IC means an unstable model.** Usually the features simply carry no ranking content.

### ML4T-13 — Deep Learning for Time Series

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-13-R1** — **Define the target before choosing the architecture.** Recursive forecasting, multi-horizon path forecasting, horizon-label prediction, and direct allocation are four different problems.
- **ML4T-13-R2** — **For cross-sectional ranking, predict the label directly** — it matches the evaluation metric and avoids compounding.
- **ML4T-13-R3** — **A forecasting-native architecture is a liability on a ranking label.** Sophisticated path-forecasting inductive biases actively hurt when only the horizon label is scored.
- **ML4T-13-R5** — **Clear D-Linear before believing anything more complex.**
- **ML4T-13-R7** — **Compare families with a paired daily-difference interval,** not two separate confidence intervals — clearing zero and beating the baseline are different claims.
- **ML4T-13-R8** — **Longer lookbacks add noise more reliably than they add signal** in weak, non-stationary series.
- **ML4T-13-R9** — **Never trust a single-split IC at this SNR.** Rerun noise can exceed the effect being measured.
- **ML4T-13-R11** — **Treat the pretraining corpus as a leakage channel** and verify temporal separation from the evaluation period.
- **ML4T-13-R12** — **Report the accuracy-efficiency frontier, not parameter count.** Scaling laws don't hold here.
- **ML4T-13-R13** — **TSFMs are credible for volatility and VaR, not returns** — the target structure transfers where the return signal does not.
- **ML4T-13-R15** — **Ranking credibility and uncertainty reliability are independent properties.** Check both before sizing on a signal.
- **ML4T-13-R16** — **Make early stopping a per-case-study outcome** — high-frequency panels peak early, longer-horizon panels keep climbing.

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R1** — **Name the objective before choosing the method.** Variance explained, variance plus pricing error, and pricing error alone select different factors.
- **ML4T-14-R2** — **A factor that explains covariation is not necessarily priced.** Attribution factors and priced factors are different objects with different uses.
- **ML4T-14-R3** — **Check N/T against the BBP threshold before trusting any component.** Below it, no technique recovers the factor.
- **ML4T-14-R4** — **Prefer idiosyncratic-volatility normalization to correlation PCA** — it removes noise without flattening genuine differences in common-factor exposure.
- **ML4T-14-R5** — **Apply shrinkage before PCA on large cross-sections,** and prefer eigenvalue shrinkage to scree-plot inspection when N/T is moderate.
- **ML4T-14-R6** — **Measure eigenvector stability with cosine similarity and apply Procrustes rotation when eigenvalues cluster.** Unstable loadings generate phantom turnover that costs real money.
- **ML4T-14-R8** — **Interpret higher-order components descriptively, never structurally** — they rotate across regimes.
- **ML4T-14-R9** — **Regress loadings on observable characteristics** to test whether a "latent" factor is a known factor renamed.
- **ML4T-14-R10** — **Lag characteristics relative to returns and impute rather than drop** — missingness is informative about firm size.
- **ML4T-14-R11** — **Report a range of K, not a single optimum.** The out-of-sample selection rule is sensitive to the test-asset set.
- **ML4T-14-R12** — **Test assets are a design choice.** Report how conclusions change when the span is enriched.
- **ML4T-14-R13** — **Never select a factor model on reconstruction loss.** Good contemporaneous fit is compatible with useless forecasts.
- **ML4T-14-R17** — **Report gross and net, with and without microcaps.** Characteristic predictability concentrates exactly where it is least tradable.
- **ML4T-14-R18** — **Read model disagreement as model risk, not as a tie to be broken** — differing rank correlations across objectives are informative in themselves.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R2** — **Write the DAG before choosing the method,** and let structure — not significance or feature importance — determine the adjustment set.
- **ML4T-15-R8** — **Cross-fit on expanding or rolling windows with a temporal gap,** never random folds.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R11** — **Check whether holding period matches signal horizon.** A mismatch requires explanation.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R4** — **Read IC as R².** An IC of 0.03 explains ~0.09% of cross-sectional variance — value comes from repetition, not single-name predictability.
- **ML4T-17-R5** — **Match estimation-window horizons to signal horizons deliberately,** not by default settings.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R11** — **Never trust a citation without verifying it.** Semantic similarity between claim and cited text is a cheap check.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R4** — **Define the schema before extraction,** so the model emits graph-ready objects rather than text requiring cleanup.
- **ML4T-23-R12** — **Cite two layers — the graph row and the underlying disclosure text.**
- **ML4T-23-R13** — **Use multiple centrality measures as separate features** rather than picking one.
- **ML4T-23-R14** — **Cross-graph interaction features are the distinctive payoff,** because they encode dependencies factor models assume away.
- **ML4T-23-R19** — **Log snapshot hash and extractor version** so historical feature values can be replayed.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R4** — **Give every persisted lesson a validity horizon,** or Reflexion converts temporary heuristics into durable blind spots.
- **ML4T-24-R22** — **Separate engineering and research observability views.**

### ML4T-25 — Live Trading Systems

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-25-R13** — **Source warm-up data from the executing session,** not a research-time loader, or rankings and sizing run on stale prices.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R3** — **Compute metrics on rolling windows across several lengths,** because point-in-time aggregates hide trends and multi-window agreement distinguishes noise from decay.
- **ML4T-26-R8** — **Use PSI for binned features and K-S for continuous ones,** and treat PSI spikes as leading indicators.
- **ML4T-26-R9** — **Watch SHAP rank stability, not just magnitude** — a collapsing core-feature contribution is an early warning.

