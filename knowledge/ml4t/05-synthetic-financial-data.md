# Ch 5 — Synthetic Financial Data

**Governs:** whether to generate synthetic paths, which generator, and how to validate it.
**Thesis:** the objective is **robustness assessment, not prediction.** Synthetic data turns a single realized history into a distribution of plausible histories. It does *not* remove selection bias — it relocates it to the generator.

---

## 1. Why — and the honest limit

Path-limited evidence: history contains few crises, regime shifts, and correlation breakdowns. **Bailey et al. (2015):** under independence and normal-error approximation, after 10 tested configurations the expected max in-sample Sharpe is **1.57 even when all true Sharpes are 0**; at 100 trials it exceeds **2.5**. Probability of backtest overfitting can exceed 50%.

Selection-aware corrections (Deflated Sharpe Ratio, Bailey & López de Prado 2014 — see Ch. 17) **adjust inference but do not create additional market histories.** That's the gap synthetic data fills.

**Three legitimate uses:** robust parameter selection across many trajectories · regime stress testing · privacy-preserving development (with explicit privacy evaluation).

**The core discipline:** if strategies are tuned on synthetic trajectories they overfit to the *generator's* inductive biases. Therefore — **fix the generator before strategy selection where possible, validate on held-out real data, and use an outer validation loop whenever synthetic data affects model selection.**

---

## 2. Stylized facts a generator must reproduce

| Fact | Diagnostic |
|---|---|
| Heavy tails | Excess kurtosis, QQ plots, tail statistics |
| Volatility clustering | **ACF of squared/absolute returns** — slow decay |
| Leverage effect | Negative returns → higher subsequent vol (equities) |
| Weak return autocorrelation | Small linear AC at daily horizons |

> **The decisive point: in finance the features that drive decisions are concentrated in the extremes.** A generator whose samples "look realistic" in the bulk can be useless if it understates drawdowns, misses volatility clustering, or fails to reproduce dependence in stress.

---

## 3. Evaluation — Fidelity / Utility / Privacy

**These trade off against each other.** More privacy costs fidelity; better fidelity doesn't imply better downstream performance; a generator good for one use case fails for another.

**Fidelity** — marginals (KS statistic, Wasserstein distance, histograms, ECDFs, QQ) **plus dependence tested separately** (correlation/covariance matrices, rank correlations, sector/regime relationships) **plus stylized-fact diagnostics.** A generator can match every marginal while destroying cross-feature structure.

**Utility — TSTR vs TRTR:**
1. Train on synthetic only
2. Evaluate on held-out real
3. Compare against train-on-real/test-on-real with the *same* model class, features, target, and evaluation period

Interpreting the error ratio (MSE/MAE): **≈1 = task-relevant information preserved · >1 = utility loss · <1 may mean synthetic data suppressed idiosyncratic noise, but equally may signal leakage, target simplification, or a too-narrow evaluation.** For score metrics (AUC, accuracy) report both directly; don't mix error ratios and score ratios without stating the convention.

**Utility is use-case-specific:** Tail-GAN → VaR/ES · Sig-CWGAN → path-wise criteria · diffusion → temporal and dependence diagnostics · tabular LLM → schema validity + distributional + downstream predictive.

**Privacy** — exact/near-duplicate detection (minimum) → nearest-neighbor distance comparison against held-out real records → **membership inference** (strongest adversarial check). For formal guarantees, DP-SGD (Abadi et al. 2016): clip per-sample gradients, add calibrated noise, budget ε. **Privacy is a design constraint, not an after-the-fact label.**

### Synthetic-specific failure modes

1. **Bias amplification** — if history overrepresents a regime/sector/state, the generator may reproduce that imbalance *more strongly*
2. **Overfitting to the generator** — a strategy selected because it works across many synthetic paths is tailored to the generator's assumptions. **Finalists must be evaluated on real data not used to train the generator**
3. **Limited novelty** — generators interpolate within the training support. **Do not treat synthetic data as evidence about events outside the training regime** unless the generator was explicitly designed and validated for that

### Minimum report for any synthetic-data experiment
- [ ] A fidelity diagnostic (marginal error, correlation distance, tail statistic, or volatility-persistence error)
- [ ] A utility benchmark (TSTR vs TRTR or a task-specific risk metric)
- [ ] A privacy check (duplicates, NN analysis, membership inference, or DP budget)
- [ ] A real-data holdout result — **mandatory when synthetic data influenced model selection**

**No universal synthetic-data score exists.** Calibrate thresholds to frequency, sample size, asset class, and objective.

---

## 4. Classical baselines — use as the bar to clear

### Bootstrap
Preserves the empirical marginal by construction (heavy tails included). **Cannot invent events absent from the record.**

| Method | Preserves | Fails |
|---|---|---|
| IID | Marginal distribution | **Destroys temporal dependence — unusable for risk or sizing studies needing time-varying vol** |
| Block (fixed) | Within-block dependence | Artificial block boundaries; weakens long-range persistence if blocks too short |
| **Stationary (Politis & Romano 1994)** | Dependence in expectation, random geometric block lengths | — |

Block length is a bias–variance tradeoff: longer preserves dependence, reduces sample diversity. **Start at ~22 trading days and adjust on diagnostics.** Stationary bootstrap is often the better default when you want volatility clustering without imposing a parametric vol model.

**Diagnostic that separates them: ACF of squared returns.** IID collapses it toward zero; block/stationary retain a decaying pattern.

### Parametric

| Model | Adds | Fails |
|---|---|---|
| **GBM** | Analytic tractability (Black-Scholes) | No vol clustering, tails too thin |
| **Merton jump-diffusion** | Fat tails, explicit crash moves | **Jump arrivals independent of vol state** — real jumps cluster in stress. Adjust drift for expected jump contribution or the unconditional mean is misstated |
| **Ornstein-Uhlenbeck** | Mean reversion; half-life = ln2/κ | Not a general return model for trend-capable assets |
| **Heston** | Leverage effect via negative ρ; fat tails + clustering | Needs careful discretization (full-truncation Euler, Andersen QE) to keep variance non-negative |
| **GARCH(1,1)** | Vol clustering, MLE-calibrated, pragmatic | Stationarity needs α+β<1 |

**Framing: bootstrap is bounded by history; parametric models go beyond history but only along the dimensions their dynamics imply — and misspecification surfaces exactly where finance cares most (tails, stress dependence, regime transitions).**

---

## 5. Learned generators — match to use case, not to leaderboard

### GAN variants

| Model | Designed for | Binding constraint |
|---|---|---|
| **TimeGAN** (Yoon et al. 2019) | Multivariate sequences; 5 networks (embedder, recovery, supervisor, generator, discriminator), 3-phase training | Doesn't target tails; assumes regular grid. **Reference impls use sigmoid recovery → output bounded [0,1], incompatible with unbounded returns — use a linear output layer** |
| **Tail-GAN** (Cont et al. 2025) | VaR/ES matching; penalties on tail-risk discrepancy, **computed on portfolio returns not individual assets** | Matching VaR/ES on the *training* benchmark portfolios doesn't generalize to other portfolios, single assets, or path-dependent measures. **Two models can match VaR and ES yet differ in tail shape, clustering, and temporal dynamics** |
| **Sig-CWGAN** (Ni et al. 2020) | Path-wise fidelity via signature-kernel MMD; replaces the learned discriminator with an analytic criterion | **Dimensionality.** Signature terms grow as dᵈᵉᵖᵗʰ: 2 assets + time at depth 3 = 40 terms; **50 assets at depth 3 = >125,000**. Signatures are time-reparameterization invariant — often useful, but elapsed time carries information, so augment with time as a channel |
| **GT-GAN** (Jeon et al. 2022) | Genuinely irregular series (neural ODE, arbitrary timestamps) | **Only worth it when observation times carry information.** For regular bars, discrete-time generators are simpler and more efficient |

**Shared GAN risks:** mode collapse (covers a subset of regimes — underrepresents exactly the rare states that matter for risk) · training instability (mitigate with spectral norm, WGAN-GP gradient penalties, phased training) · hyperparameter sensitivity · evaluation ambiguity (no ground truth).

Kwon & Lee (2024): GANs approximate marginal return distributions but struggle with finer temporal structure and multivariate dependence; **multivariate generation can collapse to a low-dimensional dependence structure. Passing marginal tests is necessary but not sufficient.**

### Diffusion

DDPM (Ho et al. 2020): forward Markov chain adds Gaussian noise over T steps; reverse process learns to denoise; MSE loss between realized and predicted noise. **Trades generation speed for training stability** — GANs sample in one forward pass, diffusion needs iterative denoising (DDIM reduces to 50–100 steps).

**Diffusion-TS** (Yuan & Qiao 2024): encoder-decoder transformer, output constrained to trend (low-order polynomial) + seasonal (truncated Fourier, top-k modes), plus a **Fourier-domain loss** alongside the time-domain loss.

> The decomposition isn't economic interpretability — it's an **operational handle**: when samples fail diagnostics you can localize the error to the slow component, the periodic component, or the unmodeled high-frequency residual.

**Known issue: variance calibration.** Trend-plus-seasonal output understates high-frequency variation — the reference implementation understates variance by ~⅓ in normalized space before post-hoc rescaling. Volatility-dependent downstream tasks need explicit variance-calibration terms during training.

**Conditional generation for regime stress testing:**
1. Fit a regime model (HMM) to label history
2. Train a classifier to predict regime labels from noised sequences across diffusion timesteps
3. At generation, use ∇ log p(regime | xₜ) to steer the denoising update

Classifier-free guidance embeds conditioning during training instead. **Tuning matters: strong guidance reduces diversity and exaggerates rare regimes, producing unrealistic extremes.** Temperature scaling and DDIM stochastic sampling help balance targeting against diversity.

> **Inherited-error warning: regimes are model-derived, so the conditional generator inherits the regime detector's errors.** Misclassified periods become mislabeled training data. Validate with regime-specific diagnostics before downstream use.

### LLM tabular (GReaT, Borisov et al. 2023)

Serialize each row as `column is value, ...` text (**randomize column order during training** to reduce presentation-order sensitivity) → fine-tune an autoregressive LLM → sample and parse back, filtering invalid outputs.

Fits mixed-type financial tables: credit/loan applications, customer profiles, corporate fundamentals (subject to strict PIT and accounting-convention checks).

**Failure modes:** internally inconsistent records (employment history incompatible with age) · **numerical fidelity — LLMs optimize token likelihood, not distributional accuracy; high-precision numeric strings are unreliable, so discretize/bin/scale before serialization and expect drift anyway** · compute cost · memorization of rare training examples.

**Constraint layer, validated per parsed row:** type constraints (age integer, ratios non-negative) · range constraints (employment years < age − 16) · logical constraints (if `home_status = RENT` then `mortgage_balance = 0`). **Monitor rejection rate — sustained above 10–15% means the serialization format, preprocessing, or training protocol needs fixing.**

---

## 6. Reported results — read these as calibration, not benchmarks

| Generator | Setup | Result |
|---|---|---|
| **TimeGAN** | 6 stocks, 24-step windows | Discriminative accuracy 68%, ROC AUC 0.87 (**materially separable from real**). **TSTR ratio 1.76** — 76% higher one-step forecast error than training on real |
| **Tail-GAN** | 5 ETFs, 32 random long-short portfolios | At the tested tail level: VaR relative error **13%**, ES error **11%**. Synthetic VaR slightly more negative than real → **overstates loss magnitude rather than understating it** |
| **Sig-CWGAN** | S&P 500 log returns 2005–2020, depth 4, 16-day windows, 2,500 gen steps | Sig-W1 0.054 train / 0.42 held-out; **TSTR 0.954 (near parity)** — but **synthetic skewness and excess kurtosis fall far short, and squared-return ACF collapses to 0.05 vs 0.49 empirical: volatility clustering not preserved** |
| **GT-GAN** | NVDA dollar bars, **only 446 bars from one day** | Reconstruction MSE 0.026; interpolation/real smoothness ratio 0.02 — **ODE paths considerably smoother than real bars.** Read as procedure illustration, not benchmark |
| **Diffusion-TS** | 20 ETF daily returns 2018–2025 | KS **0.06**, correlation error **0.04**, ACF error **0.05**. Regime-conditional: low-vol 0.93× and high-vol 1.08× historical vol (2.1× ratio between conditioned samples). **TSTR ≈ parity.** Best general-purpose result in the chapter — TSTR 1.00 vs TimeGAN's 1.76 on similar inputs |
| **LLM (distilgpt2)** | ETF-derived tabular features, 50 epochs ≈ 13 min on RTX 3090 | **TSTR AUC 0.70 vs TRTR 0.74 (92% ratio) — good utility.** But fidelity is poor: only `volume_ratio` matches (KS 0.10); volatility and all four return features KS 0.30–0.59, p<0.001. **Severe categorical mode collapse: direction=down 94% synthetic vs 45% real; momentum=flat 69% vs 36%; momentum=strong 10% vs 28%; vol_regime=high 1% vs 7%** |

> **The LLM row is the chapter's clearest lesson: high task utility coexisting with badly distorted marginals.** This is exactly why utility and fidelity must be evaluated separately — either one alone would have given the wrong verdict.

### DP-GAN privacy–utility sweep (Opacus DP-SGD)

| ε | Mean abs diff | Correlation distance | Reading |
|---|---|---|---|
| 1.0 | 8.02 | 0.12 | Strong privacy, poor utility |
| 5.0 | 2.40 | 0.15 | Balanced |
| 10.0 | 2.67 | 0.06 | Good utility |
| 50.0 | 1.68 | 0.11 | Best utility, weak privacy |

**Privacy cannot be inferred from realism.** Synthetic data can look different from training data and still leak; it can satisfy privacy constraints while being too distorted to model on. Strong fidelity + strong utility ≠ privacy.

---

## 7. Transferable rules

1. Synthetic data is a robustness tool, not evidence. Real held-out data is the arbiter.
2. Fix the generator before strategy selection; otherwise you overfit to its biases.
3. Evaluate fidelity, utility, and privacy **separately** — each can pass while another fails badly.
4. Marginal-distribution tests are necessary and never sufficient; test dependence and temporal structure independently.
5. ACF of squared returns is the cheapest high-value diagnostic for volatility clustering.
6. Beat the classical baseline (stationary bootstrap, GARCH) before accepting a deep generator.
7. Never treat generated data as evidence about scenarios outside the training support.
8. Regime-conditioned generation inherits the regime detector's errors.
9. Choose the generator by objective alignment: tails → Tail-GAN, paths → Sig-CWGAN, irregular timing → GT-GAN, general → Diffusion-TS, mixed-type tables → LLM.
10. For LLM tabular, add an explicit constraint layer and treat rejection rate as a monitored metric.

---

## 8. Notebooks

`00_classical_simulation` · `01_timegan` · `02_tailgan_tail_risk` · `03_sigcwgan_signatures` · `04_gtgan_irregular` · `05_diffusion_ts` · `06_llm_tabular_great` · `07_dp_gan`

**Cross-refs:** Ch. 3 dollar bars (GT-GAN input) · Ch. 9 regime detection / HMMs, GARCH · Ch. 17 Deflated Sharpe Ratio

**Citations:** Bailey et al. (2015) · Bailey & López de Prado (2014) · Cetingoz & Lehalle (2025) · Takahashi & Mizuno (2024) · Politis & Romano (1994) · Yoon, Jarrett & van der Schaar (2019) · Cont et al. (2025) · Ni et al. (2020) · Jeon et al. (2022) · Ho et al. (2020) · Yuan & Qiao (2024) · Dhariwal & Nichol (2021) · Borisov et al. (2023) · Abadi et al. (2016) · Kwon & Lee (2024)
