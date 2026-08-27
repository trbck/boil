# Rules — Regime detection & market state

`23` rules · ~426 words · ~575 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-03 — Long/Short Methodologies: Absolute and Relative

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-03-R6** — **Treat valuation as sector- and regime-conditional.** Cheap PBR in machinery is a sell signal, not a buy.
- **ASSP-03-R7** — Track **sector rotation**, not market tops and bottoms. Use `cyclicals − defensives` on the relative series; negative → defensive posture.

### ASSP-04 — Regime Definition

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-04-R1** — **Regime is triage, not forecasting.** Its job is to allocate research effort, not to predict.
- **ASSP-04-R2** — **Use the same regime model on both sides.** Trend-following longs plus mean-reverting shorts is two contradictory models.
- **ASSP-04-R3** — **Compute fractals on `mean(H, L, C)`, never on Close alone.** Close-based fractals land several bars off the true turn.
- **ASSP-04-R4** — **Prefer parameter-free primitives.** Fractals port across timeframes and asset classes; RSI(14) and MACD(12,26) do not.
- **ASSP-04-R5** — **Blend methods; do not crown one.** A weighted average of eight regime methods beats the best single one. Robustness comes from averaging, not from tuning weights.
- **ASSP-04-R6** — **Weight lower fractal levels more heavily** (`{1:0.1, 2:0.4, 3:0.3, 4:0.2}`) — high levels lag badly at regime turns.
- **ASSP-04-R7** — **Floor and ceiling only needs one condition** (a lower high, or a higher low) vs. three sequential conditions for higher-highs. It is more stable and it is the method of choice.
- **ASSP-04-R8** — **Only two regimes.** Sideways is a pause inside a bull or bear context. Stability beats responsiveness for position management.
- **ASSP-04-R9** — **In production, detect fractals by diffing the last row**, not by recomputing history.
- **ASSP-04-R10** — **Choose your floor/ceiling baseline consciously**: `_chg` = nervous with many stops; fractal price = the production default with smaller sizes and lower risk appetite.
- **ASSP-04-R11** — **The composite score is a sizing input**, not just a filter — multiply it into the position sizing algorithm for strength-adjusted sizing.
- **ASSP-04-R12** — **Long-lookback breakouts need a time exit.** Halve size when a position has not made new extremes after half the duration.

### ASSP-05 — The Trading Edge Is a Number, and Here Is the Formula

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-05-R8** — **Short only in sideways or bear regimes**, and enter when a **bear-market rally rolls over** — not on breakdowns.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R4** — **Choose the response curve by market shape:** linear for trending, aggressive (convex) for sideways/bear-trap regimes, conservative (concave) when you want to stay defensive longer.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R5** — Regimes gate risk posture, never entry timing.
- **ML4T-01-R6** — Drift is a flag; always follow it with a four-way diagnosis (data / feature / execution / regime).

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R14** — **Report all standard regimes including the unfavorable ones,** and pre-specify definitions to avoid regime snooping.
- **ML4T-16-R15** — **Ask whether regime dependence is intentional and compensated,** not merely whether it exists.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R7** — **Use the upper end of published impact-coefficient ranges when calibrating from priors,** and the stressed parameters when the regime is ambiguous.
- **ML4T-18-R13** — **Condition TCA on regime,** or the comparison set is unfair in both directions.
- **ML4T-18-R14** — **Read TCA residual structure as a specification diagnostic:** regime-specific residuals mean missing conditioning; size-specific residuals mean a misspecified impact function.

