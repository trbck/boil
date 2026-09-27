# Rules — Live execution & operations

`97` rules · ~1851 words · ~2498 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-02 — 10 Classic Myths About Short Selling

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-02-R2** — **Build shorts around institutional liquidation flow**, not around fundamental doom. You are following size, not leading it.
- **ASSP-02-R5** — **Prefer relative underperformance as the short thesis.** Sustainable, non-confrontational, and it is what the rest of the book is engineered around.

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R2** — **Classify with a single outer merge on (date, ticker, broker)** using `indicator=True`. Three categories fall out of one operation.
- **ASSP-10-R3** — **Never let missed/override records mutate the portfolio.** They are pure audit rows, tagged for separate study.
- **ASSP-10-R6** — **Store lots as separate portfolio rows with their own `entry_date`** or FIFO cannot work.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R7** — Monitoring must distinguish signal decay from operational failure, or intervention becomes another overfitting channel.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R10** — Default storage stack is partitioned Parquet + DuckDB/Polars. Escalate only on concurrency, governance, or latency pressure.

### ML4T-03 — Market Microstructure

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-03-R7** — **Dollar bars are the default.** Information bars only when order-flow dynamics are the object of study.
- **ML4T-03-R9** — Watch for the threshold spiral in adaptive imbalance bars; fixed thresholds in production.
- **ML4T-03-R12** — Sequence numbers over timestamps for ordering, when both exist.

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R7** — **Separate fast volatility dynamics from slow correlation dynamics** with different half-lives in production risk models.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R4** — **Separate signal computation from execution in time.** Same-bar execution fuses past and future.
- **ML4T-16-R6** — **Treat engine defaults as assumptions** — order sequencing, cash release, share granularity, and missing-data policy all change the path.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R19** — **Precommit kill criteria before deployment.**

### ML4T-21 — Reinforcement Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-21-R1** — **Use RL where the action is the optimization target and the reward is directly measurable** — not for generic alpha discovery.
- **ML4T-21-R3** — **Reward engineering, not algorithm choice, determines whether the learned policy matches the financial objective.**
- **ML4T-21-R4** — **Include regime indicators in the state** and the policy becomes regime-conditioned without explicit switching logic.
- **ML4T-21-R5** — **Never let hard constraints depend on learned behavior.**
- **ML4T-21-R7** — **Use distributional RL when risk preferences may change** — it makes them configurable without retraining.
- **ML4T-21-R8** — **Treat seed variation as a policy-character question, not just a performance variance question.** The same reward can produce uniform, back-loaded, or oscillating policies across seeds.
- **ML4T-21-R9** — **Constrain the action space and penalize deviation from a reference schedule** to keep execution agents economically coherent.
- **ML4T-21-R10** — **A simulator without queue priority, partial fills, impact, and latency will teach the agent to exploit assumptions that do not survive contact with live markets.**
- **ML4T-21-R11** — **Inspect policy *shape* against the analytical benchmark before comparing performance** — inventory-responsive quoting is the diagnostic, not one episode's PnL.
- **ML4T-21-R12** — **Require matched accounting and a friction-aware benchmark set** before claiming a learned hedge beats delta hedging.
- **ML4T-21-R13** — **Prefer IRL to behavior cloning when the environment may change,** since cloning copies actions rather than objectives.
- **ML4T-21-R14** — **Read inferred rewards qualitatively.** The feature basis constrains what objectives can be expressed.
- **ML4T-21-R15** — **Randomize the domain rather than calibrating one "correct" environment.**
- **ML4T-21-R16** — **Check participation rate before believing any strategy result.** Above roughly one day's volume, strong impact assumptions flip essentially every paper winner into a loser.
- **ML4T-21-R17** — **Run offline policy evaluation before any capital,** and define go/no-go criteria before staged scaling.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R11** — **Make query safety architectural, not optional:** read-only credentials, allowlisted schema, parameterization, execution limits, query logging.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R18** — **Monitor sharpness alongside ECE.** Improved calibration with collapsed sharpness is not improvement.
- **ML4T-24-R19** — **Treat search-retrieved post-cutoff evidence as the dominant contamination risk** on resolved panels, and let contamination analysis override demo performance.
- **ML4T-24-R25** — **Reuse existing governance artifacts (the IPS) as the agent's operational boundary** rather than inventing new ones.

### ML4T-25 — Live Trading Systems

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-25-R1** — **Separate technical divergence from statistical decay before diagnosing anything.** Until parity is verified, live deviations could be either, making diagnosis impossible.
- **ML4T-25-R2** — **Run the same source files in both modes.** Rewriting for production creates two implementations and two places for bugs to hide.
- **ML4T-25-R3** — **Make signal generation deterministic** — no system time, no run-varying seeds, no environment-dependent external state.
- **ML4T-25-R4** — **Detect stale connectivity actively with a heartbeat,** and reconcile broker state on every reconnect before resuming trading.
- **ML4T-25-R5** — **Treat broker routing as an execution-quality decision.** Cost dispersion across brokers dwarfs commission differences, and PFOF explains little of it.
- **ML4T-25-R6** — **Use client order IDs as idempotency keys** so crashes and timeouts cannot produce duplicates.
- **ML4T-25-R7** — **Model orders as an explicit state machine that tolerates out-of-order messages** and records race resolutions in the audit trail.
- **ML4T-25-R8** — **Never blindly retry rejections** — the cause determines the correct response.
- **ML4T-25-R9** — **Halt on reconciliation discrepancies rather than auto-correcting,** or record-keeping errors become trading errors.
- **ML4T-25-R10** — **Verify parity stage by stage** so divergence can be binary-searched rather than guessed at.
- **ML4T-25-R11** — **Make parity tests fail loudly on a missing live pipeline** rather than silently passing against an empty log.
- **ML4T-25-R12** — **Match training and inference venues,** and when impossible, measure and document the convention differences as an explicit verification task.
- **ML4T-25-R13** — **Source warm-up data from the executing session,** not a research-time loader, or rankings and sizing run on stale prices.
- **ML4T-25-R14** — **Persist kill-switch state across restarts** — an unlatched switch after a crash re-enables trading at the worst moment.
- **ML4T-25-R15** — **Reject orders on stale data** using a per-asset freshness timestamp.
- **ML4T-25-R16** — **Refuse to start a trading cycle on a non-clean startup reconciliation.**
- **ML4T-25-R17** — **Keep the kill switch independent of the component it controls,** and make each level a single tested action.
- **ML4T-25-R18** — **Encode the training-cutoff invariant explicitly** and persist both cutoff dates for later audit.
- **ML4T-25-R19** — **Partition basket disposition into intended / attempted / accepted / failed** rather than a single status string.
- **ML4T-25-R20** — **Run paper and live in parallel during transition** — the divergence is more diagnostic than either book's PnL.
- **ML4T-25-R21** — **Verify legality, automated access, taxes, and margin rules in the target jurisdiction before building,** not after.

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R1** — **Classify the failure before responding.** Same inputs → different outputs is a bug; same outputs → poor returns is decay.
- **ML4T-26-R2** — **Validate data at ingest with a fail-closed policy on execution-critical feeds.** Most apparent drift is a silent data defect.
- **ML4T-26-R3** — **Compute metrics on rolling windows across several lengths,** because point-in-time aggregates hide trends and multi-window agreement distinguishes noise from decay.
- **ML4T-26-R4** — **Decompose Sharpe into hit rate and win/loss** — the two move differently and point to different causes.
- **ML4T-26-R5** — **Track the backtest-to-live realization ratio over time,** not just absolute performance.
- **ML4T-26-R6** — **Monitor execution quality alongside model metrics.** Cost inflation looks like model decay and retraining is the wrong fix.
- **ML4T-26-R7** — **Calibrate alert thresholds from historical degradation episodes,** and delete any threshold that fires without changing a decision.
- **ML4T-26-R8** — **Use PSI for binned features and K-S for continuous ones,** and treat PSI spikes as leading indicators.
- **ML4T-26-R9** — **Watch SHAP rank stability, not just magnitude** — a collapsing core-feature contribution is an early warning.
- **ML4T-26-R10** — **Run ADWIN or DDM continuously on the prediction-error stream,** and monitor the detector's own alert frequency.
- **ML4T-26-R11** — **Read the drift-vs-decay cross-tab.** Drift without decay means a robust model; decay without drift means your monitoring has gaps.
- **ML4T-26-R12** — **Combine scheduled and triggered retraining** rather than choosing one.
- **ML4T-26-R13** — **Shadow every candidate long enough to span multiple regimes,** with at least two rebalance cycles.
- **ML4T-26-R14** — **Define a minimum effect size for promotion** and check statistical power before concluding the candidate is better.
- **ML4T-26-R15** — **Phase capital in through explicit gates** — A/B testing with real money reveals illiquidity clustering and market impact that shadow mode cannot.
- **ML4T-26-R16** — **Test the rollback mechanism before deploying the candidate.**
- **ML4T-26-R17** — **Automate low-level rollbacks and require confirmation for performance-based ones.**
- **ML4T-26-R18** — **Halt immediately on hard loss limits.** Do not wait for review; do not trade out of the hole.
- **ML4T-26-R19** — **Restart gradually at reduced size after any breaker trip.**
- **ML4T-26-R20** — **Time-limit and log every manual override.**
- **ML4T-26-R21** — **Record a run manifest for every training run** so any deployed model traces to its exact inputs.
- **ML4T-26-R22** — **Right-size the MLOps stack.** Monitoring and safety outrank tooling.

### ML4T-27 — The Systematic Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-27-R7** — **Allocate frontier attention by time-to-return:** DeFi and AI governance now, quantum as monitoring only.

### NOTE-alpaca-index-options-spx-vix-xsp — Alpaca Index Options (SPX/VIX/XSP) — Envelope, and a Correction to R1  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-alpaca-index-options-spx-vix-xsp-R1** — **Alpaca supports Cboe index options — SPX, SPXW, VIX, VIXW, DJX and XSP — cash-settled and European-style, confirmed per contract by the API (`style=european`, `size=100`).** The prior note's envelope covered only American-style equity and ETF options and should not be read as excluding index options.
- **NOTE-alpaca-index-options-spx-vix-xsp-R2** — **Index options receive NO greeks and NO implied volatility from Alpaca — zero of 26,214 sampled VIX/SPX/XSP contracts carried either, while quotes were served for all of them.** This corrects `NOTE-options-strategies-on-alpaca-fmp-R1`, which recorded greeks as "live-snapshot only": that is true for equity options but optimistic for index options, where none exist in any form.
- **NOTE-alpaca-index-options-spx-vix-xsp-R3** — **Local implied-vol inversion is mandatory rather than optional for index options**, since there is no served field to fall back on even at decision time.
- **NOTE-alpaca-index-options-spx-vix-xsp-R4** — **VIX options must be priced off VIX futures forwards, not spot VIX.** Inverting implied vol against spot VIX with a Black-Scholes helper returns a confidently wrong number, so equity-option greeks code is not transferable to VIX without substituting the forward.
- **NOTE-alpaca-index-options-spx-vix-xsp-R6** — **Cash settlement removes assignment into the underlying**, eliminating the "assignment into a falling name" failure mode that dominates cash-secured-put and covered-call archetypes on equities.
- **NOTE-alpaca-index-options-spx-vix-xsp-R7** — **Multi-leg calendars and diagonals are blocked on index options**, because Alpaca's `mleg` rule requires European-style legs to share an expiration; the permission to trade calendars applies only to American-style equity options.
- **NOTE-alpaca-index-options-spx-vix-xsp-R8** — **Index option history reaches back to at least March 2024, comparable to equity options**, so index archetypes are no less backtestable than equity ones.
- **NOTE-alpaca-index-options-spx-vix-xsp-R9** — **Index options carry a ×100 multiplier against the index level, so contract notional dwarfs a small account** — one SPX contract near a 6,400 index level is roughly $640,000 of notional. VIX, at an index level typically in the teens, is the only one of these whose per-contract notional is small enough for a five-figure account.
- **NOTE-alpaca-index-options-spx-vix-xsp-R10** — **Alpaca's index-option order acceptance is documented but unverified by a fill here**, unlike the equity multi-leg path, where a real 4-leg order was accepted and a naked short was rejected with code 40310000.
- **NOTE-alpaca-index-options-spx-vix-xsp-R11** — **Treat `NOTE-options-strategies-on-alpaca-fmp-R1` as scoped to equity and ETF options.** For index options the stronger statement holds: no greeks or IV are served at all.
- **NOTE-alpaca-index-options-spx-vix-xsp-R12** — **Do not reuse spot-based Black-Scholes IV inversion for VIX options.** Substitute the VIX futures forward for spot, or exclude VIX from any greek-conditioned archetype.
- **NOTE-alpaca-index-options-spx-vix-xsp-R15** — **Verify index-option order acceptance with one small paper order before designing around it**, mirroring how the equity multi-leg envelope was established by a real accepted order rather than by documentation.
- **NOTE-alpaca-index-options-spx-vix-xsp-R16** — **Size index-option positions off the ×100 multiplier against the index level, not against an equity-scale notional assumption.**

### NOTE-options-strategies-on-alpaca-fmp — Options Strategies on Alpaca + FMP: What the Envelope Actually Allows  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-options-strategies-on-alpaca-fmp-R1** — **Greeks and implied volatility are served only as live snapshots**; no historical greeks exist in the API or SDK, so any IV- or greek-conditioned signal is unbacktestable without locally recomputing from bid/ask and underlying bars [6][7][9][11][15].
- **NOTE-options-strategies-on-alpaca-fmp-R3** — **Level 3 permits four-leg atomic `mleg` orders but not uncovered shorts**, which require Level 4; the binding rule is that all legs must be covered within the same order, which constrains rolling more than entry [1][4].
- **NOTE-options-strategies-on-alpaca-fmp-R9** — **Execution style decides survival** — 1.3 cents effective spread for timed trades against 6.2–8.1 cents for naive spread-crossing, and a scheduled bot is firmly in the second group [29].
- **NOTE-options-strategies-on-alpaca-fmp-R11** — **Paper trading performs no liquidity or market-impact modelling** and lags live on assignment reporting by a day, so it validates logic, not edge [3][13][14].
- **NOTE-options-strategies-on-alpaca-fmp-R12** — **Rank by turnover and execution patience, not gross Sharpe.** The cost evidence says this is the axis that determines survival [28][29]. Prefer low-turnover, held-to-expiry structures.
- **NOTE-options-strategies-on-alpaca-fmp-R19** — **Budget the paid OPRA data tier** as a fixed cost of doing options work; the indicative feed is randomised and unsuitable for both live trading and realistic cost modelling [8].
- **NOTE-options-strategies-on-alpaca-fmp-R20** — **Settle two open questions cheaply**: whether equity and option legs combine in one `mleg` order [1][2], and whether the short-vol sleeve's "empty historical option bars" premise is now stale. Both are single test orders or single queries.

