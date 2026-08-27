# Ch 13 — Deep Learning for Time Series

**Governs:** whether the sequence history adds ranking content beyond lag-feature engineering, and which architecture family to reach for if it does.
**Thesis:** architecture matters only after the target is defined correctly. In a horizon-label ranking setting, deep sequence models credibly beat the best tabular baseline on **one of eight** case studies — and the formulation choice (direct regression vs. path forecasting) explains more of the variance than the architecture choice.

*Thin file by design — standard architecture mechanics omitted. Kept: the formulation taxonomy, the benchmark-skepticism results, the finance transfer gap, and the case evidence.*

---

## 1. The formulation taxonomy — the most consequential choice

| Formulation | Mechanics | Failure mode |
|---|---|---|
| **Recursive one-step** | Predict *t+1*, append, repeat to *t+h* | **Errors compound across the horizon** |
| **Direct multi-horizon path** | Predict the full path in one pass | No recursive propagation, but must learn the joint structure of all intermediate steps |
| **Direct horizon-label** | Skip the path entirely; predict the 5-day return, direction, or cross-sectional rank | **The dominant formulation in Ch. 11–14** |
| *(Direct allocation — Ch. 17)* | Output positions/weights, train on Sharpe, drawdown, or cost-adjusted return | A different problem again |

> **For cross-sectional ranking, direct horizon-label prediction is usually correct** for two reasons: it matches the evaluation metric (Spearman IC on the final label, not the intermediate path), and it avoids compounding errors over the horizon.

> **The controlled test, with numbers.** Run as a multi-step forecaster through Darts, TSMixer reaches IC **+0.029** on ETFs at 21 days — real signal, but below both direct-regression NLinear and Ridge on the same data. To remove compounding from the comparison, US Equities was **resampled to weekly non-overlapping returns** so the five-day horizon becomes a *single* step:
>
> | Model | Approach | Mean IC (4 folds) |
> |---|---|---|
> | NLinear | Direct regression | **+0.018** |
> | LSTM | Direct regression | +0.006 |
> | N-BEATS (Darts) | One-step forecasting | **−0.013** |
>
> **Matching data frequency to horizon removes one source of error but does not salvage the forecasting objective.** Direct regression still ranks better, and both trail the daily tabular baselines (GBM at +0.032 on the primary one-day label).

**Library choice implies a modeling choice.** Darts and NeuralForecast are built around per-series path forecasting; for cross-sectional panel prediction evaluated on Spearman IC, raw PyTorch with custom training loops is the natural fit. Running N-BEATS and TSMixer through Darts' forecasting formulation produced substantially weaker signal than direct regression adaptations on the same data.

---

## 2. Why LSTMs lost, and what replaced them

Two limitations, only one of which is about compute:

- **Sequential bottleneck** — hidden state at *t* depends on *t−1*, limiting temporal parallelism versus attention. Prohibitive for high-frequency data with tens of thousands of observations.
- **Gradient flow** — gating mitigates but doesn't eliminate vanishing gradients. **Long nominal lookbacks do not guarantee the model uses distant information; they often just add noise, training instability, and hyperparameter sensitivity.** For weak, non-stationary financial series that distinction matters more than theoretical capacity.

> **Calibration for what recurrence buys on a noisy target.** Pooled 60-day ETF return windows predicting next-day return: the LSTM trains **~2× slower than a comparable MLP (32s vs. 17s) and ranks no better — both post cross-sectional IC near zero.** The GRU cuts parameters ~25% and trains slightly faster, and its IC is also near zero. **A lighter recurrent cell does not solve the return-prediction problem.**

---

## 3. The LTSF-Linear critique — and how to read it

Zeng et al. (2022) showed one-layer linear models outperforming Transformer architectures across all nine LTSF benchmarks, with **20–50% improvements over Informer, Autoformer, and FEDformer.**

**The three baselines worth keeping in your ladder:**

| Model | Mechanism |
|---|---|
| **Linear** | Lookback → horizon via a single matrix multiply |
| **D-Linear** | Moving-average decomposition into trend/seasonal, separate linear layers, sum |
| **N-Linear** | **Subtract the last input value before the linear layer, add it back after** — stabilizes under distribution shift |

> **The diagnostic that made the case, not the headline numbers.** Shuffling input sequences to destroy all temporal structure: **D-Linear's MSE more than quadrupled (0.345 → 1.406) while the Transformer's barely moved (0.379 → 0.391).** D-Linear exploits temporal structure and collapses without it; the Transformer relied primarily on channel correlations, so removing the time axis cost it almost nothing. **Attention was not learning temporal patterns.** A second failure mode: forecasting error *increased* for most Transformers as the lookback grew — they were confused by added noise rather than extracting signal.

**Read it as a reset, not an indictment.** Counterpoints that matter: the study was univariate (Transformers may do better with rich covariates and cross-series structure) · careful tuning can let attention match or exceed linear baselines, indicating sensitivity to training budget · **small experimental changes — hyperparameter budgets, splits, metric choice — can flip model rankings on standard LTSF suites.** The real problem extends beyond "Transformers vs. Linear" to **the fragility of benchmark conclusions themselves.**

> Where Transformers do succeed on these benchmarks, **tokenization and normalization choices matter more than the attention mechanism.** Performance is largely driven by intra-variate dependencies and dataset stationarity. The honest comparison is "strong linear baselines vs. time-series-aware tokenization with careful tuning," and the latter's advantage is conditional on problem characteristics.

---

## 4. Modern variants — matched to problem shape

| Model | Key innovation | Attention over | Best for |
|---|---|---|---|
| Vanilla Transformer | Self-attention | Time steps | Short sequences, baseline only |
| **TFT** | Variable selection + covariate typing | Time steps | **Covariate-rich, multi-horizon, native quantile output** |
| **PatchTST** | Patching + **channel independence** | Time patches | Long-horizon LTSF |
| **iTransformer** | **Variate-as-token inversion** | Variables | **Cross-asset dynamics, portfolio forecasting** |

**PatchTST's counterintuitive choice:** it *ignores* cross-channel dependencies, processing each series independently through shared weights. **Channel independence acts as a regularizer** — cross-channel attention frequently overfits to spurious training correlations that don't generalize. It pairs this with RevIN (instance normalization, reversed on output) to neutralize local distribution shifts before attention sees the data.

**iTransformer's inversion sidesteps the temporal-order critique entirely:** attention never operates on time steps. Temporal patterns within each variable are captured by the embedding (which can be any time-aware architecture); attention models **cross-variable dependencies, where permutation invariance is far less problematic** because variables have no intrinsic ordering.

**TFT is the right choice only in covariate-rich settings** with static metadata, time-varying observed inputs, and known-future inputs. For pure time series without covariates, PatchTST's simpler design typically matches or exceeds it. Note the emerging counterpoint: **reframing forecasting as tabular regression with temporal features achieves competitive covariate-aware performance without any time-series-specific architecture** — which routes back to Ch. 11–12.

> **Patching introduces a leakage channel.** If normalization statistics are computed across the full window rather than causally, the patch encodes future information. Normalize each patch independently or use only backward-looking statistics.

**State space models (Mamba):** selective, input-dependent SSM coefficients make the recurrence content-aware, at linear complexity. **Reach for SSMs above ~10,000 time steps** (tick or minute bars spanning weeks) where quadratic attention exhausts memory. **For shorter sequences with rich cross-variate structure, attention retains the edge** because cross-variable attention captures portfolio dynamics SSMs don't natively model. Treat SSMs as a sequence-mixing primitive, not an attention replacement; the finance-specific work (FinMamba) is a single-paper result awaiting replication.

---

## 5. Foundation models — the finance transfer gap

**Four adaptation modes, in ascending cost:** zero-shot inference · in-context learning (feed related series and covariates in the context window; no weight updates) · PEFT/LoRA · full domain-specific training.

> **Treat foundation models as initializations, not solutions.** Match the adaptation mode to compute budget, data availability, and deployment constraints — not to the model's marketing.

### The evidence on returns is bad and specific

> **Large-scale evaluation across 94 countries over 34 years.** US zero-shot, 512-day window: **Chronos Large reaches out-of-sample R² of −1.37%, TimesFM 500M −2.80%, while CatBoost achieves −0.03%.** Directional accuracy sits at the noise floor for everything — Chronos just above 51%, TimesFM just below 50%, **CatBoost 51.16%.** Even the tree ensembles barely clear random.
>
> **But pretraining on financial data changes the picture materially:** annualized returns and Sharpe of **36.84% / 5.42** for Chronos small and **30.36% / 3.66** for TimesFM 20M at the same window. **Domain-specific adaptation is required, not optional.**

> **Smaller-scale confirmation on ETFs:** zero-shot Chronos posts IC **−0.015** and TTM **−0.017** — both worse than random — while a task-specific LSTM (50K parameters) reaches **+0.025** and Ridge (**60 parameters**) reaches **+0.022.** Chronos carries ~20M parameters. Parameter count is not the operative variable.

**Root cause:** general time-series corpora emphasize seasonality, trend, and clear patterns that are **largely absent in financial returns.** Heavy tails, low SNR, and non-stationarity differ fundamentally from the electricity, weather, and traffic data dominating pretraining.

**Where TSFMs are credible: risk forecasting.** Volatility and VaR targets exhibit stronger, more transferable structure (clustering, persistence, mean reversion), and fine-tuned foundation models rank among top performers across VaR quantiles under Diebold–Mariano and Giacomini–White tests. **Zero-shot is still insufficient even here** — incremental fine-tuning is essential. Prefer Student-t or mixture output distributions for financial data.

> **Pretraining corpora are a new leakage channel.** Standard temporal train/test splits are **necessary but not sufficient.** If the TSFM was pretrained on data overlapping or correlated with the evaluation period, zero-shot claims are compromised. Verify evaluation data postdate the pretraining corpus or are excluded from it, and check for proxy leakage via correlated series.

> **Scaling laws do not hold for time series.** Hybrid architectures with **under 3 million parameters** achieve competitive zero-shot performance matching dense models with **1.5 billion.** Report active parameter counts, wall-clock inference, and memory footprint alongside predictive metrics; the right frame is the **accuracy-efficiency Pareto frontier, not raw parameter count.**

---

## 6. Selection framework

### Baseline ladder — each rung must be cleared before adding complexity

1. **Seasonal naive** (irrelevant for returns — no seasonal pattern)
2. **LTSF-Linear (D-Linear / N-Linear)** — *if a sophisticated model cannot beat D-Linear, its complexity is unjustified*
3. **Statistical** — ARIMA/ETS univariate, VAR multivariate
4. **Gradient boosting with lag features, rolling statistics, calendar features** — often matches neural approaches, especially with limited data. Note GBMs **cannot extrapolate beyond the training range**
5. **TabM** — useful additional baseline on cross-sectional panels without strong sequential structure

**Sample-size thresholds** (calibrated on daily-frequency, moderate-SNR data — adjust for signal strength and feature dimensionality):

| Samples | Choice |
|---|---|
| < 5,000 | Ridge or LightGBM — DL overfits |
| 5,000–20,000 | LightGBM best accuracy-to-compute; DL may match, rarely exceeds |
| > 20,000 | DL testable at scale, **but a large sample should trigger model comparison, not model replacement** |

### Selection matrix

| Scenario | Primary | Alternative | Baseline |
|---|---|---|---|
| Univariate, interpretability required | N-BEATS-I | Autoformer | Seasonal ARIMA |
| Univariate, black-box fine | PatchTST | N-BEATS generic | D-Linear |
| Multivariate, **known** graph structure | GNN (Ch. 23) | — | VAR |
| Multivariate, unknown correlations | PatchTST | iTransformer | D-Linear |
| High dimensionality (>50 series) | **iTransformer** | PatchTST | Linear |
| Covariate-rich, multi-horizon | **TFT** | PatchTST | LightGBM |
| Sequences > 10K steps | **Mamba** | TCN | Rolling stats + GBM |
| Limited data, need robustness | ARIMA/LightGBM | N-Linear | Seasonal naive |
| Zero adaptation budget | D-Linear | Zero-shot TSFM | Seasonal naive |
| Moderate budget (PEFT) | PatchTST + LoRA | TSFM ensemble | LightGBM |

> **Post-hoc attribution methods (SHAP, LIME) typically ignore sequential dependencies among inputs**, making them unreliable for attributing importance in recurrent or attention architectures. N-BEATS-I gives trend/seasonal decomposition, TFT gives learned variable importance; standard Transformers are black boxes.

> **N-BEATS-I should be benchmarked against N-BEATS-G before committing.** The interpretable configuration underperforms the generic one when the process doesn't decompose cleanly into polynomial trend and Fourier seasonality — **common in financial data, where regime changes violate both assumptions.**

---

## 7. Uncertainty

**MC dropout** keeps dropout active at inference over 50–100 forward passes, sampling a different subnetwork each time. **Deep ensembles** train 3–10 independent models with different initializations. Both yield a mean (often more accurate, since idiosyncratic errors partly cancel) and a spread (the uncertainty signal).

| | MC dropout | Deep ensembles |
|---|---|---|
| Cost | Cheap; minimal architectural change | Training and inference scale ~linearly with members |
| Quality | Weaker | Often more robust, better calibrated |

**~5 members is a reasonable compromise.**

> **The number that should change your defaults.** Without calibration, Gaussian intervals from either method are **under-covered by roughly an order of magnitude at the 95% nominal level.** After split-conformal post-processing, empirical coverage lands within ~3 percentage points of nominal at the 50, 80, and 95% levels for both. **The calibration step recovers interval validity without retraining the base model.** Ensemble disagreement also tracks realized error better than dropout-subnetwork variance — that ordering survives reruns even though magnitudes drift.

**The test that matters for trading:** do forecasts flagged as more uncertain actually produce larger out-of-sample errors, and does the interval target achieve its intended coverage? Not nominal coverage accepted at face value.

> For foundation models under regime shift, **nominal intervals may be too narrow exactly when risk control matters most.** For VaR and Expected Shortfall, calibration is not secondary to point accuracy — a TSFM may predict the conditional mean reasonably while **understating tail risk.**

---

## 8. Case study evidence

Eight of nine case studies (all but US Firms), primary regression labels, HAC 95% CIs.

| Case study | Horizon | Best deep | Deep IC (t) | Best tabular | Tabular IC | Δ IC |
|---|---|---|---|---|---|---|
| **ETFs** | 21 days | NLinear | **+0.062 (3.0)** | Ridge | +0.054 | +0.009 |
| **Crypto** | 8 hours | NLinear | **+0.029 (4.6)** | GBM | +0.011 | **+0.018** |
| S&P 500 Options | to expiry | PatchTST | +0.013 (1.8) | GBM | +0.018 | −0.005 |
| FX | 1 day | NLinear | +0.011 (1.3) | TabM | +0.007 | +0.004 |
| S&P 500 Eq+Opt | 5 days | PatchTST | +0.011 (1.1) | TabM | +0.011 | ≈ 0 |
| **US Equities** | 1 day | LSTM | **+0.007 (5.4)** | GBM | +0.032 | **−0.025** |
| **NASDAQ-100** | 15 min | NLinear | **+0.005 (2.3)** | GBM | +0.006 | −0.001 |
| CME Futures | 5 days | LSTM | −0.001 (−0.1) | GBM | +0.032 | **−0.033** |

> **Clearing zero is not the same as beating the baseline, and the two come apart sharply.** On US Equities the LSTM's IC is credibly above zero yet at +0.007 sits far below GBM's +0.032 on the same data. **Always compare the paired daily IC difference with its own HAC interval, not two separate intervals.**

**On the paired-delta measure, across eight case studies: direct sequence modeling credibly improves the ranking on one (Crypto, +0.018 over a near-zero baseline), credibly trails on two (US Equities −0.025, CME Futures −0.033), and is statistically indistinguishable on the other five — at substantially higher training cost.**

### Which architectures win, and why

**NLinear leads on four** (ETFs, Crypto, NASDAQ-100, FX), **LSTM on two** (CME Futures, US Equities), **PatchTST on two** (both S&P 500 case studies), **TCN on none.**

> **That ordering follows from the formulation, not from architecture quality.** These models are used as **direct horizon-label predictors.** NLinear's normalize-and-project structure and the LSTM's gating retain enough temporal information to rank the cross-section without paying the error-compounding cost of a multi-step objective. **N-BEATS, TSMixer, PatchTST, and iTransformer carry inductive biases designed for path forecasting or cross-variate modeling, and those biases don't align with a cross-sectional rank label.** A sophisticated forecasting architecture is a liability when only the horizon label is evaluated.

**Training-budget trajectories split by frequency:** high-frequency case studies (NASDAQ-100, S&P 500 Options, Crypto) **peak early then decay**; daily and longer-horizon (FX, CME Futures, US Equities) **drift upward** through training. Early stopping is a per-case-study tuning outcome, not a fixed rule.

### Ranking quality and uncertainty quality are separate properties

Single split-conformal layer, 90% nominal, splits the eight three ways:

- **Near nominal (~0.90):** CME Futures, ETFs, US Equities
- **Over-cover** (intervals wider than warranted): both S&P 500 case studies
- **Under-cover:** Crypto (well short), FX (modestly short), **NASDAQ-100 (near-zero empirical coverage)**

> **Coverage refines the IC reading rather than restating it.** A case study with credibly nonzero IC *and* near-nominal coverage (ETFs, US Equities) is operationally different from one with credibly nonzero IC but unreliable coverage (Crypto, NASDAQ-100) — **the model may rank assets while its uncertainty layer cannot be trusted.** Responses: multi-fold conformal calibration where split noise dominates; **Mondrian group-conditional calibration** where coverage fails along known groupings (asset class, horizon, volatility regime), at the cost of fewer calibration points per group.

### A caution on generality

> This entire comparison is scoped to **horizon-label ranking scored by IC.** Evaluated instead for risk-adjusted position sizing and scored on Sharpe, downside risk, and cost robustness, hybrid recurrent and feature-selection architectures are found more competitive. **The target and the metric, not the architecture alone, determine what is being tested.**

> **Single-split point estimates are not a ranking signal at this SNR.** On the ETF panel, TCN flipped from **+0.051 to −0.013 across reruns of identical code**, TSMixer from +0.013 to +0.001, and PatchTST/iTransformer ordering drifts across reruns at the same seed — cuDNN non-determinism in the attention path is large relative to the IC scale. Walk-forward across folds is the only authoritative comparison.

---

## Transferable rules

1. **Define the target before choosing the architecture.** Recursive forecasting, multi-horizon path forecasting, horizon-label prediction, and direct allocation are four different problems.
2. **For cross-sectional ranking, predict the label directly** — it matches the evaluation metric and avoids compounding.
3. **A forecasting-native architecture is a liability on a ranking label.** Sophisticated path-forecasting inductive biases actively hurt when only the horizon label is scored.
4. **Library choice is a modeling choice.** Forecasting frameworks impose the path formulation.
5. **Clear D-Linear before believing anything more complex.**
6. **Test whether shuffling the input degrades the model.** If it doesn't, the model isn't using temporal structure.
7. **Compare families with a paired daily-difference interval,** not two separate confidence intervals — clearing zero and beating the baseline are different claims.
8. **Longer lookbacks add noise more reliably than they add signal** in weak, non-stationary series.
9. **Never trust a single-split IC at this SNR.** Rerun noise can exceed the effect being measured.
10. **Zero-shot foundation models on returns are worse than random.** Domain pretraining or fine-tuning is required, not optional.
11. **Treat the pretraining corpus as a leakage channel** and verify temporal separation from the evaluation period.
12. **Report the accuracy-efficiency frontier, not parameter count.** Scaling laws don't hold here.
13. **TSFMs are credible for volatility and VaR, not returns** — the target structure transfers where the return signal does not.
14. **Always conformally calibrate deep-model intervals.** Raw Gaussian intervals under-cover by an order of magnitude.
15. **Ranking credibility and uncertainty reliability are independent properties.** Check both before sizing on a signal.
16. **Make early stopping a per-case-study outcome** — high-frequency panels peak early, longer-horizon panels keep climbing.
17. **A large sample size triggers model comparison, not model replacement.**

---

## Notebooks

`01_core_architectures` (LSTM/GRU/MLP timing and IC on ETF next-day returns) · `02_nbeats_interpretable` (blocks, stacks, doubly-residual from scratch; N-BEATS-I vs. -G on SPY) · `03_great_debate` (all three LTSF-Linear variants vs. vanilla Transformer; shuffle diagnostic on ETF returns) · `04_transformers` (PatchTST, iTransformer, Ridge) · `05_tcn` · `06_tsmixer` · `07_mamba_ssm` · `08_cnn_image_encoding` (Gramian Angular Fields) · `09_foundation_models` (zero-shot Chronos and TTM vs. trained baselines) · `10_uncertainty` (MC dropout, 5-member LSTM ensemble, split-conformal calibration) · `11_library_landscape` (raw PyTorch vs. sktime vs. Darts with code-effort metrics) · `case_studies/us_equities_panel/12_dl_weekly` (the weekly non-overlapping formulation experiment)

**Library selection:** Darts (broadest coverage, unified API, limited panel support) · NeuralForecast (native multi-series via `unique_id`, optimized loops) · PyTorch Forecasting (TFT, rich covariates) · GluonTS/AutoGluon (Chronos-2, native probabilistic) · sktime (composable, wraps backends) · **raw PyTorch for cross-sectional panel prediction.**

---

## Cross-references

Ch. 6 walk-forward protocol required for all validation here · Ch. 9 ARIMA-style one-step forecasting as model-based features; Kalman filtering behind deep state-space models; volatility clustering as the long-memory case · Ch. 10 self-attention mechanics, positional encoding, patching analogues · Ch. 11 §11.5 conformal calibration applied here to deep intervals; SHAP caveats for sequential inputs · Ch. 12 GBM and TabM baselines this chapter must beat; benchmark-skepticism framing · Ch. 14 latent factor models · Ch. 17 direct allocation learning — the fourth formulation, with economic objectives · Ch. 23 GNNs for known relational structure · Ch. 16–19 turning these rankings into economic profit

---

## Citations

Aksu et al. (2024), GIFT-Eval · Ansari et al. (2025), Chronos-2 · Bai, Kolter & Koltun (2018), TCN · Challu et al. (2022), N-HiTS · Chen et al. (2023), TSMixer · Gal & Ghahramani (2016), MC dropout · Gu & Dao (2023), Mamba · Hochreiter & Schmidhuber (1997), LSTM · Hu et al. (2025), FinMamba · Jiang et al. (2020), CNN image encoding of price histories · Karadag et al. (2025), ms-Mamba · Lakshminarayanan et al. (2017), deep ensembles · Lim et al. (2021), TFT · Lim & Zohren (2021), survey · Liu et al. (2024), iTransformer; Moirai-MoE · Nie et al. (2023), PatchTST · Oreshkin et al. (2019), N-BEATS · Rahimikia et al. (2025), TSFMs in financial forecasting · Rangapuram et al. (2018), deep state space models · Saly-Kaufmann et al. (2026), risk-adjusted sizing evaluation · Smyl (2020), ES-RNN · Vaswani et al. (2017) · Zeng et al. (2022), LTSF-Linear · Zhang, Zohren & Roberts (2019), DeepLOB · Zou et al. (2025), TIME benchmark

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 13.*
