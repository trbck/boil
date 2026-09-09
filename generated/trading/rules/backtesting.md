# Rules — Backtesting & validation

`92` rules · ~1771 words · ~2390 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-05 — The Trading Edge Is a Number, and Here Is the Formula

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-05-R7** — **Shift signals forward one bar.** Always. Signal today, trade tomorrow.

### ASSP-06 — Position Sizing: Money Is Made in the Money Management Module

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-06-R4** — **Compute daily P&L on the existing position before resizing.** Doing it after is lookahead bias — check for this in any backtest you inherit.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R8** — AIC and similar in-sample criteria are unreliable for selecting interpretable structure — check separation diagnostics too.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R3** — Every cross-source join carries two time constraints (`available_at`, and `effective_date` ranges on ID mappings). Silent lookahead enters through joins that succeed.

### ML4T-05 — Synthetic Financial Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-05-R1** — Synthetic data is a robustness tool, not evidence. Real held-out data is the arbiter.
- **ML4T-05-R2** — Fix the generator before strategy selection; otherwise you overfit to its biases.
- **ML4T-05-R3** — Evaluate fidelity, utility, and privacy **separately** — each can pass while another fails badly.
- **ML4T-05-R4** — Marginal-distribution tests are necessary and never sufficient; test dependence and temporal structure independently.
- **ML4T-05-R5** — ACF of squared returns is the cheapest high-value diagnostic for volatility clustering.
- **ML4T-05-R6** — Beat the classical baseline (stationary bootstrap, GARCH) before accepting a deep generator.
- **ML4T-05-R7** — Never treat generated data as evidence about scenarios outside the training support.
- **ML4T-05-R8** — Regime-conditioned generation inherits the regime detector's errors.
- **ML4T-05-R9** — Choose the generator by objective alignment: tails → Tail-GAN, paths → Sig-CWGAN, irregular timing → GT-GAN, general → Diffusion-TS, mixed-type tables → LLM.
- **ML4T-05-R10** — For LLM tabular, add an explicit constraint layer and treat rejection rate as a monitored metric.

### ML4T-06 — Strategy Research Framework

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-06-R2** — **Separate feasibility from durability.** A credible story with an infeasible implementation is not a strategy; a feasible implementation with no story is a backtest whose failures are uninterpretable.
- **ML4T-06-R3** — **Prefer edges grounded in constraints over edges grounded in information.** Information edges erode on replication; constraint and risk-tolerance edges survive publicity.
- **ML4T-06-R4** — **Distinguish mechanics from parameters.** Mechanics changes bump the version and reset the baseline; parameter changes don't.
- **ML4T-06-R5** — **Use three metric layers with distinct roles** and never let end-to-end economics drive micro-decisions during development.
- **ML4T-06-R6** — **Test admissibility with one question:** at decision time *t*, were the features computable and was the label already resolved?
- **ML4T-06-R7** — **Count buffers in trading days, never calendar days.**
- **ML4T-06-R8** — **Seal the holdout and open it once,** after the whole pipeline — including mapping and cost assumptions — is frozen.
- **ML4T-06-R9** — **Run cadence feasibility before signal research.** If costs dominate at the intended horizon, no signal quality rescues it.
- **ML4T-06-R10** — **Make search countable.** Trial counts are an input to overfitting corrections, not paperwork.
- **ML4T-06-R11** — **When a preflight check fails, revise the setup, don't engineer around it.**

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R12** — **Treat AUC above 0.65 out-of-sample as a leakage alarm,** not a success.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R1** — **Treat a good equity curve as a claim to attack, not a result to confirm.** Failed tests are the main product.
- **ML4T-16-R2** — **Default to disbelief.** With a low prior on edge, false positives can outnumber true ones.
- **ML4T-16-R3** — **Record the protocol before interpreting results** — timing, rebalance, sizing, fills, constraints, costs.
- **ML4T-16-R4** — **Separate signal computation from execution in time.** Same-bar execution fuses past and future.
- **ML4T-16-R5** — **Choose vectorized vs. event-driven on semantics, not aesthetics.** The question is whether strategy behavior depends on simulated state.
- **ML4T-16-R6** — **Treat engine defaults as assumptions** — order sequencing, cash release, share granularity, and missing-data policy all change the path.
- **ML4T-16-R7** — **Build an unflattering baseline first,** and use large deviations from it as an infrastructure-bug signal in both directions.
- **ML4T-16-R8** — **Report gross and net together.** The gap reveals whether performance comes from forecasting or is consumed by trading.
- **ML4T-16-R9** — **Compute break-even cost and compare it to the assumed cost.** Proximity is fragility regardless of headline Sharpe.
- **ML4T-16-R11** — **Check whether holding period matches signal horizon.** A mismatch requires explanation.
- **ML4T-16-R12** — **Build regime labels point-in-time with expanding medians.** A full-sample threshold contaminates the diagnostic.
- **ML4T-16-R13** — **Weight conditional metrics by slice size,** and report observation counts alongside every regime statistic.
- **ML4T-16-R14** — **Report all standard regimes including the unfavorable ones,** and pre-specify definitions to avoid regime snooping.
- **ML4T-16-R15** — **Ask whether regime dependence is intentional and compensated,** not merely whether it exists.
- **ML4T-16-R16** — **Adjust Sharpe inference for serial dependence** before annualizing or testing.
- **ML4T-16-R17** — **Count effective, not nominal, trials** — adjacent parameter values are neither independent nor identical.
- **ML4T-16-R18** — **Keep exploration and confirmation separate,** and confirm on data that did not guide the specification.
- **ML4T-16-R19** — **Read the screening-prior table as a scrutiny trigger, not a threshold.** A Sharpe above 2.0 on a diversified strategy is a reason to look harder, not to celebrate.

### ML4T-17 — Portfolio Construction

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-17-R16** — **Pool the Sharpe across the universe when training end-to-end,** and use a two-pass gradient because Sharpe is non-separable across mini-batches.
- **ML4T-17-R19** — **Respect closing calendars in cross-sectional attention** — asynchronous closes are a lookahead channel.

### ML4T-18 — Transaction Costs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-18-R11** — **Generate execution schedules under multiple scenarios.** Wide trajectory variation means the trade is fragile to miscalibration.

### ML4T-19 — Risk Management

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-19-R1** — **Build every adaptive control from information available at decision time,** and treat model-inferred regimes as a leakage channel unless the state path is never re-estimated.
- **ML4T-19-R2** — **A control that cannot be specified ex ante and reconstructed afterward is not a valid control.**
- **ML4T-19-R4** — **Report VaR and CVaR together,** and prefer historical simulation as the base method — Cornish-Fisher destabilizes at high confidence under realistic kurtosis.
- **ML4T-19-R5** — **Use the Cantelli bound as a distribution-free floor** when parametric methods are untrustworthy.
- **ML4T-19-R6** — **Compute tail metrics by regime and present worst-regime CVaR prominently.** Unconditional estimates average over states that differ by ~2.7×.
- **ML4T-19-R11** — **Report factor attribution with HAC confidence bands.** A contribution whose interval spans zero did not "drive" performance.
- **ML4T-19-R12** — **Span every asset class held in the factor model,** or cross-asset exposures get misattributed to alpha.
- **ML4T-19-R13** — **Check residual correlations and precision-matrix stability** before trusting a covariance model in an optimizer.
- **ML4T-19-R14** — **Monitor exposures on a rolling basis.** Static loadings silently mis-size hedges as tilts drift.
- **ML4T-19-R15** — **Stress costs alongside returns.** Historical replay alone understates execution damage in crisis.
- **ML4T-19-R17** — **Run reverse stress tests,** which surface combinations forward scenarios miss.
- **ML4T-19-R18** — **Pre-define regime thresholds** or the cap logic becomes an overfitted parameter.
- **ML4T-19-R21** — **Wrap learned policies in hard deterministic envelopes.**
- **ML4T-19-R23** — **Give every kill switch a metric, threshold, action, escalation path, and reinstatement condition.**

### ML4T-21 — Reinforcement Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-21-R1** — **Use RL where the action is the optimization target and the reward is directly measurable** — not for generic alpha discovery.
- **ML4T-21-R2** — **"Model-free" describes the algorithm, not the modeling burden.** State design, reward shaping, and simulator construction carry the assumptions.
- **ML4T-21-R3** — **Reward engineering, not algorithm choice, determines whether the learned policy matches the financial objective.**
- **ML4T-21-R4** — **Include regime indicators in the state** and the policy becomes regime-conditioned without explicit switching logic.
- **ML4T-21-R5** — **Never let hard constraints depend on learned behavior.**
- **ML4T-21-R6** — **Choose on-policy vs. off-policy on the stability-efficiency trade:** cheap simulator data favors SAC; scarce historical data favors PPO.
- **ML4T-21-R7** — **Use distributional RL when risk preferences may change** — it makes them configurable without retraining.
- **ML4T-21-R8** — **Treat seed variation as a policy-character question, not just a performance variance question.** The same reward can produce uniform, back-loaded, or oscillating policies across seeds.
- **ML4T-21-R10** — **A simulator without queue priority, partial fills, impact, and latency will teach the agent to exploit assumptions that do not survive contact with live markets.**
- **ML4T-21-R11** — **Inspect policy *shape* against the analytical benchmark before comparing performance** — inventory-responsive quoting is the diagnostic, not one episode's PnL.
- **ML4T-21-R12** — **Require matched accounting and a friction-aware benchmark set** before claiming a learned hedge beats delta hedging.
- **ML4T-21-R13** — **Prefer IRL to behavior cloning when the environment may change,** since cloning copies actions rather than objectives.
- **ML4T-21-R14** — **Read inferred rewards qualitatively.** The feature basis constrains what objectives can be expressed.
- **ML4T-21-R15** — **Randomize the domain rather than calibrating one "correct" environment.**
- **ML4T-21-R16** — **Check participation rate before believing any strategy result.** Above roughly one day's volume, strong impact assumptions flip essentially every paper winner into a loser.
- **ML4T-21-R17** — **Run offline policy evaluation before any capital,** and define go/no-go criteria before staged scaling.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R4** — **Track publication date, fiscal period, and ingestion timestamp separately.** Filtering by period labels alone leaks information into backtests.
- **ML4T-22-R12** — **Delegate arithmetic to code.** Computation failure is invisible to faithfulness metrics because the evidence is correct.
- **ML4T-22-R14** — **Score abstention quality as a first-class metric,** and include unanswerable queries in the evaluation set.
- **ML4T-22-R15** — **Put security in the accuracy harness** so robustness regressions surface like accuracy regressions.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R8** — **Monitor schema validity, provenance coverage, duplicate-node rate, and temporal consistency** — standard NLP metrics hide these regressions.
- **ML4T-23-R15** — **Trust topology metrics from stated relationships more than from estimated correlations,** and match the network filter to the analytical goal.
- **ML4T-23-R16** — **Start with hand-crafted graph features; add learned representations only on out-of-sample evidence after costs.**

### ML4T-26 — MLOps and Governance

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-26-R4** — **Decompose Sharpe into hit rate and win/loss** — the two move differently and point to different causes.

### ML4T-27 — The Systematic Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-27-R8** — **Treat model governance as measurable risk,** not philosophy — interpretability, bias, robustness, auditability each have techniques and metrics.

### NOTE-21-gate-audit-of-the-strategies — §21 gate audit of the strategies repo — seven changes, two falsified hypotheses  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-21-gate-audit-of-the-strategies-R1** — **A gate's false-positive rate is a function of sample size, and reporting a verdict without it is a category error.** The same §21 battery passes 4.0% of no-edge draws at n≈2500 and 8.5% at n≈317 — a 2.1× difference that the verdict line does not carry. Any gate report should print its own calibrated error rate for the sleeve's sample regime beside the verdict.
- **NOTE-21-gate-audit-of-the-strategies-R3** — **A block bootstrap cannot generate a left-skew strategy's lethal event, because that event is by construction absent from the sample the strategy survived.** Demonstrated: a synthetic left-skew sleeve scoring §21 PASS 7/7 shows a −27.9% deepest-decile drawdown and 9% of paths negative once single-day replace-mode jumps are injected at 1.5× the worst observed day. The clean bootstrap on such a sleeve measures nothing and reads as reassurance.
- **NOTE-21-gate-audit-of-the-strategies-R4** — **Anchor a break-even cost ratio to the harshest cost the sweep certifies at, never the cheapest tested.** Anchoring to the cheapest row turned a sleeve with 6.7bps break-even into "3.3× headroom"; anchoring to the 20bps corner the gate actually certifies at reports 0.3× and flags it. Where the sweep never crosses zero, extrapolate the terminal slope and label it extrapolated — reporting ">max tested" collapses a Sharpe of 1.7 and a Sharpe of 0.05 into one indistinguishable line.
- **NOTE-21-gate-audit-of-the-strategies-R5** — **New gate content must ship reported-but-not-gating until every candidate has a reading.** Adding a gating checkbox to an established battery retroactively flips the verdict on every stored report, which is the mid-stream definition change `ML4T-01` warns against: improvements stop being interpretable as stronger signal and become changed definitions. Promotion to a gating check is a separate deliberate pass.
- **NOTE-21-gate-audit-of-the-strategies-R6** — **Declaration coverage is the honest measure of whether a choice is frozen, and it is usually far lower than assumed.** In a repo with a mature gate, 11 of 29 sleeves could be given an archetype declaration from their own stated mechanism and only 6 of 29 a holding-period declaration; the rest were reported as undeclared rather than guessed. An audit that reports a mechanism as "added" without its coverage number has not measured anything.
- **NOTE-21-gate-audit-of-the-strategies-R7** — **Guard the switch, not the default.** A configuration whose default is safe can still be unsafe to change: the risk lives in the transition, and the effective control is to require the governing rule ID in the change's written reason, so the acknowledgement lands in the audit journal instead of a dismissed dialog.

### NOTE-options-strategies-on-alpaca-fmp — Options Strategies on Alpaca + FMP: What the Envelope Actually Allows  *(derived)*

<sub>Research notes & reports</sub>

- **NOTE-options-strategies-on-alpaca-fmp-R21** — **State the one-regime limitation in every options gate.** With an unsampled tail, deflated-Sharpe and cross-validation machinery cannot see the risk that matters most [5][12].

