# Rules — Signals, edge & expectancy

`41` rules · ~686 words · ~926 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-01 — The Stock Market Game

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-01-R1** — Optimize **gain expectancy under a survival constraint**, never terminal return. If a rule cannot lose the game, you have modeled the wrong game.
- **ASSP-01-R2** — Treat prediction accuracy as a **weak lever**. Average win and average loss have far more range than win rate.
- **ASSP-01-R3** — **Never add a filter without measuring its false-negative cost.** Over-filtering is the default failure mode of the competent.
- **ASSP-01-R4** — Design for **cheap a posteriori exits**, not accurate a priori selection. The separation you want at entry does not exist.
- **ASSP-01-R7** — Simplicity is not a compromise. In complex systems, the robust heuristic usually outperforms the elaborate model.

### ASSP-02 — 10 Classic Myths About Short Selling

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-02-R7** — When a short becomes emotionally satisfying, **that is an exit signal**, not a conviction signal.

### ASSP-03 — Long/Short Methodologies: Absolute and Relative

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-03-R9** — Enter shorts on relative weakness early — the margin of safety matters more at the exit than the entry.

### ASSP-05 — The Trading Edge Is a Number, and Here Is the Formula

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-05-R1** — **Report gain expectancy first.** Sharpe, Sortino, and friends are meaningless until expectancy is positive.
- **ASSP-05-R2** — **Compute all three formulas** (arithmetic, geometric, Kelly) from the same three inputs. Use **partial Kelly (⅓–½)** in production.
- **ASSP-05-R3** — **Decompose every improvement into signal vs. money management.** Know which module you are working on.
- **ASSP-05-R5** — **Win rate is not the target.** A 30% win rate with right skew beats a 99% win rate with left skew.
- **ASSP-05-R6** — **Match the risk metric to the skew**: trend following → **profit factor / gain-to-pain**; mean reversion → **tail ratio**.
- **ASSP-05-R7** — **Shift signals forward one bar.** Always. Signal today, trade tomorrow.
- **ASSP-05-R9** — **Design the exit before the entry.** Bad exits are unrecoverable.
- **ASSP-05-R10** — **Search pairs within sectors**, not across the universe. Require cointegration *and* ADF stationarity on both spread and ratio.
- **ASSP-05-R11** — **In mean reversion, stationarity is the stop loss.** When it breaks, stop trading the pair.
- **ASSP-05-R12** — **Moderate z-score thresholds beat extremes.** Enter ~1.7σ, exit ~1.2σ.
- **ASSP-05-R13** — **Constrain evaluation windows to the period the relationship was tested on.**

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R5** — **Never average down.** It degrades three of four edge variables and its best case is breakeven.
- **ASSP-06-R11** — **Use rolling Kelly as a signal, not only as a size.** Its collapse to zero in trendless markets is the feature, not a bug.

### ASSP-07 — Refining the Investment Universe

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-07-R1** — **Judge short liquidity by the exit, never the entry.** Liquidity is thinner on the way out than the way in, structurally.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R6** — **Never lever a left-skewed strategy** because the win rate looks safe. That is how they die.

### ASSP-09 — Asset Allocation

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-09-R13** — **Read allocation scorecards in two columns**: comfort metrics (Sharpe, MaxDD, win rate) and robustness metrics (profit ratio, tail ratio, gain expectancy, common sense ratio). Optimize the second.
- **ASSP-09-R14** — **A profit ratio below 1 with a high win rate is the left-skew trap.** Check both together, always.

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R13** — **Calibrate stops with MAE**, and classify strategies with **MFE/MAE** (>1 trend following, <1 mean reversion).

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R12** — **Test the signal against a realistic availability delay.** IC that dies with a one-hour lag is a speed edge, not an information edge.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R2** — **Match the penalty to the signal's structure.** Diffuse and correlated → Ridge. Genuinely sparse → LASSO. Correlated clusters → Elastic Net.
- **ML4T-11-R17** — **A significant IC on a huge sample is not a strong signal.** Separate statistical from economic significance every time.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R15** — **Treat discovered edges as hypotheses.** Method outputs on identical data ranged from 1 to 42 edges.
- **ML4T-15-R17** — **Causal analysis reduces out-of-sample degradation when heterogeneity carries information; it does not manufacture alpha when the signal inverts.**

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R2** — **Default to disbelief.** With a low prior on edge, false positives can outnumber true ones.
- **ML4T-16-R7** — **Build an unflattering baseline first,** and use large deviations from it as an infrastructure-bug signal in both directions.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R10** — **Alpha ranking matters more than alpha calibration.** Scale error is absorbed by leverage; ranking error is not.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R16** — **Rank signals by alpha-to-go, not raw IC.** A fast signal with high impact cost can be worthless by the time the position is built.

### ML4T-25 — Live Trading Systems

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-25-R3** — **Make signal generation deterministic** — no system time, no run-varying seeds, no environment-dependent external state.

### ML4T-27 — The Systematic Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-27-R3** — **Choose the firm type as deliberately as the role.** It determines which skills you actually develop.
- **ML4T-27-R4** — **Build T-shaped expertise,** because the boundary between alpha research and execution is dissolving.
- **ML4T-27-R5** — **Read a few papers deeply rather than many shallowly.**
- **ML4T-27-R6** — **Document failed experiments,** which carry more information than successes.
- **ML4T-27-R9** — **Apply every new technique to a real problem immediately,** or it never becomes expertise.
- **ML4T-27-R10** — **Close gaps that complement existing strengths** rather than opening new skill tracks.

