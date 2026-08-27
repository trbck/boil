# Rules — Position sizing

`18` rules · ~295 words · ~398 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-04 — Regime Definition

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-04-R11** — **The composite score is a sizing input**, not just a filter — multiply it into the position sizing algorithm for strength-adjusted sizing.

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R1** — **Sizing beats picking.** Same signals + same universe + different sizing = different businesses. Optimize sizing before optimizing signals.
- **ASSP-06-R2** — **Every sizing algorithm = NAV allocation ÷ denominator.** Make both explicit; the denominator is where the design lives.
- **ASSP-06-R3** — **Round lots down, sign-preserving.** Naive rounding of negative share counts increases short risk.
- **ASSP-06-R4** — **Compute daily P&L on the existing position before resizing.** Doing it after is lookahead bias — check for this in any backtest you inherit.
- **ASSP-06-R5** — **Never average down.** It degrades three of four edge variables and its best case is breakeven.
- **ASSP-06-R6** — **Express conviction in units of risk**, never in units of feeling.
- **ASSP-06-R7** — **Never equal-weight.** Volatility ignored at the position level reappears at the portfolio level.
- **ASSP-06-R9** — **Translate the annual vol budget to daily** (÷√252) and across names (÷√n).
- **ASSP-06-R10** — **Prefer ATR** among volatility measures — most stable, lowest readings; but expect higher gross exposure and turnover.
- **ASSP-06-R11** — **Use rolling Kelly as a signal, not only as a size.** Its collapse to zero in trendless markets is the feature, not a bug.
- **ASSP-06-R12** — **Trade fractional Kelly.** Full Kelly's drawdowns are survivable mathematically and not psychologically.
- **ASSP-06-R13** — **Continuous resizing costs you the average price** (FIFO drags it toward the trend) and costs commissions. Budget for both.
- **ASSP-06-R14** — **Capacity is signaled by inertia**, not by a formula.
- **ASSP-06-R15** — **Net exposure is a property of the signal; gross exposure is a property of the sizing.** Do not confuse the two knobs.

### ML4T-08 — Financial Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-08-R5** — **Use range-based estimators for variance and ATR for sizing** — they answer different questions.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R11** — **Calibrate probabilities only if position size depends on probability levels.** Rank-based mappings don't need it.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R13** — **Treat full Kelly as an upper bound.** Raw Kelly implies 30×+ leverage on real data.

