# Ch 4 — Fundamental and Alternative Data

**Governs:** building PIT-correct pipelines for revision-prone sources, and deciding whether an alt-data set is worth buying.
**Thesis:** two failures dominate — **time consistency** and **entity consistency**. Everything else is secondary.

---

## 1. PIT pipeline

**Restatement leakage:** Q3 revenue reported $95M in Oct → restated $98M → restated $100M. A backtest using $100M for October decisions applied a later accounting view to an earlier decision. Luo et al. (2014) list this among the "seven sins" (with survivorship, storytelling, overfitting/snooping, turnover/costs, outliers, shorting cost).

**As-of query pattern:**
1. Select the latest reporting period eligible at time *t*
2. Within that period, select the latest version with availability timestamp ≤ *t*

**Timestamp authority by source:**

| Source | Authoritative timestamp | Note |
|---|---|---|
| SEC | `accepted_at` (filing acceptance) | Markets react first to 8-K Item 2.02 earnings release, later to 10-Q/10-K. Using 10-Q/K acceptance is **conservative** — track both if event-time precision matters |
| Macro | Official release timestamp, TZ-normalized | Use ALFRED vintages |
| Commodities | Agency release timestamp + contract roll mapping | EIA/USDA/CFTC each have their own schedule |
| Crypto | Block time + **confirmation/finality policy** + vendor ingestion | Treat as available only after N confirmations — otherwise **reorg lookahead** |

> **Trap: the SEC XBRL Frames API returns the "last filed" value matching a period. Useful for cross-sectional snapshots and prototyping, not PIT-safe.** Reconstruct from filing-level records.

**Consistency problems beyond PIT:** taxonomy evolution (`RevenueFromContractWithCustomerExcludingAssessedTax` replacing `SalesRevenueNet` mid-series); company discretion within GAAP (one firm's "Cost of Revenue" ≠ another's); amendments (10-K/A) creating coexisting versions; corporate actions (3:1 split → historical EPS ÷ 3; mergers/spinoffs create discontinuities no adjustment factor resolves).

**Leakage detection method:** run the same simple strategy twice — once on an as-known view, once on "latest available today." The second usually looks better. That gap *is* the leakage.

**Decision rule: if a vendor cannot explain how it handles revisions, amendments, and identifier history, presume not PIT-correct until proven otherwise.**

**EDGAR access:** bulk FSN datasets (parsed XBRL, all 10-K/10-Q/8-K back to 2009; tables SUB/NUM/TAG/DIM + TXT/PRE/CAL/REN) · REST APIs (no auth; identify via user-agent; company-concept endpoint returns full history for a metric) · libraries `edgartools`, `sec-edgar`, `sec-downloader`, `datamule` for bulk. **For systematic research: bulk FSN → Parquet → bitemporal DB.**

XBRL tags carry concept, period (instant for balance sheet, duration for income statement), unit, optional dimensions. Companies may extend the taxonomy with custom tags — the same economic fact appears under different tags across firms.

---

## 2. Entity resolution

**Asymmetric failure: a missed match costs coverage; a false match corrupts every downstream join.** Optimize precision first, recall via escalation.

Concrete: "ZOOM VIDEO COMMUNICATIONS" (ZM) vs "ZOOM TECHNOLOGIES INC" (formerly ZOOM, now ZTNO). IBM contracts filed as "INTERNATIONAL BUSINESS MACHINES CORPORATION" / "IBM CORP" / "IBM GLOBAL SERVICES" all map to IBM — but spun-off Kyndryl must not.

### The layer problem

**"Identifier match succeeded" ≠ "resolved correctly."** Identifiers point to different layers:

| Layer | Identifiers |
|---|---|
| Legal entity | LEI (ISO 17442, 20-char), CIK (SEC filer) |
| Security | FIGI (OpenFIGI), CUSIP (US), ISIN (global), SEDOL (UK) |
| Contract | Exchange-listed contract/expiration |

Production systems maintain **three linked master tables** — entities, securities, contracts — with time-valid mappings.

**Silent wrong-join example:** alt data arrives at issuer level ("Amazon.com Inc" web traffic), returns are measured at security level (AMZN common). Without an effective-date security master you can join to the wrong share class (Class A vs B), to an ADR instead of the ordinary, or to a ticker that belonged to a different entity pre-corporate-action.

### Three stages

1. **Deterministic** — join on standard identifiers via crosswalk. Resolves the bulk.
2. **Probabilistic** — Levenshtein (edit count: "TESLA INC" vs "TESLA, INC." = 1) · Jaro-Winkler (prefix-weighted, handles abbreviations: "INTERNATIONAL BUSINESS MACHINES" vs "INTL BUSINESS MACH") · token/Jaccard ("APPLE INC" vs "APPLE INCORPORATED"). `rapidfuzz` implements these.
3. **Manual review** — middle-confidence band. **Separate the queue by failure mode** (ambiguous fuzzy match / missing identifier / candidate tie) so reviewers apply the right procedure. Write decisions back as alias or rejection with reviewer, timestamp, rationale.

**Tiered thresholds (calibrate against a labeled sample, don't treat as constants):** ~95%+ auto-accept · 85–95% manual review · <85% escalate to richer features (address, website, description).

**Cases fuzzy matching can't handle:** subsidiaries with names unrelated to the parent brand ("Amazon Web Services" won't fuzzy-match "Amazon.com Inc") · DBAs and trade names · JVs and consortia · generic names colliding across unrelated entities. These need subsidiary lookup tables or embedding-based semantic matching (Ch. 10, Ch. 23 / FinKG).

### Temporal mapping — the hidden bias source

Static mapping causes lookahead *and* survivorship. Tickers get reused; identities evolve (FB → META on 2022-06-09). Store `identifier_type`, `identifier_value`, `effective_date`, `end_date`.

**Every cross-source join constrained by `effective_date <= decision_time < end_date`.** Otherwise you join 2015 alt data to 2024 tickers — a dataset that could never have existed.

### QA cadence

| Check | Method | Frequency |
|---|---|---|
| Confidence tiers | Segment by calibrated cutoffs | Per batch |
| Sampling audit | Manually verify 1–5% of auto-accepts | Monthly |
| Drift monitoring | Track match rate + confidence distribution | Weekly |

Metrics: match rate by tier · confidence score distribution (**watch for bimodality — indicates a threshold problem**) · false-positive estimate from the audit · week-over-week temporal drift.

Diagnostic reads: declining match rate → source changed (new naming conventions, added subsidiaries). Rising false positives → threshold drift or reference-data coverage gaps.

---

## 3. Fundamentals by asset class

**The failure mode is universal; only the timestamp authority and instrument mapping vary.**

### Macro / rates / FX
- **Release cadence:** measured over a period, published later. GDP quarterly with advance/second/third vintages; claims weekly; CPI monthly. Policy for the daily grid: treat releases as timestamped events, carry forward only after availability. **Never interpolate — it blends future values into the past.**
- **Release time:** "same day" ≠ "pre-trade." Many US releases at 8:30 ET, but schedules shift on holidays. **Ingest and store the published release timestamp; don't hard-code.**
- **Normalize to UTC**, track local release calendars — jurisdictions release and revise on different schedules.
- **Vintages:** backtesting on today's "final" series leaks. Use ALFRED (real-time validity windows, vintage-specific downloads) or the Philadelphia Fed Real-Time Data Set. Two production patterns: query specific vintage dates, or store the full revision ladder when the strategy is revision-sensitive.

Anchor: US 10y-2y inverted on **15.5% of days since 2000, 36% of days since 2020**.

### Commodities
Two-part problem: ingest scheduled releases with correct timestamps, **and map them to the contract you could actually trade.**

Release calendar: EIA Weekly Petroleum Status Report Wed 10:30 ET (holiday exceptions) · USDA WASDE 12:00 ET on scheduled dates (risk event for grains/oilseeds) · **CFTC COT — positions as of Tuesday, released Friday 15:30 ET.** Enforce that lag.

Weather (NOAA) enters as a high-frequency state variable, not a scheduled lock-up release — treat differently.

**Mapping rule:** price response concentrates in the active front-month (or most liquid curve point), not an abstract continuous series. Join fundamental events to the active contract *at their timestamp*, then carry into the continuous representation **using the same roll rules as prices** (Ch. 3 roll logic becomes an input dependency).

### Crypto on-chain
Access is easy; **interpretation is the problem.** Chains differ in finality speed, reorg vulnerability, token standards, and event representation — the same metric may need different definitions per ecosystem.

Metrics and their caveats: network activity (active addresses, tx counts — **inflated by bots, internal transfers, address reuse**) · security (hash rate for PoW, staked value for PoS — rough proxies for attack cost) · economics (supply schedules, issuance, fee dynamics) · **TVL — may reflect double-counting, leverage, or token price swings rather than net new activity; record the exact aggregator definition.**

Sources: running nodes (max control, high ops cost) · indexing/analytics (The Graph, Dune) · commercial aggregators (**treat as any vendor feed — document transformations, definitions, backfills**). Alexander & Dakos (2020): major aggregators are statistically equivalent for liquid assets, diverge for illiquid tokens.

---

## 4. Alt-data evaluation framework

**Structure the process to fail fast on hard constraints rather than debate marginal scores.**

### Signal content
- **Uniqueness** — specify the baseline feature set and test *incremental* value, not raw correlation. Improvements vanishing under reasonable controls are redundant proxies.
- **Decay** — treat half-life as a design constraint. **McLean & Pontiff (2016): published predictors lose ~58% of performance post-publication.** Use as a baseline erosion rate.
- **Two common failures:** real signal but not tradable after costs/capacity; apparent performance created by revisions or lookahead.

### Data quality
- **Stability of measurement** — versioning, revision exposure, detectability of methodology changes. Berg et al. (2022) on ESG ratings shows how methodological differences drive disagreement.
- **Coverage** — representativeness across names/regions/sectors *and across regimes*; diagnose systematic missingness (small-cap, non-US).
- **Latency** — **if "first observable time" cannot be stated precisely, PIT backtests are not defensible.** Hard stop.

### Legal — hard-fail gate, not optimizable by model performance
- Provenance, permitted uses, contractual restrictions, audit/deletion obligations, redistribution limits
- **Red flags:** MNPI by *narrowness* (small panels, constrained geographies, entity-specific channel checks) · privacy risk **through linkage even without explicit identifiers** (device/ad IDs, granular location) → GDPR/CCPA exposure

### Commercial
Total cost of ownership = integration + entity resolution + storage + monitoring + schema-change handling + incident load. Estimate one-time lift, ongoing maintenance, and a conservative value range after realistic latency/cost/capacity.

**Decision rule: only compare scores among datasets that clear the hard-fail gates.**

### Build vs buy (alt-data specific)
- **Alpha crowding** — proprietary internal pipelines stay differentiated; purchased datasets erode with adoption
- **Legal risk asymmetry** — scraping is a gray area; vendor representations don't transfer compliance ownership
- **Maintenance burden** — API breaks, coverage shifts, methodology updates; vendors absorb this

Hybrid default: buy cleaned mainstream sources, build only where internal data or relationships give unique access.

### Taxonomy (Green & Zhang 2024)
Text/attention (news, social, transcripts, search — Tetlock 2007) · business process (card transactions, POS, job postings; **LinkedIn entry/exit and Glassdoor can predict operational health, and 10-K figures are often too lagged to compete**) · sensor/geospatial (satellite, geolocation, AIS) · prediction markets (**Ng et al. 2025: meaningful price discovery, faster in higher-liquidity venues; limits are thin liquidity outside headline contracts and regulatory fragmentation**).

Marketplaces (Nasdaq Data Link, Snowflake, AWS Data Exchange) simplify procurement but **do not remove the need for PIT validation and methodology audit.**

---

## 5. Text extraction pipeline

Target sections: **MD&A (Item 7)** — narrative on financial condition, results, liquidity, cash flows (Reg S-K Item 303). **Risk Factors (Item 1A)** — Reg S-K Item 105. Lengthy and boilerplate-heavy, but **changes in structure, emphasis, or newly introduced themes are usually more informative than the level.**

**Four steps:**
1. **Document selection** — the primary filing document, not an exhibit
2. **Section extraction** — layered (structured access when available, HTML-anchored boundaries otherwise). **Item numbers appear multiple times per filing (TOC, cross-references); formatting varies by filer and era; 10-K/A and older filings break naive boundary logic.** Instrument with quality checks: missing sections, collisions, length outliers. Treat extraction quality as a measurable output.
3. **Cleaning** — remove HTML remnants (unclosed tags, `&nbsp;`, style attrs), handle embedded financial tables, and **measure boilerplate via year-over-year text overlap** before deciding to remove it (for novelty/change features) or keep it (for level-based sentiment). **Preserve paragraph boundaries** — needed for chunking and change detection.
4. **PIT storage** — primary key is the **triple `cik + accession + section`** (accession, not date, because multiple filings share dates and amendments need separate tracking). Store `filing_date` and `accepted_at` (knowledge time, to the second — use `accepted_at` for intraday PIT), `period_end` (valid time), raw *and* cleaned text, plus extraction method, pattern version, and character offsets so extraction can be audited and rerun when rules change. Persist to Parquet.

Anchor from the notebook: Apple's 2025 10-K Risk Factors = 9,792 words, 92.9% word overlap YoY, Jaccard 0.31, 28 new risk-factor terms.

---

## 6. Transferable rules

1. Every fact carries two timestamps: the period it describes and when that version became observable.
2. Conservative default for equities: use filing acceptance as availability; track the earlier 8-K separately only if event precision matters.
3. Crypto needs a **confirmation policy** in the PIT contract — block time alone permits reorg lookahead.
4. Never interpolate macro series onto a decision grid.
5. Store the *published* release timestamp; schedules shift.
6. Identifier match ≠ correct resolution. Pick the layer (entity / security / contract) explicitly.
7. Precision over recall in entity matching; the failure is asymmetric.
8. All joins constrained by both availability time and identifier effective-date range.
9. Detect leakage by running as-known vs. latest-available and comparing.
10. Legal and PIT integrity are hard gates; score comparisons happen only after.
11. For text: accession number as key, `accepted_at` for timing, store raw + cleaned + extraction metadata.

---

## 7. Notebooks

`01_academic_characteristics` · `02_sec_filing_explorer` (EdgarTools) · `03_sec_form4_insider_transactions` · `04_sec_xbrl_fundamentals` (bitemporal queries) · `05_entity_resolution` · `06_fred_macro_eda` · `07_macro_data_alignment` (publication lag, vintage vs. latest) · `08_futures_positioning` (COT, PIT timestamps, positioning z-scores) · `09_onchain_fundamentals` · `10_institutional_holdings_13f` (2024Q3 manager-stock graph, concentration, co-ownership) · `11_defi_tvl_evaluation` (**peak IC 0.12 — weak**) · `12_kalshi_prediction_markets` · `13_polymarket_prediction_markets` · `14_text_data_extraction`

**Cross-refs:** Ch. 2 PIT vocabulary and bitemporal model · Ch. 3 futures roll logic · Ch. 8 feature engineering consumes these artifacts · Ch. 10 NLP featurization (FinBERT, embeddings, news-surprise factor) · Ch. 23 knowledge graphs / FinKG

**Citations:** Luo et al. (2014) · Ekster & Kolm (2020) · Green & Zhang (2024) · McLean & Pontiff (2016) · Berg et al. (2022) · Tetlock (2007, 2014) · Croushore (2008) · Harvey et al. (2022) · Alexander & Dakos (2020) · Lehar & Parlour (2021) · Ng et al. (2025) · Chen et al. (2023) FinKG
