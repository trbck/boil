# Ch 11 — The ML Pipeline

**Governs:** the regularized linear baseline every later model must beat, plus the three layers wrapped around it — SHAP attribution, probability calibration, and conformal uncertainty.
**Thesis:** in a 1–3% R² environment, variance dominates MSE. The job of the pipeline is not to find signal but to avoid manufacturing it, and the baseline's main output is knowing *where signal exists at all*.

---

## 1. Why prediction needs different estimators than inference

OLS is BLUE — minimum variance **subject to the constraint of unbiasedness**. It never claims to minimize MSE. Relaxing unbiasedness opens a path to lower total error, and in finance that path is mandatory.

**Three aspects make it acute:**

| Problem | Consequence |
|---|---|
| **High dimensionality relative to n** | OLS unstable as p grows; undefined when p > n |
| **Pervasive multicollinearity** | Momentum overlaps trend; valuation ratios share accounting inputs. OLS assigns arbitrary weights to correlated features, producing **offsetting coefficients that amplify noise** |
| **Low signal-to-noise** | Cross-sectional return regressions typically reach **R² of 1–3% in-sample, lower out-of-sample.** Variance dominates MSE — an unconstrained model fits noise |

> A coefficient can be highly significant yet economically negligible (large n, tiny effect), or insignificant yet genuinely predictive in combination with other features. **Statistical significance is not a feature-selection criterion for prediction.**

**The penalty encodes a prior about signal structure:**

| Penalty | Prior | Behavior |
|---|---|---|
| **Ridge (L2)** | Signal is **diffuse** across many correlated features | Shrinks proportionally; never zeros. Adds λ to every singular value before inversion → **disproportionately shrinks low-variance (poorly identified) directions** while leaving well-identified ones intact |
| **LASSO (L1)** | Signal is **sparse** | Diamond constraint set has corners on the axes → exact zeros, automatic selection |
| **Elastic Net** | Correlated **groups** matter | L2 component pulls correlated features to similar coefficients; L1 then selects whole clusters |

> **LASSO is unstable under correlation.** Among similar indicators it picks one essentially at random and zeros the rest, and which one survives shifts with minor training perturbations. This may not hurt accuracy (the survivor proxies for the group) but it **complicates interpretation and can raise turnover** if the signal depends on which features are active.

### Calibration: what regularization actually buys

> **ETF case study, 21-day labels, n ≈ 394,000, 57 features.** Below α ≈ 100 Ridge is indistinguishable from OLS (IC ≈ 0.028, ICIR ≈ 0.54). Peak **ICIR 1.30 at α ≈ 10⁶ — a 2.4× improvement over OLS**, driven by a **60% rise in mean IC** (0.046 vs. 0.028) *combined with a 33% reduction in IC standard deviation across folds.* Mean IC peaks earlier at α ≈ 3×10⁴ (0.047), but variance keeps shrinking faster, so ICIR improves past that point.
>
> LASSO tells the opposite story on the same data: even α ≈ 0.0001 zeros roughly a quarter of features, and α ≥ 0.01 eliminates virtually all. **With 57 correlated momentum and volatility features the ETF signal is diffusely distributed** — Ridge's uniform shrinkage preserves it, LASSO discards informative features along with noise.

**The transferable reading: most of the ICIR gain comes from variance reduction, not IC improvement.** Optimize for the stability ratio, not the mean.

---

## 2. Standardization and search-space calibration

Regularization penalizes all coefficients equally, but raw coefficients carry units. Without standardization the penalty shrinks large-scale features harder **for reasons of unit choice, not predictive importance.**

- [ ] **Fit scaler on training data only,** recomputed at every walk-forward refit
- [ ] **Winsorize before standardizing** — one extreme observation inflates σ and compresses everything else toward zero. Clip at 1st/99th percentiles computed from training data.

> Both errors are **silent**. No exception is raised; the model simply benefits from information unavailable at prediction time.

### The search-range trap

Penalty scale depends on the estimator's loss convention. `sklearn.Ridge` uses an **unnormalized sum-of-squares** objective, so effective alphas scale with sample size; `sklearn.ElasticNet` **averages** the loss, absorbing a factor of n. **Comparable penalties differ by roughly that factor between the two conventions.**

> **Concrete failure:** on the ETF case study with ~400,000 observations, a Ridge search stopping at α = 10² explores only the near-OLS region and would **falsely conclude that regularization has little effect.** The correct sweep spans 10⁻² to 10⁸ — covering both the under-regularized plateau and the strongly regularized regime.

### Nested CV is not optional when signal is weak

> **The single most important number in this chapter.** On the same splits, **single-loop CV reports mean IC = +0.028; nested CV returns −0.032.** Selection bias is large enough to **flip the reported sign.** Fold-level standard deviation across the alpha grid runs 0.04–0.10 and dwarfs the cross-fold mean, flagging the landscape as noise-dominated.

**Diagnostic before trusting any tuned configuration:** examine the full distribution of validation ICs, the stability of trial rankings across folds, and the uncertainty around the selected trial. A best trial that materially exceeds the rest but owes its advantage to **one fold, regime, or seed** is a warning sign.

**Always report:** number of trials · search space · selected hyperparameters · **fold-level dispersion of the selected configuration.**

---

## 3. Loss function and evaluation

| Loss | Estimand | Use when |
|---|---|---|
| **MSE** | Conditional mean | Default; but forces the model to accommodate extremes that may be idiosyncratic |
| **MAE** | Conditional **median** | A few large moves dominate — outliers shift the median far less |
| **Huber** | Robust location | Quadratic below threshold, linear above — MSE efficiency for typical observations, bounded outlier influence |
| **Quantile** | Specified percentile | **Changes the estimand entirely.** Foundation for conformalized intervals |

> **The quantile argument is the important one.** If a long-short strategy trades only the top and bottom deciles, **the conditional mean is the wrong target** — most of the model's capacity is spent distinguishing among assets that will never be traded.

**Evaluation metrics, keyed to how predictions become trades:**

- **IC / ICIR** — primary for cross-sectional ranked signals
- **RMSE / MAE** — relative comparison only; **neither has a standalone "good" threshold.** The benchmark is always a naive model (e.g. predicting the cross-sectional mean)
- **Turnover** — no statistical metric measures tradability. **Report it alongside every metric.**
- **Quantile/decile spreads** — IC measures *global* ranking quality; strategies trading only the extremes must verify separation in the traded tails specifically

### Sample weighting

Two schemes from Ch. 7 apply directly and **compose multiplicatively**:

- **Uniqueness weighting** (average inverse concurrency) — corrects overlapping-label dependence that violates the independence assumption implicit in sum-of-squared-errors
- **Recency weighting** (exponential decay) — adapts to regime evolution; decay rate sets the effective lookback

> **Report effective sample size alongside performance.** A small n_eff relative to nominal signals that a few observations dominate the fit. This risk is **acute when minority-class observations cluster in crisis periods** — verify the reweighted training set spans multiple market conditions rather than concentrating on one regime.

> **Training loss ≠ trading objective.** A model can reduce MSE while degrading PnL if the improvement comes from fitting the middle of the cross-section (never traded) or from raising turnover. Maintain strict separation between model selection (validation loss and rank metrics) and strategy evaluation (turnover- and cost-adjusted returns).

---

## 4. Classification

**Choose based on the signal-to-trade mapping, not on preference.** Threshold or quantile rule → classification directly optimizes the decision that matters. Position size proportional to predicted return → regression preserves magnitude information that classification discards.

> Classification is not universally safer. A model that predicts direction correctly 55% of the time but **systematically misses large moves** may underperform a regression model that captures magnitude in the tails.

**Regularization is more critical here than in regression:** the maximum-likelihood objective **diverges when classes are near-separable.** In high dimensions a separating hyperplane almost always exists, driving coefficients toward infinity and producing arbitrarily confident predictions that fail out of sample. OLS has no analogous failure — it has a closed form whenever XᵀX is invertible.

### Probability calibration

Two forces distort the correspondence between predicted probability and realized frequency:

| Force | Character |
|---|---|
| **Regularization** | **Predictable and directional** — shrinkage flattens the sigmoid, pulling extremes toward 0.5. The model becomes systematically **under**confident |
| **Misspecification** | Unpredictable — depends on the specific form of the misspecification |

| Correction | Handles | Cost |
|---|---|---|
| **Platt scaling** | Systematic compression from regularization | Cheap; fits a logistic to raw outputs |
| **Isotonic regression** | More complex non-monotone miscalibration | Needs more data to estimate reliably |

Both must use data not used for training — the validation fold serves this.

**Diagnostic:** bin by predicted probability, compute accuracy per bin. Monotonically increasing hit rates as probability moves away from 0.5 = well calibrated. **Non-monotonic patterns — high-confidence predictions performing worse than moderate-confidence ones — indicate overfitting or misspecification.**

> **Check whether you need calibration before paying for it.** For threshold- and rank-based signal generation only the *ordering* matters. Calibration is essential only when position size depends on probability *levels*.

### Probability → position

| Method | Mechanics | Calibration sensitivity |
|---|---|---|
| **Threshold** | Long if p > 0.55, short if p < 0.45, else flat. Asymmetric thresholds accommodate asymmetric long/short costs | Moderate |
| **Probability-weighted** | Size ∝ distance from 0.5 | **High** — if the model is systematically underconfident (as regularization makes it), positions are systematically undersized |
| **Rank-based** | Long top decile, short bottom decile within cross-section | **None** — depends only on ordering; robust to miscalibration, and fixes position count regardless of the probability distribution |

Thresholds and quantile cutoffs must be **recomputed within each training window.**

### Classification metrics

> **AUC calibration anchor for finance:** 0.5 is random; **0.55–0.60 represents meaningful predictive power** given the signal-to-noise ratio. **Values above 0.65 on out-of-sample financial data warrant scrutiny** — likely data leakage or an evaluation window aligned with a strong trend.

Precision guards against wasted trades; recall against missed opportunities. **High transaction costs favor precision; capacity constraints favor recall.** F1 weights them equally, which rarely matches the economics.

Log-loss and Brier score matter only when the mapping uses probability *levels* rather than ranks.

---

## 5. SHAP as a validation diagnostic

Coefficient magnitudes are a tempting shortcut but **shrinkage entangles importance with penalty strength**, and correlated features split or steal credit depending on the penalty type.

Shapley values are the unique allocation satisfying efficiency (attributions sum to prediction minus baseline), symmetry, null player, and linearity. **LinearSHAP** is exact and O(p) per observation — the right choice for this chapter; TreeSHAP and KernelSHAP extend to later ones.

### The four-layer economic narrative protocol

1. **Sign consistency** — does each contribution have the expected sign? A model that learned the opposite of every documented factor relationship is almost certainly fitting noise
2. **Magnitude plausibility** — does one feature imply a 5% monthly contribution where median monthly returns are 0.8%? Then it's extrapolating
3. **Stability across folds** — compute per fold, track whether the same features stay top-five with consistent signs and stable magnitudes. **The SHAP stability chart is among the most informative validation diagnostics available**
4. **Regime-conditional** — partition by volatility tercile and recompute. A model shifting from momentum to mean reversion across regimes may be sensible, **but only if regime identification is itself robust**

> **Refinement worth the effort:** fold-to-fold variation in SHAP rankings conflates temporal regime shifts (interesting) with finite-sample estimation noise (uninteresting). **Bootstrap SHAP values within a single fold** to get confidence intervals that separate the two.

### Concentration risk and the right-vs-wrong decomposition

> **Flag predictions where a single feature accounts for more than a threshold share of the total** as an automated trigger for manual review or size reduction. The worked example is stark: a correct high-conviction call spreads attribution across ten features; an incorrect one has a single volume-ratio feature contributing +0.018 against a **realized return of −11.7%.** Concentrated attribution is fragility.

**Complementary diagnostic:** compare SHAP profiles for high-conviction predictions that were directionally *correct* vs. *incorrect*. Features the model leaned on heavily when wrong are candidates for re-engineering or nonlinear modeling. **This targets the predictions that matter most for PnL.**

### Limitations

> **SHAP is descriptive attribution, not causal evidence.** A high SHAP value means the feature contributed to *this model's* prediction — not that it caused the return. It could equally reflect correlation with an omitted predictor or a pipeline confound. Shapley explanations mislead specifically when features are correlated or when read causally.

Standard SHAP marginalizes absent features **independently**, creating impossible feature combinations under correlation. Manageable for linear models; for nonlinear ones, conditional SHAP requires estimating conditional distributions. Permutation importance inflates scores for correlated features; LIME attributions need not sum to the prediction.

---

## 6. Conformal prediction

Classical Gaussian intervals assume approximately normal, homoskedastic errors. Returns exhibit heavy tails, volatility clustering, nonlinear residual dispersion, and regime dependence — **uncertainty is rarely constant across assets, horizons, or market states.**

Conformal prediction is a **model-agnostic calibration layer**: fit the base model, evaluate forecast errors on a held-out calibration set, use the empirical error distribution to build intervals. No normality, homoskedasticity, or correct likelihood required.

### The exchangeability caveat — read this before trusting the guarantee

Under exchangeability, conformal delivers **finite-sample marginal coverage**, distribution-free, independent of base-model correctness.

> **Financial time series are not exchangeable.** Order matters — autocorrelation, volatility clustering, changing liquidity, structural breaks. The rank argument behind the guarantee no longer applies exactly, and yesterday's calibration residuals may not represent tomorrow's errors.
>
> **The guarantee is also marginal, not conditional.** 90% coverage on average does *not* mean 90% within every asset, fold, volatility regime, or predicted-return bucket. In finance, treat conformal intervals as **empirically calibrated estimates whose coverage must be monitored, stress-tested, and adapted** — not as a theorem you can cite.

### Three variants

| Method | Mechanics | Interval width | Trade-off |
|---|---|---|---|
| **Split conformal** | Partition into proper-training + calibration; nonconformity score = absolute residual; take the conservative order statistic ⌈(n+1)(1−α)⌉ | **Fixed** for every observation | Simple, auditable, robust to base-model misspecification. **Cannot vary width across regimes** — a volatility-spike forecast gets the same correction as a quiet one |
| **CQR** | Train lower/upper conditional quantile models, calibrate the band with the same conformal correction | **Adaptive** — widens where conditional dispersion is higher | Usually more informative under heterogeneous dispersion. **Depends on quantile-model quality** — unstable estimates or small calibration samples favor the alternatives |
| **ACI** | Online update of effective miscoverage: a miss lowers α (widening the next interval); coverage raises it (narrowing) | Adaptive over **time** | Long-run coverage control under nonstationarity. **Weaker guarantee** — average empirical coverage over time, not per-point or per-subgroup |

**If n_calibration < 1/α − 1, the calibration set is too small to give a finite conformal quantile at the target level.**

**ACI tuning:** the learning rate controls speed vs. stability — larger adapts faster after misses but makes widths oscillate; smaller is smoother but slow to abrupt volatility changes. **Clip the adaptive miscoverage level to a bounded range to avoid degenerate intervals.**

### Adaptations for nonexchangeability

- **Rolling calibration windows** (e.g. most recent 250 trading days) — more responsive to current conditions, at the cost of higher estimation noise
- **Weighted calibration** — exponential time decay as a practical heuristic
- **Regime-conditional calibration** — partition scores by pre-specified states (realized-vol quantiles, VIX terciles, liquidity buckets). **Partition must be defined ex ante**, and each regime needs enough observations for a stable quantile
- **Online coverage feedback** — the ACI mechanism

### Empirical comparison

> **ETF case study: 99 ETFs, 2006–2025, eight walk-forward folds spanning 2015–2023, 80/20 proper-training/calibration split within each fold, Ridge base model, 90% target.**

| Method | Marginal coverage | Mean width | Width σ |
|---|---|---|---|
| Split conformal | **88.4%** | 16.9% | **3.3** |
| **CQR** | **89.9%** | **15.7%** | 7.5 |
| ACI on split-conformal base | 89.5% | 16.3% | 6.8 |

**CQR comes closest to target and produces the narrowest average interval** while allowing width to vary. Split conformal undercovers with low width dispersion (every observation in a fold gets the same correction). ACI improves on the static baseline but still lands slightly below target here.

> **Don't attribute undercoverage to exchangeability violations reflexively.** It can equally arise from calibration leakage, an overly small calibration window, unstable quantile estimates, an inappropriate score definition, or interpolated-quantile implementation choices. **Inspect coverage by fold, regime, and asset group before changing method.**

**Four warning signs:**

- Coverage below 80% during volatility spikes at a 90% target → calibration distribution is stale or poorly stratified
- Monotonically deteriorating coverage across the backtest → drift the scheme isn't tracking
- **Asymmetric violations** (many more outcomes above than below, or vice versa) → directional bias or residual skewness. **Symmetric split conformal can widen intervals but cannot recenter a biased forecast**
- Coverage reported as a single pooled number → use fold-level dispersion, block-bootstrap CIs, or cluster-robust errors; 89.9% may be indistinguishable from target while 88.4% may or may not be material

### Conformal classification

Produces a **prediction set** rather than a forced label. For three-class direction labels, a singleton {long} conveys more confidence than {long, neutral}; a set containing all classes means the classifier cannot distinguish alternatives at the target coverage.

**Conservative rule: trade only singleton sets, abstain otherwise.**

> **But the guarantee doesn't transfer to the traded subset.** Conformal coverage applies over *all* evaluated observations, not automatically to the observations you selected for trading. Report coverage, hit rate, abstention rate, turnover, and realized performance **separately for singleton and non-singleton cases.**

> Conformal calibrates *set coverage*, not the probability estimates. Poorly calibrated probabilities can still yield valid sets — they just produce **inefficiently large** ones. Probability calibration and conformal set calibration are related diagnostics, not the same object.

### Uncertainty → position size

Scale position inversely with calibrated interval width: a name with a 50 bp interval receives **twice** the uncertainty-adjusted weight of one with a 100 bp interval, before volatility, correlation, turnover, and portfolio constraints.

---

## 7. Cross-case-study evidence — the most important table in the book so far

One pipeline, unchanged, across nine case studies. Average daily IC vs. realized return, HAC (Newey–West) corrected.

| Case study | Horizon | IC | t | 95% CI | n |
|---|---|---|---|---|---|
| **ETFs** | 21 days | **+0.054** | 2.4 | [+0.009, +0.098] | 2,016 |
| **US Equities** | 1 day | **+0.016** | **9.1** | [+0.012, +0.019] | 4,018 |
| **NASDAQ-100** | 15 min | **+0.005** | 4.3 | [+0.003, +0.007] | 64,580 |
| Crypto | 8 hours | +0.009 | 1.4 | [−0.003, +0.020] | 1,956 |
| S&P 500 Options | ~30 days | +0.007 | 0.6 | [−0.015, +0.029] | 502 |
| FX | 1 day | +0.005 | 0.6 | [−0.012, +0.022] | 2,064 |
| CME Futures | 5 days | −0.000 | −0.0 | [−0.034, +0.034] | 1,290 |
| S&P 500 Eq+Opt | 5 days | −0.006 | −0.4 | [−0.033, +0.022] | 502 |
| US Firms | 1 month | −0.005 | −0.6 | [−0.022, +0.011] | 120 |

> **Three of nine clear zero. Reliable cross-sectional ranking from a linear model on engineered features is the exception, not the rule — before any trading friction enters.** Calibrate your expectations to this before starting a new research line.

> **And read the significance carefully: NASDAQ-100 reaches significance on the smallest IC of the three because its intraday history is enormous (n = 64,580). Sample size, not effect size, is doing much of the work.** A small but significant IC is not a strong signal. Both statistical and economic significance matter.

**Ridge wins wherever there is measurable signal** — the features (momentum at several horizons, volatility at several scales, cross-sectional ranks) are correlated by construction, so a penalty that keeps and shrinks them all discards less than one that zeros some out. **The gain from regularizing at all, relative to unpenalized, is small.** Regularization buys numerical stability; it does not manufacture signal the features don't carry.

**Persistence check:** a positive average IC can come from a few good stretches. Use a **three-month rolling average of daily IC.** The ETF signal holds above zero with sharp but temporary drawdowns; the FX signal crosses zero repeatedly with no persistent sign — which is *why* its interval includes zero.

> **The mirror-image check matters too.** Across folds the models keep coefficient signs in the vast majority of cases even where IC overlaps zero. **The fits are stable; the flat case studies lack ranking content in the features, not a settled model.** Don't diagnose a near-zero IC as instability without checking sign consistency.

**Horizon effects:** ETFs, US equities, and S&P 500 Eq+Opt show IC *rising* with horizon as day-to-day noise averages out. NASDAQ-100 is **flat across 5, 15, and 60 minutes**; Crypto is flat across 8- and 24-hour labels, consistent with a funding-rate signal that doesn't decay within a day. **Match the horizon to where the information lives.**

### Direction vs. magnitude are different problems

| Case study | Horizon | Native AUC | Cross-IC (t) | Cross-AUC (regression) |
|---|---|---|---|---|
| Crypto | 8 hours | 0.509 [0.498, 0.521] | **+0.033 (5.3)** | 0.498 |
| US Firms | 1 month | **0.539 [0.528, 0.550]** | **+0.074 (6.8)** | 0.494 |
| S&P 500 Eq+Opt | 5 days | 0.510 | overlaps zero | 0.496 |
| S&P 500 Eq+Opt | 10 days | 0.507 | overlaps zero | 0.523 |

> **The two targets do not track each other.** On Crypto and US Firms the *classifier's* score ranks continuous returns well, yet only US Firms separates direction from chance. Run it the other way and the regression score barely moves AUC off 0.5 even where it ranks returns successfully. **Choosing which target to predict is a modeling decision, not a formality** — and note that US Firms, which showed a *negative* regression IC in the main table, is the one case where the classifier works.

### IC does not equal profitability

> **A simple 126-day momentum signal carries a lower IC than Ridge on the ETF case study, yet matches or beats it on net Sharpe — because the Ridge portfolio trades far more to act on its scores.** Every IC improvement must be read against the turnover it costs.

---

## Transferable rules

1. **Unbiasedness is not a goal for prediction.** Trading bias for variance lowers MSE when p is large relative to n and signal-to-noise is low.
2. **Match the penalty to the signal's structure.** Diffuse and correlated → Ridge. Genuinely sparse → LASSO. Correlated clusters → Elastic Net.
3. **Optimize the stability ratio, not the mean.** Most of the achievable gain comes from variance reduction across folds.
4. **Calibrate the hyperparameter search range to the estimator's loss convention and sample size,** or you will search only the near-OLS region and conclude regularization does nothing.
5. **Use nested walk-forward whenever signal is weak.** Single-loop selection bias can flip the reported sign.
6. **Report trial count, search space, selected configuration, and fold-level dispersion** with every tuned result.
7. **Winsorize before standardizing, and fit both on training data only.** Both errors fail silently.
8. **Report turnover alongside every statistical metric.** No statistical metric measures tradability.
9. **Report effective sample size whenever weights are applied,** and verify the reweighted set spans multiple regimes.
10. **Choose regression vs. classification from the score-to-position mapping,** not from preference — they encode different information.
11. **Calibrate probabilities only if position size depends on probability levels.** Rank-based mappings don't need it.
12. **Treat AUC above 0.65 out-of-sample as a leakage alarm,** not a success.
13. **Use SHAP for descriptive attribution, never causal claims,** and bootstrap within fold to separate regime shift from estimation noise.
14. **Flag single-feature-dominated predictions** for review or size reduction — concentrated attribution is fragility.
15. **Conformal coverage in finance is empirical, not guaranteed.** Monitor by fold, regime, magnitude bucket, and asset characteristic; a marginal number hides the failures that matter.
16. **Diagnose undercoverage before switching methods** — leakage, window size, and score definition are more common causes than exchangeability.
17. **A significant IC on a huge sample is not a strong signal.** Separate statistical from economic significance every time.
18. **Check sign stability before concluding a flat IC means an unstable model.** Usually the features simply carry no ranking content.
19. **Every later model must beat this baseline.** A gradient-boosting model that underperforms Ridge has added complexity without adding predictive power.

---

## Notebooks

| Notebook | Covers |
|---|---|
| `01_ols_inference` | OLS summaries, Gauss–Markov diagnostic battery, VIFs, robust standard errors |
| `02_regularization_paths` | Ridge/LASSO/EN coefficient paths, loss-function comparison at best alpha, recency weighting with n_eff, rank-stability across consecutive windows |
| `03_logistic_classification` | Walk-forward logistic pipeline, L1/L2 sweeps, calibration curves, all three probability→position mappings on one fold, balanced class weights |
| `04_nested_cv_hpo` | Alpha sweep 10⁻²–10⁸, single-loop vs. nested CV, selection-bias quantification |
| `05_shap_analysis` | LinearSHAP end-to-end, beeswarm summaries, waterfall decompositions, right-vs-wrong comparison, SHAP stability chart |
| `06_conformal_prediction` | Split conformal, ACI online update and α trajectory, CQR, full calibration comparison and conditional coverage diagnostics |
| `07_case_study_insights` | The nine-case-study IC evidence, rolling IC persistence, horizon effects, direction-vs-magnitude comparison |
| `08_ml_backtest_intro` | The IC-to-profitability gap: 126-day momentum vs. Ridge on net Sharpe |
| `06_linear` (per case study) | Elastic Net grid search across l1_ratio and alpha |

---

## Cross-references

Ch. 6 §6.5 walk-forward and nested protocols this pipeline instantiates; §6.4 three metric layers · Ch. 7 §7.2 uniqueness and recency weighting; §7.3 IC/ICIR and quantile diagnostics; §7.4 selection-bias accounting that nested CV operationalizes · Ch. 8 the engineered features evaluated here · Ch. 9 regime labels used for regime-conditional SHAP and conformal calibration · Ch. 12 Optuna pruning, multi-objective tuning, TreeSHAP · Ch. 13 KernelSHAP and deep-learning uncertainty · Ch. 14 latent-factor models, including joint multi-horizon training · Ch. 16–19 turning rankings into returns: simulation, portfolio construction, cost modeling, risk · Ch. 17 uncertainty-scaled allocation in a full framework · Ch. 25 online learning and incremental updates for high-frequency deployment

---

## Citations

Aas et al. (2021), conditional SHAP · Akiba et al. (2019), Optuna · Breiman (2001), two cultures · Cawley & Talbot (2010), selection bias in model comparison · Gibbs & Candès (2021, 2023), adaptive conformal inference · Hastie, Tibshirani & Friedman (2009) · Huber (1964) · Kumar et al. (2020), limits of Shapley explanations · Lei et al. (2018), distribution-free predictive inference · Lundberg & Lee (2017), SHAP · Niculescu-Mizil & Caruana (2005), probability calibration · O'Donovan & Yu (2024), hold-to-maturity straddle construction · Papadopoulos et al. (2002), inductive conformal prediction · Romano, Patterson & Candès (2019), CQR · Shapley (1953) · Simonian (2024) · Tibshirani (1996), LASSO · Zou & Hastie (2005), elastic net

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 11.*
