# Ch 6 — Strategy Research Framework

**Governs:** the invariants you fix *before* research starts — what is traded, when decisions fire, how scores become positions, and what counts as evidence.
**Thesis:** a backtest is only interpretable if the evaluation environment is frozen and versioned; without that, every "improvement" is confounded with a silent change in assumptions.

---

## 1. Two loops, one timing contract

The research loop must be a faithful simulation of the live loop. Live loop, per decision:

1. Snapshot available information
2. Compute features → produce score
3. Map score → target positions under constraints
4. Execute → fills with slippage, spread, fees, financing, funding, roll
5. Monitor, update, repeat

The research loop wraps it: declare environment → build minimal end-to-end baseline → evaluate under time-series protocol → diagnose and change **one component** → log the run.

> The trap is not "using future data" — that's obvious. It's that timing conventions drift silently across iterations, so a performance delta gets attributed to a model change when it actually came from a shifted snapshot. Freeze conventions first; that's what makes attribution possible at all.

---

## 2. Strategy families = feasibility filters (what breaks first)

Family does not determine cadence. It tells you which constraint becomes first-order once you pick one.

| Family | Dominant constraint | Fix early | First screen |
|---|---|---|---|
| **Price-based** (trend, XS momentum, ST reversal) | Turnover/execution at short cadence; episodic drawdown at long | Holding horizon, rebalance cadence, lookback, score→position map | Does it survive modest lookback/cadence perturbation under turnover-aware costs? |
| **Fundamental / valuation** | Decision-time meaning of inputs, not speed | PIT conventions, coverage rules, universe construction | Effective sample size (slow signals ≪ row count) |
| **Flow / microstructure** | Timing discipline, latency, fill realism | Observation→execution delay, depth-relative sizing | Do fills scale plausibly with size vs. depth and volume? |
| **Market mechanics / payoff** (roll, funding, options) | Instrument lifecycle mechanics *are* the payoff | Return decomposition, contract selection, roll schedule | Component attribution; behavior when margin/funding binds |

> "Machine learning" is not a strategy family. It's a decision-support layer that *expands* degrees of freedom, which raises — not lowers — the value of a bounded setup definition.

---

## 3. Four time notions to keep separate

Conflating these is a routine source of incoherent specs.

| Notion | Definition |
|---|---|
| **Decision cadence** | How often position may change (the rebalance schedule) |
| **Holding period** | How long risk is actually held; fixed or signal/risk-triggered |
| **Forecast horizon** | The interval the model predicts — need not equal holding period |
| **Lookback window** | How far back features reach at decision time; may differ per feature |

---

## 4. Six sources of edge, ranked by durability

Durability is the question "what must remain true for this to persist," and it is separate from feasibility.

| Source | Mechanism | Durability | Why |
|---|---|---|---|
| Risk compensation | Bearing exposures others avoid (tail, vol, illiquidity) | **High** | Constraint is risk aversion, not information |
| Liquidity provision | Premium for supplying immediacy / absorbing inventory | **High** | Structural demand for immediacy |
| Funding constraints | Dislocations when capital scarce / leverage restricted | Moderate | Episodic; strongest in stress |
| Flow predictability | Positioning ahead of mandated, rules-based demand | Moderate | Erodes with crowding, recurs per event |
| Informational advantage | Better inference from public data | **Low–moderate** | Erodes as methods are replicated |
| Pure arbitrage | Identical-asset mispricing across venues | **Very low** | Fleeting, capacity-constrained, ops-heavy |

**Decision rule:** edges resting on *information alone* erode. Edges resting on *risk tolerance, constraints, or capacity limits* can persist even when fully public. State the dominant source explicitly, then test its specific failure mode.

**Calibration anchor:** published predictors lose roughly **half** their predictive power post-publication (McLean & Pontiff, 2016) — part overfitting correction, part arbitrage inflow. Passive holdings at ~**35–40%** of US equity market cap make index-reconstitution flow events larger *and* more crowded simultaneously.

> **Prediction ≠ profit.** The 3Com/Palm case: implied Palm valuation exceeded the parent's, visible to everyone, and persisted for months. Borrow was scarce, fees spiked, spin-off timing was open-ended. Before engineering features for a mispricing hypothesis, verify short-side access, that borrow+funding don't consume the spread, and that holding-period risk is bounded.

### Failure-mode tests by source

| Narrative | Test first |
|---|---|
| Slow adjustment / underreaction | Drawdown-and-rebound episodes; does performance concentrate in benign states and reverse on vol spikes? |
| Risk compensation | Tail episodes with binding constraints; performance conditional on vol and liquidity proxies |
| Segmentation / limits to arbitrage | Stressed financing and fee regimes; realism of access assumptions; crowding behavior |
| Mechanical flows | Calendar/event alignment; decay under crowding; execution sensitivity (these live near the spread) |
| Measurement advantage | Robustness to definition choices; sensitivity to coverage/missingness |

---

## 5. The trading setup — five things it must fix

The setup is the versioned invariant set. Explore aggressively *inside* it; changing it creates a new version.

1. **Universe and tradability** — eligibility filters, membership mechanics, listing/delisting/stale-price handling
2. **Decision schedule and admissible information** — timestamp convention, bar frequency, mechanical execution delay
3. **Score-to-trade mapping** — position state space, entry logic, exit logic, sizing, order timing
4. **Constraints and risk controls in scope** — leverage/exposure limits, concentration, capacity; any action-changing overlay or kill switch must be explicit and versioned
5. **Cost model class and components** — which of fees / spread / slippage / financing / funding / borrow / roll are treated as material, and how conservative

### Version-bump rule

| Same version (parameter tuning) | New version (mechanics changed) |
|---|---|
| Threshold 1.8 → 2.0 | Rank selection → threshold gating |
| Top 10% → top 20% | Long-only → long/short |
| 20-day → 60-day normalization | Adding a stop rule where none existed |
| Different lookback horizon | Changing rebalance cadence or execution delay |
| Cost 10 bps → 15 bps per leg | Adding funding/roll as a cost component |

Results across setup versions remain informative but are **not direct competitors** within one research program.

### Worked calibration — the ETF momentum setup (v1)

Concrete numbers worth stealing as defaults for a daily/monthly cross-asset baseline:

- Universe: 100 cross-asset ETFs, PIT eligibility at trailing annual **ADV ≥ $10M** (lenient on purpose — preserves breadth; yields **70–95 eligible names/year**)
- Schedule: month-end close snapshot, execution at **next-day open**
- Mapping: long-only (ETFs expensive to short), rank-select top-N, equal-weight (isolates ranking from sizing)
- Costs: **$0.0035/share** commission (IBKR Pro Tiered) + tiered half-spread slippage — **0.5¢** mega-ETFs, **1¢** sector, **2¢** default for thematic/regional
- Feasibility screen: **5–15 bps per leg** reference line; monthly moves exceed **30 bps round-trip** in **>90%** of observations

> Residual bias worth naming: within-universe eligibility is PIT-correct, but the *composition* of the 100-ETF universe still carries survivorship bias that cannot be fully resolved without historical constituent data. Document it rather than pretending it's clean.

### Cadence feasibility — three regimes

Before any signal work, ask: at this horizon, what fraction of typical price moves exceeds round-trip cost?

| Regime | Meaning | Example |
|---|---|---|
| **Hard floor** | Costs clearly dominate | 15-minute bars on the microstructure panel |
| **Gray zone** | Feasible only if signal strong and turnover controlled | ETFs, daily |
| **Comfortable** | Costs not the binding constraint | ETFs, monthly |

---

## 6. Three metric layers — never collapse them

| Layer | Question | Typical metrics | Needs cost model? |
|---|---|---|---|
| **Model diagnostics** | Can the model learn the label and generalize across time splits? | Loss/error, calibration, fold stability | No |
| **Signal diagnostics** | Does the output behave like a tradable score under the mapping? | IC (Spearman rank corr. of score vs. forward return) | No |
| **Strategy outcomes** | Does the end-to-end process create economic value? | Risk-adjusted return, vol, drawdown, exposure, realized turnover | Yes |

**Decision rule:** one primary selection metric for development, a separate reporting set for outcomes.

> The named failure mode: driving every micro-decision off strategy outcomes. That overfits to the simulator's degrees of freedom and will disappoint out-of-sample. Keep strategy outcomes late-stage. If model diagnostics fail, downstream trading results are uninterpretable — the predictor is unstable, so stop rather than proceeding to the backtest.

---

## 7. Leakage taxonomy — three forms beyond source-data problems

| Form | What it looks like |
|---|---|
| **Label leakage** | Future returns leak into the same observation's features |
| **Standardization leakage** | Scaler statistics (mean, σ for z-scores) computed on the full dataset instead of train-only — reveals distribution shift in the validation period |
| **Threshold leakage** | "Enter when z > 2.0" chosen *after* observing that 2.0 maximizes test-period returns |

---

## 8. Walk-forward as the baseline protocol

Why k-fold fails on financial series: (a) the live procedure is directional — random splits train on timestamps after the validation point, estimating a procedure that cannot be executed; (b) rows are coupled through lookback and forward windows, so even chronological splits leak across boundaries.

**Admissibility test — one question:** at decision time *t*, a sample is eligible for training only if its features are computable from information at or before *t* **and** its label is already resolved by *t*.

Minimal design: choose training window → choose validation window → enforce boundary admissibility → fit → predict → score → advance by fixed step → repeat.

| Window type | Trade-off |
|---|---|
| **Expanding** (all admissible history) | Lower variance; bias risk from stale data |
| **Rolling** (most recent L observations) | Faster adaptation; higher variance |

**Retraining cadence anchor:** retrain when new data is **1–5%** of the training window, or when OOS performance degrades systematically. 10-year window → monthly or quarterly. 20-day window → daily.

---

## 9. Temporal buffers — count in trading days

Two channels let training observations see validation data:

- **Label buffer** (López de Prado's *purge*): removes training rows whose label windows overlap validation. Size = label horizon. 20-day forward returns → exclude training observations within 20 trading days of the boundary. One-day-ahead on daily data → no buffer needed.
- **Feature buffer** (*embargo*): removes training rows whose lookback windows reach into the validation period. Only needed when training data appear *after* validation — i.e. k-fold and combinatorial schemes, not standard walk-forward. Rule of thumb 1% of sample length; correct size depends on horizon and dependence strength.

> **The calendar-day trap, with numbers.** A 21-*trading*-day label buffer spans 30–32 calendar days in January 2024. A naive 21-*calendar*-day purge covers only ~15 trading days — leaving **6 days of unpurged label leakage**. Always count buffers in trading days.

Worked example: 5-day forward-return labels, decision time Tuesday Feb 10 → latest eligible training timestamp is Tuesday Feb 3. Everything between is ineligible because labels haven't resolved.

---

## 10. Holdout governance — when to stop selecting and start measuring

Reserve a **sealed** holdout: a final time block playing no role in signal definition, feature selection, tuning, model selection, or reporting choices. Inspect only after the pipeline is frozen — once.

| Mode | Procedure | Estimates |
|---|---|---|
| **Fixed holdout** | Walk-forward select on dev period → freeze *entire* pipeline incl. mapping and cost assumptions → evaluate once on sealed holdout | Performance of one frozen configuration |
| **Rolling retuning (nested walk-forward)** | Outer test loop + inner selection loop; at each step tune on data strictly prior, refit on admissible history, score the next window (measurement only) | Performance of a *procedure that retunes* |

Nested is more realistic — with a 2-year test period and 5-year lookback, a live strategy would retune more than once, which the fixed-holdout mode assumes away. Bates et al. (2021) show nested CV yields better-behaved confidence intervals. Cost: computationally heavy; mitigate with parallel evaluation, incremental retraining, feature caching.

**Combinatorial (CPCV):** partitions time into blocks and evaluates many train/test combinations, producing a *distribution* of outcomes instead of one historical path. Use when comparing many variants and selection risk needs a stable view. It does **not** replace decision-time discipline — both buffers still apply, since validation blocks can sit anywhere relative to training. Diminishing returns on short series or when most blocks share one regime.

### Design commitments — log before experimenting

These are commitments, not tuning parameters. Changing them mid-research defines a *different evaluation procedure*, not a better result.

- [ ] Window lengths (train / validation / test)
- [ ] Step size
- [ ] Retraining cadence
- [ ] Label horizon → determines label buffer
- [ ] Longest feature lookback → determines feature buffer
- [ ] Test period dates, reserved and untouched

---

## 11. Baseline checkpoint — narrow by design

**Three preflight sanity checks** (these are not evidence of edge — they confirm the checkpoint is well-posed):

- [ ] **Timing sanity** — baseline measurement and label computable from the declared snapshot only, respecting pipeline timelines and execution delay
- [ ] **Coverage sanity** — how much of the intended universe is actually tradable at each decision time, and does coverage shift materially across history?
- [ ] **Trading-intensity sanity** — coarse proxy for turnover, to catch definitions implicitly demanding unrealistic activity *before* building a detailed cost model

**If a check fails, revise the setup conventions — do not optimize around a brittle definition.**

First reference run: one label and horizon · compact feature families representing the narrative at the right cadence · one simple baseline model class, minimal tuning · one walk-forward design. It answers only: *does a simple baseline behave stably and non-pathologically without fragile timing or extreme implied turnover?*

---

## 12. Search accounting

**Trial taxonomy** (four levels, deliberately small):

| Level | Fixed at this level |
|---|---|
| **Strategy** | Named setup + objective; universe, cadence, mapping class, cost model class |
| **Trial family** | Same setup and evaluation design, differing along **one** intended axis |
| **Trial** | One fully specified pipeline config — signal, features, model class, hyperparameters, sizing |
| **Run** | One execution: code version, data snapshot, seed, compute environment |

**Run log — five non-negotiable categories:**

1. **Provenance** — setup version, trial IDs, git hash, timestamp, seeds
2. **Data & evaluation** — dataset and PIT conventions, dev/holdout ranges, split scheme (windowing, step, both buffers), label horizon, admissibility constraints
3. **Configuration** — baseline definition and timing, feature/preprocessing spec, model class and hyperparameters, position mapping, risk and cost parameters
4. **Artifacts** — pointers to features/labels, predictions, backtest outputs (positions, trades, PnL, diagnostics)
5. **Decision and gates** — selection metric and rule, reported acceptance metrics, holdout gate outcome

**Rule:** if a field doesn't affect reproducibility, comparability, or the holdout gate, don't log it by default.

> Logging isn't bureaucracy — it's the precondition for a deflation adjustment. The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) corrects for the probability of overfitting **given the number of trials**. If trials aren't counted, the correction cannot be computed, and selection bias stays invisible. LLM-assisted hypothesis generation multiplies trial counts, which makes this worse, not better.

**Pre-registration** — specify economic thesis, signal definition, and evaluation criteria before running the backtest. It doesn't preclude exploration; it draws the line between confirmatory tests (which count toward deflation) and exploratory analyses (which seed future hypotheses).

---

## Transferable rules

1. **Freeze the evaluation environment before optimizing anything in it.** Attribution of a performance delta to a design change is only valid if everything else is versioned and recorded.
2. **Separate feasibility from durability.** A credible story with an infeasible implementation is not a strategy; a feasible implementation with no story is a backtest whose failures are uninterpretable.
3. **Prefer edges grounded in constraints over edges grounded in information.** Information edges erode on replication; constraint and risk-tolerance edges survive publicity.
4. **Distinguish mechanics from parameters.** Mechanics changes bump the version and reset the baseline; parameter changes don't.
5. **Use three metric layers with distinct roles** and never let end-to-end economics drive micro-decisions during development.
6. **Test admissibility with one question:** at decision time *t*, were the features computable and was the label already resolved?
7. **Count buffers in trading days, never calendar days.**
8. **Seal the holdout and open it once,** after the whole pipeline — including mapping and cost assumptions — is frozen.
9. **Run cadence feasibility before signal research.** If costs dominate at the intended horizon, no signal quality rescues it.
10. **Make search countable.** Trial counts are an input to overfitting corrections, not paperwork.
11. **When a preflight check fails, revise the setup, don't engineer around it.**
12. **Treat a published anomaly as a hypothesis, not evidence.** Independent validation must happen inside your own setup and cost assumptions.

---

## Notebooks

- `01_cv_foundations` — walk-forward, purging/embargo, nested and combinatorial splits via the `ml4t-diagnostic` library
- `02_case_study_overview` — trading setup inventory (universe, schedule, mapping, constraints, cost model) and validation configs for all nine case studies
- `01_setup.py` — per-case-study setup notebook; writes versioned `setup.yaml`, consumed downstream as a `WalkForwardConfig`

**Case study inventory** (referenced throughout Ch. 7–20):

| Key | Asset class | Frequency | Coverage |
|---|---|---|---|
| `etfs` | Multi-asset | Daily | ~100 symbols, 20y |
| `us_equities_panel` | Equities | Daily | ~3,000 symbols, 50y |
| `us_firm_characteristics` | Equities | Monthly | ~2,500 stocks, 1996–2016, ~57 characteristics |
| `fx_pairs` | FX | 4h bars / daily NY 5pm | 20 pairs, 2011–2025 |
| `cme_futures` | Futures | Daily | 30 contracts, 15y |
| `crypto_perps_funding` | Crypto | 8h | ~20 symbols, 5y |
| `nasdaq100_microstructure` | Equities | Minute → 15-min | ~114 symbols, 2y |
| `sp500_equity_option_analytics` | Equities + options | Daily | S&P 500, 5y |
| `sp500_options` | Options | Daily | S&P 500, 5y |

---

## Cross-references

Ch. 2 §PIT conventions and identifier stability · Ch. 3 microstructure and execution realism (feeds the flow/microstructure family) · Ch. 4 alternative-data PIT pipelines · Ch. 7 labels, IC, and signal diagnostics · Ch. 8–10 feature engineering under the fixed setup · Ch. 11 conformal prediction intervals as a calibration diagnostic · Ch. 16 §16.7 Rademacher Anti-Serum (multiple-testing penalty) · Ch. 17 portfolio construction metrics and CPCV in depth · Ch. 18 cost model expansion · Ch. 25 live deployment · Ch. 26 §26.6 MLOps governance and experiment tracking

---

## Citations

Asness, Moskowitz & Pedersen (2013) · Bailey & López de Prado (2014), Deflated Sharpe Ratio · Bates, Hastie & Tibshirani (2021), nested CV inference · Bergmeir, Hyndman & Koo (2018), k-fold validity for autoregressive models · Daniel & Moskowitz (2016), momentum crashes · Hurst, Ooi & Pedersen (2017) · Jegadeesh & Titman (1993) · Kohavi (1995), cross-validation · López de Prado (2018), purging, embargo, CPCV · McLean & Pontiff (2016), post-publication decay · Moskowitz, Ooi & Pedersen (2012), time-series momentum · Paleologo (2025), taxonomy of edge sources

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 6.*
