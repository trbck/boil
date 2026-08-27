# Ch 25 — Live Trading Systems

**Governs:** the transition from verified backtest to live execution — broker integration, order lifecycle, technical parity, and the operational gates that precede real capital.
**Thesis:** live trading has two failure classes, and they must be separated before diagnosis is possible. **Technical divergence is self-inflicted and should be eliminated by construction; statistical decay is a monitoring problem. Until parity is verified, you cannot tell which one you have.**

---

## 1. Technical divergence vs. statistical decay

> **The failure mode: research in notebooks, rewrite for production in a different language or framework, possibly by a different team. Two parallel implementations of the same logic — and two opportunities for bugs to hide.**
>
> **The problems compound. A researcher improves feature engineering; production must replicate it. Production hits an edge case; the fix doesn't propagate back. Six months later the backtest shows 15% annual return and live delivers 3%. The discrepancy is real but hard to diagnose.**

**Four common divergence sources:**

| Source | Example |
|---|---|
| **Feature calculation** | Moving average on adjusted closes in research, unadjusted in production; slightly different volatility lookback |
| **Timing assumptions** | Research computes at close and assumes next-open execution; production receives data with varying delays and executes asynchronously |
| **Data edge cases** | Missing prices, corporate actions, ticker changes — **research often ignores these; production must handle them** |
| **Order translation** | Converting "+0.05 target weight" into orders involves lot-size rounding and liquidity constraints; **different implementations make different choices** |

> **These differences often go undetected until cumulative divergence becomes material.**

### The unified framework — same source files, both modes

**Four design principles:**

1. **Abstract interfaces for data and execution hide the source** — the strategy is indifferent to whether data comes from a historical database or a live WebSocket
2. **Signal generation must be deterministic** — no system-time dependencies, no run-varying random seeds, no external state that differs between environments
3. **Both modes share an event-driven core.** Backtest replays events from history; live receives them from feeds. **The same event handlers process both**
4. **Position, order, and strategy state are maintained identically,** with persistence and recovery so a restarted live system resumes from saved state

> **The payoff: strategies from Ch. 16–19 are production code waiting for a live data source.** The `on_data()` logic, allocation rules, and portfolio intent carry over unchanged. **Ch. 17's weight-follower becomes the live execution strategy; Ch. 18's cost parameters become the live cost budget against which realized execution is measured; Ch. 19's kill-switch levels become safety controls enforced by the broker wrapper rather than assumptions inside a simulator.**

**What live adds around the unchanged strategy:** asynchronous broker connectivity, startup checks, shadow mode, persistent risk state, guarded order submission.

---

## 2. Broker integration

### Interactive Brokers

**TWS vs. Gateway:** TWS is the full desktop app requiring a display — **valuable during development for visual feedback, complicating headless deployment.** Gateway runs headlessly with fewer resources — **typically the better production choice.** Both require periodic authentication refresh; **automated login solutions exist but the credentials provide full account access.**

**Connection:** long-lived socket, one client ID per process (**duplicate IDs cause disconnection conflicts**). Default ports 7496/7497 for TWS live/paper, 4001/4002 for Gateway.

> **The socket is long-lived, so the system must actively detect broken or stale connectivity.** Use a lightweight heartbeat (periodic `reqCurrentTime()`), treat missed responses as failure, reconnect with exponential backoff, **re-subscribe to market data, and reconcile broker state by reloading open orders, completed orders, executions, positions, and account values before resuming trading.**

**SmartRouting** scans multiple venues and **does not sell order flow to wholesalers.**

> **The execution-quality anchor: 85,000 simultaneous market orders across five US brokers found round-trip cost dispersion from 0.07% to 0.46%, with payment for order flow explaining only 3.4% of the variation. Broker routing choices can matter more than direct commissions.**

**Error codes worth handling:** 502 (cannot connect) · 504 (**connection dropped — reconnect and reconcile state**) · 201 (order rejected — parse for reason) · 202 (cancelled, client- or broker-initiated) · 162 (**historical data pacing — implement request queuing**).

**Historical data:** pacing restrictions with pattern-dependent limits, availability varying by instrument and exchange, bar sizes from 1 second to 1 month **but not all sizes for all instruments.**

> **Use IBKR primarily for recent data and verification against a primary vendor source rather than as the bulk historical source.**

### Alpaca

> **"Commission-free" does not mean cost-free: routing quality, spread capture, and venue selection still determine realized execution cost.**

| | Alpaca | IBKR |
|---|---|---|
| Assets | US equities/ETFs, listed options, crypto | **170 markets, all asset classes** |
| Order types | Market, limit, stop, stop-limit | Adaptive, pegged, conditional, many more |
| Rate limits | 200 req/min (unlimited paid) | 50 messages/second |
| Auth | API key/secret, no expiry | **Session-based, periodic renewal** |
| Routing | **PFOF to wholesalers (standard)**; smart routing paid tier | SmartRouting, no PFOF (Pro) |

> **Paper trading uses the same account and order workflow but simulates fills rather than negotiating against real liquidity. Useful for integration testing, not for measuring live slippage, market impact, or partial-fill behavior.**

**Coverage gap worth planning for:** Alpaca's USD-quoted spot subset covers **11 of the 19 Binance USDT perpetuals** the crypto case study trades. **A strategy ported from the perp universe must route the missing names elsewhere or log them signal-only.**

### Direct crypto exchange APIs

> **For crypto derivatives, broker-mediated access is insufficient.** Major exchanges operate as **both venue and counterparty** — the closest analog to direct market access available to retail, **though the exchange is simultaneously matching engine and custodian, a structural counterparty risk absent in traditional finance where broker, exchange, and clearinghouse are distinct.**

> **Geographic restrictions are the binding constraint. Treat venue eligibility as a legal and operational prerequisite, not a detail to verify after the strategy is finished.**

### Idempotency keys — the pattern that prevents duplicates

**Generate unique client order IDs** (UUIDs or deterministic from strategy + symbol + signal timestamp), store the mapping to internal references.

> **Retry safely: if a submission times out, retry with the same ID. If the original succeeded, the broker returns the existing order; if it failed, it creates a new one. The system should never create duplicate orders due to network issues or crash recovery.**

---

## 3. Managed platforms

**What platforms bundle:** infrastructure, pre-built broker integrations that update when APIs change, historical and real-time feeds, optimized backtest engines.

**Five evaluation dimensions:** development speed · **flexibility** (self-hosted integrates any data source and broker; *if your strategy needs something the platform doesn't offer, you're stuck*) · **cost structure** (modest at small scale; **calculate the crossover point for expected capital**) · **intellectual property** (platform deployment means strategy code on third-party infrastructure) · operational burden.

**Platforms fit** retail-scale where infrastructure costs dominate · rapid prototyping · **teams where development time is more valuable than operational control** · simpler strategies on liquid instruments through supported brokers.

**Migration planning:** keep strategy logic separable from platform boilerplate · **maintain independent data-vendor relationships rather than relying solely on platform data** · **test that exports actually run on alternative infrastructure before depending on migration.**

---

## 4. Order lifecycle as a state machine

**Seven primary states:** Created (internal, not submitted) → Submitted (awaiting acknowledgment) → Acknowledged (working at exchange) → Partially Filled → **terminal: Filled, Canceled, Rejected.**

> **The uncertainty window matters: until acknowledgment arrives, the order's existence is uncertain — a network failure during submission leaves it unclear whether the order reached the broker.**

> **The state machine is the critical integration point between the unified framework and the broker APIs. Backtest simulates transitions instantaneously; live processes asynchronous broker callbacks through the same logic — so order-handling behavior is verified in backtests and reproduced exactly in production.**

**Three edge cases the machine must handle:**

| Case | Handling |
|---|---|
| **Out-of-order messages** | A fill may arrive before acknowledgment. **Accept valid transitions regardless of message order** |
| **Concurrent events** | A cancel sent as the order fills: order moves to PENDING_CANCEL, the fill arrives ahead of the cancel ack, **the in-flight cancel is discarded, and the audit trail records the PENDING_CANCEL → FILLED transition so the resolution stays reconstructible** |
| **Network timeouts** | **Query broker state before deciding whether to retry** |

**Rejections demand understanding the cause** — insufficient buying power (retry after other orders free capital), invalid symbol (log and investigate), market closed (wait). **Don't blindly retry rejections.**

**Cancellations:** end-of-day cancellation of day orders is expected; **midday broker-initiated cancellation indicates a problem requiring investigation.**

### Reconciliation

**Three comparisons daily:** position quantities (**discrepancies indicate missed fills, erroneous calculations, or trades made outside the system**) · open orders (**orphaned broker orders not tracked internally are dangerous — they can fill unexpectedly**) · cash balance (missed fills, fee miscalculations, external deposits).

> **When reconciliation detects discrepancies, halt automated trading until resolved. Automatic correction risks turning record-keeping errors into trading errors. Manual review before adjustment is safer.**

**Crash recovery sequence:** check whether the order ID exists in pending orders → query the broker by client order ID → if the broker has it, update internal state to match → **if not, the submission failed; retry with the same ID.**

---

## 5. Pipeline parity verification

**Four stages, compared checkpoint by checkpoint:** raw data → features · features → predictions · predictions → signals · signals → orders.

> **Feed identical inputs to backtest and live at each stage; any difference indicates technical divergence. This enables binary search for the divergence point.**

**Feature parity failure sources:** **look-ahead bias in the backtest** (backtest uses future data unavailable at decision time; the correct live system computes different features) · data adjustment differences (split-adjusted history vs. unadjusted live prices) · **missing data handling** (backtest forward-fills; live raises an error, uses a different fill, or passes missing values to the model) · timezone confusion.

**Prediction divergence sources:** serialization differences (**different library versions, missing dependencies, or platform differences causing subtle changes**) · preprocessing mismatch · random state · **numerical precision — float32 vs. float64 differences accumulate through deep networks.**

**Sizing divergence sources:** optimizer configuration (constraint tolerances, solver settings) · risk model differences · **universe differences from data availability or listing status.**

### Automated regression testing

> **Automate rather than spot-check. For a daily strategy, check each morning whether the previous day's live signals match what the backtest would have produced from the same information set. Any mismatch should halt trading until explained.**

**Per-commit tests compare features and predictions against ground-truth cases; periodically replay the complete live pipeline on historical data** to catch integration errors unit tests miss.

> **A failure mode the harness explicitly closes: silent passes against an empty live log. The harness emits explicit SKIP semantics when the async live pipeline cannot run, and annotates expected differences (warm-up window mismatches) informationally rather than failing the gate.**

**Diagnosis order:** verify inputs are identical first (**a data-feed issue easily looks like a computation bug**) → compare intermediate artifacts stage by stage → **matching features but different predictions points to the model layer; matching predictions but different signals points to the optimization layer** → check dependency versions.

### Venue mismatch is a distribution shift no code verification catches

> **Training on one exchange's history while running live inference on another creates a distribution shift.** Quote conventions differ (spreads, price rounding, timestamp alignment) · **fee structures affect signals** (a funding-rate signal trained on one exchange's rate methodology may not generalize) · **liquidity profiles vary, so cross-sectional features that rank by volume can yield different rankings across exchanges.**

> **First preference: use the same venue for training and inference. When matching is impossible, treat the mismatch as an explicit verification problem — feature definitions may match while exchange conventions still differ. Measure and document before live deployment.**

**Practical tension:** a single exchange's public API may provide only **90 days of history** while archived datasets offer years. **When mixing sources, verify feature distributions are comparable before training on combined data.**

---

## 6. Parity vs. regime stability — the chapter's key distinction

> **A parity-verified pipeline can still lose money when market structure shifts after training. The crypto funding-rate case demonstrates the difference.**

The LightGBM classifier trained on 2020–2023 showed positive validation edge; **holdout including the late-2025 crypto drawdown did not. The natural reaction is to suspect a bug — the verification discipline rules that out: features, predictions, and signals match across environments.**

> **The explanation is structural, not technical.** Funding-rate signals prescribe long tokens with unusually negative funding, short those with positive. **In the 19-perp universe, that loaded the long leg onto smaller-cap tokens (COMP, DOT, SUI, AVAX) at ~10% each and the short leg onto majors (BTC, ETH). When the drawdown compressed the entire asset class, the long-alt leg drew down harder than the short-major leg paid out. The signal remained internally consistent; the implied factor exposure — alts over majors — swung against the strategy.**

> **And the losses are diffuse rather than blow-up-driven: the top three loss-contributing tokens account for only ~8% of total losses. Universe filtering would not fix it — removing the long-alt leg leaves an unhedged short position, which is not the strategy the signal prescribes.**

**The division of responsibility:**

| Chapter | Question |
|---|---|
| **25** | **Does the live system compute the same quantities as the backtest?** Here, yes |
| **26** | **Should the system continue trading given current regime characteristics?** A monitoring question that can pause a technically correct pipeline |

> **The demo is therefore a parity artifact, not a profitable strategy.** Its value is exposing every live mechanic: authenticated and unauthenticated endpoints, asynchronous feed orchestration, the trained-model-to-order pathway, kill-switch behavior under adverse PnL.

**The contrasting FX deployment** shows the cooperative case — holdout consistent with validation, daily cadence, narrow spreads, continuous weekday markets, **and an implied factor exposure (carry blended with short-horizon momentum) less tightly coupled to a single market-wide drawdown.**

### Two parity gaps a live deployment reveals

From the IB basket-rebalance demo, both documented rather than worked around:

- **Warm-up bars pulled from the broker session rather than a research-time loader,** so rank inputs and order-value reference prices come from the same session that will execute. **Using a research-time loader would rank names on stale prices and size positions against historical levels — a feature-parity failure.** Cost: pacing limits and per-contract qualification add latency, requiring parallelized requests
- **Post-submission state reconciled by polling rather than subscribing to execution events.** Simpler and sufficient for a daily rebalance, **but it adds latency and can miss fills landing between intervals; event-driven reconciliation is the production-grade alternative**

---

## 7. Operational readiness

### Preflight gate — five checks that block trading on failure

1. **Runtime environment** — container health, broker network paths, current data feeds, supporting services. *A strategy starting from a partially degraded environment is already abnormal before it places an order*
2. **Authentication** — **the dangerous case is partial success: the session authenticates but to the wrong account, wrong environment, or a limited permission set**
3. **State coherence** — internal positions match broker positions, cash reconciles, no orphaned orders, previous reconciliation completed cleanly. **Without this baseline, the strategy is compounding an unknown discrepancy rather than extending yesterday's state**
4. **Market context** — venue open, no restrictions or circuit breakers active, prices current rather than stale
5. **Configuration** — risk limits, order-size caps, kill-switch access verified

**These run automatically at startup, produce a short human-readable report, and block trading if any required condition fails.**

### Four-level kill switch

| Level | Action | When |
|---|---|---|
| 1 | Pause new signals, let existing orders finish | Behavior suspicious but not clearly dangerous |
| 2 | Cancel working orders, leave positions | Order routing or logic suspect, inventory acceptable |
| 3 | Flatten to cash | Holding risk no longer justified by confidence in system state |
| 4 | Full shutdown of process and dependent automation | Infrastructure failure, corrupted state, **operator trust completely broken down** |

> **Each level must be a single tested control — a command, shortcut, or button. Under stress, multi-step emergency procedures fail because they ask the operator to reason clearly at the moment the system is least trustworthy.**

> **The kill switch must remain independent of the component it controls. If the strategy engine hangs, the operator still needs a broker-side or infrastructure-side path to cancel orders and flatten risk.**

### Two controls that fail open without persistence

- **The daily-loss kill switch is useful only if it survives an engine restart during a trading day** — otherwise a crash and reconnect reset the loss counter and re-enable trading at the worst possible moment. Write state on every transition, reload on reconnect
- **The data-staleness check requires a per-asset timestamp for the last bar received,** rejecting orders whose freshest data exceeds the threshold

> **Together these prevent two of the most common live failure modes: trading on a stale feed during a venue outage, and re-entering positions after the kill switch was supposed to be latched.**

**Startup reconciliation closes the third:** diff the persisted snapshot from the previous session against the broker's current authoritative state.

> **A non-clean report means something changed between sessions — an after-hours order finally filled, a manual flatten in the GUI, an out-of-band cancel, or a partial fill landing after the last persist. Any production launcher should refuse to start a new trading cycle until the report is clean or the operator has explicitly reset the persisted state.**

### Two deployment-loop invariants the runtime cannot infer

- **Training-cutoff guard:** `LABEL_AVAILABLE_AS_OF = LIVE_WINDOW_START − forward_horizon_days`, so no training label reads prices from the live window. *A 21-day forward return on a 2025-01-01 live window forces training to cut at 2024-11-29, not 2024-12-31.* **Both cutoff dates are persisted alongside the run record so monitoring can audit the invariant after the fact without re-running training**
- **Basket disposition partitioned** across intended / attempted / accepted / failed and persisted separately, **rather than collapsed into one status string** — so monitoring can alert on a non-empty failed basket without re-parsing exec records, and **the dry-run path keeps the full basket in `intended` so disposition stays testable without a live broker**

**Shadow-mode health states a watchdog should consume:** `ok` · `waiting_for_data` · `feed_silent` · `idle_market_closed` · `broker_disconnected`. **These are inputs to a supervisor process, not a substitute for one.**

### Paper to live

> **Paper trading validates integration but not market impact, live commissions, or the operational pressure of real money.**

**Extended paper phase** long enough to observe routine behavior → **first live deployment at a fraction of intended capital, whose purpose is not to prove profitability but to verify that live fills, fees, and position updates behave as expected when money is at risk** → gradual increase, each step another test of operational stability under higher stakes.

> **Parallel operation makes the transition more informative: running live and paper side by side exposes divergence in signals, order timing, and realized fills. Those differences are often more useful diagnostically than the raw PnL of either book during the transition.**

### Jurisdiction

| Region | Constraints |
|---|---|
| **US** | No special registration for retail algo trading. **Pattern Day Trader rule: $25,000 minimum for 4+ day trades in 5 business days — binding for smaller intraday accounts.** SEC Rule 15c3-5 requires broker pre-trade risk controls, prohibiting naked market access |
| **EU** | MiFID II Article 17 requires notification, risk controls, price collars, maximum order values, kill buttons — **applying to regulated investment firms, not retail individuals through a licensed broker. A retail trader scaling to external capital enters regulated territory** |
| **India** | **One of the most prescriptive retail-algo regimes** — broker-mediated approval workflows and exchange-assigned identifiers. **Details have changed repeatedly; check current broker and exchange guidance rather than older blog posts** |

> **Transaction taxes, leverage caps, and venue access can turn an attractive backtest into an untradeable strategy** — UK stamp duty, European FTTs, product-level crypto restrictions.

**Four checks before deploying in any jurisdiction:** Is the product legal to trade? Does the broker support automated access for it? What taxes or market-access fees apply? Which leverage or margin rules govern the account?

> **These belong in the deployment checklist, not an appendix after the strategy is built.**

---

## Transferable rules

1. **Separate technical divergence from statistical decay before diagnosing anything.** Until parity is verified, live deviations could be either, making diagnosis impossible.
2. **Run the same source files in both modes.** Rewriting for production creates two implementations and two places for bugs to hide.
3. **Make signal generation deterministic** — no system time, no run-varying seeds, no environment-dependent external state.
4. **Detect stale connectivity actively with a heartbeat,** and reconcile broker state on every reconnect before resuming trading.
5. **Treat broker routing as an execution-quality decision.** Cost dispersion across brokers dwarfs commission differences, and PFOF explains little of it.
6. **Use client order IDs as idempotency keys** so crashes and timeouts cannot produce duplicates.
7. **Model orders as an explicit state machine that tolerates out-of-order messages** and records race resolutions in the audit trail.
8. **Never blindly retry rejections** — the cause determines the correct response.
9. **Halt on reconciliation discrepancies rather than auto-correcting,** or record-keeping errors become trading errors.
10. **Verify parity stage by stage** so divergence can be binary-searched rather than guessed at.
11. **Make parity tests fail loudly on a missing live pipeline** rather than silently passing against an empty log.
12. **Match training and inference venues,** and when impossible, measure and document the convention differences as an explicit verification task.
13. **Source warm-up data from the executing session,** not a research-time loader, or rankings and sizing run on stale prices.
14. **Persist kill-switch state across restarts** — an unlatched switch after a crash re-enables trading at the worst moment.
15. **Reject orders on stale data** using a per-asset freshness timestamp.
16. **Refuse to start a trading cycle on a non-clean startup reconciliation.**
17. **Keep the kill switch independent of the component it controls,** and make each level a single tested action.
18. **Encode the training-cutoff invariant explicitly** and persist both cutoff dates for later audit.
19. **Partition basket disposition into intended / attempted / accepted / failed** rather than a single status string.
20. **Run paper and live in parallel during transition** — the divergence is more diagnostic than either book's PnL.
21. **Verify legality, automated access, taxes, and margin rules in the target jurisdiction before building,** not after.

---

## Notebooks

`01_unified_framework_demo` (signal parity on shared historical replay, zero strategy-code changes) · `02_etfs_deployment_loop` (**the anchor: refresh panel, retrain Ridge, replay live window for an offline reference tape, submit top-K through Alpaca paper, reconcile symbol by symbol**) · `03_ib_paper_trading_demo` · `04_alpaca_paper_trading_demo` · `05_alpaca_crypto_live_demo` · `06_quantconnect_case_study` (export predictions to Object Store, consume from LEAN) · `07_order_state_machine` (**10 states, 19 valid transitions, audit trails**) · `08_pipeline_verification` (**five gated parity tests with explicit SKIP semantics**) · `09_crypto_funding_deployment_loop` (**split-venue: OKX for data, Alpaca paper for execution on 11 of 19 names**) · `10_safety_risk_demo` · `11_fx_deployment_loop` (**single-venue: IB as both data and execution plane via IDEALPRO**) · `12_ib_basket_rebalance_demo` (startup-reconciliation pattern, refuses to launch on a non-clean report) · `13_runtime_safety_showcase` (**stale-data rejection, kill-switch latch surviving broker reconstruction, deliberately divergent reconciliation state**)

**Libraries:** `ml4t-backtest` (research and validation engine from Ch. 16–19) · `ml4t-live` (same Strategy interface for paper and live, broker adapters, `SafeBroker` enforcement point, `ml4t-live status` and `ml4t-live shadow` CLI).

---

## Cross-references

Ch. 3 order types, execution mechanics, ITCH message flow (which the state machine mirrors) · Ch. 12 the LightGBM funding-rate and FX models deployed here · Ch. 16 the backtest protocol and event-driven engine; probability of backtest overfitting · Ch. 17 the weight-follower strategy that becomes the live executor · Ch. 18 cost parameters becoming the live cost budget; Almgren-Chriss urgency trade-off · Ch. 19 kill switches and drawdown thresholds becoming broker-enforced controls · Ch. 20 the case studies whose pipelines port unchanged · Ch. 24 the read-only agent boundary this chapter's execution layer sits beyond · Ch. 26 drift detection, circuit breakers, and safe model rollout after parity is established

---

## Citations

Almgren & Chriss (2001), optimal execution · Bailey et al. (2015), probability of backtest overfitting · Harris (2003), trading and exchanges · López de Prado (2018), look-ahead bias · Madhavan (2002), microstructure and execution quality · Schwarz et al. (2022), broker execution cost dispersion

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 25.*
