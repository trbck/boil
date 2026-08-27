# Rules — Risk, drawdown & survival

`41` rules · ~725 words · ~978 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-04 — Regime Definition

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-04-R10** — **Choose your floor/ceiling baseline consciously**: `_chg` = nervous with many stops; fractal price = the production default with smaller sizes and lower risk appetite.

### ASSP-05 — The Trading Edge Is a Number, and Here Is the Formula

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-05-R11** — **In mean reversion, stationarity is the stop loss.** When it breaks, stop trading the pair.

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R8** — **Cap single-trade risk at ~2%.** A ⅓ win rate implies routine 10-loss runs and 25-loss tails → 30–50% drawdowns at 2%.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R3** — **Drive gross with `risk_appetite()`** — measure drawdown from peak, normalize against tolerance, EWM-smooth, apply a response curve, scale into bands. Set tolerance at ~**40% of annual volatility**.
- **ASSP-08-R9** — **Beware the two net-reduction cheats**: oversized short bets and index futures. Both cut net while leaving real risk intact.
- **ASSP-08-R14** — **Stay on main exchanges when risk is off.** The reverse trade (long blue chips / short speculation) does not execute.

### ASSP-09 — Asset Allocation

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-09-R1** — **Define smoothness as drawdown depth × duration × frequency**, never as volatility or Sharpe.
- **ASSP-09-R2** — **Simulate strategy returns, not asset prices.** Distribution shape is an emergent property of exit rules, not of the instrument.
- **ASSP-09-R4** — **Never let recent volatility drive allocation.** Left-skewed strategies are at their calmest immediately before failing.
- **ASSP-09-R5** — **Do not penalize right-skewed strategies for drawdowns.** Drawdowns are the price of convexity.
- **ASSP-09-R7** — **Derive position caps from failure geometry**: min(st_dd_tolerance/st_dd, lt_dd_tolerance/lt_dd) × (1 − corr) × (1 − liquidity haircut).
- **ASSP-09-R9** — **Remove leverage faster than you add it.** Asymmetric response is the design goal.
- **ASSP-09-R10** — **Boost the working strategy when its counterpart fails**, and turn the boost off when both work or both fail. Smooth it monthly.
- **ASSP-09-R12** — **Make max drawdown tolerance the single control parameter.** Leverage becomes a consequence, not an input.

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R4** — **Preserve intent fields (price, stop, target, risk) on missed trades** — that is the data that reveals *why* you didn't act.
- **ASSP-10-R13** — **Calibrate stops with MAE**, and classify strategies with **MFE/MAE** (>1 trend following, <1 mean reversion).
- **ASSP-10-R14** — **Measure drawdowns on all three axes** (depth, duration, frequency) and consecutive losses on two (max run, average run). Size down during losing streaks.

### ML4T-06 — Strategy Research Framework

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-06-R3** — **Prefer edges grounded in constraints over edges grounded in information.** Information edges erode on replication; constraint and risk-tolerance edges survive publicity.

### ML4T-12 — Advanced Models for Tabular Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-12-R14** — **Loss function choice can dominate depth.** On heavy-tailed targets, MAE's refusal to chase extremes is worth more than extra capacity.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R10** — **Never read max drawdown as a standalone quality measure** — it is an extreme statistic that grows with sample length.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R12** — **Volatility-match the short leg** rather than equal-notional dollar neutrality.

### ML4T-19 — Risk Management

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-19-R1** — **Build every adaptive control from information available at decision time,** and treat model-inferred regimes as a leakage channel unless the state path is never re-estimated.
- **ML4T-19-R2** — **A control that cannot be specified ex ante and reconstructed afterward is not a valid control.**
- **ML4T-19-R3** — **Variance is the highest moment you can usually estimate.** Treat skewness, kurtosis, and deep quantiles as requiring stronger assumptions or much more data.
- **ML4T-19-R4** — **Report VaR and CVaR together,** and prefer historical simulation as the base method — Cornish-Fisher destabilizes at high confidence under realistic kurtosis.
- **ML4T-19-R5** — **Use the Cantelli bound as a distribution-free floor** when parametric methods are untrustworthy.
- **ML4T-19-R6** — **Compute tail metrics by regime and present worst-regime CVaR prominently.** Unconditional estimates average over states that differ by ~2.7×.
- **ML4T-19-R7** — **Apply liquidity haircuts to tail estimates** — the effect can be 50–100% of effective VaR.
- **ML4T-19-R8** — **Evaluate volatility models with QLIKE for risk and variance-MSE for alpha.** Other loss functions reverse rankings depending on the proxy.
- **ML4T-19-R9** — **Measure duration and recovery time, not just drawdown depth.** Investors redeem before recovery, and their realized return is worse than the strategy's.
- **ML4T-19-R10** — **Distinguish gamma from delta drawdowns** — they call for different hedges.
- **ML4T-19-R11** — **Report factor attribution with HAC confidence bands.** A contribution whose interval spans zero did not "drive" performance.
- **ML4T-19-R12** — **Span every asset class held in the factor model,** or cross-asset exposures get misattributed to alpha.
- **ML4T-19-R14** — **Monitor exposures on a rolling basis.** Static loadings silently mis-size hedges as tilts drift.
- **ML4T-19-R15** — **Stress costs alongside returns.** Historical replay alone understates execution damage in crisis.
- **ML4T-19-R16** — **Map every discovered vulnerability to accepted risk, a hedge, reduced exposure, or a trigger** — and enforce it with a written memo.
- **ML4T-19-R19** — **Calibrate stops from the strategy's own MAE/MFE excursions,** and judge them by realized exit behavior rather than headline drawdown.
- **ML4T-19-R20** — **Use learned exits to size winners, not to replace stops on losers.**
- **ML4T-19-R21** — **Wrap learned policies in hard deterministic envelopes.**
- **ML4T-19-R22** — **Prefer graduated escalation to a binary cutoff,** because mechanical drawdown rules can lock in losses that would have recovered.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R18** — **Halt immediately on hard loss limits.** Do not wait for review; do not trade out of the hole.

