# Ch 17 — Portfolio Construction

**Governs:** the mapping from forecasts to positions — and the constraints, risk estimates, and rebalancing rules that determine whether a signal becomes profit.
**Thesis:** the allocator is itself a model with inputs, hyperparameters, and failure modes. **Simple heuristics set a high bar, allocators live in narrower performance bands than the models feeding them, and allocator gains cannot rescue a weak signal-cost combination.**

---

## 1. The allocation problem

**Three inputs:** a view on expected returns (model scores, rankings, forecasts) · a description of expected risk (volatility estimates at minimum, covariance for anything beyond simple diversification) · **the investor's definition of admissible risk** — volatility targets, leverage caps, position limits, concentration rules, drawdown tolerance, liquidity requirements.

> **Constraints are part of the allocation model, not an implementation afterthought.** The same forecast justifies a very different portfolio for a long-only pension fund than for a leveraged market-neutral mandate.

**Signal preprocessing is a modeling choice:** rank transformations produce more even position sizes; **z-scores let conviction affect sizing but can concentrate risk in names with the most extreme forecasts.** Even modest distortions in relative expected returns materially change allocations.

### Four decisions embedded in the weight vector

| Decision | Consequence |
|---|---|
| **Long-only vs. long-short** | Long-only substantially shrinks the feasible region and **often prevents full expression of relative views**. Long-short hedges market exposure but introduces leverage, borrow costs, and short-book constraints |
| **Gross vs. net exposure** | Gross measures total risk regardless of direction; net measures directional bias. A market-neutral book can be zero-net with substantial gross |
| **Leverage** | Improves use of weak but diversified signals; **amplifies estimation error, drawdowns, and implementation risk.** Sizing and leverage cannot be separated |
| **Rebalance frequency** | **No universal optimum** — depends on signal decay, frictions, liquidity, and the rate at which the covariance structure itself changes |

> **On long-short scaling: equal-notional dollar neutrality is usually not the best sizing.** Short legs are typically more volatile and less diversified than long legs, so **volatility-matched scaling of the short side improves both absolute and risk-adjusted performance and yields market exposure closer to zero** than standard equal-notional construction.

**Constraint form changes behavior:** a hard cap creates a literal boundary in the feasible region; a soft penalty makes large positions progressively more expensive. **Hard constraints for true operational, regulatory, or mandated restrictions; soft penalties for preferences about diversification, turnover, or stability.**

> **Turnover limits make portfolio choice path-dependent.** Today's optimal allocation depends not only on today's signals but on the inherited portfolio and the cost of moving away from it.

### The Fundamental Law — as calibration, not prediction

**IR ≈ IC × √BR.**

> **Worked calibration:** the ETF case study's best linear specification delivers daily IC ≈ 0.054. With ~100 ETFs rebalanced monthly to 20 positions, **nominal breadth implies an attractive IR before costs. But effective breadth is the operative quantity.** If those 20 positions are driven by roughly **five common risk factors, effective breadth collapses accordingly** — and that gap is one of the main reasons realized performance falls short of naive FLAM projections.

> **The variance-explanation framing is sobering and worth internalizing.** In a univariate cross-sectional weighted regression with intercept, **squared weighted Pearson IC equals the regression R².** An IC of 0.03 therefore explains about **0.09% of cross-sectional return variation.** The signal's economic value comes not from single-name predictability but from **repeated application across many assets and periods.**

> FLAM assumes unbiased forecasts, a correct covariance model, independent bets, and negligible frictions — **none holds exactly.** The useful intuition: **doubling IC has the same effect as quadrupling breadth, and both can be overwhelmed by high correlation among bets, poor risk estimation, or implementation costs. Allocation quality can amplify a weak signal, but it can also destroy it.**

---

## 2. Workflow — the allocator term sheet

> **Its purpose is to prevent allocation from becoming an unlogged search layer after model selection.**

Record: the **objective function, explicit enough that two practitioners would produce the same optimizer** · expected-return source and horizon · covariance method and horizon · constraints with numerical values and **enforcement rules, distinguishing hard feasibility from soft penalty** · rebalancing protocol and drift thresholds · cost treatment · evaluation plan (metrics, subperiods, regime slices).

> **Once written down in advance, poor performance can be traced to a forecast, a covariance estimate, a constraint set, or an execution assumption.**

### Three leakage protections

- **Strict temporal ordering** — expected returns, covariance, risk budgets, and execution assumptions all from information available at portfolio formation
- **Matched estimation windows** — *next-week forecasts with a 10-year covariance matrix combines a short-horizon return view with a long-horizon risk view.* **Defensible, but as a conscious choice rather than an accident of defaults.** Short-horizon signals usually call for shorter, more adaptive risk estimates, accepting more estimation noise
- **Out-of-sample validation of the allocator itself** — **shrinkage intensity, risk-aversion parameters, turnover penalties, and constraint values are hyperparameters in exactly the same sense as model choices.** Tuning them by repeatedly inspecting the test sample fits the allocator to the answer key even with the forecasting model held fixed

---

## 3. Evaluation metrics beyond Ch. 16

### Benchmark-relative

**Active return, tracking error, information ratio, active share.**

> **Sharpe no longer answers the full question. An allocator can improve Sharpe simply by lowering total risk while failing to add value relative to a simple benchmark.** The IR asks: given the benchmark already available, did the deviations earn their keep?

> **Tracking error is ambiguous by itself** — high TE may reflect deliberate, well-paid active bets or unnecessary churn and unstable positions. Read alongside concentration and trading metrics. **Active share ignores covariance, so pair it with TE to distinguish a genuinely different portfolio from a cosmetically active one.**

### Concentration vs. risk concentration

Herfindahl–Hirschman Index; its reciprocal is the **effective number of bets.**

> **Capital concentration is only part of the picture. Equal capital weights do not imply equal risk contributions, and inverse-volatility weights do not imply equal portfolio-risk contributions once correlations are present. A portfolio that looks diversified in capital space can be dangerously concentrated in risk space.**

### The diversification ceiling

> With identical standalone Sharpe, identical volatility, and constant pairwise correlation ρ, the equal-weight portfolio Sharpe **converges to a finite limit as N grows.** Not a trading rule — a diagnostic. **When correlations are high, adding more assets from the same opportunity set contributes little independent risk. The allocator must find less correlated bets, reduce concentration in the common factor, or accept that diversification cannot rescue the strategy.**

### Judge the risk model through the portfolio

> Form comparable minimum-variance or risk-budgeted portfolios from competing covariance estimates and compare **realized out-of-sample risk.** A portfolio-based criterion beats a generic matrix norm because **the allocator never trades the covariance matrix directly — it trades the portfolio implied by it.**

**High turnover carries an extra meaning here:** it can indicate the allocator is **unstable, reacting aggressively to small changes in forecasts or covariance estimates** — a signal that the portfolio may be fitting noise, relevant even before costs are modeled.

---

## 4. Baseline allocators

*The trade-off axis: methods using fewer inputs are more robust; methods exploiting richer information pay in noise. **Risk parity and HRP occupy the middle — full covariance, but structural constraints dampening estimate sensitivity.***

| Allocator | Uses | Key property |
|---|---|---|
| **Equal weight** | Nothing | **The null model.** No estimation, maximum diversification, famously hard to beat |
| **Inverse volatility** | Volatility only | Equalizes **standalone** volatility exposure — *not* marginal risk contribution |
| **Score-weighted** | Forecasts | Normalizes gross but **not net exposure** |
| **Conformal sizing** | Prediction *uncertainty* | Inverse interval width |
| **Risk parity (ERC)** | Full covariance | Equalizes **contribution to portfolio risk** |
| **Volatility targeting** | Realized vol | **An overlay wrapping any base allocator** |

> **Why equal weight is hard to beat: optimization trades diversification for concentration based on estimated inputs. When those estimates are noisy — and they always are — the concentration may add more risk than the "optimal" tilt adds return.** In competitive markets where no asset offers an obvious free lunch, agnosticism is wisdom.

> **Inverse volatility's appeal is estimation reliability:** volatility is sufficiently persistent that recent or model-based estimates contain useful information, whereas **short-window expected-return estimates are usually dominated by noise.**

**Score weighting fails when extreme scores concentrate exposure in correlated assets.** Combine with position limits or volatility targeting. For dollar-neutral books, **normalize long and short legs separately.**

**Risk parity requires leverage to achieve competitive returns** — whether leveraged risk parity outperforms depends on **financing costs and correlation stability.**

### Conformal position sizing — a real implementation trap and a real result

> **Pooled split-conformal calibration produces a single quantile per fold and collapses the rule to equal weight.** The widths must vary across assets for inverse-width weights to differ from equal weights — requiring **per-symbol Mondrian calibration under strict walk-forward ordering**, with the trailing timestamps embargoed so calibration cannot peek across the holdout boundary.

| Case study | Val baseline → conformal | Holdout baseline → conformal | Δ holdout |
|---|---|---|---|
| **sp500_equity_option_analytics** | +2.39 → +1.23 | **−0.73 → +0.08** | **+0.81** |
| etfs | +1.36 → +1.04 | +1.00 → +1.02 | +0.02 |
| us_firm_characteristics | +2.75 → +2.73 | +1.77 → +1.79 | +0.02 |
| crypto_perps_funding | +2.57 → +2.41 | −0.13 → −0.13 | 0.00 |
| **us_equities_panel** | +2.03 → +1.56 | −0.49 → −0.73 | **−0.24** |
| **cme_futures** | +1.36 → +1.07 | +1.11 → +0.70 | **−0.41** |
| fx_pairs | +0.05 → −0.11 | +0.19 → — | n/a |

> **Conformal sizing trails the baseline on validation in all seven cases — because the baseline is selection-maximized in-sample — then improves on four of six holdout comparisons, with only one material move.** The pattern is consistent with the mechanism: **a rule driven by calibrated uncertainty trades in-sample Sharpe for tighter alignment between sizing and model confidence.**

> **The fx_pairs row is the flat-signal case and the important caveat. With no real dispersion in predictive confidence to exploit, inverse-width weights only add noise. Conformal sizing carries no embedded direction-of-effect — it amplifies whatever per-symbol confidence the underlying model reports, so it can neither rescue nor distort a signal with no resolved edge.**

### Kelly — the bridge from heuristics to optimization

**The objective is expected growth rate of wealth over many bets, not expected wealth after one bet** — because wealth compounds, this is expected change in log wealth. For one risky asset the growth-maximizing exposure is **μ/σ²**; in multi-asset form the unconstrained solution is **Σ⁻¹μ**, pointing in the same direction as the tangency portfolio. **The difference: a normalized tangency portfolio fixes the scale of risky exposure, while Kelly also determines the implied leverage.**

> **Betting too much reduces expected log growth even when the bet has positive expected value.** And because **full Kelly scales aggressively with the estimated edge, modest overestimation of μ produces excessive leverage and severe drawdowns** — it is sensitive to exactly the estimation errors that destabilize MVO.

> **Calibration:** raw Kelly on real ETF returns typically implies **30×+ leverage** before shrinkage. **Treat full Kelly as an upper bound, not an operating rule.** Fractional Kelly (½, ¼) sacrifices expected log growth under the assumed model to buy robustness under misspecification.

---

## 5. MVO and the Markowitz curse

**Three linked failure reasons:** expected returns are hard to estimate · **covariance inversion becomes unstable when sample size is not large relative to universe size** · **the optimizer concentrates on assets whose alphas are overestimated by chance — the error-maximization effect.**

> **The tangency portfolio is the fragile point.** It is determined by the slope of the capital allocation line, so **small changes in estimated moments materially shift the optimum.** Portfolios near the minimum-variance region are less fragile because they depend less on precise expected-return estimates.

> **The curse, reproduced concretely:** on a 30-ETF universe the **unconstrained max-Sharpe solution collapses to two assets (XLK 78.9% / GLD 21.1%)** and the **unconstrained min-variance solution to one (SHY ~98%).**

> **A useful nuance: allocation quality depends more on alpha *ranking* than on alpha *calibration*.** Uniform scale miscalibration changes portfolio composition little — leverage absorbs most of it. **Ranking mistakes do most of the damage.**

**Robustness fixes:** Ledoit–Wolf shrinkage toward a structured target · factor-structure covariance (separating common-factor from idiosyncratic risk — **complementary to shrinkage, not competing**) · position caps · long-only constraints (suppressing fragile shorts supported only by noisy estimates) · turnover penalties.

> **Constraints are part of the estimator, not secondary implementation details — they regularize the mapping from noisy inputs to weights.** Read as robustness statements: **quadratic penalties reflect uncertainty about alpha magnitudes, sparse allocations reflect a preference for parsimony, conservative covariance acts like higher effective risk aversion, and turnover penalties reflect uncertainty about net alpha after costs.** MVO is not a claim of precise optimality; it is a disciplined procedure for translating uncertain beliefs into weights under explicit guardrails.

**MVO is most defensible when** the universe is modest, covariance estimation is tractable, and signal quality is strong enough that return tilts survive costs. **Under those conditions, shrinkage, realistic constraints, and turnover control matter more than the particular optimizer form.**

### Shrinkage hedging — the defensive version of the same problem

> **When the beta estimate is noisy, full beta-neutral hedging can *increase* realized variance rather than reduce it.** The hedge overreacts to estimation error, trading against noise as if it were true exposure. **The remedy is shrinkage: scale the hedge ratio down when estimation error in beta is large relative to aggregate exposure.**

> **This matters most for concentrated portfolios, where beta-estimation errors do not diversify across positions.** A concentrated book should hedge more conservatively; a highly diversified book can move closer to full neutrality. **The rule is not "always hedge to zero" but "hedge in proportion to the reliability of the exposure estimate."**

**Factor-mimicking portfolios** isolate a single factor exposure with minimal residual risk, converting feature-level hypotheses into tradable portfolios. **Evaluate factors by the out-of-sample marginal Sharpe of orthogonalized FMPs.**

---

## 6. Hierarchical Risk Parity

**Three steps:** convert correlations to distances → hierarchical clustering and quasi-diagonalization (ordering assets by dendrogram traversal so the covariance becomes block-like) → **recursive bisection**, splitting capital between sub-clusters in inverse proportion to cluster variance.

> **The intuition: not every asset should compete with every other asset for weight.** In MVO, small changes in estimated moments alter the entire allocation. **HRP localizes estimation error** — errors in the Apple–Microsoft relationship primarily affect the technology branch rather than propagating through a global covariance inverse. **Diversify first across dissimilar groups, then within similar ones.**

**Four stability sources:** no matrix inversion · **hierarchical regularization** (errors within a cluster partially cancel) · the hierarchy itself is relatively stable across rebalance dates · ignoring expected returns eliminates error-maximization.

**Limitations:**

- **Basic HRP ignores return forecasts entirely** — an acceptable trade when forecast error dominates, **a real opportunity cost when the model has stable directional information**
- **Vanilla HRP is long-only by construction** (recursive bisection assigns positive shares at every level). For long-short, apply hierarchical allocation separately to long and short pools, or use NCO
- **Sensitive to the clustering recipe** — bootstrap-based model confidence sets find strong out-of-sample performance for the class as a whole **but no universally dominant specification**
- **Treats the hierarchy as point-in-time clusterings rather than a dynamic structure with turnover control** — cluster-membership changes create their own instability

**NCO** uses clustering to *decompose the optimization* (optimize within clusters, then across cluster portfolios), preserving expected-return views and constraints while reducing dimensionality. **Closer to a clustered, regularized MVO than to vanilla HRP — more flexible, but it reintroduces optimizer assumptions and can still overfit noisy return estimates.** **Schur Complementary Allocation** reframes HRP-vs-minimum-variance as a **continuum**, letting the practitioner decide how much off-block covariance information to admit based on estimate reliability.

### ETF walk-forward results

*GBM-selected top-5 ETFs, 252-day covariance window, 2010–2023:*

| Method | Annual Return | Sharpe | Max DD | Calmar |
|---|---|---|---|---|
| **Min Variance (LW)** | 11.83% | **0.8437** | −28% | 0.4215 |
| **HRP** | 11.41% | 0.8293 | −28% | 0.4063 |
| Inverse Volatility | 10.92% | 0.8074 | −28% | 0.3893 |
| Equal Weight | 10.38% | 0.7763 | −28% | 0.3698 |

> **Spread is 0.067 Sharpe and all four share the same −28% max drawdown, because the GBM-ranked top-5 selection dominates the path.** With only five names per rebalance the correlation structure has limited room to express itself, and equal weighting is already close to the inverse-variance solution on a small universe. **HRP's structural advantages matter most on larger, more heterogeneous universes than the one tested.**

---

## 7. Controlled allocator comparison

**Hold everything constant except the allocation method** — same forecasts, rebalance frequency, cost assumptions, dividend and corporate-action treatment, constraints, estimation windows, **and covariance estimator** (unless the experiment explicitly tests the covariance model).

*Identical ML signals, ETF universe, 2018–2023:*

| Method | Annual Return | Vol | Sharpe | Max DD | Avg Turnover |
|---|---|---|---|---|---|
| **MVO (Ledoit-Wolf)** | 6.7% | 18.0% | **0.450** | −21.7% | 10.5% |
| Inverse Volatility | 6.8% | 19.2% | 0.439 | −23.3% | **8.3%** |
| HRP | 6.1% | 19.3% | 0.404 | −25.6% | 10.1% |
| Equal Weight | 4.6% | 19.5% | 0.327 | **−19.7%** | **6.8%** |

> **The top two methods differ by 0.011 Sharpe; best-to-worst spread is 0.123. Equal weight delivers the shallowest drawdown despite the lowest Sharpe.** Allocator choice changes risk shape and turnover, **but by narrower margins than most researchers assume before running the test.**

> **And the cost channel dwarfs the allocator channel: for inverse volatility, weight-based return of +46.6% drops to +1.5% after commission, slippage, and fill timing.**

**Cross-case pattern: allocator uplift over equal weight correlates positively with signal strength.** Optimization helps most where the underlying signal already had measurable predictive power.

> **The broader lesson is humility. Allocation methods live in narrower performance bands than the predictive models that feed them.** More value is usually created by improving signal quality and execution realism than by re-parameterizing allocator geometry.

**Matching allocator to signal:** strong, stable forecasts justify score-based tilts or constrained optimization — **there is something worth expressing.** Weak or noisy forecasts call for robust heuristics that resist overreacting to estimation error. **HRP is the middle ground when the priority is diversification stability rather than aggressiveness.**

---

## 8. End-to-end deep allocators

**The alignment argument:** classical allocators separate prediction from sizing, and **the losses are not aligned** — a model can reduce forecast error while producing signals that are expensive to trade, poorly diversified, or fragile under leverage. End-to-end training rewards the model for improving portfolio returns **after risk scaling and costs.** The cost is **diagnostic opacity:** prediction error, sizing, turnover, and exposure control become entangled in one loss surface.

> **Evaluate learned allocators on a separate evidence track.** They do not consume the same forecast stream as equal weight, inverse volatility, MVO, or HRP, so a direct head-to-head **confounds forecasting architecture with allocation logic.** The right question is whether they clear simple heuristics after leakage checks, seed variation, turnover costs, and regime slicing.

### The five-stage pipeline

Per-asset lookback features → **shared-weight sequence encoder** (any Ch. 13 architecture) → tanh signal head → **volatility-targeting position layer** → cross-sectional aggregation and portfolio loss, with gradients flowing through every stage.

> **Shared encoder weights (channel independence) are deliberate regularization** preventing the model from memorizing asset identities through temporal weights; identity re-enters separately via learned ticker embeddings.

> **The position layer does two things at once:** it equalizes risk contributions so **learning is not dominated by the highest-volatility markets**, and it makes gross exposure self-scaling — **when realized volatility rises, positions mechanically shrink, limiting drawdowns without an explicit regime label.**

### Training on the objective

Loss is **negative annualized Sharpe.** Two standard refinements:

- **Pooled Sharpe across all training returns concatenated**, not per asset or per window. **Per-asset Sharpe encourages the model to specialize in a few easy names; pooled forces performance across the full universe** and is the better proxy for out-of-sample Sharpe
- **Transaction-cost-aware loss** subtracting a turnover penalty inside the numerator, so the network internalizes friction during training

> **A subtle and important gradient bug: Sharpe is non-separable — its gradient depends on global sample mean and standard deviation. Naive microbatch gradient accumulation optimizes the average of mini-batch Sharpes, a different objective from pooled Sharpe.** The fix is an exact two-pass procedure: accumulate sufficient statistics without storing activations, then compute analytical gradients. **Matters whenever effective batch sizes must span multiple years to stabilize the estimator.**

### Which encoder wins under a portfolio loss

> **The central finding: inductive bias matters more than raw capacity.** Linear baselines are unreliable across regimes; **generic Transformers are mixed — iTransformer trades too little, posting low turnover but weak economic performance**; plain state-space models don't consistently beat the recurrent class. **Recurrent and hybrid architectures lead**, with VLSTM (TFT-style variable selection + shared LSTM encoder) on top.

> **Robustness reorders the architectures.** VLSTM leads on average Sharpe but is not dominant on every axis: **LPatchTST and VxLSTM are more attractive on drawdown and tail risk, and xLSTM often achieves the highest breakeven transaction cost because it trades less aggressively.** The "best" architecture depends on whether the objective is maximum average return, downside protection, or implementation robustness.

**Why variable selection pays:** financial features have very uneven signal strength across markets and time. **A plain LSTM receiving all features stacked spends capacity learning to ignore noisy channels at every time step.** The VSN gives explicit gating — each feature through its own gated residual network, with a softmax gate computing a per-time, per-asset weighted mixture.

### Three notebooks, decomposed contributions

| Model | Sharpe | Max DD | Note |
|---|---|---|---|
| Softmax long-only LSTM (Zhang et al.) | 0.48 | **lowest of the three** | Trails heuristics despite low drawdown, at less than half their volatility |
| **VLSTM** | **0.66 gross** | 17.6% | Degrades to **0.55 @ 5bp, 0.44 @ 10bp, 0.22 @ 20bp** |
| **DeePM (full)** | **0.98** | **less than half the heuristics'** | Leads on every margin |
| DeePM, no-SoftMin ablation | 0.74 | — | Structural priors only |
| Equal weight / inverse vol | 0.69 / 0.69 | — | **EW is cost-invariant (0.65→0.64 across 0–50bp)** |

> **The VLSTM result is the honest one: variable selection recovers most of the gap to the heuristics *in gross terms but does not clear them at realistic cost*.** Equal weight is effectively cost-invariant because rebalance-to-equal carries near-zero turnover, so **the VLSTM's relative gap widens monotonically with cost.** The training diagnostics show the characteristic failure: **pooled training Sharpe climbs past 12 while validation Sharpe collapses within a few dozen epochs.**

### DeePM's four components, each targeting a named failure

| Failure mode | Component |
|---|---|
| **Asynchronous closes corrupt cross-sectional attention** | **Directed Delay (Causal Sieve)** — shifts allowed information flow per pair to respect closing calendars |
| Channel-strength heterogeneity beyond plain VSN | **V-VSN temporal backbone** — VSN per time step, then LSTM, then self-attention on its own past |
| Cross-sectional attention overfits in low-signal regimes | **Macro Graph Prior (GAT)** — fixed economic adjacency; learned dynamic edge weights within it |
| **Lucky-window overfit on long pooled-Sharpe horizons** | **SoftMin penalty over rolling sub-windows** |

> **The Directed Delay problem, concretely: when the Nikkei closes at 06:00 UTC and the S&P at 21:00 UTC, an attention layer giving the Nikkei representation access to the same-date S&P close uses information from the Nikkei's future filtration.** This is the cross-sectional analogue of the lookahead discipline running through the whole book — **and it is what makes cross-asset attention deployable in a multi-region universe at all.**

> **The Macro Graph Prior fixes *which* edges are admissible while leaving *how strongly* each transmits to the data** — the cross-sectional counterpart of how a variable-selection network reasons over features. It can upweight the bonds-equity link in risk-off regimes and downweight it in growth regimes.

> **SoftMin has a distributionally robust interpretation:** it is equivalent to expectation of negative Sharpe under an adversarial reweighting of training sub-windows, constrained to a KL ball around uniform. **The gradient asks the network to invest capacity in the regimes where average-case Sharpe would have let it coast.**

> **SoftMin's contribution is sharply localized and worth the specificity: calm-window Sharpe barely moves (1.26 → 1.21) while crisis-window Sharpe lifts from 0.57 to 1.00 — a +0.43 gain accounting for almost the entire regime-gap reduction (0.69 → 0.21). Regime-robust training delivered a Sharpe lift and a drawdown improvement simultaneously; read the two together rather than trading them against each other.**

### Three evaluation considerations specific to learned allocators

- **Seed sensitivity is a first-class metric.** The loss surface is non-convex and the gradient depends on global batch statistics — **variance across initializations can dominate small performance differences, and an architecture ranking ignoring it can be reordered by changing the random-seed budget**
- **Turnover stops being a post hoc diagnostic.** Architectures with similar gross Sharpe **can differ by a factor of two in breakeven cost**
- **The heuristic comparison stays non-negotiable.** An end-to-end allocator that cannot clear equal weight and inverse volatility on its own test window is not competitive, however sophisticated the encoder

> **When to prefer each:** classical allocators when signals are stable and covariance structure is the binding constraint. **End-to-end when the objective is hard to factor cleanly into forecasting plus optimization** — regime robustness, cost-aware sizing, or cross-asset interaction with known structure.

---

## Transferable rules

1. **The allocator is a model.** Specify its objective, inputs, constraints, and evaluation before implementing an optimizer.
2. **Constraints are part of the estimator.** They regularize the mapping from noisy inputs to weights, and each has a robustness reading.
3. **Effective breadth, not nominal breadth, drives realized IR.** Correlated positions are not independent bets.
4. **Read IC as R².** An IC of 0.03 explains ~0.09% of cross-sectional variance — value comes from repetition, not single-name predictability.
5. **Match estimation-window horizons to signal horizons deliberately,** not by default settings.
6. **Treat allocator hyperparameters as tunable parameters requiring out-of-sample validation.** Holding the forecast model fixed does not protect against fitting the allocator to the answer key.
7. **Check risk contribution, not just capital concentration.** Equal capital weights ≠ equal risk contributions.
8. **Judge covariance models by the portfolios they generate,** not by matrix-fit metrics.
9. **Clear equal weight before taking any allocator seriously.** Estimation error often overwhelms the theoretical gains from optimization.
10. **Alpha ranking matters more than alpha calibration.** Scale error is absorbed by leverage; ranking error is not.
11. **Hedge in proportion to the reliability of the exposure estimate.** Full neutralization on a noisy beta can raise realized variance.
12. **Volatility-match the short leg** rather than equal-notional dollar neutrality.
13. **Treat full Kelly as an upper bound.** Raw Kelly implies 30×+ leverage on real data.
14. **Expect narrow allocator spreads.** Best-to-worst of 0.12 Sharpe against a cost channel that moved returns from +46.6% to +1.5%.
15. **Allocator optimization helps most where signal is strongest** — and cannot rescue a weak signal-cost combination.
16. **Pool the Sharpe across the universe when training end-to-end,** and use a two-pass gradient because Sharpe is non-separable across mini-batches.
17. **Report the cost-stress curve, not the gross number.** Gross parity with heuristics can vanish entirely by 20 bp.
18. **Make seed variance a reported metric for learned allocators.**
19. **Respect closing calendars in cross-sectional attention** — asynchronous closes are a lookahead channel.

---

## Notebooks

`01_portfolio_metrics` (full diagnostic suite vs. SPY: alpha, beta, TE, IR, up/down capture, VaR/CVaR, stress periods) · `02_mean_variance_optimization` (efficient frontier, five objectives on 30 ETFs, reproduces the Markowitz curse) · `03_robust_optimization` (six allocators via Riskfolio-Lib under Ledoit-Wolf, equal-capital-vs-equal-risk gap) · `04_kelly_criterion` (SymPy derivations, full-vs-fractional on real ETF returns) · `05_factor_allocation_evidence` (Fama-French and AQR Century-of-Premia: HLZ thresholds, value-momentum negative correlation, TSMOM crisis alpha) · `06_hierarchical_risk_parity` (clustering → quasi-diagonalization → recursive bisection, walk-forward vs. three alternatives) · `07_conformal_position_sizing` (Mondrian split-conformal, inverse-width weights) · `08_library_comparison` (skfolio WalkForward; PyPortfolioOpt vs. Riskfolio-Lib vs. skfolio) · `09_allocator_comparison` (the controlled four-way comparison) · `11_dl_portfolio_allocation` (softmax long-only LSTM baseline) · `12_vlstm_portfolio` (VSN + LSTM, 5bp cost-aware loss, 0/5/10/20/50bp sweep) · `13_deepm_regime_robust` (Directed Delay, Macro Graph, SoftMin, calm-vs-crisis slicing)

> The three DL notebooks train on **raw ETF prices, not the case-study GBM predictions** — deliberately, to isolate the architectural and loss-design contribution. **Reusing case-study predictions on these encoders would conflate signal quality with allocator architecture.**

---

## Cross-references

Ch. 7 §7.3 the IC that feeds FLAM · Ch. 11 §11.5 conformal prediction underlying uncertainty-based sizing · Ch. 11–14 the forecast streams allocators consume · Ch. 13 every sequence architecture usable as the end-to-end encoder slot; the fourth forecast formulation (direct allocation learning) lands here · Ch. 14 §14.2–14.3 PCA covariance estimation and eigenportfolio betas as risk dimensions · Ch. 15 weighting factors by causal confidence · Ch. 16 the backtest protocol and regime framework reused here as a secondary view · Ch. 18 the transaction-cost channel that dominates allocator differences · Ch. 19 tail risk, stress constraints, and risk overlays · Ch. 20 §20.5 the cross-case allocator synthesis read jointly with cost survival and risk overlays

---

## Citations

Antonov, Lipton & López de Prado (2024), MVO out-of-sample failure · Cotton (2024), Schur Complementary Allocation · DeMiguel, Garlappi & Uppal (2009), 1/N · French (2024), long-short leg scaling · Grinold & Kahn (2000), Fundamental Law and active management · Hurst (2010), risk parity introduction · Ledoit & Wolf (2003), covariance shrinkage · López de Prado (2016), HRP and the Markowitz curse · Maillard, Roncalli & Teiletche (2008), ERC · Markowitz (1952) · Marti et al. (2021), hierarchical clustering methods survey · Paleologo (2025), robust optimization reading of constraints; shrinkage hedging; FMP derivation · Raffinot (2016), hierarchical clustering variants · Saly-Kaufmann et al. (2026), unified end-to-end architecture benchmark; VLSTM · Wood, Roberts & Zohren (2026), DeePM · Zhang, Zohren & Roberts (2020), deep portfolio allocation

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 17.*
