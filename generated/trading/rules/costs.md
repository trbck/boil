# Rules — Costs, liquidity & capacity

`85` rules · ~1968 words · ~2656 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-02 — 10 Classic Myths About Short Selling

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-02-R1** — **Model the frictions as first-class constraints**: borrow availability (3–5% of float), locate, uptick rule, SSR at −10%, jurisdictional bans. A backtest without them overstates short performance systematically.
- **ASSP-02-R2** — **Build shorts around institutional liquidation flow**, not around fundamental doom. You are following size, not leading it.
- **ASSP-02-R3** — **Exclude the squeeze geometry explicitly**: high short interest ∧ thin trading ∧ exhausted selling pressure. Crowded shorts are false positives (Ch. 1 §4).
- **ASSP-02-R5** — **Prefer relative underperformance as the short thesis.** Sustainable, non-confrontational, and it is what the rest of the book is engineered around.

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R6** — **Express conviction in units of risk**, never in units of feeling.
- **ASSP-06-R13** — **Continuous resizing costs you the average price** (FIFO drags it toward the trend) and costs commissions. Budget for both.
- **ASSP-06-R14** — **Capacity is signaled by inertia**, not by a formula.

### ASSP-07 — Refining the Investment Universe

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-07-R1** — **Judge short liquidity by the exit, never the entry.** Liquidity is thinner on the way out than the way in, structurally.
- **ASSP-07-R2** — **Borrow utilization > 50% is a hard exclusion.** Not a caution — an exclusion.
- **ASSP-07-R3** — **Crowded shorts are anti-hedges.** They outperform in pullbacks because there is no institutional long money left to sell.
- **ASSP-07-R4** — **Expensive or callable-only borrow is a long signal** (Ch. 3 §7), not a short signal.
- **ASSP-07-R5** — **High dividend yield is a short *source*, not a short deterrent** — the yield defers the decline, it does not prevent it.
- **ASSP-07-R6** — **Never short a name doing buybacks.** You are fighting an unlimited, price-insensitive bid.
- **ASSP-07-R7** — **Short liability for dividends is real.** Maintain a dividend calendar per short position.
- **ASSP-07-R8** — **Rich valuation alone is never a short thesis.** The thesis is rich valuation + decelerating earnings momentum = multiples compression.
- **ASSP-07-R9** — **Expensive PBR = investing cash flow financed by financing cash flow.** Never hold those long through a bear market.
- **ASSP-07-R10** — **Let regime ask the question, let fundamentals answer it.** "Why is it going down?" beats "why should it go down?"
- **ASSP-07-R11** — **Beta *momentum* beats beta *level*.** Rising beta → worse returns; falling beta → better returns. Both contradict CAPM.
- **ASSP-07-R13** — Resample to month-end for beta — daily rolling beta costs a great deal of compute for no signal.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R5** — **Keep gross bands sane** — 50–100% multi-strategy, 40–60% single strategy. Deleveraging has market impact.
- **ASSP-08-R8** — **Keep borrow utilization below 40%** at the portfolio level (Ch. 7 excludes names above 50% at the security level).

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R1** — **Log missed trades and overrides, not just fills.** The executed log is the surviving fleet; the missed signals are the planes that never came back.
- **ASSP-10-R5** — **FIFO with per-lot patching** handles pyramids, partial exits, and reversals in one code path. Pro-rate commission across closed lots; carry the position sign into the P&L calculation.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R3** — Run the tradability check *early*, not after signal refinement.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R6** — Represent instrument families at the right abstraction: options → surfaces, futures → raw contracts *plus* continuous variants, commodities → contract spec in the data, DEX → slippage from reserves.

### ML4T-03 — Market Microstructure

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-03-R1** — Backtests that assume fills at the close mis-model price formation, not just costs. Model spread, depth, and queue explicitly.
- **ML4T-03-R2** — Liquidity is three things (spread/depth/resiliency); check the one your strategy actually needs.
- **ML4T-03-R3** — Intraday seasonality is a confounder before it's a feature — the same signal means different things at different times of day.
- **ML4T-03-R4** — Choose the feed level by what your signal *requires*; L1 signals are crowded precisely because L1 is cheap.
- **ML4T-03-R5** — Midprice for signal measurement, executable prices for PnL. Report both markouts; the gap is the tradability test.
- **ML4T-03-R6** — Reconstruction is accounting — enforce invariants and fail fast; a venue-local book is not the market.
- **ML4T-03-R8** — Information bars are gated by trade-classification accuracy: Lee-Ready ~95% vs. tick test ~80%. Reconstruct the book to get quotes if you need imbalance bars.
- **ML4T-03-R10** — Use jump-robust local volatility (Lee–Mykland) rather than daily-σ thresholds — the naive rule fails in both directions depending on the day.
- **ML4T-03-R11** — Flag and exclude; never interpolate ticks and quotes.
- **ML4T-03-R13** — Nulls in a continuously-sessionized panel may mean "no activity," not "missing data." Check before aggregating.

### ML4T-07 — Defining the Learning Task

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-07-R8** — **Thresholds set both event magnitude and base rate simultaneously** — choose them against the turnover and cost budget, and estimate percentiles within-fold.
- **ML4T-07-R13** — **A gross spread that doesn't clear estimated costs is a stop, not a revise.**

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R8** — **Report turnover alongside every statistical metric.** No statistical metric measures tradability.

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R6** — **Measure eigenvector stability with cosine similarity and apply Procrustes rotation when eigenvalues cluster.** Unstable loadings generate phantom turnover that costs real money.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R3** — **Record the protocol before interpreting results** — timing, rebalance, sizing, fills, constraints, costs.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R14** — **Expect narrow allocator spreads.** Best-to-worst of 0.12 Sharpe against a cost channel that moved returns from +46.6% to +1.5%.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R1** — **Model costs from feature evaluation onward, not as a final haircut.** Turnover and IC must be judged together.
- **ML4T-18-R2** — **There is no universal cost number.** Routing, urgency, and execution style determine whether an edge survives — TAQ-based estimates and zero-cost assumptions err in opposite directions.
- **ML4T-18-R3** — **Model financing, borrow, and transaction taxes explicitly.** They are the costs most often omitted and can exceed the spread.
- **ML4T-18-R4** — **Separate temporary from permanent impact** — only the temporary component responds to scheduling and venue choice.
- **ML4T-18-R5** — **Capacity depends on who else is trading the idea.** It is not a static property of the signal.
- **ML4T-18-R6** — **Match model complexity to participation:** spread below 0.5% ADV, linear to 2%, square-root above.
- **ML4T-18-R7** — **Use the upper end of published impact-coefficient ranges when calibrating from priors,** and the stressed parameters when the regime is ambiguous.
- **ML4T-18-R8** — **Backtest with contemporaneous regime costs** so crisis periods pay crisis prices.
- **ML4T-18-R9** — **Replace notional-bps whenever traded price and notional exposure are not proportional** — options are the canonical case.
- **ML4T-18-R10** — **Execution algorithms trade impact against timing risk; they do not remove cost.** Tie urgency to alpha decay.
- **ML4T-18-R11** — **Generate execution schedules under multiple scenarios.** Wide trajectory variation means the trade is fragile to miscalibration.
- **ML4T-18-R12** — **Decompose implementation shortfall before acting on it,** and always ask whether the cost was market-driven or execution-driven.
- **ML4T-18-R13** — **Condition TCA on regime,** or the comparison set is unfair in both directions.
- **ML4T-18-R14** — **Read TCA residual structure as a specification diagnostic:** regime-specific residuals mean missing conditioning; size-specific residuals mean a misspecified impact function.
- **ML4T-18-R15** — **Test how much turnover your risk model creates with the signal held fixed.** Covariance churn is trades with no informational content.
- **ML4T-18-R16** — **Rank signals by alpha-to-go, not raw IC.** A fast signal with high impact cost can be worthless by the time the position is built.
- **ML4T-18-R17** — **Compute break-even turnover and minimum required edge both ways;** disagreement means one of the inputs is wrong.
- **ML4T-18-R18** — **State capacity as a function of AUM and a Sharpe threshold,** and remember turnover, not participation alone, converts flow limits into capital limits.
- **ML4T-18-R19** — **Precommit kill criteria before deployment.**
- **ML4T-18-R20** — **Try the repair ladder before abandoning** — turnover, execution, universe, capacity — but drop the strategy if net performance stays unacceptable.
- **ML4T-18-R21** — **Run both fixed and relative cost regimes.** Disagreement diagnoses the cost model, not the signal.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R6** — **Benchmark embeddings on your own corpus and query mix.** Cross-model spread can be no larger than within-model variation across query types.

### ML4T-25 — Live Trading Systems

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-25-R5** — **Treat broker routing as an execution-quality decision.** Cost dispersion across brokers dwarfs commission differences, and PFOF explains little of it.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R15** — **Phase capital in through explicit gates** — A/B testing with real money reveals illiquidity clustering and market impact that shadow mode cannot.

### NOTE-21-gate-audit-of-the-strategies — §21 gate audit of the strategies repo — seven changes, two falsified hypotheses  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-21-gate-audit-of-the-strategies-R1** — **A gate's false-positive rate is a function of sample size, and reporting a verdict without it is a category error.** The same §21 battery passes 4.0% of no-edge draws at n≈2500 and 8.5% at n≈317 — a 2.1× difference that the verdict line does not carry. Any gate report should print its own calibrated error rate for the sleeve's sample regime beside the verdict.
- **NOTE-21-gate-audit-of-the-strategies-R2** — **Turnover cost does much of a gate's rejecting, so low-turnover strategies face a materially weaker gate.** Switching turnover cost off roughly doubles the null pass rate (4.0% → 9.0% daily, 8.5% → 12.5% event) and roughly triples the near-pass rate. A gate's headline size is therefore only earned by strategies that actually pay for their turnover.
- **NOTE-21-gate-audit-of-the-strategies-R3** — **A block bootstrap cannot generate a left-skew strategy's lethal event, because that event is by construction absent from the sample the strategy survived.** Demonstrated: a synthetic left-skew sleeve scoring §21 PASS 7/7 shows a −27.9% deepest-decile drawdown and 9% of paths negative once single-day replace-mode jumps are injected at 1.5× the worst observed day. The clean bootstrap on such a sleeve measures nothing and reads as reassurance.
- **NOTE-21-gate-audit-of-the-strategies-R4** — **Anchor a break-even cost ratio to the harshest cost the sweep certifies at, never the cheapest tested.** Anchoring to the cheapest row turned a sleeve with 6.7bps break-even into "3.3× headroom"; anchoring to the 20bps corner the gate actually certifies at reports 0.3× and flags it. Where the sweep never crosses zero, extrapolate the terminal slope and label it extrapolated — reporting ">max tested" collapses a Sharpe of 1.7 and a Sharpe of 0.05 into one indistinguishable line.
- **NOTE-21-gate-audit-of-the-strategies-R5** — **New gate content must ship reported-but-not-gating until every candidate has a reading.** Adding a gating checkbox to an established battery retroactively flips the verdict on every stored report, which is the mid-stream definition change `ML4T-01` warns against: improvements stop being interpretable as stronger signal and become changed definitions. Promotion to a gating check is a separate deliberate pass.
- **NOTE-21-gate-audit-of-the-strategies-R6** — **Declaration coverage is the honest measure of whether a choice is frozen, and it is usually far lower than assumed.** In a repo with a mature gate, 11 of 29 sleeves could be given an archetype declaration from their own stated mechanism and only 6 of 29 a holding-period declaration; the rest were reported as undeclared rather than guessed. An audit that reports a mechanism as "added" without its coverage number has not measured anything.
- **NOTE-21-gate-audit-of-the-strategies-R7** — **Guard the switch, not the default.** A configuration whose default is safe can still be unsafe to change: the risk lives in the transition, and the effective control is to require the governing rule ID in the change's written reason, so the acknowledgement lands in the audit journal instead of a dismissed dialog.

### NOTE-options-strategies-on-alpaca-fmp — Options Strategies on Alpaca + FMP: What the Envelope Actually Allows  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-options-strategies-on-alpaca-fmp-R4** — **Ratio spreads, calendars and diagonals are permitted**, contrary to common assumption; the leg-ratio rule is a normalisation, not a prohibition [1][2].
- **NOTE-options-strategies-on-alpaca-fmp-R5** — **Open interest is absent from every options endpoint**, removing the conventional liquidity screen [7][9].
- **NOTE-options-strategies-on-alpaca-fmp-R6** — **FMP's earnings calendar is a mutable record with no versioning** and no distinct confirmed flag, so historical dates are realised dates — a silent lookahead for any earnings-timed strategy [24].
- **NOTE-options-strategies-on-alpaca-fmp-R8** — **The volatility risk premium is roughly the size of one round-trip cost**: about $0.43 per ATM delta-hedged call against a $0.375 mean spread [28].
- **NOTE-options-strategies-on-alpaca-fmp-R9** — **Execution style decides survival** — 1.3 cents effective spread for timed trades against 6.2–8.1 cents for naive spread-crossing, and a scheduled bot is firmly in the second group [29].
- **NOTE-options-strategies-on-alpaca-fmp-R10** — **The mandated backtest engine has no atomic multi-leg fill semantics** and no native options instrument, though it does support fixed per-contract fees correctly [38][39][40].
- **NOTE-options-strategies-on-alpaca-fmp-R11** — **Paper trading performs no liquidity or market-impact modelling** and lags live on assignment reporting by a day, so it validates logic, not edge [3][13][14].
- **NOTE-options-strategies-on-alpaca-fmp-R12** — **Rank by turnover and execution patience, not gross Sharpe.** The cost evidence says this is the axis that determines survival [28][29]. Prefer low-turnover, held-to-expiry structures.
- **NOTE-options-strategies-on-alpaca-fmp-R14** — **Audit the earnings sleeves' date provenance immediately.** If dates came from FMP's mutable calendar, the samples carry lookahead that flatters results invisibly [24]. This is the highest-value check available right now.
- **NOTE-options-strategies-on-alpaca-fmp-R16** — **Model costs as per-contract commission plus spread as a fraction of premium**, calibrated to the conventional effective spread rather than the sophisticated-trader figure [29]. Report break-even cost against assumed cost.
- **NOTE-options-strategies-on-alpaca-fmp-R17** — **Decide explicitly about greeks.** Either build a local IV/greeks pipeline from historical bid/ask and underlying bars — accepting ownership of the solver, including its documented 0DTE and deep-OTM failures [6] — or exclude greek-conditioned archetypes. Do not leave this implicit.
- **NOTE-options-strategies-on-alpaca-fmp-R18** — **Resolve the multi-leg simulation gap before gating any new multi-leg sleeve**, via custom simulation callbacks or an explicit all-or-none pre-check, so simulated fills cannot violate the venue's coverage rule [1][38].
- **NOTE-options-strategies-on-alpaca-fmp-R19** — **Budget the paid OPRA data tier** as a fixed cost of doing options work; the indicative feed is randomised and unsuitable for both live trading and realistic cost modelling [8].

