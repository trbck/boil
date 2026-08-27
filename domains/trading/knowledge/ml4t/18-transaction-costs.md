# Ch 18 — Transaction Costs

**Governs:** the friction stack that separates gross alpha from realized return, and the guardrails that decide whether a strategy is deployable at all.
**Thesis:** cost modeling is a first-class research concern, not a percentage shaved off at the end. **The goal is not to eliminate costs but to understand them well enough to make informed trade-offs** — is this factor's IC worth its turnover, and at what AUM does the answer change?

---

## 1. Where costs enter, and the two symmetric errors

**Costs bite at every stage:** feature evaluation (a feature with higher IC is not better if it needs 10× the turnover) → strategy simulation → portfolio construction (turnover constraints and position limits **regularize the optimizer and keep weights inside the market's liquidity budget**) → risk management (capacity as a risk limit) → production monitoring.

**Two lenses, one loop:** *ex ante* models forecast hypothetical trade costs for backtests and portfolio design; *ex post* TCA measures what the desk actually paid. **The first prevents naive simulations, the second prevents stale parameters. Estimate, trade, measure, recalibrate.**

> **Both directions of error are real and documented.** Using **$1.7 trillion of live institutional executions across 21 developed markets**, Frazzini et al. (2018) find patient execution costs **far below** TAQ-inferred estimates — TAQ describes the average trade, not a patient allocator using schedule control, passive liquidity, and venue selection. From the other side, Schwarz et al. (2022) document **large execution-price differences across retail brokers even at zero commission with orders matched on observable characteristics.**
>
> **There is no universal cost number. Routing, urgency, and execution style decide whether an edge survives. TAQ-based costs can reject viable strategies; zero-cost assumptions approve strategies that fail on contact. The fix is conservative calibration absent execution data, and continuous TCA recalibration once you have it.**

---

## 2. Cost taxonomy

*Convention: basis points of notional, one-way unless stated. Impact model outputs are fractions of price — multiply by 10,000 for bps.*

### Explicit — contractually defined

Commissions, exchange fees, clearing. **Regulatory fees scale mechanically with notional or share count and should be modeled as fixed-schedule inputs rather than buried in slippage.**

> **Financing is explicit but routinely overlooked.** Margin interest, borrow fees, and futures roll **convert gross alpha into carry decisions — an instrument with sub-basis-point trading friction can still be expensive to hold.** Borrow deserves special attention: broker-specific, time-varying, and **often the dominant cost on the short side.** Absent historical borrow data, use a defensible proxy from market cap, float, and short-interest pressure.

> **Transaction taxes are a mechanical first-order wedge.** Stamp duties can **exceed the spread** for the most liquid names. Any cross-market comparison omitting them **is wrong before the first simulated trade.**

> **The modeling error is usually not in this bucket — it is in treating the exact, visible costs as if they were the whole problem.**

### Implicit — order/market interaction

**Spread is the lower bound.** **Slippage** is the gap between intended benchmark and actual fill (quote drift, queue position, partial fills, adverse selection). **Spread is paid immediately; slippage accumulates while the order works.**

**Market impact splits in a way that determines the remedy:**

| Type | Mechanism | Implication |
|---|---|---|
| **Temporary** | Liquidity consumption, dealer inventory; **partially reverts** | **The part the trader can reduce** through scheduling and venue choice |
| **Permanent** | Information footprint — the market revises its value estimate | Reflects **how visible and informative the order has become** |

### Capacity — scaling into the liquidity budget

**Participation:** trading 0.25% of ADV and 5% of ADV are different businesses; **impact rises concavely with size, which is why the square-root rule is the practical default.** **Crowding:** liquidity co-moves across names and sectors, so **capacity is not a static property of the signal — it depends on who else is trying to trade the same idea and when they arrive.** **Opportunity cost:** slower execution cuts impact but raises the chance the market moves first.

> **Capacity is a joint property of signal decay, order size, and execution urgency.**

### Dominant cost by strategy — determines where modeling effort goes

| Strategy type | Dominant costs |
|---|---|
| High-frequency | Spread, exchange fees |
| Daily rebalancing | Spread, slippage |
| **Weekly/monthly** | **Market impact** |
| Low-turnover | Explicit fees, opportunity cost |

### Magnitude anchors (one-way)

| Asset class | Retail (bps) | Institutional (bps) | Dominant component |
|---|---|---|---|
| **Liquid ETFs (SPY, QQQ)** | **0.5–3** | 1–5 | Spread |
| Index futures (ES, NQ) | 0.7–1.5 | **0.5–1.0** | Tick-constrained spread |
| US large-cap equities | 1–5 | 5–15 | Spread + execution quality |
| US small-cap equities | 10–30 | 20–50 | Spread + impact |
| FX spot (majors) | 5–30 | 0.5–3 | **Venue segmentation** |
| Crypto perps (CEX) | 5–50 | 2–10 | Fee tier + volatility regime |
| IG corporate bonds | 30–80 | 5–20 | Embedded markup |
| **Equity options** | **10–100+ of premium** | 3–20 | Spread (**no Rule 605 transparency**) |

> **The two-orders-of-magnitude range is driven primarily by market structure, not asset fundamentals.**

---

## 3. Regime dependence — constant parameters are wrong by construction

**Intraday pattern (US equities):** open (9:30–10:00) is high volatility, wide spreads, thin depth — **materially more expensive than midday.** Midday (11:00–14:00) is lowest volatility, tightest spreads, maximum depth — **cheapest for patient traders but introduces timing risk for urgent orders.** Close (15:30–16:00) concentrates volume as index funds rebalance; **spreads tighten but depth can be consumed quickly**, and closing auctions offer execution certainty at the cost of impact.

**Spreads widen with volatility** through adverse selection: informed traders are more likely to trade when they have private information, which coincides with volatility, so market makers widen to compensate. **Impact also scales with volatility** — the square-root model includes σ explicitly, so higher volatility means higher impact **at the same participation rate.**

> **Regime transitions invalidate quiet-period parameters.** March 2020 is the template: across rates, credit, and equities, execution costs moved **by multiples rather than percentages. Any systematic strategy forced to rebalance during stress pays those stressed costs, not the trailing average.**

> **No single indicator defines the regime — read them jointly.** Implied volatility, relative volume, quote-depth imbalance, and spread-normalized-to-history. **A high VIX print without spread widening does not imply the same execution response as a high VIX print with depth collapse and one-sided order-book imbalance.**

**Four modeling consequences:** estimate parameters **separately by volatility bucket and trading window**, not pooled · **when the regime is ambiguous, stressed parameters are the safer default** because underestimation produces false positives · monitor the same indicators in real time and adjust participation when spreads or depth move outside bounds · **backtests should use contemporaneous regimes so crisis periods incur crisis-level costs**, not a diluted full-sample average.

---

## 4. Baseline models — a ladder, not competing philosophies

Any transient-impact model separates three ingredients: an **instantaneous impact function**, a **decay kernel (propagator)** governing persistence, and a **market-specific scale parameter** for liquidity, volatility, spread, and depth.

> **A distinction worth holding: the single integral of the impact process is the price pressure remaining at a point in time. The cost of execution depends on impact incurred throughout the schedule — which is why the cost expression involves the trading rate against the evolving impact process, not just the endpoint.**

| Model | Core assumption | When to use |
|---|---|---|
| **Spread** | Main cost is crossing the bid-ask | Small orders in liquid markets — **a lower bound** |
| **Linear participation** | Impact rises ~linearly with participation | Medium orders, conservative baseline; **overstates cost of large orders** |
| **Square-root metaorder** | Concave in size, scales with volatility | **The empirical workhorse** for meaningful sizes |
| Transient linear | Linear in rate, decays as liquidity replenishes | Multi-period execution where schedule timing matters |
| Propagator | Slow decay, possibly interacting with concave impact | HF, multi-period, execution-focused research |

> **Transient-impact and propagator models are better treated as *execution* models than as default *backtest* cost models** — stronger assumptions, more calibration data.

**Model selection by participation:**

| Participation | Model |
|---|---|
| **< 0.5% of ADV** | Spread |
| **0.5–2% of ADV** | Linear slippage |
| **> 2% of ADV** | Square-root impact |

> Rules of thumb, not hard boundaries. **Their purpose is to keep the backtest from using a model that is structurally too optimistic.** A spread-only model may be fine for low-turnover strategies trading small fractions of volume; **it will materially understate costs for a strategy repeatedly trading several percent of dollar volume.**

**Conservative defaults absent execution data:** spread — 5–10 bps US large-cap, 20–50 small-cap, 50–100+ EM/illiquid. Slippage — 5 bps liquid large-cap, 15–25 mid/small-cap, **2–3× higher during volatile periods.**

**Impact coefficient η by asset class:**

| Asset | Range |
|---|---|
| FX majors | 0.05–0.15 |
| Liquid futures | 0.1–0.2 |
| Large-cap equities | 0.1–0.3 |
| Mid-cap equities | 0.2–0.4 |
| Small-cap equities | 0.3–0.6 |

> **Use the upper half or upper quartile of the applicable range for backtesting.** η is not a universal constant — it varies with asset class, liquidity, volatility, regime, and execution style, and **realized impact also depends on recent order flow and market state, so even a well-estimated coefficient is only an average summary.**

> **Concavity, quantified.** On a 100,000-share order: **linear charges 330 bps, square-root 103 bps, power-law (exp 0.3) 850 bps.** Doubling order size does not double impact — **but it still increases total cost enough that schedule design matters.**

**One-way specification:** explicit fees + half-spread + square-root impact. **For small trades spread and fees dominate; as size grows the impact term usually becomes the largest component.**

### The cost-base trap

> **Notional-bps breaks down when traded price and notional exposure are not proportional.** For a short at-the-money straddle on an index constituent, the **premium may be only 3–5% of underlying notional, while the bid-ask on that premium is another 5–15% of the premium** — roughly **15–75 bps of underlying notional per side**, far above single-digit assumptions reasonable for equities. **Replace the notional-bps framework with a price-scaled model calibrated to the instrument.**

**Square-root model limits:** breaks down in stressed markets where impact may steepen sharply · for very small trades where fixed costs dominate · in fragmented or queue-driven microstructure where execution priority matters.

> **Costs regularize the optimizer.** Frictionless MVO assumes rebalancing is free; **realistic costs make the optimizer less willing to chase small forecast changes with large weight changes.**

---

## 5. Execution algorithms as controls, not solutions

> **They do not eliminate costs. The question is which benchmark an algorithm optimizes and which risks it leaves behind, not whether it is "optimal" in the abstract.**

| Algorithm | Optimizes | Fails when |
|---|---|---|
| **TWAP** | Simplicity and schedule certainty | Ignores intraday volume patterns, doesn't respond to spread blowouts, **full timing-risk exposure across the window** |
| **VWAP** | **Benchmark tracking, not pure cost minimization** | Realized session departs from expected profile; spreads widen suddenly; **the benchmark itself is a poor proxy for execution quality** |
| **Regime-aware participation** | Cost, conditioned on state | Requires real-time conditioning infrastructure |

> **The real limitation of both static schedules: they commit to a path before the market reveals whether the session will be calm, stressed, or information-heavy — and continue through regime changes, unexpected news, and liquidity vacuums unless a separate rule interrupts.**

**The core trade-off is explicit: aggressive execution minimizes timing risk but maximizes impact; passive execution minimizes impact but accepts timing risk. The optimal balance depends on the strategy's alpha decay rate — fast-decaying signals require aggressive execution despite costs.**

> **Sophisticated desks use a receding-horizon approach** — optimize a multi-period plan, execute only the first period, re-optimize with updated state. **This is model predictive control:** market state (depth, recent volume, price trajectory) is the system state, the schedule is the control input, the objective trades shortfall against risk and impact. **It explains why institutional desks do not simply follow textbook Almgren–Chriss trajectories but continuously replan.**

**Execution feeds back into strategy design:** a high-turnover signal needs cheap execution just to survive · **capacity limits are execution limits stated in portfolio language** · holding period determines urgency — **slow alpha can wait for liquidity, fast alpha must pay for immediacy.**

---

## 6. Almgren–Chriss

Minimize expected impact cost plus a risk penalty scaled by urgency λ. **Larger λ → stronger preference for completion certainty → more front-loaded schedule.**

> **The optimal path is not TWAP.** Higher volatility or stronger urgency raises the decay rate directly; shorter horizon enters only through the boundary condition. **All three front-load execution.**

**Scenario planning instead of point estimates:**

| Scenario | Volatility | Impact | Risk aversion |
|---|---|---|---|
| Base | Historical avg | Calibrated | Medium |
| High vol | +50% | +30% | Higher |
| Low liquidity | +20% | +50% | Higher |
| Benign | −20% | −20% | Lower |

> **If optimal trajectories vary dramatically across scenarios, the trade is fragile to miscalibration — prefer a blended or conservative approach to false precision.**

> **Impact decay and capacity interact over days**, so a schedule can look feasible under a same-day model and still be too aggressive once lingering impact is included.

**Four durable research lessons:** execution cost depends on **how** the order is traded, not only what · the execution problem has its own frontier — impact buys immediacy, patience buys a lower footprint · **capacity is endogenous to execution style**, so the same signal may be viable under patient trading and infeasible under urgent liquidation · **urgency should be tied to alpha decay** — a signal with a half-life in minutes should not use a schedule designed for daily rebalancing.

> **The principal contribution is organizational: it converts execution from ad hoc judgment into a model with named inputs and observable trade-offs.**

---

## 7. TCA — the feedback that keeps models calibrated

**Implementation shortfall** = decision price vs. execution price. **For sells, negate the numerator. For multi-leg trades, compute per leg and aggregate by notional weight.** It captures spread, slippage, impact, and timing in one number — **the difference between the paper portfolio and the executed portfolio.**

**But IS is diagnostic only after decomposition:**

| Component | Example share |
|---|---|
| Spread cost | **35%** |
| Explicit fees | **25%** |
| Impact cost | 22% |
| Timing/slippage | 18% |

> **Timing can help or hurt, and that sign matters — it separates bad luck from bad scheduling.**

> **The question a TCA report answers before anything else: was the cost market-driven or execution-driven?** Market-driven (volatility spike, news, market-wide liquidity deterioration) **calls for better regime conditioning.** Execution-driven (participation too aggressive for available depth, stale parameters, poorly timed schedule) **calls for policy changes. Without that separation, TCA is descriptive accounting rather than a calibration tool.**

> **Condition TCA on regime or the comparison set is unfair.** "Bad fills" in a high-volatility period may be **good execution given conditions**, while identical fills in a calm period indicate failure. **Comparing stressed open-auction fills with calm midday fills produces noise, not evidence.**

**Closing the loop — residuals tell you what to fix:** systematic underestimation → coefficients too low · **regime-specific residuals → conditioning is missing** · **size-specific residuals → the impact function is misspecified.**

> **The strongest calibration test compares backtested net PnL with realized live PnL over the same strategy logic. Persistent divergence means the cost model is wrong. Vendor coefficients are starting values, not authority.**

### Risk-model-driven turnover — the hidden cost

> **A null experiment worth running: hold the alpha signal fixed and recompute weights as only the covariance matrix changes. Large turnover under that null means the risk model is creating trades with no informational content.** The Frobenius norm of the change in factor-mimicking portfolios is a compact summary. **This links directly to Ch. 14's eigenvector-stability problem — unstable loadings become unnecessary turnover unless estimation is stabilized.**

**A TCA report must support decisions:** summary statistics (average IS, fill rate, completion time) · attribution separating spread, impact, timing, missed fills · regime slices by volatility, time of day, size bucket · **a validation page comparing predicted with realized costs. If the report cannot tell the desk which parameters to change, it is incomplete.**

---

## 8. Guardrails

### Break-even turnover and minimum required edge

**Break-even turnover ≈ expected gross annual return ÷ round-trip cost per unit turnover.** 5% gross return at 25 bps → **~20× capital of annual turnover** before costs consume the edge.

**Minimum required edge** inverts it: 20 bps round-trip over a 5-day average holding period → **4 bps per day just to cover costs.** If the signal is worth 2 bps/day, **it is not viable at that cadence.**

> **These are the same constraint in different algebraic forms. Use both — if they disagree, either the turnover estimate or the cost estimate is wrong.**

> **Once turnover moves into the high single digits, even modest execution costs demand implausibly large pre-cost alpha.**

### Alpha-to-go — the ranking metric that replaces raw IC

> **If rebalancing is costly, the relevant quantity is not today's expected return but the cumulative cost-discounted expected return over the holding period** — the signal's value after building the position and eventually unwinding it. For an AR(1) signal with persistence φ, the discount depends on both φ and the speed-of-trading parameter.
>
> **A fast-decaying signal with high impact costs has very low alpha-to-go: by the time the position is built, the signal has disappeared. Slow signals with long half-lives amortize entry costs and retain most of their raw alpha. The useful ranking metric is cost-adjusted signal quality, not raw IC in isolation.**

Alpha-to-go sits **between model output and allocation** — the cost-aware filter determining how much predicted alpha is capturable.

### Capacity

**Capacity is not a fixed number** — it is the AUM at which net Sharpe drops below a minimum threshold. **Linear costs produce linear Sharpe degradation; square-root costs produce concave degradation, so capacity increases less than linearly with AUM.**

**Participation-based first pass:** 5% max participation on a $1B ADDV universe → **$50M capacity for a fully-rebalanced daily strategy (turnover = 1), rising to ~$250M at 20% daily turnover.**

> **Participation caps constrain daily trading flow first; portfolio capacity follows only after turnover is specified.** The same logic applies to the impact-adjusted version — the impact model determines maximum daily traded notional within a cost budget, and **turnover converts that into deployable capital.**

**Capacity varies dramatically by anomaly:** low-turnover strategies (size, profitability) absorb much larger bases; **momentum capacity decays at substantially lower AUM; high-frequency strategies typically have capacities an order of magnitude smaller.**

### Kill switches and the repair ladder

**Define kill criteria before deployment, not during stress.** Absolute triggers catch slow bleed (sustained negative net returns, IS far above budget, chronic underfilling); relative triggers compare realized to modeled cost (rolling overshoot, cost-adjusted Sharpe below threshold). **The common feature is precommitment: the strategy stops because it violates a published operating rule, not because confidence was later lost.**

**Repair before abandoning:** reduce turnover, improve execution, narrow the universe to liquid names, accept lower capacity. **These target the implementation channel directly rather than pretending the research signal changed. If they still cannot produce acceptable net performance, drop the strategy regardless of gross backtest quality.**

### The options cascade — execution discipline flipping a conclusion

*Systematic short straddle on S&P 500 constituents with daily delta hedging:*

| Rung | Change | Result |
|---|---|---|
| **1. Naive round-trip** | Enter Friday, hold 10 days, close at market — **both legs cross the spread** | **Decisively unprofitable.** Entry-leg cost comparable in magnitude to position notional; **the option bid-ask consumes the VRP before any signal is realized** |
| **2. Hold to expiry** | Contract settles at intrinsic value — **the exit bid-ask is never paid** | Moves to **negative Sharpe within a wide bootstrap interval** — indistinguishable from flat at best |
| **3. + liquid-universe filter** | Restrict to **bottom quintile of relative half-spread** (~120 of ~600 names) | **Validation +0.160 [−0.975, +1.778], holdout +0.974 [−0.836, +3.135]** |

> **Three features deserve attention.** The cascade is **monotonic** — each rung is a real improvement and the holdout point estimate crosses zero only once both are applied. The improvement is **large enough to flip the qualitative deployability conclusion**, even though the interval still straddles zero. And **the mitigation does not compose without limit** — tightening past the bottom quintile leaves an execution set too thin to diversify across. **A short staircase, not a parameter to push.**

> **The result is conditional on a lenient assumption.** The cost model charges only **20.3% of the quoted option half-spread** (~2.6¢ effective against a 12.8¢ quoted half-spread) — **the strategy-favorable end of the range, with newer auction-based evidence putting the realized fraction materially higher.** This is why the synthesis sweeps the spread fraction (0.203, 0.5, 0.75, 1.0) rather than fixing a point.

> **And the honest caveat on the number itself: annualized Sharpe on a twelve-month window carries a standard error of roughly ±1.** The meaningful shift is from "indistinguishable from a sizable loser" to "indistinguishable from flat" — **a change in the qualitative deployability conclusion, not a claim about a specific Sharpe.** But the direction matters: **rung 1 to rung 3 is not a small effect that disappears under multiple-testing adjustment. It is the difference between an execution discipline that fits the instrument's microstructure and one that does not.**

### When the cost model, not the signal, drives the conclusion

*US equities panel, ~3,200 names: an 11-point bps grid (0–50 bps/leg) vs. a six-point per-share grid (0–10¢).*

At low cost the regimes agree (**bps mean 1.93 at 10 bps, per-share mean 1.90 at 1¢**) because the median post-2001 adjusted price of ~$18.44 makes a 1¢ half-spread roughly half a basis point. **Then they diverge: the bps grid stays positive through 20 bps (0.86) and barely positive at 30 bps (0.01), while the per-share grid decays sharply through 2.5¢ (0.66) and turns negative at 5¢ (−0.29).**

> **The cause is applying a constant per-share charge to adjusted historical prices spanning a wide nominal range. The same position costing 5 bps at $200 costs 50 bps when the adjusted history prints at $20, and 200 bps if a 1990s split sequence pushed it to $5.**

**Practical rule:** use **bps-of-notional when the universe spans a wide adjusted-price range.** Use fixed per-share-plus-spread only when nominal prices are relatively stable **or** per-asset spreads are measured from quote data. **Use both for sensitivity. When the two regimes disagree about survival, the disagreement is a diagnostic about the cost model, not a finding about the signal.**

---

## Transferable rules

1. **Model costs from feature evaluation onward, not as a final haircut.** Turnover and IC must be judged together.
2. **There is no universal cost number.** Routing, urgency, and execution style determine whether an edge survives — TAQ-based estimates and zero-cost assumptions err in opposite directions.
3. **Model financing, borrow, and transaction taxes explicitly.** They are the costs most often omitted and can exceed the spread.
4. **Separate temporary from permanent impact** — only the temporary component responds to scheduling and venue choice.
5. **Capacity depends on who else is trading the idea.** It is not a static property of the signal.
6. **Match model complexity to participation:** spread below 0.5% ADV, linear to 2%, square-root above.
7. **Use the upper end of published impact-coefficient ranges when calibrating from priors,** and the stressed parameters when the regime is ambiguous.
8. **Backtest with contemporaneous regime costs** so crisis periods pay crisis prices.
9. **Replace notional-bps whenever traded price and notional exposure are not proportional** — options are the canonical case.
10. **Execution algorithms trade impact against timing risk; they do not remove cost.** Tie urgency to alpha decay.
11. **Generate execution schedules under multiple scenarios.** Wide trajectory variation means the trade is fragile to miscalibration.
12. **Decompose implementation shortfall before acting on it,** and always ask whether the cost was market-driven or execution-driven.
13. **Condition TCA on regime,** or the comparison set is unfair in both directions.
14. **Read TCA residual structure as a specification diagnostic:** regime-specific residuals mean missing conditioning; size-specific residuals mean a misspecified impact function.
15. **Test how much turnover your risk model creates with the signal held fixed.** Covariance churn is trades with no informational content.
16. **Rank signals by alpha-to-go, not raw IC.** A fast signal with high impact cost can be worthless by the time the position is built.
17. **Compute break-even turnover and minimum required edge both ways;** disagreement means one of the inputs is wrong.
18. **State capacity as a function of AUM and a Sharpe threshold,** and remember turnover, not participation alone, converts flow limits into capital limits.
19. **Precommit kill criteria before deployment.**
20. **Try the repair ladder before abandoning** — turnover, execution, universe, capacity — but drop the strategy if net performance stays unacceptable.
21. **Run both fixed and relative cost regimes.** Disagreement diagnoses the cost model, not the signal.

---

## Notebooks

`01_cost_taxonomy` (cross-asset fee schedules, breakeven, decomposition primitives) · `02_spread_estimation` (regime-conditioned empirical spreads) · `03_market_impact_calibration` (η by VIX regime; feeds the capacity formula) · `04_vwap_twap_execution` · `05_almgren_chriss_optimal_execution` (scenario-based planning) · `06_ml4t_execution_demo` (`ml4t.backtest.execution` API) · `07_ml4t_volume_participation` (participation-gated mechanics) · `08_ml_dynamic_execution` (ML-based adaptive execution) · `09_frequency_tradeoff` (cadence vs. cost) · `10_gross_vs_net_performance` (break-even, capacity, null-turnover decay) · `11_cost_cliff` (HF viability stress tests) · `12_commission_slippage_comparison`

**Case studies:** `sp500_options/14_costs.ipynb` (the three-rung cascade) · `us_equities_panel/18_costs.ipynb` and `sp500_equity_option_analytics/16_costs.ipynb` (dual-regime sweeps) · `etfs/16_costs.ipynb` (per-share with tiered commissions)

**Tooling:** pyfolio TCA module, tca-tools for IS decomposition; Bloomberg TCA and Virtu Analytics for standardized FIX-protocol institutional reports.

---

## Cross-references

Ch. 3 microstructure, order types, FIX protocol · Ch. 7–8 cost-aware signal thresholds; scoring factors against break-even turnover rather than raw IC · Ch. 14 eigenvector stability, whose failure becomes null turnover here · Ch. 16 §16.2 the cost model in the backtest protocol; §16.6 cost-sensitivity sweeps and break-even diagnostics · Ch. 17 turnover constraints and position limits as cost decisions; costs as MVO regularizer · Ch. 19 capacity and execution stress as risk limits · Ch. 20 §20.6 cross-case cost-survival tables and the spread-fraction sweep

---

## Citations

Almgren & Chriss (2001), optimal execution · Amihud (2002), illiquidity measure · Avellaneda & Stoikov (2008), market-making inventory · Bouchaud (2022), market inelasticity · Chan (2022), multi-day impact decay and capacity · Chordia, Roll & Subrahmanyam (2000), commonality in liquidity · Cont et al. (2014), depth- and imbalance-dependent impact · Donnelly (2022), robust execution under model uncertainty · Eisler et al. (2010), order-book impact · Frazzini, Israel & Moskowitz (2018), live institutional execution costs · Gabaix & Koijen (2021), inelastic markets · Hasbrouck (1991), informational impact measurement · Hautsch & Huang (2012), limit order flow · Heston et al. (2023) · Ho & Stoll (1981), inventory-based spreads · Karnaukh et al. (2015), FX liquidity · Kyle (1985), linear impact · Madhavan (2002), implementation shortfall · Muravyev & Pearson (2020), effective option spreads · Nevmyvaka, Feng & Kearns (2006), RL for execution · Obizhaeva & Wang (2013), order-book resilience · O'Donovan & Yu (2024), option cost mitigation cascade · Paleologo (2025), alpha-to-go; risk-model turnover · Perold (1988), implementation shortfall · Said (2022), market- vs. execution-driven attribution · Sato & Kanazawa (2024), square-root exponent across asset classes · Schwarz et al. (2022), retail broker execution dispersion · Taranto et al. (2018), order-flow-dependent impact · Toth et al. (2011), square-root law and order-book dynamics · Wagner & Edwards (1993)

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 18.*
