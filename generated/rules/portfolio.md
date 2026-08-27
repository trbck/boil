# Rules — Portfolio construction & exposure

`62` rules · ~1081 words · ~1459 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-01 — The Stock Market Game

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-01-R6** — Assume the short book's weights drift adversely by construction; build the correction into the algorithm.

### ASSP-02 — 10 Classic Myths About Short Selling

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-02-R4** — **Never hold a short that requires no maintenance.** The structural short is a myth; every short position needs the same continuous risk process as a long — more, given the adverse weight drift.
- **ASSP-02-R6** — **Run the short book in bull markets too.** Skill decay is real, and downside protection is the product investors are actually paying for.

### ASSP-03 — Long/Short Methodologies: Absolute and Relative

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-03-R2** — **Never mix series across sides.** The long book must mirror the short book's series and signals.
- **ASSP-03-R3** — Choose `rebase=True` for development (memory) and rolling/`rebase=False` for tested production (lightweight, corporate-action-proof). Know which one you are running.
- **ASSP-03-R8** — **Expensive or callable-only borrow is a long signal, not a short signal.**
- **ASSP-03-R10** — Relative stop levels are invisible to hunting algorithms but **require active management** to be fillable.

### ASSP-05 — The Trading Edge Is a Number, and Here Is the Formula

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-05-R4** — **Track two durations**: long for "does it make money over time," short for cyclicality → exposure allocation.

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R7** — **Never equal-weight.** Volatility ignored at the position level reappears at the portfolio level.
- **ASSP-06-R10** — **Prefer ATR** among volatility measures — most stable, lowest readings; but expect higher gross exposure and turnover.
- **ASSP-06-R15** — **Net exposure is a property of the signal; gross exposure is a property of the sizing.** Do not confuse the two knobs.

### ASSP-07 — Refining the Investment Universe

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-07-R12** — **Size inversely to beta**, and understand that beta-neutral implies **negative** net exposure. Net exposure and net beta are different constraints.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R1** — **Risk management is the business.** The four levers (gross, net, net beta, concentration) are the entire dashboard.
- **ASSP-08-R2** — **Gross exposure is the accelerator and the brake.** Make it dynamic, not fixed.
- **ASSP-08-R3** — **Drive gross with `risk_appetite()`** — measure drawdown from peak, normalize against tolerance, EWM-smooth, apply a response curve, scale into bands. Set tolerance at ~**40% of annual volatility**.
- **ASSP-08-R5** — **Keep gross bands sane** — 50–100% multi-strategy, 40–60% single strategy. Deleveraging has market impact.
- **ASSP-08-R6** — **Never lever a left-skewed strategy** because the win rate looks safe. That is how they die.
- **ASSP-08-R7** — **Net exposure is a view, not a risk measure.** Always read it alongside net beta.
- **ASSP-08-R8** — **Keep borrow utilization below 40%** at the portfolio level (Ch. 7 excludes names above 50% at the security level).
- **ASSP-08-R9** — **Beware the two net-reduction cheats**: oversized short bets and index futures. Both cut net while leaving real risk intact.
- **ASSP-08-R10** — **Bear-market target: negative net beta with neutral-to-positive net exposure.** Not negative net exposure — that buys alpha at the cost of violent volatility.
- **ASSP-08-R11** — **Run structurally more names short than long** (net negative concentration). It is the only way to keep short-book volatility from driving the portfolio, and it is only possible on relative series.
- **ASSP-08-R12** — **Cap the largest-to-smallest bet ratio at 2.5.** Below it, tracking error and AUM stability improve materially.
- **ASSP-08-R13** — **Name count must scale with gross exposure** if the volatility target is fixed.
- **ASSP-08-R14** — **Stay on main exchanges when risk is off.** The reverse trade (long blue chips / short speculation) does not execute.
- **ASSP-08-R15** — **Write the mandate down**, including the skew of your return distribution.

### ASSP-09 — Asset Allocation

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-09-R2** — **Simulate strategy returns, not asset prices.** Distribution shape is an emergent property of exit rules, not of the instrument.
- **ASSP-09-R3** — **Model each strategy's failure mode explicitly** — single-day replace-mode jumps for left skew, block-replacement regimes for right skew — plus correlated portfolio-level shocks.
- **ASSP-09-R4** — **Never let recent volatility drive allocation.** Left-skewed strategies are at their calmest immediately before failing.
- **ASSP-09-R6** — **Among classic allocators, prefer equal weight.** Its naivety is a feature: it does not rebalance into failure.
- **ASSP-09-R8** — **Let upper bands sum above 1.** Elasticity that is *earned* — both strategies working, equity near highs, oscillator at peak — is not the same as an arbitrary leverage cap.
- **ASSP-09-R9** — **Remove leverage faster than you add it.** Asymmetric response is the design goal.
- **ASSP-09-R10** — **Boost the working strategy when its counterpart fails**, and turn the boost off when both work or both fail. Smooth it monthly.
- **ASSP-09-R11** — **Path dependency requires recursion.** `equity[t-1]` must determine allocation at `t`; pre-fill arrays with NaN.
- **ASSP-09-R13** — **Read allocation scorecards in two columns**: comfort metrics (Sharpe, MaxDD, win rate) and robustness metrics (profit ratio, tail ratio, gain expectancy, common sense ratio). Optimize the second.
- **ASSP-09-R14** — **A profit ratio below 1 with a high win rate is the left-skew trap.** Check both together, always.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R13** — **Attention weights are routing, not explanation.**

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R9** — **Report effective sample size whenever weights are applied,** and verify the reweighted set spans multiple regimes.

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R4** — **Prefer idiosyncratic-volatility normalization to correlation PCA** — it removes noise without flattening genuine differences in common-factor exposure.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R16** — **Weight edges by cross-method agreement and effect magnitude,** not by p-value or by any single implementation.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R1** — **The allocator is a model.** Specify its objective, inputs, constraints, and evaluation before implementing an optimizer.
- **ML4T-17-R2** — **Constraints are part of the estimator.** They regularize the mapping from noisy inputs to weights, and each has a robustness reading.
- **ML4T-17-R3** — **Effective breadth, not nominal breadth, drives realized IR.** Correlated positions are not independent bets.
- **ML4T-17-R4** — **Read IC as R².** An IC of 0.03 explains ~0.09% of cross-sectional variance — value comes from repetition, not single-name predictability.
- **ML4T-17-R5** — **Match estimation-window horizons to signal horizons deliberately,** not by default settings.
- **ML4T-17-R6** — **Treat allocator hyperparameters as tunable parameters requiring out-of-sample validation.** Holding the forecast model fixed does not protect against fitting the allocator to the answer key.
- **ML4T-17-R7** — **Check risk contribution, not just capital concentration.** Equal capital weights ≠ equal risk contributions.
- **ML4T-17-R8** — **Judge covariance models by the portfolios they generate,** not by matrix-fit metrics.
- **ML4T-17-R9** — **Clear equal weight before taking any allocator seriously.** Estimation error often overwhelms the theoretical gains from optimization.
- **ML4T-17-R10** — **Alpha ranking matters more than alpha calibration.** Scale error is absorbed by leverage; ranking error is not.
- **ML4T-17-R11** — **Hedge in proportion to the reliability of the exposure estimate.** Full neutralization on a noisy beta can raise realized variance.
- **ML4T-17-R12** — **Volatility-match the short leg** rather than equal-notional dollar neutrality.
- **ML4T-17-R13** — **Treat full Kelly as an upper bound.** Raw Kelly implies 30×+ leverage on real data.
- **ML4T-17-R14** — **Expect narrow allocator spreads.** Best-to-worst of 0.12 Sharpe against a cost channel that moved returns from +46.6% to +1.5%.
- **ML4T-17-R15** — **Allocator optimization helps most where signal is strongest** — and cannot rescue a weak signal-cost combination.
- **ML4T-17-R16** — **Pool the Sharpe across the universe when training end-to-end,** and use a two-pass gradient because Sharpe is non-separable across mini-batches.
- **ML4T-17-R17** — **Report the cost-stress curve, not the gross number.** Gross parity with heuristics can vanish entirely by 20 bp.
- **ML4T-17-R18** — **Make seed variance a reported metric for learned allocators.**
- **ML4T-17-R19** — **Respect closing calendars in cross-sectional attention** — asynchronous closes are a lookahead channel.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R9** — **Replace notional-bps whenever traded price and notional exposure are not proportional** — options are the canonical case.

### ML4T-19 — Risk Management

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-19-R13** — **Check residual correlations and precision-matrix stability** before trusting a covariance model in an optimizer.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R13** — **Shadow every candidate long enough to span multiple regimes,** with at least two rebalance cycles.

