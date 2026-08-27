# Rules — Research process & evidence discipline

`52` rules · ~803 words · ~1084 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-01 — The Stock Market Game

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-01-R3** — **Never add a filter without measuring its false-negative cost.** Over-filtering is the default failure mode of the competent.
- **ASSP-01-R5** — Any system for an infinite game must be **stress tested, not optimized** — optimization tunes to a sample that will not repeat.
- **ASSP-01-R7** — Simplicity is not a compromise. In complex systems, the robust heuristic usually outperforms the elaborate model.

### ASSP-08 — The Long/Short Toolbox

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-08-R15** — **Write the mandate down**, including the skew of your return distribution.

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R9** — **Reward completeness, not performance.** Score the process out of 120; compound a streak multiplier at `1 + streak/20`; forgive one missed weekday.

### ML4T-01 — The Process Is Your Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-01-R1** — Freeze the five evaluation-defining choices before iterating; iterate only downstream of them.
- **ML4T-01-R2** — Log every trial. Unlogged search is uncountable, and uncountable search cannot be adjusted for.
- **ML4T-01-R3** — Run the tradability check *early*, not after signal refinement.
- **ML4T-01-R4** — Prefer graceful degradation over optimal point estimates.
- **ML4T-01-R5** — Regimes gate risk posture, never entry timing.
- **ML4T-01-R6** — Drift is a flag; always follow it with a four-way diagnosis (data / feature / execution / regime).
- **ML4T-01-R7** — Monitoring must distinguish signal decay from operational failure, or intervention becomes another overfitting channel.
- **ML4T-01-R8** — AIC and similar in-sample criteria are unreliable for selecting interpretable structure — check separation diagnostics too.
- **ML4T-01-R9** — Model-agnostic: this whole loop applies to rule-based systems as well.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R8** — Buy commoditized history and crosswalks; build everything that encodes your assumptions.

### ML4T-05 — Synthetic Financial Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-05-R1** — Synthetic data is a robustness tool, not evidence. Real held-out data is the arbiter.
- **ML4T-05-R7** — Never treat generated data as evidence about scenarios outside the training support.

### ML4T-06 — Strategy Research Framework

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-06-R1** — **Freeze the evaluation environment before optimizing anything in it.** Attribution of a performance delta to a design change is only valid if everything else is versioned and recorded.
- **ML4T-06-R4** — **Distinguish mechanics from parameters.** Mechanics changes bump the version and reset the baseline; parameter changes don't.
- **ML4T-06-R7** — **Count buffers in trading days, never calendar days.**
- **ML4T-06-R8** — **Seal the holdout and open it once,** after the whole pipeline — including mapping and cost assumptions — is frozen.
- **ML4T-06-R9** — **Run cadence feasibility before signal research.** If costs dominate at the intended horizon, no signal quality rescues it.
- **ML4T-06-R10** — **Make search countable.** Trial counts are an input to overfitting corrections, not paperwork.
- **ML4T-06-R11** — **When a preflight check fails, revise the setup, don't engineer around it.**
- **ML4T-06-R12** — **Treat a published anomaly as a hypothesis, not evidence.** Independent validation must happen inside your own setup and cost assumptions.

### ML4T-08 — Financial Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-08-R1** — **Separate meaning-changing choices from noise-reduction choices.** The first create new hypotheses and new trials; the second trade variance for bias within one hypothesis.
- **ML4T-08-R2** — **If you cannot name the economic mechanism, you have a data pattern.** Hold it to a higher evidentiary standard or drop it.
- **ML4T-08-R7** — **The anchor, the peer set, and the maturity pair *are* the hypothesis.** Changing them is not tuning.
- **ML4T-08-R8** — **Verify venue-specific clocks** (funding intervals, roll schedules, session boundaries) rather than assuming the common convention.
- **ML4T-08-R9** — **Repeating slow data across fast rows inflates N without adding information.** Weight by uniqueness.
- **ML4T-08-R10** — **Encode event proximity and phase, never event outcomes,** in pre-event windows.
- **ML4T-08-R11** — **Breadth beats marginal IC.** A slightly better signal on a small universe loses to a thin signal on a large one.
- **ML4T-08-R12** — **Deduplicate within families before the model stage,** and prefer fold stability over single-metric wins when picking cluster representatives.
- **ML4T-08-R13** — **Every interaction is a separate trial** and enters the multiple-testing budget — 5 × 3 × 3 is 45 tests, not one experiment.
- **ML4T-08-R14** — **Demand the right event-time shape, not just a significant average.** Correct sign, correct timing, correct asymmetry.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R5** — **Use nested walk-forward whenever signal is weak.** Single-loop selection bias can flip the reported sign.
- **ML4T-11-R6** — **Report trial count, search space, selected configuration, and fold-level dispersion** with every tuned result.

### ML4T-14 — Latent Factor Models

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-14-R16** — **Adversarial objectives discipline against worst cases; reconstruction objectives discipline against averages.** Choose based on which failure you care about.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R4** — **Timing discipline is necessary but insufficient** — a pre-treatment variable can still be a collider or selection variable.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R17** — **Count effective, not nominal, trials** — adjacent parameter values are neither independent nor identical.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R6** — **Store evidence with the edge.** A relationship without source context cannot be verified or corrected.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R6** — **Use typed state objects, not chat history.** Transcripts cannot be queried for the evidence behind a specific estimate.
- **ML4T-24-R8** — **Replay by freezing tool outputs and varying only prompts or policies,** or you will mistake evidence drift for prompt improvements.

### ML4T-27 — The Systematic Edge

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-27-R1** — **Optimize for the process, not the strategy.** Individual models decay; a repeatable generate-test-deploy pipeline compounds.
- **ML4T-27-R2** — **The systematic workflow is a bias-control mechanism first** — falsifiable hypotheses, out-of-sample testing, multiple-testing corrections.
- **ML4T-27-R3** — **Choose the firm type as deliberately as the role.** It determines which skills you actually develop.
- **ML4T-27-R5** — **Read a few papers deeply rather than many shallowly.**
- **ML4T-27-R6** — **Document failed experiments,** which carry more information than successes.
- **ML4T-27-R7** — **Allocate frontier attention by time-to-return:** DeFi and AI governance now, quantum as monitoring only.
- **ML4T-27-R8** — **Treat model governance as measurable risk,** not philosophy — interpretability, bias, robustness, auditability each have techniques and metrics.
- **ML4T-27-R9** — **Apply every new technique to a real problem immediately,** or it never becomes expertise.
- **ML4T-27-R10** — **Close gaps that complement existing strengths** rather than opening new skill tracks.

