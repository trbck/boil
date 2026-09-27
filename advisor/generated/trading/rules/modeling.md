# Rules — Models & learning

`113` rules · ~1918 words · ~2589 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R9** — Model-agnostic: this whole loop applies to rule-based systems as well.

### ML4T-07 — Defining the Learning Task

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-07-R1** — **Define the label before selecting an algorithm.** Label misalignment manufactures predictability that no model choice can fix.
- **ML4T-07-R3** — **Any step estimating parameters from data is fit train-only, refit per fold.** When unsure, treat it as fitted.
- **ML4T-07-R4** — **Preserve tails when tails are the prediction target;** winsorize only when they aren't.
- **ML4T-07-R5** — **Treat missingness as three distinct mechanisms** and never let imputation erase it without an indicator.
- **ML4T-07-R6** — **Compute standard errors on effective sample size, not row count.** Overlap can shrink 248k observations to 12k.
- **ML4T-07-R7** — **Summarize diagnostics by fold, never pooled.** Sign consistency across folds is the stability gate; pooled IC can read 0.001 while fold-level reads 0.064.
- **ML4T-07-R9** — **Log the searched-set size with every p-value.** Without it, significance claims are uninterpretable.
- **ML4T-07-R10** — **Separate the exploration pass from the confirmation pass,** and never confirm on the data used to promote.
- **ML4T-07-R11** — **Post-hoc parameter changes are new trials.** Count them.
- **ML4T-07-R12** — **Assign a causal role (confounder / mediator / collider) before conditioning on any variable.** More controls is not safer — conditioning on a collider fabricates correlation.
- **ML4T-07-R14** — **Expect most candidates to fail correction.** Zero of 13 surviving BH-FDR is a normal result, not a broken pipeline.

### ML4T-09 — Model-Based Feature Extraction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-09-R1** — **A fitted object is a feature generator with an estimation window attached.** Refit inside the training fold, version the parameters, log the window.
- **ML4T-09-R2** — **Always use filtered output, never smoothed.** Smoothed states and full-sample posteriors borrow from the future.
- **ML4T-09-R3** — **Model selection is a fitted step.** ARIMA order, HMM state count, fractional *d* — all must be re-selected within each training window.
- **ML4T-09-R5** — **Take the smallest differencing order that achieves stationarity,** preserving maximum memory — and record the boundary convention as part of the definition.
- **ML4T-09-R6** — **Prefer methods that separate direction, surprise, and confidence** over methods that collapse them into one smoothed line.
- **ML4T-09-R7** — **Compute spectral features causally on trailing windows,** and remember window length sets frequency resolution.
- **ML4T-09-R8** — **Treat non-causal transforms (wavelets) as horizon-discovery diagnostics,** then build causal proxies at the discovered scale.
- **ML4T-09-R9** — **Time-augment path signatures** or ordering information is lost; default to depth-2 log-signatures.
- **ML4T-09-R10** — **HAR is the strongest simple volatility baseline** — roughly half the out-of-sample RMSE of GARCH on index data.
- **ML4T-09-R12** — **Separate refit cadence from between-refit update logic.** Most recursions update daily on fixed parameters.
- **ML4T-09-R13** — **Uncertainty is a feature even when the point estimate is already included.** Identical forecasts with different interval widths are different states.
- **ML4T-09-R15** — **Feed regime probabilities as continuous inputs rather than hard-switching between models** — inference is least certain exactly at the transitions that matter.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R2** — **Verify the model's training cutoff predates the backtest period** — for the encoder, the topic model, and every other fitted component.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R1** — **Unbiasedness is not a goal for prediction.** Trading bias for variance lowers MSE when p is large relative to n and signal-to-noise is low.
- **ML4T-11-R2** — **Match the penalty to the signal's structure.** Diffuse and correlated → Ridge. Genuinely sparse → LASSO. Correlated clusters → Elastic Net.
- **ML4T-11-R3** — **Optimize the stability ratio, not the mean.** Most of the achievable gain comes from variance reduction across folds.
- **ML4T-11-R4** — **Calibrate the hyperparameter search range to the estimator's loss convention and sample size,** or you will search only the near-OLS region and conclude regularization does nothing.
- **ML4T-11-R5** — **Use nested walk-forward whenever signal is weak.** Single-loop selection bias can flip the reported sign.
- **ML4T-11-R6** — **Report trial count, search space, selected configuration, and fold-level dispersion** with every tuned result.
- **ML4T-11-R7** — **Winsorize before standardizing, and fit both on training data only.** Both errors fail silently.
- **ML4T-11-R8** — **Report turnover alongside every statistical metric.** No statistical metric measures tradability.
- **ML4T-11-R9** — **Report effective sample size whenever weights are applied,** and verify the reweighted set spans multiple regimes.
- **ML4T-11-R10** — **Choose regression vs. classification from the score-to-position mapping,** not from preference — they encode different information.
- **ML4T-11-R11** — **Calibrate probabilities only if position size depends on probability levels.** Rank-based mappings don't need it.
- **ML4T-11-R12** — **Treat AUC above 0.65 out-of-sample as a leakage alarm,** not a success.
- **ML4T-11-R13** — **Use SHAP for descriptive attribution, never causal claims,** and bootstrap within fold to separate regime shift from estimation noise.
- **ML4T-11-R14** — **Flag single-feature-dominated predictions** for review or size reduction — concentrated attribution is fragility.
- **ML4T-11-R15** — **Conformal coverage in finance is empirical, not guaranteed.** Monitor by fold, regime, magnitude bucket, and asset characteristic; a marginal number hides the failures that matter.
- **ML4T-11-R16** — **Diagnose undercoverage before switching methods** — leakage, window size, and score definition are more common causes than exchangeability.
- **ML4T-11-R17** — **A significant IC on a huge sample is not a strong signal.** Separate statistical from economic significance every time.
- **ML4T-11-R18** — **Check sign stability before concluding a flat IC means an unstable model.** Usually the features simply carry no ranking content.
- **ML4T-11-R19** — **Every later model must beat this baseline.** A gradient-boosting model that underperforms Ridge has added complexity without adding predictive power.

### ML4T-12 — Advanced Models for Tabular Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-12-R1** — **Choose the GBM library on operational criteria** — training throughput, inference latency, categorical leakage safety, ecosystem — because post-tuning accuracy differences are noise.
- **ML4T-12-R2** — **Verify GPU actually helps before assuming it does.** Precision support and dataset scale can make GPU slower than CPU.
- **ML4T-12-R3** — **Match the objective to where trading occurs.** Rank objectives pay in high-breadth cross-sections where only tails trade; they cost calibration you may need downstream.
- **ML4T-12-R4** — **Use monotonic constraints as theory-driven regularization,** and verify via constrained-vs-unconstrained SHAP dependence that they cost no IC.
- **ML4T-12-R5** — **Tune regularization before tree structure.** It has the larger out-of-sample effect in low-SNR regimes.
- **ML4T-12-R6** — **Cap trial budgets at 50–100.** More trials find validation noise, and that is the most common backtest-to-live failure.
- **ML4T-12-R7** — **Try multi-objective search even when you only care about one objective** — constraining a second can reach parameter regions single-objective search misses.
- **ML4T-12-R8** — **Prefer TreeSHAP to native importance for any decision,** and use exact interaction values to detect mechanisms that shift by regime beneath a stable-looking average.
- **ML4T-12-R9** — **Monitor SHAP drift as a leading indicator,** but confirm with outcome metrics before acting.
- **ML4T-12-R10** — **Cross-validate explanations across model families.** Equal-accuracy models disagree; agreement across architectures is the stronger evidence.
- **ML4T-12-R11** — **Discount tabular benchmarks that assume IID splits.** Attention-heavy architectures degrade fastest under exactly the temporal shift finance has.
- **ML4T-12-R12** — **Audit retrieval-augmented models for temporal isolation** before believing any reported number.
- **ML4T-12-R13** — **Flexibility extends signal; it does not create it.** Where the linear baseline is flat, expect the interval to stay on zero.
- **ML4T-12-R15** — **Treat early stopping as a tuned outcome** — the optimal tree count varied by 10× across case studies.

### ML4T-13 — Deep Learning for Time Series

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-13-R1** — **Define the target before choosing the architecture.** Recursive forecasting, multi-horizon path forecasting, horizon-label prediction, and direct allocation are four different problems.
- **ML4T-13-R3** — **A forecasting-native architecture is a liability on a ranking label.** Sophisticated path-forecasting inductive biases actively hurt when only the horizon label is scored.
- **ML4T-13-R4** — **Library choice is a modeling choice.** Forecasting frameworks impose the path formulation.
- **ML4T-13-R5** — **Clear D-Linear before believing anything more complex.**
- **ML4T-13-R6** — **Test whether shuffling the input degrades the model.** If it doesn't, the model isn't using temporal structure.
- **ML4T-13-R7** — **Compare families with a paired daily-difference interval,** not two separate confidence intervals — clearing zero and beating the baseline are different claims.
- **ML4T-13-R8** — **Longer lookbacks add noise more reliably than they add signal** in weak, non-stationary series.
- **ML4T-13-R9** — **Never trust a single-split IC at this SNR.** Rerun noise can exceed the effect being measured.
- **ML4T-13-R10** — **Zero-shot foundation models on returns are worse than random.** Domain pretraining or fine-tuning is required, not optional.
- **ML4T-13-R11** — **Treat the pretraining corpus as a leakage channel** and verify temporal separation from the evaluation period.
- **ML4T-13-R12** — **Report the accuracy-efficiency frontier, not parameter count.** Scaling laws don't hold here.
- **ML4T-13-R13** — **TSFMs are credible for volatility and VaR, not returns** — the target structure transfers where the return signal does not.
- **ML4T-13-R14** — **Always conformally calibrate deep-model intervals.** Raw Gaussian intervals under-cover by an order of magnitude.
- **ML4T-13-R15** — **Ranking credibility and uncertainty reliability are independent properties.** Check both before sizing on a signal.
- **ML4T-13-R17** — **A large sample size triggers model comparison, not model replacement.**

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R5** — **Apply shrinkage before PCA on large cross-sections,** and prefer eigenvalue shrinkage to scree-plot inspection when N/T is moderate.
- **ML4T-14-R7** — **Separate fast volatility dynamics from slow correlation dynamics** with different half-lives in production risk models.
- **ML4T-14-R8** — **Interpret higher-order components descriptively, never structurally** — they rotate across regimes.
- **ML4T-14-R11** — **Report a range of K, not a single optimum.** The out-of-sample selection rule is sensitive to the test-asset set.
- **ML4T-14-R12** — **Test assets are a design choice.** Report how conclusions change when the span is enriched.
- **ML4T-14-R13** — **Never select a factor model on reconstruction loss.** Good contemporaneous fit is compatible with useless forecasts.
- **ML4T-14-R14** — **Use the adapter's separability** — swap Stage 2 forecasters without retraining Stage 1.
- **ML4T-14-R15** — **Where N/T is unfavorable, prefer models that map characteristics to loadings** over models that estimate loadings from returns.
- **ML4T-14-R17** — **Report gross and net, with and without microcaps.** Characteristic predictability concentrates exactly where it is least tradable.
- **ML4T-14-R18** — **Read model disagreement as model risk, not as a tie to be broken** — differing rank correlations across objectives are informative in themselves.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R1** — **Identification precedes estimation.** No estimator rescues a design that cannot justify a causal interpretation.
- **ML4T-15-R2** — **Write the DAG before choosing the method,** and let structure — not significance or feature importance — determine the adjustment set.
- **ML4T-15-R3** — **More controls is not safer.** Mediators change the estimand, colliders open closed paths, treatment descendants introduce post-treatment bias.
- **ML4T-15-R4** — **Timing discipline is necessary but insufficient** — a pre-treatment variable can still be a collider or selection variable.
- **ML4T-15-R5** — **Start with the treatment–outcome pair, not the estimator.** Mechanism-adjacent outcomes support more credible claims than broad market outcomes.
- **ML4T-15-R6** — **Declare the estimand precisely,** including horizon — different horizons are different causal questions, not robustness checks.
- **ML4T-15-R7** — **Distinguish subgroup ATEs from CATEs, and confounders from effect modifiers.** Both distinctions change what is being estimated.
- **ML4T-15-R8** — **Cross-fit on expanding or rolling windows with a temporal gap,** never random folds.
- **ML4T-15-R9** — **Sweep nuisance learners and treat large variation as instability,** not as a menu to pick from.
- **ML4T-15-R10** — **Report the naive-vs-orthogonalized gap.** It is often above 50%, and it can run in either direction.
- **ML4T-15-R11** — **Size permutation blocks to the autocorrelation.** Too-short blocks understate the null and inflate apparent significance.
- **ML4T-15-R12** — **Run placebo dates before believing any event study,** and reject the design if the false-positive rate is high — no individual finding survives a broken design.
- **ML4T-15-R13** — **Test every control as a target for spillover, per event.** For macro events, truly unaffected controls may not exist.
- **ML4T-15-R14** — **A cumulative-effect credible interval is the diagnostic; a fraction of positive rows is not a posterior probability.**
- **ML4T-15-R15** — **Treat discovered edges as hypotheses.** Method outputs on identical data ranged from 1 to 42 edges.
- **ML4T-15-R16** — **Weight edges by cross-method agreement and effect magnitude,** not by p-value or by any single implementation.
- **ML4T-15-R17** — **Causal analysis reduces out-of-sample degradation when heterogeneity carries information; it does not manufacture alpha when the signal inverts.**
- **ML4T-15-R18** — **Causal credibility and predictive signal are separable in both directions** — neither licenses the other.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R8** — **Report gross and net together.** The gap reveals whether performance comes from forecasting or is consumed by trading.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R6** — **Treat allocator hyperparameters as tunable parameters requiring out-of-sample validation.** Holding the forecast model fixed does not protect against fitting the allocator to the answer key.

### ML4T-21 — Reinforcement Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-21-R2** — **"Model-free" describes the algorithm, not the modeling burden.** State design, reward shaping, and simulator construction carry the assumptions.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R1** — **Treat grounding as architecture, not prompting.** Post-hoc fact-checking neither scales nor addresses the cause.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R9** — **Maintain a frozen gold subset** and regression-test extraction across prompt and model changes.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R5** — **Cap the reasoning budget** and return bounded output with explicit uncertainty when exhausted.
- **ML4T-24-R12** — **Enforce cutoffs at the tool boundary, never in the model narrative.**
- **ML4T-24-R23** — **Version prompts, corpora, and models as regulated artifacts.**
- **ML4T-24-R24** — **Cascade models by phase and measure per-phase error rates,** never assuming the saving.

### ML4T-25 — Live Trading Systems

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-25-R12** — **Match training and inference venues,** and when impossible, measure and document the convention differences as an explicit verification task.
- **ML4T-25-R18** — **Encode the training-cutoff invariant explicitly** and persist both cutoff dates for later audit.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R21** — **Record a run manifest for every training run** so any deployed model traces to its exact inputs.

