# Ch 16 — Strategy Simulation

**Governs:** turning a prediction into a falsifiable claim about realized portfolio behavior — the trading protocol, the simulator's semantics, and the inference that survives the search path.
**Thesis:** a backtest is evidence to be attacked, not a verdict. **A good equity curve is a claim that now needs deliberate attempts to break it,** and the main product of disciplined research is failed tests.

---

## 1. The falsification posture

Verification asks whether performance looks attractive. **Falsification asks what would disprove the result**, forcing three questions: is the signal genuine or an artifact of leakage, data errors, or selection? Is execution feasible at the assumed timing, liquidity, and impact? Is performance stable across regimes and small specification changes?

| Failure mode | Diagnostic |
|---|---|
| Lookahead bias | Walk-forward validation; PIT data audit |
| Survivorship bias | Include delisted securities; verify universe construction |
| **Data snooping** | **Deflated Sharpe Ratio; hold-out validation** |
| Unrealistic execution | Slippage modeling; capacity analysis |
| Cost underestimation | **Cost sensitivity across realistic ranges** |
| Regime fragility | Regime-sliced diagnostics |

> **ML workflows add leakage channels that look like normal preprocessing:** fitting transformations to full samples, leaking future information through target construction, cross-validation splits allowing information across folds.

**Three simulation frameworks with different inferential roles — use as complements:** walk-forward establishes temporal plausibility (but estimates remain sample-specific) · **resampling/block-bootstrap** characterizes uncertainty around observed statistics (conclusions depend on how dependence is preserved) · **Monte Carlo** probes model-conditional stress behavior (only as credible as the structural assumptions behind the generator).

> **The base-rate argument sets the default posture.** If only a small fraction of candidate strategies has a true edge, false positives can rival or exceed true positives. **In competitive markets the prior on edge is plausibly low, so rejection standards should be stricter than most exploratory research practice suggests. Default to disbelief until evidence survives multiple documented attempts at rejection.**

---

## 2. The protocol — six components, recorded before results are read

> **Two backtests of the same signal can reach different conclusions because they answer different protocol questions.**

### Signal timing

| Convention | Validity |
|---|---|
| **Close-to-next-open** | Conservative and realistic for most signals |
| Close-to-close | **Only valid if the signal is computed before the close** (e.g. from intraday data) |
| **Same-bar execution** | **Generally unrealistic** |

> **Decision, order placement, and fill are sequential events. Assuming simultaneity fuses past and future.** Strategy returns must reflect **order executions, not trade decisions.** Misspecifying this lag can dramatically inflate returns.

### Score-to-signal conversion

| Method | Trade-off |
|---|---|
| **Fixed threshold** | Simple, interpretable; **does not adapt to changing score distributions** |
| **Rolling percentile** | Adapts to regime shifts; **higher turnover as the threshold moves** |
| **Cross-sectional percentile** | Controls position count exactly, always invested; **ignores absolute signal strength** |

### Rebalancing, sizing, fills, constraints

- **Frequency mixing must be modeled explicitly.** A monthly-rebalance strategy cannot be validated with daily returns unless the backtest enforces monthly position changes
- **Exit rules are separate from the rebalance schedule** — strategic exits (signal weakens, rank threshold lost) and protective exits (stops, trailing, max holding period)
- **Futures: position size is contracts × notional, where notional = price × multiplier.** The multiplier also converts price moves into PnL — **omitting it misstates PnL by orders of magnitude**
- **Corporate actions:** use adjusted prices and **include delisting returns**

> **A constraint that is checked after returns are computed was not simulated.**

### Cost sensitivity procedure

Define a conservative grid → run across it → **identify the break-even region where net Sharpe or net return turns negative** → compare against realistic execution costs for the market and trading style.

> **If the strategy only works in the optimistic corner of the grid, the signal has not survived validation.** The thinner the edge, the more important sensitivity becomes. **Better to reject a profitable strategy than implement an unprofitable one.** Document the cost assumptions that would make it unprofitable — **that defines the operational requirements for live trading.**

---

## 3. Vectorized vs. event-driven — a semantic distinction, not a stylistic one

> **The distinction is not NumPy arrays vs. a loop. It is whether the trading protocol is naturally a static array transformation or a state-transition system.** Vectorized backtests are not inherently naive; event-driven backtests are not inherently realistic. **Each is only as credible as the protocol it implements.**

**The two selection questions:** Can the full protocol be expressed as timestamped signals, target exposures, and cost formulas **without changing the strategy's meaning**? Or does it require explicit simulation of orders, fills, cash, positions, and risk state?

**Use event-driven when the next action depends on simulated outcomes:** drawdown circuit breakers · Kelly-style sizing updating on realized PnL · stops and trailing stops that depend on the path after entry · multi-leg strategies where leg two depends on leg one filling · futures where roll, margin, and available capital interact.

> **The main failure mode of vectorized research is semantic drift — the arrays no longer correspond to a feasible trading protocol.** Common examples: same-bar execution from close-to-close signals, implicit trading in assets with missing bars, **forward-filled prices creating artificial tradability**, target weights ignoring cash constraints, cost formulas penalizing turnover without checking whether the trade could be financed.

> **Event-driven simulation does not automatically match live trading** — bar data still hides the order book, queue position, intrabar path, and impact unless modeled separately. **Its benefit is that it exposes the state variables and transition rules the strategy actually uses, making the protocol inspectable.** A poorly specified event-driven backtest can be less reliable than a disciplined vectorized one.

### Simulation semantics that change results

| Choice | Why it matters |
|---|---|
| **Signal-to-fill timing** | Same-bar close, next-bar open, next-bar close imply **different information sets** |
| **Fill price basis** | Open/close/mid/stop/limit/slippage-adjusted change both PnL and **trade feasibility** |
| **Order sequencing** | **Sells first releases cash; buys first can cause rejection or resizing** |
| Target-weight translation | Portfolio value convention may be frozen or updated during rebalance |
| Cash accounting | Cash release, unsettled proceeds, commissions, short proceeds, margin |
| Fractional vs. integer shares | Rounding creates residual cash, allocation drift, unintended trades |
| Insufficient-cash behavior | Reject / resize / partial fill / allow through margin — **each changes the path** |
| Short-sale rules | Cash generation, margin, borrow availability, financing |
| Stop and limit semantics | **Can dominate results for path-dependent exits** |
| Missing bars and calendars | Sparse prices, late entry, delistings, holidays, forward-fill determine **what is tradable** |

> **Order sequencing is easy to miss in weight-based research and is not philosophical.** Sell-then-buy lets proceeds finance the purchase; buy-then-sell may reject or resize it. **It is a concrete statement about the simulated trading process.**

**Library positioning:** array-first tools (vectorBT, vectorBT PRO) are strongest for large-scale research and parameter sweeps **(with corresponding multiple-testing exposure — see §7)**. Zipline, backtrader, Lean, and ml4t-backtest expose the trading process as decisions, orders, fills, and portfolio updates — better when the claim depends on execution state, path-dependent risk management, cash constraints, or order-level behavior.

> **Credibility comes from aligning three objects: the economic claim, the trading protocol, and the simulator's state and timing semantics. Defaults are assumptions, not conveniences.**

---

## 4. The auditable baseline — and why it should be unflattering

**Two purposes:** a performance yardstick, and **forcing the full backtesting infrastructure to exist before model complexity is added.** Bugs in data pipelines, execution assumptions, or cost models affect all strategies equally — a baseline with known properties surfaces infrastructure problems **before they contaminate model evaluation.**

**Specification (permanent reference):**

| Component | Value |
|---|---|
| Universe | 10 asset-class ETFs: SPY, QQQ, IWM, EFA, EEM, AGG, TLT, GLD, VNQ, DBC |
| Signal | **6-month risk-adjusted momentum** (cumulative return ÷ realized volatility) |
| Positioning | Top 3 momentum ETFs (risk-on) or 60% AGG / 40% TLT (risk-off) |
| Regime | **10Y−2Y Treasury spread > 0.5% = risk-on** |
| Weighting | Equal weight among selected |
| Rebalance | Monthly, first trading day; signal at month-end close |
| Costs | **5 bp per trade (10 bp round trip)** |
| Benchmark | Static 60% SPY / 40% AGG |
| Period | 2010-01-04 to 2023-12-29 |

> The universe is deliberately small and ETF-based **so the strategy can express cross-sectional momentum and regime rotation without introducing stock-level survivorship and delisting mechanics.** The 12-minus-1 academic standard is adapted to 6-month risk-adjusted momentum because a small cross-asset universe has widely differing volatility.

**Results:**

| Metric | ETF Momentum | 60/40 Benchmark |
|---|---|---|
| Total Return | 171.4% | **282.8%** |
| CAGR | 7.4% | **10.1%** |
| Volatility | **11.4%** | 12.7% |
| Sharpe | 0.65 | **0.80** |
| Sortino | 0.86 | **0.96** |
| Max Drawdown | −31.9% | **−26.9%** |

> **The baseline is useful precisely because it is not flattering.** It loses to a static 60/40 on total return with a deeper drawdown. **That is a healthy outcome — any later ML strategy claiming progress must improve on an explicit, somewhat disappointing benchmark rather than a straw man.**

> **Calibration for infrastructure debugging:** if your baseline **significantly exceeds** these figures, investigate for lookahead, survivorship, or cost omission. If it **significantly underperforms**, verify data quality and protocol implementation.

---

## 5. Metrics — three design principles

**Completeness** (returns, risk, risk-adjusted, trading behavior, implementation costs — omitting any category can make a fragile strategy look robust) · **parsimony** · **comparability** (a metric whose definition changes across notebooks loses most of its diagnostic value).

### What each metric hides

| Metric | Caveat |
|---|---|
| **Cumulative return** | Depends heavily on sample length — use CAGR for cross-sample comparison |
| **Hit rate** | Useful only with context. **Trend-following and option-like strategies may have low hit rates but positive expectancy.** Varies with measurement interval — don't compare across daily/weekly/monthly |
| **Max drawdown** | **An extreme statistic, highly sample-dependent.** Longer samples produce more severe drawdowns for the same underlying strategy. Useful for stress interpretation, **unreliable as a standalone quality measure** |
| **Drawdown duration** | Often the more economically important measure — **investors may redeem before the eventual recovery.** Moderate MDD with repeated multi-year underwater periods can be harder to hold than a sharper, shorter loss |
| **Calmar** | High Calmar over a short sample can just reflect a period with no stress event |
| **Sharpe** | Symmetric on up/down volatility · summarizes the distribution with two moments · **sensitive to serial dependence, non-normality, and sample size** |
| **Sortino** | **Not automatically more reliable than Sharpe** — depends on the target threshold, unstable with few downside observations, still doesn't characterize tail risk |
| **Annualized volatility** | √t annualization **assumes weak dependence across periods** |

**Exposure metrics:** one-way turnover uses the ½ factor to avoid double-counting buys and sells · **gross exposure above 1.0 signals leverage or shorts**, raising sensitivity to financing, margin, and position limits · **persistent nonzero net exposure indicates directional bias that may explain performance attributed to selection** · **average holding period ≈ 1/turnover** detects mismatches — *a strategy built on monthly features but turning over the book every few days requires explanation.*

### Break-even cost — the key diagnostic threshold

**Break-even cost per dollar traded = expected gross excess return ÷ traded notional.**

> **Worked intuition:** 1% expected gross excess return per period on 10% of NAV traded → **10 cents per dollar traded** would consume the entire excess return. **This is not a forecast of implementation cost — it is the maximum average linear trading cost consistent with non-negative expected excess return.**

> **State the turnover convention.** One-way traded notional, round-trip turnover, leverage-adjusted turnover, and half-turnover each change the cost interpretation.

> **A strategy attractive before costs but unattractive after realistic costs is not a trading strategy; it is an artifact of an incomplete simulation.** Report gross *and* net — **the difference is often as informative as the net result**, revealing whether performance comes from forecast quality or is consumed by trading intensity.

---

## 6. Economic diagnostics

Three layers: **implementation robustness · incremental model value · state dependence.**

### Cost sensitivity, with the worked numbers

> **The ETF baseline runs ~460% annualized two-way turnover** — rotation between top-3 momentum and the defensive sleeve generates substantial trading every rebalance. Sweeping per-leg fees 0→200 bp moves net Sharpe from **0.68 to slightly negative**, crossing zero net CAGR near **166 bp per leg.**
>
> **That break-even is a fragility ceiling, not a target.** The protocol's 5 bp assumption sits **roughly 30× below** it, so realistic commission errors won't change the conclusion. **But a higher-frequency strategy with the same gross CAGR and 10× the turnover would have one-tenth the headroom.**

**Report:** gross and net performance · average and annualized turnover · break-even cost per dollar traded · performance under conservative/baseline/optimistic assumptions · sensitivity of Sharpe, CAGR, and drawdown to the cost model.

> **A strategy whose break-even cost sits close to its assumed cost is fragile regardless of headline net Sharpe.** For high-turnover strategies the cost-sensitivity table is **core evidence, not supplementary.**

### Baseline comparison protects against three mistakes

Separating **model value from market exposure** (the universe may have performed well) · **forecasting skill from portfolio construction** (a simple rank rule may capture most of the edge) · and imposing an **economic opportunity cost** — ML pipelines require data engineering, feature maintenance, monitoring, retraining, and governance, and complexity should justify that burden.

> **On this sample the baseline fails its own test:** static 60/40 earns higher Sharpe (0.80 vs. 0.65) with shallower drawdown (−26.9% vs. −31.9%) **at a small fraction of the turnover. The momentum rule has not established that complexity earns incremental economic value.**

### Regime slicing — construct the labels point-in-time

Volatility regime from trailing realized volatility vs. an **expanding historical median** (or one estimated on the training sample); trend regime from trailing 6-month return vs. its **expanding median.**

> **A full-sample median uses future information to classify earlier periods and contaminates the diagnostic.** Comparing to an expanding median enforces a 50/50 split by construction, so each vol × trend cell carries enough observations for conditional metrics to mean something. **Align the regime label using information known before the return is realized.**

| State | Time % | n | CAGR | Vol | Sharpe | MDD |
|---|---|---|---|---|---|---|
| **Risk-on** (low vol, up) | 36.0% | 1,223 | **1.6%** | 10.7% | **0.15** | −18.3% |
| **Caution** (high vol, up) | 13.4% | **454** | 17.1% | 14.0% | **1.23** | −13.9% |
| **Crisis** (high vol, down) | 33.8% | 1,146 | 6.6% | 11.9% | 0.55 | **−24.0%** |
| **Recovery** (low vol, down) | 16.8% | 572 | 16.4% | 9.9% | **1.66** | −10.9% |
| Overall | 100% | 3,395 | 7.7% | 11.5% | 0.67 | −31.9% |

> **The aggregate Sharpe of 0.67 is carried by Recovery and Caution — not by Risk-on, where most of the sample sits.** In low-volatility uptrends the top-3 rotation captures only a fraction of what buy-and-hold earns. Crisis holds the deepest within-regime drawdown because **the binary yield-curve filter rotates to bonds only once the signal flips**, leaving exposure when volatility spikes alongside a steep curve. **The aggregate −31.9% is the path combination of Crisis losses and the Risk-on shortfall; the regime table separates two channels that aggregate metrics flatten.**

> **Weight conditional Sharpes by sample size.** The Caution slice has 454 observations — roughly an eighth of the sample — so its metrics carry substantially more sampling variability than the aggregate.

**Compare regime-conditional metrics against a simpler allocator.** Against unfiltered equal-weight across the same 10 ETFs: equal-weight leads in Caution (1.50 vs. 1.23), ties in Recovery, and **wins Crisis on both axes (0.78 vs. 0.55 Sharpe, shallower drawdown).** The momentum rule outscores only in Risk-on, and there **both allocators underperform buy-and-hold.**

**Three regime-drawdown measures beyond conditional averages:** regime-conditional drawdown · **drawdown attribution** (decomposing full-sample drawdowns into regime components — a crisis may begin in high-vol downtrend and continue into recovery) · **recovery time by regime.**

> **Not all regime dependence invalidates a strategy.** Some strategies are designed to bear state-contingent risks. **The diagnostic question is whether those risks are intentional, measured, and compensated. Unexpected regime losses require investigation before allocation or live trading.**

### Regime snooping

> **Framing an analysis in economic language does not exempt it from multiple-testing logic.** Snooping enters through volatility lookback, percentile threshold, macro variable and crisis definition, sample split, number of states, and the decision to combine or omit regimes. **A researcher who tries enough combinations can usually find a definition under which the strategy looks robust. That is not evidence of robustness — it is another search path.**

**Four rules:** pre-specify main regime definitions before inspecting conditional performance · prefer transparent definitions over latent-state models with many tuning choices · **report all standard regimes including unfavorable ones — the purpose is to find where the strategy fails** · treat exploratory regime searches as part of the trial accounting.

---

## 7. Inference and search adjustment

### A Sharpe ratio is an estimate

Standard error ≈ 1/√T for small per-period Sharpe.

> **Calibration:** an annualized Sharpe of 1.0 over **five years of daily data (~1,260 observations)** carries a rough 95% CI of roughly **±0.55**. Even under favorable IID assumptions, five years does not precisely pin down an annualized Sharpe.

**Minimum track record length** scales as ((z_α + z_β)/SR)². For SR = 1.0 at conventional significance and power, this runs to multiple years. **Modest Sharpe ratios can be economically useful, especially as diversifiers, yet still require long samples to establish statistical reliability.**

### Serial dependence

> **√t annualization is valid only when returns are uncorrelated.** Overlapping positions, persistent signals, stale prices, gradual rebalancing, and portfolio smoothing all induce dependence. **Positive autocorrelation typically overstates the naive annualized Sharpe; negative autocorrelation can understate it.** Positive autocorrelation also reduces the effective number of independent observations. **Use HAC-adjusted standard errors or a dependence-aware bootstrap.**

### The search-adjusted null

Fixed-strategy inference assumes the rule was specified before evaluation. **After a search, the null becomes the maximum over candidates — the selected strategy is the winner of the search, not a random member of the family. Even if every candidate has zero true edge, the best observed will usually look positive.**

> **The expected maximum of m zero-skill estimates scales as σ√(2 ln m). The simulation makes it concrete: among 100 zero-skill candidate strategies, the best observed annualized Sharpe reaches 2.54 — an artifact of selection alone.**

**Four complementary tools, answering different questions:**

| Tool | Question |
|---|---|
| **White's Reality Check** | Does the best result in the searched family exceed what the search itself could produce under the null? **Bootstrap must preserve cross-strategy dependence, and time dependence where present** (stationary or block bootstrap). Hansen's SPA refines the centering to reduce conservatism when the candidate set has many poor models |
| **Deflated Sharpe Ratio** | Does the observed Sharpe survive adjustment for **non-normality, sample length, and multiple testing**? Built on the Probabilistic Sharpe Ratio; denominator adjusts for skewness and kurtosis |
| **FWER / FDR control** | **Holm–Bonferroni** when one false discovery could promote a spurious strategy; **Benjamini–Hochberg** for large signal libraries with later validation stages |
| **Rademacher Anti-Serum** | Simultaneous lower confidence bounds for a **correlated** strategy family |

> **The DSR requires an *effective* number of independent trials, not a raw configuration count. One hundred adjacent lookback windows are not one hundred independent ideas, but they are not one idea either.**

> **Dependence is the hard part.** Candidates share signals, universes, horizons, cost models, and training samples. **Counting every configuration as independent overstates the penalty; ignoring the search understates it.** Rademacher complexity measures effective search richness directly: draw random sign vectors and record the largest signed average across strategies. **If many strategies are nearly identical, random signs have few independent patterns to exploit and complexity stays low. If the family spans many independent return patterns, some strategy will align with noise and complexity rises.** Validity depends on construction — material serial dependence requires non-overlapping blocks.

> **Search consumes evidence.** The required Sharpe scales with √(2 ln m / T). **Two years of daily data cannot support as many adaptive modeling choices as twenty years of monthly data, unless the observed edge is unusually large and stable.**

**Trial accounting boundary:** include every adaptive choice that could have changed the selected strategy — features, labels, horizons, lookbacks, model class, hyperparameters, training window, rebalance rule, universe filter, cost model, risk overlay, constraints, regime definition, selection metric. **Replacing invalid outputs caused by a bug is not a new hypothesis; changing the specification after observing performance is.**

### Screening priors for unadjusted Sharpe

*Diversified, multi-year, daily-to-monthly, net of realistic costs. **Screening priors, not decision rules.***

| Unadjusted Sharpe | Reading |
|---|---|
| **< 0.5** | Weak standalone evidence; useful only with strong diversification, low costs, or high capacity |
| **0.5–1.0** | Economically interesting if costs, drawdowns, and portfolio-level diversification are favorable |
| **1.0–1.5** | Promising if net of costs, stable across regimes, superior to simple baselines, supported by CIs |
| **1.5–2.0** | Strong for many medium-frequency strategies but **requires careful checks** for leakage, costs, sample selection, search bias |
| **> 2.0** | **Unusual for diversified, scalable strategies; requires aggressive scrutiny** of implementation, capacity, leakage, multiple testing |

> **The pattern matters more than any single gate.** Across the case-study sweeps, some high raw Sharpes don't survive correction; others pass a DSR screen but **fail minimum-track-record adequacy, HAC-adjusted IC significance, cost sensitivity, or regime stability.** IC, Sharpe, baseline comparison, cost sensitivity, regime stability, and search-adjusted significance answer different questions.

---

## Transferable rules

1. **Treat a good equity curve as a claim to attack, not a result to confirm.** Failed tests are the main product.
2. **Default to disbelief.** With a low prior on edge, false positives can outnumber true ones.
3. **Record the protocol before interpreting results** — timing, rebalance, sizing, fills, constraints, costs.
4. **Separate signal computation from execution in time.** Same-bar execution fuses past and future.
5. **Choose vectorized vs. event-driven on semantics, not aesthetics.** The question is whether strategy behavior depends on simulated state.
6. **Treat engine defaults as assumptions** — order sequencing, cash release, share granularity, and missing-data policy all change the path.
7. **Build an unflattering baseline first,** and use large deviations from it as an infrastructure-bug signal in both directions.
8. **Report gross and net together.** The gap reveals whether performance comes from forecasting or is consumed by trading.
9. **Compute break-even cost and compare it to the assumed cost.** Proximity is fragility regardless of headline Sharpe.
10. **Never read max drawdown as a standalone quality measure** — it is an extreme statistic that grows with sample length.
11. **Check whether holding period matches signal horizon.** A mismatch requires explanation.
12. **Build regime labels point-in-time with expanding medians.** A full-sample threshold contaminates the diagnostic.
13. **Weight conditional metrics by slice size,** and report observation counts alongside every regime statistic.
14. **Report all standard regimes including the unfavorable ones,** and pre-specify definitions to avoid regime snooping.
15. **Ask whether regime dependence is intentional and compensated,** not merely whether it exists.
16. **Adjust Sharpe inference for serial dependence** before annualizing or testing.
17. **Count effective, not nominal, trials** — adjacent parameter values are neither independent nor identical.
18. **Keep exploration and confirmation separate,** and confirm on data that did not guide the specification.
19. **Read the screening-prior table as a scrutiny trigger, not a threshold.** A Sharpe above 2.0 on a diversified strategy is a reason to look harder, not to celebrate.

---

## Notebooks

`01_backtest_first_principles.py` (full ETF momentum baseline from scratch — NumPy and Pandas only, every protocol decision visible, with 60/40 comparison) · `02_futures_backtesting.py` (contract multipliers, per-contract fees, session conventions) · `03_single_asset_vectorbt.py` · `04_single_asset_ml4t_backtest.py` · `05_stateful_strategies.py` (when explicit state is the natural formulation) · `06_framework_parity.py` · `07_engine_divergence_anatomy.py` · `08_signal_method_comparison.py` (turnover and risk-adjusted returns across all three score-to-signal methods) · `09_performance_reporting.py` · `10_regime_backtest_analysis.py` (PIT vol × trend labels, regime tear sheet, within-regime drawdown attribution) · `11_sharpe_ratio_inference.py` (minimum track record length) · `12_dsr_validation.py` (the 100-zero-skill-strategies simulation) · `14_cost_sensitivity.py` (per-leg sweep, turnover, break-even) · `15_lean_engine_parity.py` · `16_case_study_lean_parity.py` · `17_backtrader_zipline_engine_parity.py` · `18_vectorbt_engine_parity.py`

---

## Cross-references

Ch. 3 order types and execution mechanics · Ch. 6 setup-level configuration and validation splits that become executable simulation semantics here; trial taxonomy and run logging · Ch. 7 §7.4 the feature-level version of the search-adjustment problem · Ch. 9 regime features (this chapter deliberately uses simpler threshold regimes for auditability) · Ch. 11–15 the predictions this chapter consumes · Ch. 17 portfolio construction and systematic allocator comparison · Ch. 18 estimating and refining the cost model itself · Ch. 19 risk overlays, stops, and constraints from a risk lens · Ch. 20 the full cross-case-study synthesis of these gates

---

## Citations

Ang & Bekaert (2002), regime-dependent returns · Bailey & López de Prado (2012), Probabilistic Sharpe Ratio; (2014b), Deflated Sharpe Ratio · Bailey et al. (2014a), backtest failure modes; (2015), backtest overfitting · Benjamini & Hochberg (1995) · Hansen (2005), Superior Predictive Ability · Harvey, Liu & Zhu (2016) · Holm (1979) · Jegadeesh & Titman (1993) · Joubert et al. (2024a), simulation framework taxonomy · Lo (2002), Sharpe ratios under serial dependence · López de Prado (2018) · McLean & Pontiff (2016) · Paleologo (2025), Rademacher Anti-Serum · White (2000), Reality Check

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 16.*
