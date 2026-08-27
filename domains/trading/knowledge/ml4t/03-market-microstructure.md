# Ch 3 — Market Microstructure

**Governs:** how to turn raw market data into modelable observables — and which sampling and execution assumptions your backtest is silently making.
**Thesis:** market data is the output of a matching engine, not a neutral measurement. When a backtest ignores spreads, depth, and queueing, the error isn't a missing cost line — it's a **mis-modeled price-formation process**.

---

## 1. Liquidity has three separable dimensions

| Dimension | Definition | What it constrains |
|---|---|---|
| **Spread** | Cost of immediate execution | Whether a small signal is viable at all |
| **Depth** | Quantity at and away from best prices | How much you can trade before moving price |
| **Resiliency** | How fast liquidity replenishes after being consumed | Capacity and repeat trading |

Small signals cannot overcome wide spreads; large positions need depth *and* resilience. These are different failure modes — check both.

**Two frictions drive quote formation:**
- **Adverse selection** — providers quote under information asymmetry; informed counterparties turn passive fills into losses. Response: widen spreads, shade quotes, reduce displayed depth. Kyle (1985): price impact ∝ net order flow, with **Kyle's lambda** measuring response strength to trade imbalance (a direct input to Ch. 18 cost models). Glosten–Milgrom (1985): spreads arise from adverse selection *alone*, even with zero transaction costs.
- **Inventory risk** — a provider too long into a falling market can lose more on inventory than it earns on spread. Constrains both quote placement and supplied depth.

Madhavan (2002): price impact has **temporary and permanent components** and is **nonlinear in order size**. In fast markets adverse selection dominates; in calm markets fee schedules and venue incentives matter more.

---

## 2. Order types — and their observable signatures

| Type | Book effect | Diagnostic signature |
|---|---|---|
| Marketable (market / marketable limit) | Removes depth | Print at best bid/ask + size reduction at that level |
| Limit (resting) | Adds depth | May improve best bid/ask |
| Stop / stop-limit | Invisible until triggered (often broker-managed) | Burst of executions + rapid top-of-book depletion near the trigger |
| Hidden / iceberg | Non-displayed size | **Repeated same-price prints with quote size refreshing rather than depleting** |
| Pegged | Reprices to a reference (often mid) | **Prints inside the spread with no displayed quote at that price** |
| Post-only | Maker-only; rejected/repriced rather than crossing | — |

These signatures are **suggestive, not identifying** — hidden liquidity and routing produce similar prints.

---

## 3. Intraday regimes — a first-order confounder

**The same "signal" means different things at 9:35 AM and 2:00 PM.**

| Regime | Character |
|---|---|
| Opening (first 30–60 min) | High vol, wide spreads, heavy volume as overnight info is incorporated. MRR-measured information asymmetry starts high and declines. Variance ratios stay elevated in the opening half-hour → **microstructure noise, not fundamental information** (Schwartz, Ross & Ozenbas 2022) |
| Midday | Low activity, thin liquidity. **Spreads may tighten while depth is shallow — the same order size has *greater* price impact than in busier periods** |
| Closing (final hour) | Institutional program completion + index rebalancing; closing auction concentrates liquidity and sets benchmark/settlement prices. Inventory costs rise toward the close |

Magnitude anchor (13-day ITCH sample): first and final 30 minutes each ≈ 15–17% of daily volume vs. 2.6% at midday — roughly **6× open-to-midday**.

> **Trade-signing trap (O'Hara 2015):** algorithmic parent orders split into many passive child orders, so a large *buy* can appear as a stream of sell-side prints (passive fills on the bid). This confounds naive trade-signing heuristics.

---

## 4. Feed hierarchy — what each level hides

| Level | Content | Enables | **Hides** |
|---|---|---|---|
| **L1** top-of-book | Best bid/ask. BBO is venue-specific; NBBO is cross-venue via SIP (protected exchanges only — not dark pools/internalizers) | Spreads, midprice, basic TAQ signals | Depth beyond top; queue dynamics driving fill probability and slippage |
| **L2** MBP | Aggregated size per price level, top N | Displayed liquidity, depth imbalance, execution difficulty | Order count, queue position, time priority within a level |
| **L3** MBO | Order-level submits/modifies/cancels/executes | Deterministic book replay, order-flow measurement, cancellation/replenishment dynamics | Nothing about displayed flow on that venue — but operationally demanding and expensive |

**Strategic consequence: L1 signals are widely available and therefore more crowded.** Depending on depth, queue dynamics, or very short-horizon order flow means L2/L3 — with a step change in engineering cost.

**Enriched TAQ products** (minute bars with precomputed microstructure fields) bridge part of the gap — but treat them as **derived features with embedded assumptions**, not raw data.

### Price conventions — not interchangeable

- **Midprice** = (bid+ask)/2 — default proxy for price discovery; reduces bid-ask bounce
- **Last trade (print)** — reflects a completed trade but carries direction and venue noise
- **Close** — last trade in the bar; for daily bars usually the official auction close

**Rule of thumb: midprice for short-horizon price response (signals) · executable prices (bid for sells, ask for buys) for PnL markouts · last trade/close for OHLC bars.**

---

## 5. LOB reconstruction

Pipeline: **parse → normalize → apply updates → enforce invariants → snapshot → validate against independent references (BBO/NBBO series).**

### State machine

Maintain **two** views:
1. **Order registry** keyed by order reference number (remaining size, price, side) — answers "what remains of order 123?"
2. **Price-level view** for fast queries and snapshots — answers "how many shares are bid at $101.23?"

ITCH 5.0 essential message types: `A`/`F` add (F = with MPID attribution, not a different economic event) · `X` partial cancel · `D` delete · `U` replace (terminates original, creates new reference — **replace-chain handling is essential**) · `E` execute at order price · `C` execute at explicit price. System messages (`S`, `R`, `H`) are needed to interpret the day correctly. **`P`/`Q` trade and cross messages are execution analytics, not book-update events** — a common conflation.

### Invariants — fail fast

- [ ] Order references exist before any modification/execution/cancellation
- [ ] Remaining quantity never negative (per order *and* per price level)
- [ ] Prices valid for the instrument (tick size, auction bands) and within sanity bounds
- [ ] Aggregate depth per price level = sum of constituent orders at that price

Maintain price-level totals as **first-class state**: decrement on execute/cancel, remove the level at zero, error if it would go negative. Reconcile persisted snapshots against event-driven state to catch drift early.

Reference implementations fail fast; production pipelines typically quarantine and count violations, then decide whether to drop symbol/time ranges or apply feed-specific repair.

### The single-venue limitation

A direct feed reconstructs **one venue's book**, not a consolidated market-wide book. Two consequences:
- Venue-local best quotes can differ materially from NBBO; depth that looks available may be irrelevant if the order routes elsewhere
- Comparing venue-local to consolidated data can show apparent **locks or crosses** (local best bid > consolidated best ask) from timestamp differences and asynchronous assembly

**Treat these as diagnostics:** they may indicate real fragmentation *or* clock misalignment *or* a message-handling bug.

> **Hard limitation: a reconstructed LOB shows displayed liquidity only.** Hidden/iceberg orders and internalized flow remain invisible. It is not total available liquidity.

### Snapshot design

Fixed clock interval (e.g. every 100ms) vs. event time (every N book updates) is a **measurement design choice**: clock-time aligns with latency and execution constraints; event-time aligns with information arrival but over-represents active periods.

### Parser performance anchor

13 GB ITCH file, 423M messages, one day (Jan 30 2020):

| | Python | Rust |
|---|---|---|
| Wall clock | ~23 min | < 5 min (~5–8×) |
| Peak memory | ~8 GB | < 500 MB (~16×) |

Both emit the same schema, validated by checksums, round-trip decoding, and identical downstream BBO series. Output = Parquet partitioned by message type. **The reconstruction logic is unchanged regardless of parse language** — don't optimize prematurely.

---

## 6. Empirical stylized facts

**Order lifecycle (NASDAQ, Jan 30 2020, 423M messages):**

| Metric | Count |
|---|---|
| Add events (A+F) | 186,610,705 |
| Delete events (D) | 180,285,101 |
| Partial cancels (X) | 4,990,972 |
| Replace events (U) | 36,777,372 |
| Execute events (E+C) | 8,555,084 |
| **Cancellation rate** | **96.6%** |
| **Execution rate** | **3.4%** |

Rates are *not* complements — an order can be partially executed then deleted. Event counts exceed unique-order counts because replaces create new order references tracked separately.

- Time to cancellation: 41% within 500ms · 50% within 1s (median 0.99s) · 80% within 10s
- Time to execution: 10% within 1ms · median 6.1s · **1% wait over 40 minutes**

High cancel/replace activity is not evidence of misconduct — it's mechanical consequence of competitive quoting and inventory control. But **it means displayed liquidity is fleeting and must be modeled as such.**

**Depth imbalance is weaker than commonly assumed.** `(bid_size − ask_size)/(bid_size + ask_size)` across 50 stocks: cross-stock correlation with subsequent returns is weak and noisy, **range −0.35 to 0.16**. Naive imbalance metrics are not directly tradeable — raw microstructure signals require conditioning on context (spread dynamics, time of day, extreme events). Ch. 6's order-flow reversal strategy shows conditional signals working where unconditional ones fail.

> **Tradability caveat worth internalizing:** a positive association at a one-second horizon is not a trading rule. At that horizon **spread and queue dynamics dominate PnL.** Always report *executable* markouts (bid/ask at decision time) alongside midprice markouts — the gap is the point.

**Bid-ask bounce** produces negative first-order autocorrelation in tick returns — mechanical mean reversion from alternating bid-hits and ask-lifts. Naive tick-to-tick returns are contaminated; this matters directly for return-target construction.

**Hautsch & Huang (2012):** limit orders — not just marketable orders — carry meaningful price-discovery information.

---

## 7. Bar sampling — the highest-leverage decision in this chapter

### The menu

| Bar type | Clock | Holds constant | Needs trade direction? | Typical use |
|---|---|---|---|---|
| Time | Calendar | Time interval | No | Clock-time forecasting |
| Tick | Activity | Trade count | No | Equal trade frequency |
| Volume | Activity | Shares/contracts | No | Size-based activity |
| **Dollar** | Activity | Traded value | No | **General ML default** |
| Tick imbalance (TIB) | Information | Signed trade count | Yes | Directional pressure |
| Volume imbalance (VIB) | Information | Signed volume | Yes | Informed flow by size |
| Run | Information | Side dominance | Yes | Persistent one-sided flow |

### Selection rules

- **Default to dollar bars.** Simple, trades-only, stable return distributions, scale naturally with price level. *Caveat:* adjust for corporate actions — a 2-for-1 split doubles share count and halves price, so the dollar threshold must be rescaled or prices split-adjusted. For futures, handle contract multipliers and roll rules.
- **Time bars** when the decision and label horizon are genuinely clock-time (next-5-minutes, intraday seasonality features, session-aligned execution). Expect heteroskedasticity and regime-dependent sample quality.
- **Volume bars** when activity is naturally in shares/contracts *and* price level is stable — otherwise dollar bars.
- **Information-driven bars when order-flow dynamics are the object of measurement** (toxicity, informed trading, execution risk) — **not** when the goal is merely "more normal returns." Higher implementation and tuning overhead.
- **With only trades and no quotes: prefer dollar or volume bars; avoid imbalance/run bars** unless tick-test noise is acceptable and sensitivity has been validated.

### Trade classification accuracy (the gating constraint on information bars)

Validated against DataBento NVDA aggressor labels as ground truth, 742,527 trades over 5 days:

| Method | Coverage | Accuracy |
|---|---|---|
| **Lee-Ready (quote + tick)** | 100% | **94.7%** (stable 94.4–95.0% across days) |
| Tick test (continuous, carries forward) | 100% | 80.0% |
| Tick test (non-zero only) | 19% | 90.0% |

Why the tick test struggles: **only ~19% of consecutive trades have a non-zero price change.** Lee-Ready exceeds the 70–90% range in the older literature — likely because tighter modern spreads make quote-based classification more precise.

**Lee-Ready mechanics:** quote/midpoint test first (above mid → buy, below → sell); tick-test fallback at/near the midpoint (uptick → buy, downtick → sell, unchanged → carry forward last non-zero direction).

> **Lee-Ready is only as good as quote alignment.** If quotes and trades aren't time-synchronized, define an as-of rule or apply a small lag — otherwise you use quotes that weren't yet visible at trade time.

Getting aggressor side directly: CME provides it via **FIX tag 5797**; DataBento MBO includes it; ITCH `P` messages **do not** (same indicator regardless of initiating side).

### Threshold spiral — a named calibration failure

The adaptive EWMA threshold in imbalance bars creates a **positive feedback loop** under persistent order-flow bias: bars grow progressively larger until the day collapses into a handful of oversized bars.

Anchor: NVDA at 47% buy fraction — the aggressive decay setting inflates expected bar size **17.5× over the trading day**; a much smaller decay holds it flat at 0.98×.

**Settings:** start with a very small decay (≈0.001) for liquid equities at tick level and verify stability · `warmup=100+` bars · monitor the `expected_imbalance` column for drift · **for production, consider fixed-threshold imbalance bars, which avoid adaptive feedback entirely.**

Other practical difficulties: circular initialization (expected bar length requires existing bars); parameter sensitivity (single days rarely suffice — use multi-day for robust thresholds); when P[buy] ≈ 0.5 expected imbalance → 0 and bars form too rapidly.

**TIB vs VIB:** TIBs count all trades equally; VIBs weight by volume. Choose TIB when trade *count* matters (informed-trading frequency), VIB when volume *flow* matters (institutional activity). TIBs are best read as a directional-pressure sampler, not a fixed bars-per-day construction.

**Run bars** count *cumulative* buy vs. sell trades within the bar and take the max — **not** the longest consecutive streak. Direction changes don't reset counts, so sustained pressure is captured even when trades interleave.

### Statistical evidence

AAPL, Jan 30 2020, tick-test classification (~78% accurate):

| Bar type | N | Jarque-Bera | Lag-1 AC |
|---|---|---|---|
| Time (1 min) | 390 | **609.0** | −0.023 |
| Volume (10K shares) | 96 | **1.9** | 0.026 |
| Dollar ($3M) | 102 | **2.2** | −0.027 |
| Tick imbalance | 139 | 22.6 | 0.057 |
| Tick run | 455 | 12.5 | −0.007 |

NVDA, Nov 4 2024, *direct* aggressor labels, 195,420 trades:

| Bar type | N | Jarque-Bera | Lag-1 AC |
|---|---|---|---|
| Time (1 min) | 390 | 132.8 | 0.014 |
| Tick (500) | 390 | 58.8 | −0.061 |
| Volume (50K) | 380 | **2.3** | −0.017 |
| Dollar ($5M) | 519 | 33.0 | 0.039 |
| Vol imbalance | 691 | 51.0 | 0.035 |

Takeaway: activity-driven bars materially beat the clock on normality; autocorrelation stays small across all types (desirable for ML). Easley, López de Prado & O'Hara (2012) "volume clock": HFT is defined by operating in **event-based time**, which produces closer-to-normal returns and exploits traders who think in clock time.

---

## 8. Jump detection — separating two processes

Intraday returns mix a **continuous diffusion** component (small order-flow innovations) and a **discrete jump** component (scheduled news, surprises, block trades). Realized variance, autocorrelation diagnostics, and label distributions all change shape once jumps are removed.

**Estimators:** realized variance RV consistently estimates total quadratic variation (continuous + squared jumps). **Bipower variation** (Barndorff-Nielsen & Shephard 2004) is jump-robust — a single large return is multiplied by its smaller neighbor and contributes negligibly. The non-negative gap RV − BV estimates jump-attributable variance.

Anchors (AlgoSeek minute bars, AMD/AMZN/FB, 2020): annualized continuous vol 45% / 30% / 34%; jump component ≈ **6–10% of annual realized variance** (6.8% AMD, 10.4% AMZN, 6.2% FB) — inflated by the March dislocation, not a steady state.

**Lee–Mykland test** standardizes each return by a *local* bipower volatility from a trailing window, which adapts to slow-moving volatility regimes. The max statistic over intraday bars converges to a **Gumbel** distribution, so **the multiple-testing burden is carried by the n-dependent Gumbel constants rather than an ad hoc Bonferroni adjustment.**

Settings used: window ≈ 1 hour at 5-min frequency (≈78 bars/day, near the authors' recommendation) → critical value 5.10, **0.37 jumps per symbol-day**. Window built strictly within session, so early bars aren't testable — the deliberate trade for removing overnight-gap contamination from the local-volatility denominator. Longer window = slower adaptation + more warm-up burn; shorter = closer intraday tracking but noisier.

**What the data show:** 24–34% of symbol-days contain ≥1 jump; median jump-day has exactly one; max 3. Q-Q plots show **jumps are the source of most tail heaviness, not diffusion heterogeneity.** 27% of flagged jumps land in the last 30 minutes (rebalancing + close auction). Open-window rejection rate is zero *by construction* (warm-up), not empirically. Jump variance is **episodic** — clustered around March 2020, earnings dates, macro releases.

### Why the naive rule fails, in both directions

Compared against the shortcut "flag any bar exceeding k × daily σ":

| Symbol | Lee–Mykland | Naive | Overlap |
|---|---|---|---|
| AMD | 70 | 55 | 2 |
| AMZN | 103 | 48 | 6 |
| FB | 109 | 49 | 6 |

**They disagree on most bars, and the disagreement is directional:** on stressed days, daily σ is dragged *up by the jumps themselves*, so genuinely large bars no longer clear the threshold → **under-detection**. On calm days σ is small and the threshold is easy to clear → **over-detection**. The bipower local estimator avoids both by ignoring its own large neighbors and tracking the intraday volatility shape.

**Jumps as features** — persist `jump_count`, `signed_jump_var`, `jump_variance`, `jump_share`. Two downstream uses: Ch. 7 label conditioning (skipping the 30 minutes after a flagged jump removes returns whose statistical properties differ sharply from the diffusive labels the model trains on) and Ch. 8 features (continuous vs. jump variance make volatility regimes estimable rather than implicit).

---

## 9. Intraday data quality and sessionization

> **Framing: most microstructure "errors" are not extreme values but inconsistencies** — out-of-sequence events, invalid book transitions, stale quotes, excluded-qualifier trades. **Prefer invariant checks and cross-field consistency over statistical filters.**

**Order first, everything else depends on it:**
- Enforce monotone timestamps per symbol *and* venue; use feed sequence numbers to break ties. **If the provider gives both, sequence is authoritative ordering and timestamp is event time.**
- Be explicit about which time a timestamp is: exchange event, SIP publication, vendor processing, or local arrival. Misaligned trade/quote times systematically bias standard microstructure measures.

**Then trades and quotes:**
- Validate positive price/size, valid symbols, expected tick size; flag impossible spreads
- **Honor qualifiers and condition codes** — feeds mark late reports, corrected prints, auctions. Default to excluding out-of-sequence, corrected, or non-last-sale-eligible records unless you're deliberately modeling them
- Distinguish **"no trades occurred" from "data is missing."** Long gaps are normal in illiquid names; in liquid symbols a long quote-update gap usually means a feed interruption

**Then derived products:**
- Reconcile bars against underlying events: bar volume = summed trade size, VWAP = size-weighted mean, OHLC = first/max/min/last by definition
- Venue-local vs. consolidated discrepancies are **investigation triggers, not automatic errors**

**Treatment policy: flag and exclude, do not interpolate.** Interpolation fabricates market activity, blurs discontinuities, and breaks consistency with the event stream. Statistical filters (MAD, rolling z-scores) are **triage to surface candidates for inspection**, not automatic cleaning. Log every winsorization/drop rule with an audit trail.

**Sessionization** — misclassifying weekends, holidays, early closes, or DST creates artificial returns (an "overnight" return inside the regular session) and invalid book states:
- [ ] Build the schedule from the current exchange calendar including early closes and special sessions
- [ ] Tag pre-/regular-/post-session using **local exchange time**
- [ ] Validate that closed dates contain no regular-session events and early closes end on schedule
- [ ] Define **session date** explicitly and apply it consistently across trades, quotes, and book states
- [ ] Handle halts and auctions deliberately — exclude from intraday modeling or model as distinct states

**Run all checks three times: after parsing, after reconstruction, after bar aggregation.**

Two concrete calibration examples: AAPL on Mar 16 2020 shows median spread 2.4 bps vs. ~1 bps baseline with 9.9% intraday range — numbers that distinguish a real liquidity event from a feed glitch. AlgoSeek's NASDAQ-100 minute panel runs 04:00–20:00 ET continuously, so **trade fields are null in 20–23% of bars (extended-hours intervals with no executions) while quote fields are never null — treating those nulls as missing data silently biases any aggregate.**

---

## 10. Latency and integrity constraints

- **SIP vs. direct feeds:** consolidation and distribution introduce delays; direct feeds arrive earlier by hundreds of microseconds to single-digit milliseconds depending on network design and proximity (Holden et al. 2023).
- **Latency arbitrage scale (Aquilina et al. 2021):** races occur roughly **once per minute per liquid symbol** (FTSE 100), modal race lasting **5–10 microseconds**, imposing an aggregate tax of **~0.5 bps** on trading.
- **Exchange time ≠ decision time.** Treating them as equal creates look-ahead. Use arrival timestamps when available; otherwise apply conservative lags based on estimated event travel time — especially for event studies and sub-second work.
- **Fragmentation:** off-exchange volume grew from ~37% (2019, SEC) to **over 50%** by the early 2020s. The burden isn't "more venues" — it's schema normalization, symbol handling, clock alignment, and deterministic replay across heterogeneous feeds.
- **Corrections/cancellations:** prefer vendor-cleaned end-of-day datasets over archived real-time captures for historical research — but confirm the provider's correction policy.

---

## 11. Transferable rules — condensed

1. Backtests that assume fills at the close mis-model price formation, not just costs. Model spread, depth, and queue explicitly.
2. Liquidity is three things (spread/depth/resiliency); check the one your strategy actually needs.
3. Intraday seasonality is a confounder before it's a feature — the same signal means different things at different times of day.
4. Choose the feed level by what your signal *requires*; L1 signals are crowded precisely because L1 is cheap.
5. Midprice for signal measurement, executable prices for PnL. Report both markouts; the gap is the tradability test.
6. Reconstruction is accounting — enforce invariants and fail fast; a venue-local book is not the market.
7. **Dollar bars are the default.** Information bars only when order-flow dynamics are the object of study.
8. Information bars are gated by trade-classification accuracy: Lee-Ready ~95% vs. tick test ~80%. Reconstruct the book to get quotes if you need imbalance bars.
9. Watch for the threshold spiral in adaptive imbalance bars; fixed thresholds in production.
10. Use jump-robust local volatility (Lee–Mykland) rather than daily-σ thresholds — the naive rule fails in both directions depending on the day.
11. Flag and exclude; never interpolate ticks and quotes.
12. Sequence numbers over timestamps for ordering, when both exist.
13. Nulls in a continuously-sessionized panel may mean "no activity," not "missing data." Check before aggregating.

---

## 12. Notebooks and data sources

**MBO (L3):** NASDAQ ITCH — `01_itch_parser` · `02_itch_lob_reconstruction` · `03_itch_lob_analysis` · `04_itch_order_lifecycle_analysis` · `05_itch_trading_activity` · `06_itch_intraday_patterns` · `07_itch_stylized_facts` · `14_itch_bar_sampling` · `15_itch_lee_ready` · `16_itch_information_bars`. DataBento MBO — `08_databento_lob_reconstruction` · `09_databento_mbo_analysis` · `17_databento_bar_sampling`
**MBP (L2):** IEX HIST (free) — `10_iex_lob_reconstruction`
**TAQ:** AlgoSeek — `11_algoseek_taq_eda` · `12_algoseek_taq_lob_reconstruction` · `13_algoseek_minute_bars_eda` (61-column microstructure schema) · `18_algoseek_jump_detection`

**Cross-refs:** Ch. 2 general data-quality framework · Ch. 6 order-flow reversal strategy (conditional signals) · Ch. 7 label conditioning on jumps, multiple testing · Ch. 8 microstructure features, trade imbalance, event-based OFI · Ch. 9 features · Ch. 18 execution cost models (Kyle's lambda)

**Key citations:** O'Hara (1995, 2015) · Kyle (1985) · Glosten & Milgrom (1985) · Madhavan (2002) · Madhavan, Richardson & Roomans (1997) · Lee & Ready (1991) · Lee & Mykland (2008) · Barndorff-Nielsen & Shephard (2004) · Easley, López de Prado & O'Hara (2012, 2021) · Cont, Kukanov & Stoikov (2014) · Hasbrouck & Saar (2013) · Hautsch & Huang (2012) · Gould et al. (2013) · Zhang, Zohren & Roberts (2019) DeepLOB · Aquilina et al. (2021) · Holden et al. (2014, 2023)
