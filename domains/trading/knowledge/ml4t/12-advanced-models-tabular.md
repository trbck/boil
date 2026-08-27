# Ch 12 — Advanced Models for Tabular Data

**Governs:** when nonlinear tabular models earn their complexity over the Ch. 11 linear baseline, and which library/objective/constraint choices are finance-specific.
**Thesis:** the accuracy gap between GBM libraries is smaller than the gap between good and bad hyperparameter configurations of any one of them. Selection criteria are operational, not statistical — and added flexibility widens the set of case studies with measurable signal only modestly.

*Thin file by design — standard boosting mechanics omitted. Kept: what changes a decision in a trading context.*

---

## 1. Library selection is an operational choice

> **Calibration for how little the library matters.** On the firm-characteristics benchmark (414K train / 307K valid / 497K test, 1967–2016), every GBM beats the Random Forest baseline (test IC **0.058–0.060 vs. 0.056**) — but **library-to-library differences are ~0.002 IC, smaller than the boosting-vs-bagging gap.** After tuning, all four libraries fall in a narrow IC band and their fold-level rankings vary over time.

**Decide on throughput, latency, categorical safety, and ecosystem — not expected accuracy.**

| Dimension | XGBoost | LightGBM | CatBoost |
|---|---|---|---|
| **CPU train** (4.9M rows, 8 threads) | ~100s | **~50s (fastest)** | ~135s |
| **GPU train** (4.9M rows, CUDA) | ~14s (~7×) | ~14s (~3.5×, FP64 only) | **~10s (~14×, fastest)** |
| **Inference** (heavy preset) | 0.5M rows/s CPU, 1.7M GPU | **0.07M rows/s CPU (slowest)** | **6.5M rows/s CPU — ~12× XGBoost** (symmetric trees → bitwise path) |
| **High-cardinality categoricals** | Native | Native | **Ordered target statistics avoid leakage** |
| **Tuning sensitivity** | Moderate | Moderate-high (leaf-wise growth needs `num_leaves`/`min_data_in_leaf` constraints) | Often lower |
| **Memory** | Moderate | Often best | Moderate |

> **The LightGBM GPU trap.** Its CUDA backend is **FP64-only** (`gpu_use_dp` works only on the OpenCL path). Consumer GPUs have an FP32:FP64 throughput ratio around **64:1** — an RTX 3090 delivers 35.6 TFLOPS FP32 but ~0.6 FP64 — so the histogram computation runs at a fraction of available throughput. On a 227K-row dataset it is **actively slower on GPU than CPU (~9.5s vs. ~48s).** Keep LightGBM on CPU unless you have a data-center card (A100 is 2:1).

**Practical defaults:** LightGBM when running walk-forward CV across many configurations on CPU. CatBoost when GPU training time at scale matters, or when sector codes / analyst IDs are in the feature set (ordered encoding eliminates a class of silent leakage bugs). XGBoost when ecosystem integration (SHAP, Optuna callbacks, deployment tooling) matters most.

---

## 2. Objectives and constraints that encode trading structure

### Learning to rank

A long-short decile strategy profits from correct *ranking*, not accurate magnitude. MSE dominated by large errors in the middle of the distribution sacrifices ranking accuracy **in the tails where trading actually occurs.**

**LTR pays most in high-breadth cross-sections where only the tails trade.** 500 stocks, decile long-short → only 100 names trade, but MSE optimizes accuracy across all 500 equally.

**It pays less when:** the strategy trades the full cross-section (rank-weighted portfolios) · breadth is low so most assets enter positions · signal-to-noise is so low that ranking and pointwise objectives converge.

> **LTR scores are well-ordered but not calibrated to return magnitudes.** If downstream construction needs return *forecasts* (mean-variance optimization), either calibrate post-hoc or use pointwise predictions. Uncalibrated ranking scores suffice for "long top quintile, short bottom quintile."

Implementation: LightGBM `lambdarank` (requires `group` by date — each group is one cross-section), XGBoost `rank:ndcg`, CatBoost `YetiRank`/`YetiRankPairwise`. Evaluate group-wise **NDCG@k by date** alongside IC to make objective–metric alignment explicit.

### Monotonic constraints as theory-driven regularization

GBMs excel at nonlinearity and are **blind to economic theory** — a model may learn that extremely high P/E predicts a *return spike* because of noise in a sparse region.

Constraints buy three things: they prevent fitting non-monotonic artifacts in low-SNR regions · improve deployability (risk committees accept auditable directional logic) · improve robustness to regime shift, since the model cannot learn complex patterns unlikely to repeat.

> **Diagnostic that tells you whether a constraint costs information:** compare constrained vs. unconstrained SHAP dependence plots. The unconstrained plot for a value feature typically shows a downward slope **with local reversals** where higher value scores paradoxically predict lower returns. **When the constrained model's IC is comparable — as it usually is for economically motivated constraints — the constraint is acting as regularization, not information loss.**

---

## 3. Tuning traps

**Three hyperparameter families:** tree structure (depth, leaves, min samples) · boosting dynamics (learning rate, rounds, subsampling) · regularization (L1/L2, min child weight).

> **The common pitfall is tuning tree structure extensively while neglecting regularization.** `reg_alpha` and `reg_lambda` often have the **greatest** impact on out-of-sample performance because they directly address overfitting in low-SNR regimes.

**Efficient default:** fix the learning rate low (0.01–0.05), let early stopping determine rounds. More efficient than tuning both jointly.

> **Validation overfitting is the most common source of backtest-to-live degradation.** In daily-return prediction, 500 TPE trials **will** find hyperparameters exploiting validation noise; the 0.02 IC improvement vanishes on truly held-out data. **Defenses: limit to 50–100 trials, use coarser grids, and always evaluate final candidates on data untouched during optimization.** Pruning (MedianPruner, HyperbandPruner) cuts computation by 50%+ without sacrificing quality.

### Multi-objective: IC vs. turnover

Aggressive hyperparameters raise IC **and** turnover together, because finer-grained patterns change more frequently across rebalances.

> **A surprising empirical result worth knowing:** on the ETF case study, NSGA-II multi-objective search finds two non-dominated solutions — IC ≈ 0.029 at turnover ≈ 0.004 and IC ≈ 0.030 at turnover ≈ 0.005 — while **single-objective TPE on IC alone, on the same search space, converges to IC ≈ 0.010.** The multi-objective search reached a region of parameter space the single-objective search never found. Constraining on turnover did not cost IC; it improved it.

**Read the frontier shape:** nearly flat in a region → you can claim both objectives without real compromise. Steeply curved → marginal IC comes at rapidly rising turnover cost, warranting transaction-cost sensitivity analysis.

Other useful pairs: return vs. drawdown · Sharpe vs. capacity.

---

## 4. TreeSHAP — what's newly available for trees

TreeSHAP computes **exact** Shapley values in O(TLD²), fast enough to run **on every walk-forward fold as standing diagnostic infrastructure**. Neural networks require approximate methods orders of magnitude slower.

**Native GBM importance is not a substitute:** gain-based importance is biased toward high-cardinality features (more candidate splits); split-count is biased toward continuous over categorical; both are unstable across random seeds, especially for correlated features the model can substitute. **Use native importance for quick screening, SHAP for anything informing a decision.**

### Exact interaction values

Unique to trees: decomposition of each prediction into main effects and **pairwise interactions**.

> **Why this matters for stability diagnosis.** In the ETF case study the strongest interaction is between the yield-curve z-score and the short-horizon volatility ratio. The yield-curve signal carries most of its predictive content **only when short-term volatility deviates from its longer-horizon baseline**, and the interaction contribution can **flip sign across volatility regimes.** Standard importance rankings rank yield-curve z-score as a top feature *regardless of regime* — which is exactly how **a model looks stable on average while its mechanism shifts underneath.**

### Drift monitoring

Comparing SHAP distributions between a baseline period and recent predictions detects mechanism change **before it shows in performance metrics** — earlier than rolling IC or Sharpe, because by the time returns degrade the damage is done. Flag features whose mean |SHAP| changes by more than ~50%.

> **SHAP drift is a diagnostic warranting investigation, not proof of concept drift.** Feature distributions can shift without affecting predictions if the model doesn't rely on them. Validate against rolling IC and residual patterns before acting.

### The Rashomon effect

> Models with **equal** predictive performance can produce **strikingly different** explanations. A Random Forest and a GBM both at 0.05 IC attributing to different features reveals model-specific logic, not ground truth. The instability is sharper than intuition suggests: **predictions differing by roughly 1.3% can yield entirely different top-three SHAP contributors.**

**Practical rule:** features that **multiple model families** rank as important more likely reflect genuine structure; features only one family highlights may be architecture-specific fitting patterns. When SHAP informs feature pruning, risk allocation, or regulatory reporting, validate across specifications.

**SHAP-based pruning:** features with consistently near-zero SHAP across folds are removal candidates. **Features with high SHAP *variance* across folds may be regime-dependent signals worth investigating rather than discarding.** Cross-check against permutation importance and MDI to filter single-method artifacts.

---

## 5. Deep tabular alternatives — the finance-relevant caveats

| Model | Role in a finance workflow |
|---|---|
| **TabPFN** (in-context learning, no gradient updates) | **Rapid prototyping** — test whether a feature set contains signal before investing in GBM tuning. v2.5 extends to ~50K rows / 2K features. Weights are **non-commercial by default**; treat as a research tool unless licensed |
| **TabM** (shared backbone + rank-1 adapters) | **Strongest practical neural baseline.** Ensemble diversity at single-network cost; showed robustness on temporal splits. Beats GBM on **3 of 8** covered case studies |
| **TabR** (retrieval-augmented) | Appealing framing (regime similarity, peer analogy) — **but see the trap below** |
| **AutoGluon** | **Ceiling sanity check,** not deployment. If your tuned model is within striking distance you've extracted most available signal; if not, inspect which family in the stack contributes the lift |

> **The TabR lookahead trap.** Standard implementations build the retrieval index over the **entire training set with no temporal constraint**, so in walk-forward the model can retrieve neighbors from periods that overlap or follow the prediction target. Enforcing temporal isolation — neighbors strictly from before the prediction date, with the same purge and embargo logic as the splits — **remains an open engineering problem. Treat TabR results without temporal isolation as upper bounds, not production estimates.**

> **Read tabular benchmarks critically before transferring conclusions.** Major benchmarks (TabArena, TALENT) **explicitly exclude temporal dependence** and assume IID splits. The one benchmark that tested temporal distribution shift found **attention-heavy architectures degraded faster than GBMs and simple MLPs** — directly relevant to nonstationary financial data. Also check tuning-budget parity (a tuned GBM vs. a default neural net proves nothing), whether the headline result relies on cross-model ensembles you can't deploy, and dataset leakage — TabArena retained **51 datasets from an initial pool of 1,053.**

**Model selection by regime:**

| Regime | Choice |
|---|---|
| < 10K effective samples, rapid signal testing | TabPFN |
| 10K–100K, production tabular | **LightGBM / XGBoost** |
| > 100K with heavy categoricals | **CatBoost** (ordered scheme prevents leakage) |
| > 1M with GPU | No reliable crossover — validate both families |
| Multi-modal (text + tabular) | End-to-end DL; GBMs don't fuse modalities |
| Local similarity / regime matching central | TabR **with temporal isolation enforced** |

---

## 6. Case study evidence — does flexibility pay?

Same nine case studies, same primary labels, HAC 95% CIs. **Bold = interval excludes zero.**

| Case study | Horizon | Linear | GBM | TabM |
|---|---|---|---|---|
| **US Firms** | 1 month | −0.005 | **+0.080** | +0.031 |
| **ETFs** | 21 days | **+0.054** | +0.037 | +0.041 |
| **CME Futures** | 5 days | −0.000 | **+0.032** | +0.004 |
| **US Equities** | 1 day | **+0.016** | **+0.032** | +0.017 |
| **S&P 500 Options** | to expiry (straddle) | +0.007 | **+0.018** | +0.002 |
| Crypto | 8 hours | +0.009 | +0.011 | +0.003 |
| **NASDAQ-100** | 15 min | **+0.005** | **+0.006** | — |
| S&P 500 Eq+Opt | 5 days | −0.006 | +0.006 | +0.011 |
| FX | 1 day | +0.005 | +0.003 | +0.007 |

**GBM clears zero on 5 of 9, linear on 3, TabM on 3 of 8.**

> **The headline finding: added flexibility does not win by default, and on no case study does it manufacture a ranking where the linear model found none.** GBM crosses the line on three case studies whose linear interval overlapped zero — US Firms, CME Futures, S&P 500 Options straddle — which is the clearest evidence nonlinear structure carries reachable ranking content.

> **The reverse also happens, and is easy to miss.** On ETFs the **linear model posts the highest IC (+0.054) and is the only family whose interval clears zero.** Cross-asset momentum is close to linear in these features; tree splits spend capacity on interactions that don't survive out of sample. Where the linear baseline was flat (FX, S&P 500 Eq+Opt), **all three families stay within noise of zero — added capacity moves the point estimate without moving the interval off zero.**

**TabM follows GBM in sign more than magnitude**, and neither dominates — they encode nonlinearity through different inductive biases (axis-aligned splits vs. learned dense embeddings). TabM edges boosting on ETFs and FX; boosting is far ahead on US Firms and the options straddle.

### Configuration findings worth stealing

> **Loss function beats depth as a tuning priority. MAE posts the highest IC on 8 of 9 primary labels** (MSE only on ETFs; Huber competitive but never highest). On US Firms the MAE curve sits near **+0.080 across every leaf budget** while Huber and MSE bunch at **+0.030 to +0.035** — a gap of two to three interval half-widths, opened by **refusing to chase the heavy-tailed extreme returns that squared error spends capacity on.** On US Equities all three losses fall within one half-width at every depth.

**Tree depth is the least consequential hyperparameter.** The best leaf budget scatters across the grid interior (7 leaves on three case studies, 63 on three others) and within-case-study depth profiles differ by less than one interval half-width.

> **Early stopping is what pays operationally, and the right number varies enormously.** Boosting trajectories peak at: **~50 trees** (S&P 500 Options, ETFs) · **~100** (CME Futures, Crypto) · **~150** (FX) · **~350** (US Firms) · **still climbing at the 500-tree cap** (US Equities, NASDAQ-100, S&P 500 Eq+Opt). **Make early stopping a tuning outcome, not a fixed prior** — a coarse checkpoint grid retires most trees on early-peaking case studies and is simply inactive where IC keeps rising.

**Ranking configurations by HAC significance rather than raw IC selects the same one on 7 of 9** — the HAC standard error varies little across configurations within a case study, so the two rankings reorder only configurations already statistically indistinguishable.

> **Credible cross-sectional signal does not require a stable top-feature set.** Per-fold feature ranking is far more stable on US Firms than on US Equities **even though US Equities carries the tighter IC.** Don't use feature-ranking instability alone to reject a model.

---

## Transferable rules

1. **Choose the GBM library on operational criteria** — training throughput, inference latency, categorical leakage safety, ecosystem — because post-tuning accuracy differences are noise.
2. **Verify GPU actually helps before assuming it does.** Precision support and dataset scale can make GPU slower than CPU.
3. **Match the objective to where trading occurs.** Rank objectives pay in high-breadth cross-sections where only tails trade; they cost calibration you may need downstream.
4. **Use monotonic constraints as theory-driven regularization,** and verify via constrained-vs-unconstrained SHAP dependence that they cost no IC.
5. **Tune regularization before tree structure.** It has the larger out-of-sample effect in low-SNR regimes.
6. **Cap trial budgets at 50–100.** More trials find validation noise, and that is the most common backtest-to-live failure.
7. **Try multi-objective search even when you only care about one objective** — constraining a second can reach parameter regions single-objective search misses.
8. **Prefer TreeSHAP to native importance for any decision,** and use exact interaction values to detect mechanisms that shift by regime beneath a stable-looking average.
9. **Monitor SHAP drift as a leading indicator,** but confirm with outcome metrics before acting.
10. **Cross-validate explanations across model families.** Equal-accuracy models disagree; agreement across architectures is the stronger evidence.
11. **Discount tabular benchmarks that assume IID splits.** Attention-heavy architectures degrade fastest under exactly the temporal shift finance has.
12. **Audit retrieval-augmented models for temporal isolation** before believing any reported number.
13. **Flexibility extends signal; it does not create it.** Where the linear baseline is flat, expect the interval to stay on zero.
14. **Loss function choice can dominate depth.** On heavy-tailed targets, MAE's refusal to chase extremes is worth more than extra capacity.
15. **Treat early stopping as a tuned outcome** — the optimal tree count varied by 10× across case studies.

---

## Notebooks

`01_ensemble_foundations` (RF vs. three GBMs on firm characteristics) · `02_gbm_comparison` (four libraries, CPU/GPU, light/medium/heavy presets; LambdaMART vs. pointwise MSE; constrained vs. unconstrained SHAP dependence) · `03_dl_vs_gbm` (LightGBM, MLP, TabM, optional TabPFN under walk-forward) · `04_optuna_tuning` (TPE, search-space design, early-stopping integration) · `05_cross_library_hpo` (loss type as a tunable hyperparameter) · `06_optuna_multi_asset` (single- vs. multi-objective, IC/turnover Pareto) · `07_hpo_comparison` (grid vs. Optuna; empirical validation overfitting as budget grows) · `08_shap_analysis` (TreeSHAP, interaction decomposition, drift flagging, SHAP vs. PFI vs. MDI) · `09_xai_limitations` (explanation instability) · `10_shap_nlp_sentiment` (token-level attribution for FinBERT) · `11_conformal_gbm` (split conformal, quantile, CQR, ACI on GBM residuals) · `12_case_study_insights` (three families across nine case studies)

---

## Cross-references

Ch. 7 §7.4 multiple-testing discipline that trial budgets inherit · Ch. 9 regime features that appear as tree split criteria · Ch. 10 text pipelines feeding `10_shap_nlp_sentiment` · Ch. 11 the linear baseline every model here must beat; SHAP framework; conformal methods extended in `11_conformal_gbm` · Ch. 13 sequential models, which add the temporal dimension to this selection framework · Ch. 17 mean-variance construction requiring calibrated forecasts (the LTR caveat) · Ch. 18 transaction costs behind the IC/turnover frontier · Ch. 19 risk monitoring and position-sizing implications of interval widening · Ch. 26 production alert thresholds and automated drift response

---

## Citations

Bergstra et al. (2011), TPE · Breiman (2001), random forests · Chen & Guestrin (2016), XGBoost · Deb et al. (2002), NSGA-II · Erickson et al. (2020), AutoGluon; (2025), TabArena · Friedman (2001), gradient boosting · Gorishniy et al. (2024), TabR; (2025), TabM · Grinsztajn et al. (2025), TabPFN v2.5 · Hollmann et al. (2025), TabPFN · Holzmüller et al. (2024), RealMLP meta-tuned defaults · Ke et al. (2017), LightGBM · Lundberg & Lee (2017); Lundberg et al. (2020), TreeSHAP · O'Donovan & Yu (2024), option transaction costs and straddle labels · Prokhorenkova et al. (2018), CatBoost · Rubachev et al. (2024), TabReD · Ye et al. (2024), TALENT

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 12.*
