# Ch 2 — The Financial Data Universe

**Governs:** what to lock down before any modeling, how to vet a vendor, and where to put the bytes.
**Thesis:** every dataset embeds definitions. When you download "daily prices" you adopt the vendor's definitions of close, adjustment, identifier, and revision policy. Getting them wrong produces silent misalignment, not an error.

---

## 1. Lock these four down before modeling anything

1. **Timestamp semantics** — is "close" the last trade, the auction close, or a timestamped snapshot? Which timezone?
2. **Corporate-action adjustment methodology** — point-in-time (as-known-then factors) or back-adjusted (end-of-sample factors applied retroactively)?
3. **Identifier stability** — which scheme, and how are mappings handled through ticker reuse and mergers?
4. **Revision/restatement handling**

Carry these forward **as pipeline metadata**, not documentation, so downstream code cannot silently reinterpret the data.

---

## 2. Taxonomy — three categories

| Category | Measures | Defining property |
|---|---|---|
| **Market** | Quotes, trades, derived aggregates | Aggregation hierarchy: moving up is easier to store/model but discards supply-demand micro information |
| **Fundamental** | Economic drivers of value | **Release-time, not event-time.** Arrives with lags, schedules, embargoes, revisions. Shaped by rules (accounting standards, agency definitions, protocol rules) |
| **Alternative** | Signals outside standard feeds, often fundamental proxies | High variety, high validation burden |

Fundamental definitions vary by asset class: equities → statements, corporate actions, guidance; commodities → inventories, production, shipping, weather; FX → rates, inflation, growth, policy; crypto → issuance schedules, fees, on-chain activity, liquidity structure.

**Alternative-data validation questions (per category):** How stable is coverage over time? What selection effects exist in the sample? Can you reproduce the methodology? Do usage rights permit your intended deployment?

Note on market data: in fragmented markets "the best price" depends on which venues your feed covers and how it merges them. Treat each venue feed as a **partial view**; any consolidated view is a constructed aggregate with its own timestamps, inclusion rules, and latency profile.

---

## 3. Asset-class map — observability, failure modes, engineering priority

| Asset class | Observability | Key failure modes | Engineering priority |
|---|---|---|---|
| Equities | High (consolidated) | Corporate actions, fragmentation, identifiers | Adjustment methodology |
| Futures | High (exchange) | Roll rules, continuity method | Continuous series construction |
| Options | High but sparse tails | Illiquidity noise, surface construction | Surface representation |
| Digital assets | Medium (venue-specific) | Volume integrity, 24/7 sessionization | Venue screening |
| FX | Low (OTC) | No consolidated tape, close conventions | Aggregation rule definition |
| Fixed income | Low (OTC, sparse) | Matrix pricing, indicative vs. firm | Liquidity inference |
| Swaps/OTC | Low (reported) | Curve construction, convention mismatches | Curve-based representation |
| Commodities | Medium (futures high) | Spot ambiguity, delivery specs | Contract spec in metadata |

### Per-class decisions worth extracting

**Equities.** Three axes shape what "the price" means: consolidation vs. fragmentation (EU consolidated tape launches 2026), auction intensity ("close" often means *auction close*, not last trade), and trading constraints (tick sizes, short-sale constraints, price limits, settlement conventions — these alter the meaning of intraday liquidity and TCA estimates). International data adds currency conversion + FX timestamps, withholding tax on dividend-inclusive series, and cross-listing/ADR mapping that breaks identifier joins.

**ETPs — treat as a distinct dataset type, not "equities with a wrapper."** Failure modes multiply:
- *Return definition* — price-only series understate returns and distort volatility; be explicit about total vs. price return, reinvested vs. cash distributions, taxes, currency
- *Premium/discount* — traded price deviates from NAV especially when the underlying is closed, illiquid, or stressed. **Never treat NAV returns as tradable**
- *Liquidity mismatch* — a liquid ETF can wrap illiquid underlyings; secondary-market liquidity overstates true capacity under stress
- *Look-through leakage* — public holdings data may not be PIT; using today's holdings to compute yesterday's exposures is forward-looking bias
- *Replication complexity* — futures-based commodity products, path-dependent leveraged/inverse from daily rebalancing, options-overlay vol surface dynamics

Lock down: return methodology, valuation anchor (price vs. NAV, and which drives signals vs. evaluation), exposure mapping + disclosure-lag policy, liquidity model (ETF-level cost vs. look-through capacity), replication metadata.

**Futures.** No perpetual ticker exists — you construct one. Roll rules (calendar / volume / open-interest) and continuity methods (ratio vs. difference adjustment) are **backtest-defining choices**; different strategies need different roll logic.
> Non-obvious: back-adjusted continuous series preserve futures price PnL but **omit collateral return (margin interest)** — they behave like excess-return proxies. When comparing to spot assets or total-return indices, state explicitly whether you model futures PnL, collateral return, or the sum.

**Rule: store raw contract histories *plus* one or more continuous variants** so roll decisions stay testable and reconstructable.

**Options.** The instrument space explodes across strikes/expiries/types with highly uneven liquidity. **The surface *is* the dataset, not a summary of it** — represent via IV surface, ATM vol, skew, term structure rather than raw chains. Store volume/OI for liquid contracts; aggregate or drop the illiquid tail.

**Digital assets.** CEX data resembles equities and Ch. 3 microstructure applies directly. **DEX data is categorically different:** AMMs replace order books with reserve-based pricing; there is no book to reconstruct, and "depth" becomes *slippage at a given trade size, computed from pool reserves*. Failure modes: 24/7 sessionization, unreliable reported volume on some venues, MEV (validators reordering/inserting/censoring transactions in a block), impermanent loss, on-chain latency, venue fragmentation. Screen venues for integrity *before* inclusion.

**FX.** "The price" is a convention — you choose a venue and an aggregation rule (mid, best-of, VW-mid). Concrete failure: a 4pm London close and a 5pm New York close for EUR/USD differ by several pips on volatile days; mixing close conventions across currencies compares non-comparable timestamps.

**Fixed income.** Liquidity estimation is an **inference problem, not a measurement**. Matrix pricing introduces model assumptions. Keep a hard line between observed prints and indicative quotes, and between model outputs and model inputs.

**Swaps/OTC.** Decide whether your dataset is transaction-based, quote-based, or curve/surface-based — treat that as fundamental. Many downstream "returns" are artifacts of curve-construction choices (day-count, calendars, collateral/discounting conventions, roll rules). Notional ≠ exposure.

**Commodities.** "Spot" is often not a single tradable object (reported, assessed, or location-specific). Decide whether your commodity price is a specific contract, a continuous series with explicit roll, or a curve representation. **Store contract-spec metadata in the dataset, not as documentation.**

**Scope limit on Ch. 3 tooling:** order-book reconstruction and bar sampling apply to exchange-traded instruments (equities, futures, options, CEX crypto). They do **not** apply to OTC markets (much of fixed income, many swaps) or to DEX AMMs. Those need quote aggregation, curve construction, matrix pricing, or reserve-based liquidity computation instead.

---

## 4. The four defects that manufacture alpha

> Framing to internalize: **errors in financial data are systematic, not random.** Microstructure artifacts, reporting lags, revisions, corporate actions, and vendor backfills create *patterns* that inflate or deflate apparent performance. Treat these four as default risks, not edge cases.

### 4.1 Point-in-time correctness

PIT = every value used in research reflects what was knowable at decision time, under the definitions and reporting conventions **then in force**. Violations come from revisions/restatements, corporate-action backfills, delayed or amended filings, and vendor updates that overwrite history.

Four time concepts to keep distinct:

| Term | Meaning |
|---|---|
| **Event time** | When the economic event occurred (end of Q4 2019) |
| **Knowledge time** | When it became publicly available (filing acceptance time) |
| **As-of time** | The historical moment being reconstructed (the decision time) |
| **Reference period** | What the value refers to |

**Implementation contract per record:** store the valid-time interval the value describes, the availability timestamp, a stable `source_id` (SEC accession number, agency release ID), an `entity_id` at the intended layer (issuer vs. security), and a version identifier.

**Two join constraints — both required:**
- `available_at <= decision_time` on all cross-source joins
- `effective_date <= decision_time < end_date` on identifier mappings (ticker→CIK, CUSIP→ISIN)

Violating either introduces lookahead **silently, through joins that succeed but were impossible at the time.**

**Red flag to grep for: zero-lag records on data that is known to be delayed.**

PIT verification has three dimensions — and passing one doesn't imply the others:

| Dimension | Question | Failure mode |
|---|---|---|
| Values | Does each point have both valid time and availability time? | Restated values used for historical decisions |
| Universe | Is index/universe membership tracked historically? | Survivorship from current-day selection |
| Identifiers | Are entity mappings time-valid through ticker changes and mergers? | Joining across corporate events incorrectly |

> A dataset that passes value-level PIT but fails universe-level PIT still produces biased backtests — especially for cross-sectional strategies.

### 4.2 Survivorship bias

Filtering the historical universe using future information ("still exists today"). **The sign is not fixed:** excluding bankruptcies inflates returns; excluding M&A targets deflates them (missed acquisition premiums). The missing names are exactly the situations many strategies are exposed to.

Magnitude anchor from the book's US equity panel: 3,199 stocks, 777 (24.3%) delisted before the end date. Monte Carlo with delisting-outcome calibration from Eckbo & Lithell (2025) — 26% compliance failures at −60%, 65% acquisitions at +25%, 9% other at 0% — gives **survivorship inflating perceived returns by 3.5–15.3pp (+8.0pp in the empirical scenario)** over 2014–2018. Leavers returned median +13.5% vs. survivors' +30.8%. (Book flags this calibration as overstating bias on M&A-heavy panels, since acquisition premia price in gradually before the delisting date while bankruptcy losses are sudden.)

Second form, easy to miss: **using today's S&P 500 constituents as a historical universe.** Even if they all survive, the selection criterion is outcome-dependent — current members grew large enough to be included, so backtesting on them bakes the success filter into the experiment.

Remedy: point-in-time universe construction. A 2010 backtest uses 2010 membership, with correct delisting returns and corporate actions.

### 4.3 Corporate actions

Failure mode is *mixing adjustment methodologies* or using end-of-sample factors in historical research. Magnitude anchor: AAPL through 2018 — raw prices show 5.9× cumulative return, adjusted shows 398×, a ~68× understatement. A 7:1 split makes raw prices look like an 86% crash.

Vendors differ on PIT vs. back-adjusted factors, dividends (total vs. price return), spinoffs, and rights issues. Mixing them introduces lookahead.

### 4.4 Identifier integrity

Tickers get reused when a delisted company's symbol is reassigned. CUSIPs change through mergers. **This creates fake alpha:** signal table "XYZ" from 2015 joined to price table "XYZ" from 2020 — different companies, join succeeds, signal now "predicts" the wrong company's returns.

Remedy: permanent IDs with effective date ranges (vendor permanent IDs, FIGI/ISIN/CUSIP crosswalks). Entity mapping across ticker changes, mergers, and cross-vendor conventions is typically a months-long effort — treat identifier integrity as **core risk control**, not plumbing.

---

## 5. Data quality framework — five dimensions

| Dimension | Check |
|---|---|
| **Timeliness** | Lag/latency from release/event to availability |
| **Completeness** | Coverage gaps across instruments, dates, fields |
| **Accuracy** | Values match ground truth |
| **Consistency** | Stable schemas and definitions over time |
| **Validity** | Timestamps ordered; values in plausible bounds; field-level invariants hold |

**Prioritization rule: check first for what creates lookahead (PIT, backfills, revisions) and universe leakage (survivorship).** Everything else is secondary.

Calibration for what "normal" noise looks like: the 100-ETF panel showed 473 OHLC invariant violations (~0.1% of rows), traced to independent split/dividend adjustment of the four price fields — small enough to ignore for most uses, worth flagging in a vendor comparison.

---

## 6. Vendor due diligence

Three questions: *Can you trust the numbers? Are you allowed to use them as intended? Will the vendor behave like a reliable dependency?*

| Tier | PIT support | Survivorship-aware | Best for |
|---|---|---|---|
| Free/public | Rare (macro vintages via ALFRED) | Rare | Learning, prototypes, sanity checks |
| Prosumer (API-first) | Partial | Sometimes partial | Individual research |
| Institutional | Often | Often | Production, regulated environments |

**Build vs. buy split:**
- **Build** the strategy-specific and assumption-encoding parts: ingestion, storage/versioning, validation checks, canonical identifiers, sessionization, adjustment policies, roll rules, PIT-aware features
- **Buy** the non-differentiating or prohibitively expensive: long-horizon cleaned histories, corporate-action adjustment at scale, survivorship-aware universes, identifier crosswalks

**Diligence dimensions:**
- *Quality* — PIT snapshots/as-of queries and revision handling; delistings with correct final prices; documented and stable adjustment methodology; true start date, coverage, cadence, field definitions; identifier scheme and mapping through entity changes
- *Legal* — MNPI provenance controls; privacy/consent (GDPR, CCPA) for consumer data; usage rights spanning backtest / live trading / redistribution / **model training**; auditability of methodology
- *Technical/commercial* — status page, uptime, SLA; versioned and communicated schema/methodology changes; rate limits, bulk export, backfill compatible with your pipelines; export portability and exit terms

**Minimum viable validation pass (run before committing):**
- [ ] No zero-lag records on delayed data
- [ ] Historical universe not filtered by future information
- [ ] Adjustment methodology documented
- [ ] Joins on permanent IDs + effective dates
- [ ] Timezone explicit, session assignment clear
- [ ] Stale-quote and anomaly detection in place
- [ ] Reproducible as-of queries possible

---

## 7. Internal governance — five areas

Good vendors don't replace this. Governance makes problems *discoverable and reversible*.

1. **Lineage** — where each dataset came from and how it was transformed
2. **Versioning** — version, don't overwrite. When you fix an error, preserve the ability to reproduce prior results
3. **Logging** — log cleaning decisions
4. **Validation automation** — Great Expectations or Pandera; **fail loudly rather than silently dropping records**
5. **Parallel runs** — when switching vendors or methodologies, run both long enough to quantify differences; preserve rollback

---

## 8. Storage — decision matrix

**Default: partitioned Parquet + Polars or DuckDB. Add server databases only when concurrency and governance justify the operational overhead.**

| Objective | Strong default | Also consider |
|---|---|---|
| Research velocity | Parquet + Polars | Parquet + DuckDB |
| SQL analytics on files | DuckDB + Parquet | Polars lazy scans |
| Production reliability | PostgreSQL | TimescaleDB |
| Extreme time-series throughput | kdb+/KDB X | ClickHouse |
| High-throughput ingestion | QuestDB | ClickHouse |
| ASOF joins in memory | Polars | pandas |
| ASOF joins with SQL | DuckDB | QuestDB |
| Lowest operational burden | Parquet + DuckDB | Managed Postgres |

**File formats** (1M-row OHLCV, L scale): Parquet 40 MB / 0.07s write / 0.02s full scan; CSV 136 MB / 0.13s / 0.05s; HDF5 71 MB / 0.13s / 0.40s. Parquet gives ~3.4× compression vs. CSV plus selective columnar reads and universal tool support. CSV for export and interoperability only. HDF5 works for specific append-and-chunked patterns but read performance lags columnar.

**Arrow IPC / Feather:** fast interchange with memory-mapped reads, but lacks predicate pushdown, partition-aware layouts, and multi-file governance. Short-lived interchange only; Parquet for persistent queryable storage.

**Lakehouse (Delta / Iceberg / Hudi):** Parquet + a transaction log giving ACID, schema evolution, multi-writer governance. Adopt when you need update-heavy workflows, guaranteed schema evolution, or concurrent multi-team writes — not before.

**Embedded:** DuckDB queries Parquet directly and supports ASOF joins in SQL — strong default for research wanting SQL over a Parquet lake. SQLite for metadata/config, not analytical scans. **ArcticDB** is DataFrame-oriented with versioning and time-travel, but licensed BSL 1.1 with time-based conversion to Apache 2.0 per release — verify licensing before adopting.

**Server:** kdb+/KDB X (free editions carry material, often non-commercial limits — verify current terms); ClickHouse (general OLAP, high-throughput columnar); QuestDB (ingestion-optimized, ASOF-style queries, tiered storage with Parquet for cold data); PostgreSQL/TimescaleDB (hypertables for automatic time partitioning, continuous aggregates for time-bucketed rollups); **InfluxDB — Flux supports equi-joins but as-of joins are not a native primitive; treat it as a monitoring database, not a market-microstructure engine.**

### ASOF joins — the dominant cost

ASOF joins align non-synchronized events (matching each trade to the prevailing quote). **Typically the dominant cost in panel preparation mixing tick streams with slower reference series.** Both pandas and Polars require sorted inputs.

Ordering at tick scale: in-memory engines (Polars `join_asof`, pandas `merge_asof`) consistently beat embedded SQL (DuckDB `ASOF JOIN`), with Polars typically fastest.

**Benchmark hygiene — three traps:**
- In-memory engines measure join execution on already-loaded data; SQL engines may include file scans and conversion overhead
- Decide whether sorting is part of the benchmark, and apply that decision consistently. If your pipeline maintains sorted data, exclude it
- ASOF performance is sensitive to the ratio of left- to right-side rows — benchmark at *your* workload's ratio

General benchmark caveats: "read time" is ambiguous (opening a handle vs. scanning a column subset vs. full scan — Arrow IPC memory-maps, so opening ≠ loading); warm vs. cold cache changes results dramatically; **relative rankings port across hardware, absolute times do not.**

---

## 9. Transferable rules — condensed

1. Lock timestamp semantics, adjustment methodology, identifier policy, and revision handling *as pipeline metadata* before modeling.
2. Data errors are systematic, not random — design validation around the four alpha-manufacturing defects, in priority order: PIT → survivorship → corporate actions → identifiers.
3. Every cross-source join carries two time constraints (`available_at`, and `effective_date` ranges on ID mappings). Silent lookahead enters through joins that succeed.
4. PIT has three independent levels — values, universe, identifiers. Passing one proves nothing about the others.
5. Zero-lag records on delayed data are a red flag, always.
6. Represent instrument families at the right abstraction: options → surfaces, futures → raw contracts *plus* continuous variants, commodities → contract spec in the data, DEX → slippage from reserves.
7. Store contract/instrument metadata in the dataset, not the docs.
8. Buy commoditized history and crosswalks; build everything that encodes your assumptions.
9. Version data, never overwrite. Fail loudly on validation violations.
10. Default storage stack is partitioned Parquet + DuckDB/Polars. Escalate only on concurrency, governance, or latency pressure.

---

## 10. Notebooks referenced

`01_us_equities_eda` · `02_corporate_actions` (validates adjustment factors vs. AAPL splits) · `03_etfs_eda` · `04_cme_futures_eda` · `05_futures_session_aggregation` · `06_futures_continuous` (volume-based roll detection, ratio vs. difference back-adjustment, validated against vendor continuous series) · `07_sp500_options_eda` · `08_options_greeks_computation` · `09_options_continuous` (roll contamination in constant-maturity series) · `10_crypto_perps_eda` · `11_crypto_premium_analysis` · `12_fx_pairs_eda` · `13_data_quality_framework` (AnomalyManager, JSON audit trails) · `14_point_in_time_validation` (bitemporal query patterns) · `15_survivorship_bias_detection` · `16_provider_comparison` · `17_complete_pipeline` (Hive partitioning preserving identifier integrity across incremental writes) · `18_data_management` (DataManager / Universe / HiveStorage) · `19_incremental_updates` (weekend-aware gap detection, health dashboard) · `20_storage_benchmark_file` · `21_storage_benchmark_database` · `22_pandas_polars_benchmark`

**Datasets used across the book:** 3,199 US equities daily 1962–2018 (Quandl WIKI/NASDAQ) · Algoseek S&P 500 daily 2017–21 and NASDAQ 100 minute bars 2020–21 with microstructure features · 100 ETFs daily 2006–2025 (Yahoo; note 41 launched after 2006, constraining lookback) · 30 CME futures hourly 2011–25 (Databento) · S&P 500 daily options 2017–21 (Algoseek) · 19 Binance perpetuals hourly + 8h premium index 2020–25 · 20 FX pairs 4h 2011–25 (OANDA)

**Cross-refs:** Ch. 3 microstructure and adjustment mechanics · Ch. 4 fundamental/alternative data and PIT pipelines · Ch. 4 §4.4 alt-data-specific evaluation · Ch. 10 NLP on EDGAR text
