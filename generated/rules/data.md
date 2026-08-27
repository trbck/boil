# Rules — Data sourcing & integrity

`60` rules · ~942 words · ~1271 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-03 — Long/Short Methodologies: Absolute and Relative

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-03-R1** — **Compute everything on the relative, currency-adjusted series** — OHLC, not just close. This is the substrate; every downstream module assumes it.
- **ASSP-03-R3** — Choose `rebase=True` for development (memory) and rolling/`rebase=False` for tested production (lightweight, corporate-action-proof). Know which one you are running.
- **ASSP-03-R4** — **Use `expanding().sum()` over `cumsum()`** for cumulative log returns; compute relative returns by subtracting benchmark log returns.
- **ASSP-03-R5** — **Survivorship bias in a short backtest is conservative**, not disqualifying — you are testing against the fittest survivors.
- **ASSP-03-R7** — Track **sector rotation**, not market tops and bottoms. Use `cyclicals − defensives` on the relative series; negative → defensive posture.
- **ASSP-03-R8** — **Expensive or callable-only borrow is a long signal, not a short signal.**
- **ASSP-03-R9** — Enter shorts on relative weakness early — the margin of safety matters more at the exit than the entry.
- **ASSP-03-R10** — Relative stop levels are invisible to hunting algorithms but **require active management** to be fillable.

### ASSP-07 — Refining the Investment Universe

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-07-R3** — **Crowded shorts are anti-hedges.** They outperform in pullbacks because there is no institutional long money left to sell.
- **ASSP-07-R5** — **High dividend yield is a short *source*, not a short deterrent** — the yield defers the decline, it does not prevent it.
- **ASSP-07-R6** — **Never short a name doing buybacks.** You are fighting an unlimited, price-insensitive bid.
- **ASSP-07-R7** — **Short liability for dividends is real.** Maintain a dividend calendar per short position.
- **ASSP-07-R8** — **Rich valuation alone is never a short thesis.** The thesis is rich valuation + decelerating earnings momentum = multiples compression.
- **ASSP-07-R9** — **Expensive PBR = investing cash flow financed by financing cash flow.** Never hold those long through a bear market.
- **ASSP-07-R10** — **Let regime ask the question, let fundamentals answer it.** "Why is it going down?" beats "why should it go down?"
- **ASSP-07-R11** — **Beta *momentum* beats beta *level*.** Rising beta → worse returns; falling beta → better returns. Both contradict CAPM.
- **ASSP-07-R13** — Resample to month-end for beta — daily rolling beta costs a great deal of compute for no signal.

### ML4T-02 — The Financial Data Universe

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-02-R1** — Lock timestamp semantics, adjustment methodology, identifier policy, and revision handling *as pipeline metadata* before modeling.
- **ML4T-02-R2** — Data errors are systematic, not random — design validation around the four alpha-manufacturing defects, in priority order: PIT → survivorship → corporate actions → identifiers.
- **ML4T-02-R3** — Every cross-source join carries two time constraints (`available_at`, and `effective_date` ranges on ID mappings). Silent lookahead enters through joins that succeed.
- **ML4T-02-R4** — PIT has three independent levels — values, universe, identifiers. Passing one proves nothing about the others.
- **ML4T-02-R5** — Zero-lag records on delayed data are a red flag, always.
- **ML4T-02-R6** — Represent instrument families at the right abstraction: options → surfaces, futures → raw contracts *plus* continuous variants, commodities → contract spec in the data, DEX → slippage from reserves.
- **ML4T-02-R7** — Store contract/instrument metadata in the dataset, not the docs.
- **ML4T-02-R8** — Buy commoditized history and crosswalks; build everything that encodes your assumptions.
- **ML4T-02-R9** — Version data, never overwrite. Fail loudly on validation violations.
- **ML4T-02-R10** — Default storage stack is partitioned Parquet + DuckDB/Polars. Escalate only on concurrency, governance, or latency pressure.

### ML4T-03 — Market Microstructure

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-03-R3** — Intraday seasonality is a confounder before it's a feature — the same signal means different things at different times of day.
- **ML4T-03-R6** — Reconstruction is accounting — enforce invariants and fail fast; a venue-local book is not the market.
- **ML4T-03-R8** — Information bars are gated by trade-classification accuracy: Lee-Ready ~95% vs. tick test ~80%. Reconstruct the book to get quotes if you need imbalance bars.
- **ML4T-03-R10** — Use jump-robust local volatility (Lee–Mykland) rather than daily-σ thresholds — the naive rule fails in both directions depending on the day.
- **ML4T-03-R11** — Flag and exclude; never interpolate ticks and quotes.
- **ML4T-03-R12** — Sequence numbers over timestamps for ordering, when both exist.
- **ML4T-03-R13** — Nulls in a continuously-sessionized panel may mean "no activity," not "missing data." Check before aggregating.

### ML4T-04 — Fundamental and Alternative Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-04-R1** — Every fact carries two timestamps: the period it describes and when that version became observable.
- **ML4T-04-R2** — Conservative default for equities: use filing acceptance as availability; track the earlier 8-K separately only if event precision matters.
- **ML4T-04-R3** — Crypto needs a **confirmation policy** in the PIT contract — block time alone permits reorg lookahead.
- **ML4T-04-R4** — Never interpolate macro series onto a decision grid.
- **ML4T-04-R5** — Store the *published* release timestamp; schedules shift.
- **ML4T-04-R6** — Identifier match ≠ correct resolution. Pick the layer (entity / security / contract) explicitly.
- **ML4T-04-R7** — Precision over recall in entity matching; the failure is asymmetric.
- **ML4T-04-R8** — All joins constrained by both availability time and identifier effective-date range.
- **ML4T-04-R9** — Detect leakage by running as-known vs. latest-available and comparing.
- **ML4T-04-R10** — Legal and PIT integrity are hard gates; score comparisons happen only after.
- **ML4T-04-R11** — For text: accession number as key, `accepted_at` for timing, store raw + cleaned + extraction metadata.

### ML4T-05 — Synthetic Financial Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-05-R3** — Evaluate fidelity, utility, and privacy **separately** — each can pass while another fails badly.
- **ML4T-05-R4** — Marginal-distribution tests are necessary and never sufficient; test dependence and temporal structure independently.
- **ML4T-05-R5** — ACF of squared returns is the cheapest high-value diagnostic for volatility clustering.
- **ML4T-05-R6** — Beat the classical baseline (stationary bootstrap, GARCH) before accepting a deep generator.
- **ML4T-05-R8** — Regime-conditioned generation inherits the regime detector's errors.
- **ML4T-05-R9** — Choose the generator by objective alignment: tails → Tail-GAN, paths → Sig-CWGAN, irregular timing → GT-GAN, general → Diffusion-TS, mixed-type tables → LLM.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R1** — **The timestamp contract, not the model, decides whether a text feature is tradable.** Publication ≠ scrape ≠ vendor timestamp; pick the one you could have acted on.
- **ML4T-10-R4** — **Benchmark accuracy does not transfer across text distributions.** Run a cross-dataset evaluation; expect drops of tens of points when label conventions differ.
- **ML4T-10-R6** — **Snapshot documents at first availability and reject revisions by default.**
- **ML4T-10-R11** — **Coverage is endogenous** — evaluate IC conditional on coverage, and consider modeling coverage as its own signal.

### ML4T-11 — The ML Pipeline

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-11-R15** — **Conformal coverage in finance is empirical, not guaranteed.** Monitor by fold, regime, magnitude bucket, and asset characteristic; a marginal number hides the failures that matter.

### ML4T-16 — Strategy Simulation

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-16-R12** — **Build regime labels point-in-time with expanding medians.** A full-sample threshold contaminates the diagnostic.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R9** — **Pre-filter on metadata before ANN search,** never post-filter.

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R5** — **Separate mentions from identities,** key on stable identifiers, and treat corporate actions as first-class identity-updating events.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R14** — **Choose frameworks on state visibility, replay, and policy enforcement,** not benchmarks.

