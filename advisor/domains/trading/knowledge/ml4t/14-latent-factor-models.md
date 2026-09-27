# Ch 14 — Latent Factor Models

**Governs:** extracting low-dimensional structure from return panels, and the distinction between factors that explain covariation and factors that are priced.
**Thesis:** these methods differ because they **optimize different objects**. A factor that explains covariance is not necessarily priced, and a factor that helps price assets need not explain the most variance. Keeping the objectives distinct is the whole discipline.

---

## 1. The factor zoo — what the evidence actually supports

**Don't adopt either extreme.** The field has genuine false-positive and specification-risk problems, but the strongest conclusion is *not* that the zoo is illusory. The evidence points to **a smaller, robust set of recurring themes embedded in a much larger set of fragile, implementation-sensitive results.**

| Axis | Core finding |
|---|---|
| **Statistical validity** | Harvey, Liu & Zhu recommend **t > 3.0** for new factors, eliminating a large share of published results retroactively. Published t-statistic distributions show truncation below 2.0 and clustering just above it — consistent with selective reporting |
| **Identification / measurement** | **Construction choices dominate.** Under NYSE breakpoints and value weighting, **65% of 452 anomalies fail even the conventional hurdle**, with worst attrition in trading-frictions variables |
| **Risk vs. mispricing** | Unresolved. Cochrane's "dark matter": we observe the gravitational pull of risk premia but cannot identify the causal macro shocks |

**The counter-evidence is substantial and worth knowing:**

- **McLean & Pontiff:** predictor returns decline ~**26%** beyond the original sample (modest overfitting), and a **further 58% post-publication** — arbitrage erosion, a *separate mechanism* from statistical bias
- **Jensen et al. (2022):** hierarchical Bayesian replication across **153 factors in 93 countries**, testing **CAPM alpha rather than raw returns** (the theoretically correct benchmark) → **82% replication rate**, clustering into ~**13 themes** that hold globally out-of-sample. Evidence is *strengthened*, not weakened, by the large factor count
- **Chen (2024):** false-discovery bounds show **at least 75–91% of published predictors are statistically valid**; high false-discovery estimates stem from **misinterpreting statistical insignificance as falsity**

> **The operative reframing: most published factors reflect genuine statistical regularities. Whether they survive trading costs and market learning is a distinct and usually more demanding question.**

**The recurring core** across independent research lines: market · value · momentum · profitability · investment. Fama-French derive theirs from the dividend discount model; the q-factor family from firm investment optimization — **different derivations converging on overlapping empirical predictions.** Dimensionality estimates: ~13 themes (Jensen et al.), ~**15 factors suffice to span the alpha of the full set** (Swade et al.) — smaller than the zoo, larger than five.

> ML reinforces rather than overturns this. Neural networks' dominant predictive inputs are familiar (price trends, liquidity, accounting quality); **gains come from nonlinear interactions among core factors, not esoteric new signals.** Double-selection LASSO shows most proposed new factors are redundant against the existing menu, with profitability and investment retaining the clearest incremental content.

### The distinction that organizes everything

| Type | Definition |
|---|---|
| **Attribution factors** | Explain co-movement among assets — **may carry zero expected return** |
| **Priced factors** | Emanate from asset pricing models, carry genuine risk premia |

Three objectives progressively tighten the link: **variance maximization** (PCA) → **variance + pricing errors** (RP-PCA) → **direct pricing-error minimization** (SDF).

> Latent factor models **do not dissolve the factor-zoo problem — they change the object of selection.** Inferring structure from returns reduces one source of researcher discretion, but does not guarantee the extracted factors are priced, interpretable, or stable out-of-sample.

---

## 2. PCA — assumptions and the diagnostics that matter

**Three assumptions to check before interpreting anything:**

- **Linearity** — relationships change across regimes, especially in stress, and characteristic interactions are nonlinear. Rolling-window PCA partially adapts to temporal variation but **does not address the linearity constraint itself**
- **Variance ≠ pricing relevance** — a factor can explain large covariance and earn no premium; a low-variance factor can command a large one
- **Second moments only** — PCA works entirely through the covariance of centered returns. Returns are skewed, heavy-tailed, and jump-prone, so PCA may miss economically meaningful structure in higher moments

### Three preprocessing choices, in ascending sophistication

| Choice | Effect |
|---|---|
| **Covariance matrix** | Preserves return scale — volatile assets get more weight |
| **Correlation matrix** | Standardizes to unit variance. **Usually preferred for cross-sectional equity**, since it emphasizes common structure over raw volatility differences |
| **Idiosyncratic-volatility normalization** | **The better third option.** Scales returns only by the *diversifiable* component |

> **Why idiosyncratic normalization beats correlation PCA:** correlation PCA forces all assets to equal total variance, which is often **too strong** — it removes not only idiosyncratic volatility differences but also **meaningful differences in common-factor exposure.** Idiosyncratic normalization is selective, leaving common variation intact. Result: cleaner signal/noise separation, more stable eigenvectors, more parsimonious structure. **Estimate idiosyncratic volatility from residuals in a prior window and normalize current returns using only that lagged information.**

### How many components are real — the BBP threshold

> **A factor is recoverable only if its population eigenvalue exceeds √(N/T)**, with eigenvalues normalized to unit idiosyncratic variance. **Below this threshold no estimation technique can separate signal from noise.** This is not a tuning problem; it is an information-theoretic limit.

| Panel shape | Consequence |
|---|---|
| ETFs (T ≫ N) | Low threshold — several components retainable |
| 500-stock equity panel, 1 year daily (N ≈ 2T) | **Only the market plus a few dominant sector factors survive** |
| CME futures (T ≫ N) | Most factors remain identifiable |

**Keep N modest relative to T where possible.** When N/T is moderately large, **eigenvalue shrinkage is more reliable than a visual scree-plot rule.** Use the Marchenko–Pastur distribution as the noise benchmark, and apply Ledoit–Wolf-family shrinkage before PCA on large equity cross-sections — otherwise the leading eigenportfolios may reflect sampling noise rather than persistent structure.

---

## 3. Eigenportfolios

**PC1 is a data-driven market proxy** — nearly all weights positive, **correlating 0.99 with the equal-weighted market return** on the 500 most liquid US stocks. Analogous to CAPM beta in measuring sensitivity to a common factor, **but it carries no asset-pricing interpretation** — it follows mechanically from the sample covariance and the PCA normalization.

Higher components produce interpretable patterns purely from covariance structure: PC2 as growth-vs-value rotation (positive Technology and Communication Services, negative Financials and Energy), PC3 as defensive-vs-cyclical.

> **Two cautions.** Higher-order eigenportfolios are orthogonal *by construction*, and often approximately market-neutral in practice, **but they are not automatically dollar- or beta-neutral.** And loadings **rotate across estimation windows** — PC2 may be growth-vs-value in one decade and defensive-vs-cyclical in the next. **Treat economic interpretations of higher components as descriptive, not structural.**

**Interpretation method:** regress each eigenvector's loadings cross-sectionally on observable characteristics (sector dummies, market cap, momentum, book-to-market). **If PC1 loadings correlate strongly with sector dummies, it is a sector factor under a different name. If PC4 shows low R² against all available characteristics, it may capture genuinely novel latent structure** — precisely the case that justifies data-driven discovery.

### Eigenvector instability — the pathology and its fix

> **Near-degenerate eigenvalues make eigenvectors poorly identified.** When two eigenvalues are close, a small perturbation — one extra day of returns, one stock swapped in the universe — causes eigenvectors to **rotate within their shared subspace or swap entirely.** In rolling PCA this shows up as loadings that **flip sign between adjacent windows**, inverting sector exposures and creating **phantom turnover in downstream portfolio weights.** PC1 is typically immune (well-separated eigenvalue); **components 3 and beyond frequently exhibit it.**

**Diagnostic:** cosine similarity between consecutive eigenvectors, absolute value (eigenvectors are identified only up to sign). **Components frequently dropping below 0.8 are unreliable for attribution or allocation without correction.**

**Fix — orthogonal Procrustes rotation:** SVD of the product of consecutive loading matrices gives the orthogonal matrix best aligning the two loading spaces. **This preserves orthogonality and factor span while removing arbitrary rotations within near-degenerate eigenspaces — the same model in a temporally smoother coordinate system.**

**Decision rule:** top 3–5 components with eigenvalue ratios exceeding **2:1** between consecutive components → loadings naturally stable, Procrustes unnecessary. **Clustered eigenvalues — common for equity returns beyond the third component — always apply Procrustes.**

### Two-stage production recipe

Separates two empirical facts: **volatility changes fast (days to weeks); correlation structure changes slowly (months to quarters).** Mixing both in one window either overreacts to volatility spikes or underreacts to correlation shifts.

1. **Volatility dynamics** — exponential time weighting, **half-life ~20 days**. Preliminary PCA, compute residuals, estimate per-asset idiosyncratic volatility
2. **Correlation structure** — normalize by Stage 1 idiosyncratic volatility, **slow exponential weighting, half-life ~120 days**, production PCA with BBP-informed eigenvalue shrinkage and Procrustes rotation. Reconstruct full covariance, restoring the original volatility scale

> **Why the separation matters operationally:** a sudden volatility spike immediately updates risk estimates **without destabilizing the slower-moving factor structure that determines diversification benefits.**

**Hierarchical PCA** injects known economic structure: PCA within each GICS sector, then PCA on the correlation matrix of sector-level factors. Resulting factors correspond to clear inter-sector bets or intra-sector momentum, resolving much of standard PCA's ambiguity.

---

## 4. The yield curve — where PCA works and why

**Three factors explain 95–99% of Treasury yield curve variation**, replicated across decades and markets.

| Factor | Variance | Pattern | Interpretation |
|---|---|---|---|
| **Level** | **>90%** | Parallel shift | Inflation, growth expectations |
| **Slope** | ~5–8% | Steepening/flattening | Monetary policy stance |
| **Curvature** | ~1–2% | Butterfly twist | Rate volatility, path uncertainty |

Worked implementation on eight constant-maturity yields recovers **82.3% / 12.3% / 3.1% (97.8% cumulative).**

> **Curvature needs at least 5–7 maturities spanning the curve.** With fewer, the third component captures residual variation rather than a clean butterfly.

**Why it works here and not in equities:** rate drivers are **low-dimensional and persistent** — inflation expectations, real growth, monetary policy affect all bonds simultaneously with maturity-varying sensitivity. **This is the rare case where the variance objective and the pricing objective largely coincide,** because no-arbitrage constraints push variance-explaining factors toward being priced. Equities are the opposite: thousands of stocks driven by idiosyncratic news, sector effects, macro shocks, and behavior produce a complex, time-varying, regime-dependent covariance.

> **Still a caveat:** PCA on yield changes is a **descriptive decomposition of curve movements, not proof that the same components are the uniquely priced term-premium factors.** No-arbitrage term-structure models add structure PCA alone does not impose. Exact percentages depend on the maturity set, sample period, and correlation-vs-covariance choice.

**Payoff: generalized duration hedging.** Neutralize three factor exposures with liquid instruments rather than managing dozens of individual bonds — more precise, cheaper in transaction terms, grounded in the empirical low-rank structure.

---

## 5. The three-stage forecasting adapter

The organizing abstraction. **PCA, RP-PCA, IPCA, and CAE differ only in Stage 1.**

| Stage | Operation |
|---|---|
| **1. Factor estimation** | Compress the excess-return panel into a factor history and a per-asset loading map. **Uses contemporaneous returns** — that's what the structural model is for |
| **2. Factor-premium forecaster** | Predict next-period premium from the training-window factor history. **Baseline is the training-sample mean** (the implicit choice in the foundational papers); AR(1), EWMA, Ridge, LightGBM, LSTM/TCN, and pretrained foundation models are drop-in replacements |
| **3. Asset map** | Combine today's exposures with the forecast premium |

> **Two properties follow, and both are practically important.** Stage 1 and Stage 2 are **separable** — the same structural model pairs with any forecaster, and the same forecaster works across structural models, **without retraining the factor model.** And **forecast quality enters at Stage 2** — better factor-premium forecasts translate directly into better asset-level signals through Stage 3.

**Forecaster ladder:** Tier 1 constant / AR(1) / EWMA · Tier 2 Ridge / LightGBM · Tier 3 LSTM / TCN.

**The SDF and SAE sit outside the adapter** — the SDF learns a discounting object directly with no factor-return history to forecast; the SAE predicts end-to-end with no factor intermediate.

### Model comparison

| Model | Estimation objective | Loading structure | In adapter? | Best use |
|---|---|---|---|---|
| **PCA** | Maximize covariance explained | Static | Optional | **Risk decomposition** |
| **RP-PCA** | Variance **+ pricing-error penalty** | Static latent | Yes | **Priced-factor discovery** |
| **IPCA** | Conditional latent factor model | **Linear** characteristic-conditioned betas | Yes | Interpretable conditional betas |
| **CAE** | Nonlinear conditional latent factor model | **Neural** characteristic-conditioned betas | Yes | Nonlinear conditional betas |
| **Adversarial SDF** | No-arbitrage moment restrictions | Pricing-kernel weights | **No** | Direct pricing-error minimization |
| **SAE** | Supervised prediction + reconstruction regularizer | Bottleneck representation | **No** | Predictive benchmark |

### IPCA — characteristics as covariances

**The central insight: characteristics predict returns not because they are standalone anomalies but because they proxy for time-varying exposures to latent risk factors.** A small-cap value stock loads on different factors than a large-cap growth stock, and loadings update as characteristics change.

**This yields a direct risk-vs-mispricing test:** if characteristics work through shaping risk exposures → strong latent factors and **insignificant alphas**. If they represent pure mispricing → the effect lands in a **significant alpha term.**

**Three identification sensitivities that recur across replications:**

- Results depend on the number of latent factors K. **Report a range (typically 3–8) rather than a single optimum** — the out-of-sample pricing-error rule is sensitive to the test-asset set
- **Missing characteristics are absorbed into residuals rather than systematic risk.** A 57-characteristic implementation (vs. 94 in the original) is a floor, not a ceiling
- The **linear map cannot capture interactions** — momentum conditional on volatility, size conditional on liquidity

> **Impute missing characteristics (cross-sectional median is standard) rather than dropping observations — missingness is informative,** since smaller firms have fewer available characteristics. **Characteristics must be lagged relative to returns**, and the interpretation is conditional risk exposure, not a reduced-form anomaly regression.

### RP-PCA — the penalty, not the loading map

Minimizes a weighted combination of unexplained variance and cross-sectional pricing errors. **γ = 0 recovers standard PCA; γ → ∞ focuses entirely on pricing.** Solved by applying standard PCA to the sample covariance plus a penalty overweighting mean-return information.

> **The example that shows why it matters:** a credit-risk factor might explain **only 2% of return variance yet carry a Sharpe of 0.8** — invisible to standard PCA, which ranks it below the 15th component. RP-PCA with moderate γ **elevates it to 3rd.** Reported out-of-sample Sharpe ratios more than double standard PCA's on US equities 1963–2017, though results are sample-dependent.

> **Sign convention trap:** the original paper writes the penalty with PCA recovered at γ = −1; the chapter's parameterization makes γ = 0 the no-penalty case. Check which convention a given implementation uses.

### Test assets are a design choice, not a neutral backdrop

Factor strength depends on the **span of the test assets** used in estimation and evaluation. Supervised PCA selects informative assets when weak factors are present; tree-based methods build test assets endogenously so the basis better spans the SDF.

**Practical rule: compare methods on a common benchmark set, but also report how results change when the test-asset span is enriched or redesigned.**

---

## 6. Conditional autoencoder

**The CAE is a strict nonlinear generalization of IPCA** — same conditional factor representation, differing only in the loading map. **With a single linear layer and no activation, the CAE collapses to IPCA.** It is not a separate direct-prediction architecture.

**Architecture:** a **beta network** (feed-forward, ReLU, batch norm, pyramidal e.g. 64→32→16→8) maps lagged characteristics to conditional loadings. A **factor side** forms characteristic-managed portfolio returns by projecting realized returns on the lagged characteristic matrix, then maps them to latent factor returns via a simple (usually single-linear-layer) network. Trained jointly to reconstruct the contemporaneous cross-section.

> **The managed-portfolio object is a cross-sectional projection, not a univariate sort.** The sorting interpretation is useful intuition; the formal object is the projection coefficient vector.

**Preprocessing:** rank stocks by each characteristic each month and rescale ranks to a bounded interval. Neural nets are scale-sensitive and characteristics carry extreme outliers.

**Working hyperparameter ranges:** 2–3 hidden layers · widths 32–128 pyramidal · L1 regularization · batch sizes 1,000–5,000 (near a full monthly cross-section) · **dropout above 0.3 underfits, below 0.05 overfits** · start with a small number of latent factors and treat **highly correlated learned factors as a signal that K is too large or regularization too weak.**

> **Train an ensemble across seeds and average.** Deep networks are sensitive to initialization; ensemble averaging reduces the variance of the fitted loading map and yields more stable downstream forecasts.

> **Reconstruction loss is an optimization diagnostic, not a model-selection criterion.** It shows whether the model can fit the training cross-section — not that the learned factors earn stable out-of-sample premia. **A CAE can reconstruct realized returns well and still forecast weakly if the extracted factors carry little persistent premium.** Select on **validation IC, ICIR, quintile spreads, turnover, and portfolio performance**; reserve reconstruction loss for diagnosing underfitting.

**Failure modes and their diagnostics:**

| Symptom | Cause |
|---|---|
| Diverging reconstruction loss | Learning rate too high, or insufficient gradient control |
| Strong seed sensitivity | Ensemble too small |
| Highly correlated latent factors | Oversized model or weak regularization |
| **Near-identical betas across assets** | **Beta-network collapse** — diagnose via cross-sectional beta dispersion |

**Cost anchor for the economic check:** net ≈ gross − turnover × one-way cost, with **5–10 bps one-way for large-cap equities, 50+ for microcaps.**

> **Report results both with and without the smallest 20% of firms by market cap.** Characteristic-based predictability is often concentrated among smaller and less liquid firms; the split separates tradable signal from microcap and liquidity artifacts.

> **SHAP on the beta network explains how the fitted network uses characteristics — it does not prove those characteristics causally drive returns,** and with correlated inputs attribution is unstable across samples. Interpretability diagnostic, not economic validation.

---

## 7. SDF and supervised autoencoder

**Adversarial SDF:** parameterizes the pricing kernel with a network over firm characteristics and macro-state variables, estimated by minimizing violations of conditional moment restrictions.

> **The conditional moment set is effectively infinite — the adversary is what makes it tractable.** A second network learns the **worst-case test portfolio**: the asset combination the current SDF would most misprice. Training alternates — SDF minimizes pricing errors on the adversary's portfolio, adversary finds new portfolios the improved SDF still misprices. **This disciplines the SDF against the hardest cases rather than the average ones — the crucial difference from the CAE's average reconstruction loss.**

A recurrent macro encoder learns a low-dimensional state from FRED indicators (yield spreads, inflation, volatility) so the kernel adapts to regime **without pre-specifying which macro variables matter** — the time-series analogue of letting the beta network discover characteristic interactions.

**Evaluation:** SDF-implied maximum Sharpe (tied to pricing-error magnitude via the Hansen–Jagannathan bound) · pricing errors against benchmark factor models · the worst-case adversarial portfolio at each step.

> **Cross-sectional GMM can yield spuriously high fit through weighting-matrix choices when the model is misspecified.** Rerun under alternative weightings and across both fixed and adaptive test-asset sets.

**Supervised autoencoder:** encoder → bottleneck → decoder (reconstruction as regularizer) + supervised head to forward returns. Known as the winning Jane Street Kaggle entry; included as a **strong baseline, not a structural asset-pricing object.**

> **The contrast worth carrying forward: both compress characteristics through a network, but the CAE's bottleneck is a conditional factor structure disciplined by reconstruction, while the SAE's bottleneck is whatever representation best predicts the label. The first is interpretable as risk; the second is not, and is not meant to be.**

---

## 8. Case study evidence

Five case studies have cross-sections balanced enough for the full latent menu. **Coverage is uneven** — US Firm Characteristics drops PCA because **anonymized firm identifiers are not stable month to month, breaking the balanced panel PCA requires.**

| Case study | Horizon | Best latent | Latent IC (t) | Strongest prior | Prior IC | Δ IC |
|---|---|---|---|---|---|---|
| **ETFs** | 21 days | **SDF** | **+0.085 (4.9)** | NLinear | +0.062 | **+0.023** |
| **US Firm Characteristics** | 1 month | **SAE** | **+0.062 (5.5)** | GBM | +0.080 | **−0.018** |
| **CME Futures** | 5 days | **SDF** | **+0.037 (2.8)** | GBM | +0.032 | +0.005 |
| S&P 500 Eq+Opt | 5 days | SDF | +0.012 (0.7) | TabM | +0.011 | +0.001 |
| **US Equities** | 1 day | **IPCA** | **+0.005 (2.2)** | GBM | +0.032 | **−0.027** |

**On the paired-difference measure: latent estimators credibly lead on ETFs, credibly trail on US Equities and US Firm Characteristics, and are indistinguishable on CME Futures and Eq+Opt.**

> **A substantial showing for estimators that lean on structure rather than direct return supervision — matching or beating the strongest supervised family on three of five — but not a wholesale improvement over models that learn the label directly.**

> **One case where the primary label hides the signal rather than lacking it:** on S&P 500 Eq+Opt every estimator overlaps zero at the 5-day return, but **IPCA on the risk-adjusted 5-day label reaches +0.041 with an interval clear of zero** — the only credibly nonzero latent point on that study. Check alternative label definitions before concluding a panel is flat.

### The objective, not the architecture, decides

**PCA — the unconditioned baseline — ranks highest on none of the five.** The SDF leads on three, the SAE on one, IPCA on one.

> **The cleanest evidence, from four objectives on one monthly cross-section (US Firm Characteristics): the SAE reaches +0.062 while the CAE lands at −0.030, with SDF and IPCA near zero between them. Both extremes clear their intervals and carry opposite signs.** A multi-task objective using the return label yields a positive ranking; **a pure reconstruction objective, fitting contemporaneous factors with no forward target, points the wrong way.** Contemporaneous-factor reconstruction is a poor proxy for one-step-ahead forecasting on monthly characteristics.

> **The models are not near-duplicates.** Across the three neural estimators on US Firm Characteristics, **pairwise rank correlations have different signs.** That disagreement is the empirical opening for multi-objective ensembling.

### Dimensionality explains much of the spread

| Regime | Case studies | Consequence |
|---|---|---|
| **T ≫ N (favorable)** | CME Futures, ETFs | Signal eigenvalues cleanly separate from the random-matrix noise floor |
| **Severely high-dimensional** | US Equities; **US Firm Characteristics carries ~9× as many assets as time periods** | Sample return covariance too noisy to invert directly |

> **The estimators that still resolve credible IC in the high-dimensional regime — IPCA on US Equities, SAE on US Firm Characteristics — both sidestep the covariance entirely by mapping characteristics to loadings rather than estimating loadings from returns.** That is the structural reason to prefer conditional models when N/T is unfavorable.

### Fold stability tracks label resolution

> **Even case studies whose intervals exclude zero with margin show wide fold-to-fold variation — which is why the HAC interval, not the point estimate, is the threshold throughout.** The monthly US Firm Characteristics result, built on a structural cross-sectional edge, is **positive on every fold**; the daily US Equities result, built on a thin per-day edge, is **positive on about three folds in five.** A small effect measured cleanly versus a smaller effect measured against more noise.

**Choose by complementarity, not competition.** PCA is for risk decomposition (eigenportfolio betas become the risk dimensions for position sizing and risk management); IPCA, CAE, SDF, and SAE add conditioning, nonlinearity, no-arbitrage discipline, and supervision. **Estimate several under one walk-forward protocol, then read agreement as likely signal and divergence as model risk.**

---

## Transferable rules

1. **Name the objective before choosing the method.** Variance explained, variance plus pricing error, and pricing error alone select different factors.
2. **A factor that explains covariation is not necessarily priced.** Attribution factors and priced factors are different objects with different uses.
3. **Check N/T against the BBP threshold before trusting any component.** Below it, no technique recovers the factor.
4. **Prefer idiosyncratic-volatility normalization to correlation PCA** — it removes noise without flattening genuine differences in common-factor exposure.
5. **Apply shrinkage before PCA on large cross-sections,** and prefer eigenvalue shrinkage to scree-plot inspection when N/T is moderate.
6. **Measure eigenvector stability with cosine similarity and apply Procrustes rotation when eigenvalues cluster.** Unstable loadings generate phantom turnover that costs real money.
7. **Separate fast volatility dynamics from slow correlation dynamics** with different half-lives in production risk models.
8. **Interpret higher-order components descriptively, never structurally** — they rotate across regimes.
9. **Regress loadings on observable characteristics** to test whether a "latent" factor is a known factor renamed.
10. **Lag characteristics relative to returns and impute rather than drop** — missingness is informative about firm size.
11. **Report a range of K, not a single optimum.** The out-of-sample selection rule is sensitive to the test-asset set.
12. **Test assets are a design choice.** Report how conclusions change when the span is enriched.
13. **Never select a factor model on reconstruction loss.** Good contemporaneous fit is compatible with useless forecasts.
14. **Use the adapter's separability** — swap Stage 2 forecasters without retraining Stage 1.
15. **Where N/T is unfavorable, prefer models that map characteristics to loadings** over models that estimate loadings from returns.
16. **Adversarial objectives discipline against worst cases; reconstruction objectives discipline against averages.** Choose based on which failure you care about.
17. **Report gross and net, with and without microcaps.** Characteristic predictability concentrates exactly where it is least tradable.
18. **Read model disagreement as model risk, not as a tie to be broken** — differing rank correlations across objectives are informative in themselves.

---

## Notebooks

`01_pca_equity_sectors` (scree plot with bootstrap CIs on loadings, rolling PCA) · `02_eigenportfolios` (full PCA pipeline, sector loading heatmaps, HPCA two-step, cumulative returns) · `03_yield_curve_decomposition` (eight Treasury maturities, level/slope/curvature, generalized-duration hedging) · `04_ipca` (ALS with synthetic parameter-recovery check, K-sensitivity, swappable Stage 2 catalog) · `05_rp_pca` (PCA vs. RP-PCA across γ) · `06_conditional_autoencoder` (characteristic preprocessing, dual-network estimation, ensemble training, three Stage 2 forecasters, SHAP, beta-dispersion diagnostics) · `07_stochastic_discount_factor` (adversarial SDF with MacroLSTM, three-phase minimax, top-200 universe) · `08_supervised_autoencoder` (purged CV, direction classification with reconstruction regularization)

**Production form:** `LatentFactorForecastPipeline(model, forecaster, mapper)` in `ml4t-models`; `ml4t.models.SAEModel` for the SAE. Teaching notebooks derive every stage from scratch.

---

## Cross-references

Ch. 4 PIT and survivorship-free panel requirements for characteristic data · Ch. 7 §7.4 multiple testing, the statistical basis of the factor-zoo critique · Ch. 8 §8.4 the characteristic families feeding IPCA and CAE · Ch. 9 Kalman filtering and covariance estimation · Ch. 10 text embeddings as additional CAE characteristics · Ch. 11 §11.4 SHAP, applied here to beta networks · Ch. 12 §12.4 Optuna for CAE architecture search; GBM baselines · Ch. 13 temporal features usable as CAE inputs; the supervised comparison set · Ch. 15 debiased ML, of which double-selection LASSO for factor testing is a special case · Ch. 17 portfolio construction consuming the PCA covariance matrix; eigenportfolio betas as risk dimensions · Ch. 18 short-term volatility updating for cost models · Ch. 19 risk management via factor decomposition · Ch. 20 multi-objective ensembling built on the model disagreement measured here

---

## Citations

Avellaneda (2019), HPCA; Avellaneda & Lee (2010), statistical arbitrage · Baik, Ben Arous & Péché (2005), BBP phase transition · Barillas & Shanken (2018), model comparison · Bryzgalova, Pelger & Zhu (2025), tree-based test assets · Chen (2024), false-discovery bounds · Chen, Pelger & Zhu (2021), adversarial SDF · Cochrane (2011), factor zoo · Connor & Korajczyk (2009), characteristic regression of statistical factors · Didisheim et al. (2023), complexity in factor models · Engel et al. (2025), factor-forecast uncertainty ranking · Fama & French (1993, 2015) · Feng, Giglio & Xiu (2020), double-selection LASSO · Giglio, Xiu & Zhang (2021), supervised PCA · Gospodinov, Kan & Robotti (2014), GMM weighting-matrix caveat · Goyal (2012) · Gu, Kelly & Xiu (2019), conditional autoencoder; (2020), empirical asset pricing via ML · Harvey (2017); Harvey & Liu (2019); Harvey, Liu & Zhu (2016) · Hou, Xue & Zhang (2015, 2020); Hou et al. (2021), q-factor family · Idzorek, Kaplan & Ibbotson (2024), attribution vs. priced factors · Jensen et al. (2022), Bayesian replication · Kelly, Pruitt & Su (2019), IPCA; Kelly et al. (2025), attention-based loadings · Lettau & Pelger (2020), RP-PCA · Litterman & Scheinkman (1991), yield curve factors · McLean & Pontiff (2016) · Paleologo (2025), production risk modeling · Swade et al. (2023), spanning the factor alpha

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 14.*
