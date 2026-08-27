# Ch 23 — Knowledge Graphs

**Governs:** questions whose answers depend on *paths between entities* rather than properties of entities in isolation — and the governance that makes graph-derived signals auditable.
**Thesis:** graphs earn their overhead only when the task is genuinely relational. **Construction is as much a governance problem as an extraction problem: identity resolution, schema constraints, provenance, and disclosure-time discipline are what turn noisy filings into replayable graph objects.**

---

## 1. The decision framework

> **The test: restate the question as a path pattern. If it naturally decomposes into "find entities connected through relationship chains," a graph is likely justified. If it concerns properties of individual entities or requires summarizing large text collections, simpler tools are more appropriate.**

### Three conditions that justify a graph

| Condition | Why the graph wins |
|---|---|
| **Multi-hop dependency** | *"Which companies share critical suppliers with Nvidia, and which of those suppliers sit in geopolitically concentrated regions?"* — a graph executes this as a pattern match; **a relational database requires recursive self-joins that grow unwieldy beyond two hops; a vector system must infer the path from disconnected fragments, exactly where high-impact errors enter** |
| **Structural crowding** | Co-ownership Jaccard, crowding scores, and ownership concentration **measure a stock's position in the ownership network, not its standalone characteristics** |
| **Temporal relationship evolution** | **Topological change** — a new supplier link or dissolved partnership — **alters the network's information-propagation properties, and these structural events are difficult to capture in tabular features because they involve relationships, not entities** |

**The contagion motivation:** financial system stability depends on the *architecture* of interconnections — the "robust-yet-fragile" property of scale-free networks. **A single node failure propagates through hub-and-spoke structures in ways per-entity risk metrics cannot capture.**

**The co-ownership motivation:** stocks connected through common institutional ownership exhibit **excess return comovement — returns correlate not because the firms are fundamentally similar, but because the same investors trade them simultaneously.** Concentrated institutional ownership creates fire-sale risk because forced liquidation by one holder triggers correlated selling by others.

### Three conditions where graphs do not help

- **Single-entity attribute lookup.** *"What was Apple's revenue last quarter?" lives in a single record.* **A common early-project mistake is encoding attributes as relationships (Company -HAS_REVENUE-> $500B), which complicates queries without adding relational insight**
- **Narrative synthesis over broad corpora.** The bottleneck is text comprehension, not traversal. **Vector retrieval with clustering and reranking often achieves comparable quality at lower infrastructure cost**
- **Sparse graphs.** **If average node degree falls below 2–3, most topology metrics are unreliable** — centrality becomes unstable, community detection degenerates, network features add noise

> **Sparsity is usually a symptom of extraction failure, not a property of the domain. If the supply chain graph of S&P 100 companies has fewer than 200 edges, fix extraction before building graph infrastructure.**

---

## 2. Construction — governance before prompt

> **The change LLMs bring is not that they can extract triples — older systems could. It is that they can map long noisy disclosures into structured outputs with enough flexibility to replace handcrafted parsing logic.**

> **Speed alone is insufficient. A graph that cannot be replayed, audited, and corrected is a liability.**

**The ordering reversal that matters:** pre-LLM pipelines normalized text first, then coerced it into graph objects — **producing duplicate entities, drifting relation names, and sparse provenance. LLM extraction defines the schema first and constrains output to emit graph-ready objects directly, moving engineering effort from parsing cleanup to validation and monitoring.**

### Three contracts

| Contract | Requirement |
|---|---|
| **Identity** | **Mentions are not identities.** "Apple," "Apple Inc.," and "AAPL" must never persist as independent canonical nodes |
| **Schema** | Finite typed relationship vocabulary — **an allowlist with explicit source-target constraints; violating edges rejected or routed for review** |
| **Provenance** | Every node and edge answers *"where did this come from?"* and *"when did it become publicly available?"* — source document ID, filing date, section/page/span, extraction timestamp, extractor version |

> **Identity resolution in finance is harder than deduplication.** Tickers change (Facebook → Meta), mergers create new entities from old (Dow/DuPont → Corteva + DowDuPont), and the same name can refer to different entities across jurisdictions.
>
> **The strategy: stable identifiers (CIK, LEI) as primary keys, tickers as time-varying attributes with validity intervals, and corporate actions treated as first-class events that update identity attributes rather than exceptions handled ad hoc.**

### Five-stage workflow

1. **Targeted document slicing** — Items 1, 1A, and 7 for 10-K pipelines; **excludes boilerplate that rarely contains relation-level evidence**
2. **Schema-constrained generation** — JSON Schema or typed function output, **validated without fragile text parsing**
3. **Canonicalization and deduplication** — resolve aliases, collapse duplicates, **preserve mention-level evidence**
4. **Rule validation** — relation allowlists, type constraints, date sanity, provenance completeness
5. **Human review queue** for low-confidence or rule-violating objects

> **The pipeline must be idempotent: reprocessing the same filing with the same extractor version produces identical graph objects.** In practice this means merge-style loading keyed on canonical node identity and relationship type. **The property is behavioral, not syntactic — reprocessing should update the same relationship record, not create a parallel copy that inflates downstream path counts.**

**Reflection-driven correction** (FinReflectKG) has the model critique and revise its own extractions before validation — extract candidates, evaluate against schema rules, propose fixes. **Particularly effective for entity normalization (splitting "John Ternus, CEO of Apple" into separate Person and Role entities) and enforcing type constraints.**

### Four metrics beyond precision

| Metric | Detects |
|---|---|
| **Schema-valid rate** | Type constraint violations — **target > 90%** |
| **Provenance coverage** | Missing evidence metadata — **target > 95%** |
| **Duplicate-node rate** | Unresolved aliases |
| **Temporal-consistency rate** | Incoherent event/public/extraction timestamps |

> **A model can produce high lexical quality but still degrade graph usability if identity or provenance quality collapses. A prompt change that improves entity extraction but degrades temporal consistency would be invisible to standard NLP evaluation and visible in graph quality metrics.**

**Maintain a frozen gold subset of filings and verify extraction stability across prompt and model updates.**

### Supply chain schema — small by design

Five object types: Company node (canonical ID, name, ticker, sector) · Filing node (accession, form, filing date) · **HAS_SUPPLIER / HAS_CUSTOMER / COMPETES_WITH edges, each carrying evidence span, public date, and extractor version.**

> **Store evidence with the edge. A relationship without source context is difficult to verify, correct, or trust downstream.**

> **Two noise sources worth naming.** 10-K supply chain relationships are **partial, selective, and sometimes intentionally vague — companies disclose what they must or choose to highlight, not a complete supplier inventory. This makes 10-K extraction high-precision, low-recall.** Separately, LLM extraction surfaces **generic placeholders ("leaf merchants," "vendors," "third parties") as candidate suppliers, requiring a curated stop list during canonicalization.**

**Scale anchor:** 601 filings across 101 S&P 100 companies → **1,057 unique typed relationships after deduplication** (276 supplier, 472 competitor, 309 customer) across 127 subject companies. **TSMC, Foxconn, and Samsung emerge as the most connected suppliers, serving 61, 33, and 28 downstream companies** — exactly the relational concentration the representation is meant to expose.

---

## 3. Graph RAG

**The division of labor: the database executes relational joins; the LLM explains results. This keeps errors localizable during debugging.**

### Five-stage architecture

1. **Query routing** — classify as graph, document, or hybrid; **reduces unnecessary text-to-Cypher generation**
2. **Text-to-Cypher generation** from a compact schema exposing **only labels, relationships, and properties the interface is allowed to use**
3. **Query safety validation** — read-only role, allowlisted schema elements, **parameterized values never string interpolation**, timeout and row-limit guards, write/admin keyword blocking
4. **Deterministic retrieval** returning structured rows with provenance
5. **Grounded synthesis** citing specific rows

> **Not all questions suit free-form query generation. Many production teams use parameterized template libraries with an LLM router that selects and fills the appropriate template rather than generating arbitrary Cypher — reducing attack surface and simplifying validation.**

> **Two-layer citation prevents a common failure mode.** Because edges carry evidence pointers, the system can fetch the original text snippets that justified each relationship and include them alongside the graph result — **preventing "the KG says X" without showing the original evidence.**

> **The cutoff-date filter is not an implementation detail. In finance it is the mechanism that keeps historical analysis from leaking post-cutoff information.**

### Two graph-retrieval families

| Family | Strength | Fit |
|---|---|---|
| **Explicit domain KG** | Typed entities, deterministic traversal | **Regulated workflows requiring provenance and replay** |
| **Community-summary GraphRAG** | Thematic synthesis from corpus-derived abstractions | **Less direct for schema-governed relational queries where audit trails matter** |

### Evidence for structured retrieval on relational questions

> **FinReflectKG-MultiHop (S&P 100 filings, 2–3 hop analyst questions): KG-guided retrieval improved correctness by ~24% while reducing token consumption by ~85% versus page-window retrieval. Structured retrieval is not just more accurate but more economical — the model spends tokens reasoning over pre-selected facts rather than navigating noisy context.**

> **The chapter's own head-to-head on a live 13F graph is starker: across seven analyst-style questions, graph retrieval achieves perfect support recall (1.00) against an embedding baseline averaging 0.13. Vector retrieval fails entirely on holdings-lookup (0.00) and returns a fraction of co-ownership rows (0.17). Graph uses roughly a third the tokens (82 vs. 267).** Magnitude depends on corpus and question type; **the direction is consistent.**

**Evaluation harness checks three properties:** query validity (syntax and schema compliance) · provenance coverage (share of claims linked to evidence) · **temporal correctness under historical cutoff constraints.**

**Common failure modes:** invented labels or properties in generated Cypher · overly broad traversals returning noisy rows · **missing cutoff filters in historical queries** · synthesis drift where generated text exceeds returned evidence.

> **When graph and vector results conflict, temporal metadata usually resolves the discrepancy — more recent evidence takes precedence, provided timestamps are reliable.**

---

## 4. Graph-derived features

### Topology

| Feature | Financial interpretation |
|---|---|
| **PageRank** | Systemic importance weighted by the importance of dependents |
| **Betweenness** | **Bottleneck position — failure would disconnect parts of the network** |
| **Clustering coefficient** | Redundancy — high clustering suggests alternative paths exist |
| **Degree** | Immediate transmission channels |

> **Different centralities carry different information. Using multiple measures as separate features lets the downstream model learn which structural role matters for a given prediction task.**

### Supply chain risk

Supplier count · shared-supplier count · single-source count · supplier-overlap ratio · supplier-dependency score.

> **A company depending on a few shared upstream suppliers is structurally fragile even if no single disclosure states that risk. The graph makes the concentration measurable in a form joinable to other feature families.**

### Institutional crowding — four families

- **Crowding score** — holder count relative to cross-sectional median; **high crowding faces correlated selling pressure during stress**
- **Smart money concentration** — value-weighted share held by top performers, **signalling analytical judgment rather than index tracking**
- **Ownership HHI** — **a stock held by three large funds is more fragile than one held by thirty small funds at the same total institutional ownership**
- **Co-ownership Jaccard** — predicts return correlation **beyond what fundamental factors explain**

### Cross-graph interaction — the distinctive value

> **A stock with both concentrated supplier dependence and high crowding faces compound risk: operational disruption would coincide with correlated institutional selling.** Unlike traditional factor models where factors are assumed independent, **KG features directly encode structural dependencies.**

Examples: `supply_chain_crowding` (supplier overlap × institutional crowding) · concentrated dependency risk (dependency score × ownership concentration) · systemic exposure (betweenness × holder count).

**Lead-lag propagation:** events affecting upstream entities **propagate to downstream firms at different speeds depending on the industrial chain — a raw material shock reaches component manufacturers before final assemblers. Graph topology determines the *timing* of information transmission, not just whether it occurs.**

**Temporal features:** relationship churn (edge turnover rate) · centrality momentum · supplier change.

> *A company whose supplier count declines while competitor connections grow signals strategic repositioning — information not reflected in quarterly financials until later.*

**Feature matrix scale:** 127 source companies × 1,057 relationships joined with 201,145 raw 13F rows (80 matched) → **31 columns across five families: topology (5), supply (7), holdings (9), temporal (6), cross-graph (4).**

---

## 5. Statistical networks and GNN maturity

**Correlation-based networks** (minimum spanning trees, hierarchical clustering) are a 25-year tradition offering a complementary perspective.

> **What works: MSTs reliably recover sector structure and detect regime changes. What remains unstable: community detection is sensitive to estimation window and filtering method, and hierarchical structures can shift substantially across adjacent time periods.**

> **The key epistemic difference: topology metrics from correlation graphs are noisier than the same metrics from explicitly stated relationships, because the edges are estimated rather than observed. The choice of filter — MST, planar maximally filtered graph, random matrix theory — determines which relationships survive and therefore which centrality rankings emerge. Match the filter to the analytical goal rather than treating it as preprocessing.**

**Network-aware allocation** gives peripheral assets greater weight since central stocks contribute less marginal diversification.

> **The empirical result is a wash on headline metrics and instructive on structure.** On a 100-stock universe 2015–2018: equal-weight, inverse-vol, and network-diversified produce Sharpe **1.58, 1.51, 1.54** with max drawdowns −10.3%, −10.6%, −10.1% — **close enough that the summary metrics do not separate them at this universe size.**
>
> **The structural argument emerges from the contagion simulation instead: a shock propagated from the highest-centrality node affects the portfolio roughly 3.8× more severely (−87.3%) than the same shock from a peripheral node (−23.0%). Topology governs contagion reach more than shock magnitude.**

### GNN maturity by domain

| Domain | Maturity | Why |
|---|---|---|
| **Fraud detection** | **Production-ready** | High signal-to-noise (distinctive fraudulent topologies), clear labels, real-time requirements GNN inference can meet |
| Systemic risk | Emerging | Academic research, regulatory pilots |
| **Alpha generation** | **Experimental** | **Market efficiency, regime non-stationarity, reproducibility gap in academic claims** |

> **The chapter's own test:** 200-stock correlation network, graph estimated **ex-ante on returns strictly before the 21-day target window**, 480 edges at threshold 0.5, density 2.41%. Four GAT embedding dimensions concatenated with eight tabular factors into ridge regression: **hybrid IC 0.215 lands roughly 7.7% *below* the tabular-only baseline (0.233).** In-sample and scale-limited, **but the direction aligns with the literature's concern — added architectural complexity does not translate into reliable improvement in structured equity forecasting at this scale.**

**The recommended path:** hand-crafted graph features first (**easier to audit, easier to debug, more stable under governance constraints**) → network-based portfolio methods with explicit structure → **add GNN or graph embeddings only if they improve out-of-sample metrics after transaction costs and temporal leakage** → keep learned graph features supplemental, not default.

**Intermediate option:** node2vec or metapath2vec produce vectors from random walks — **faster to train than message-passing, usable alongside hand-crafted metrics.**

---

## 6. Temporal integrity — the decisive discipline

### Three timestamps

| Timestamp | Definition |
|---|---|
| **Event time** | When the underlying event occurred |
| **Disclosure time** | **When the information became publicly available — the visibility gate** |
| **Extraction time** | When the pipeline processed the source |

> **An acquisition may be agreed in March but filed in April; a supplier relationship may exist for years before appearing in a 10-K. Information that was true economically but not yet disclosed cannot enter the model.**

**8-K disclosure lags:** material agreements, acquisitions, and executive changes all **1–4 business days**; Regulation FD **same day by definition**; other events **variable**.

> *An executive departure on March 1 filed on March 5 should not be available to a model evaluated on March 3.*

**Executive turnover clustering** is visible only when event timestamps are aggregated across the graph — **individual filings reveal individual changes; the cluster is a structural observation.**

### 13F's three complications

- **Quarterly lag** — 45-day delay. **A December 31 snapshot filed February 14 enters the graph on the filing date**
- **Position masking** — institutions request confidential treatment while building positions; masked positions appear in later amendments. **Any crowding or co-ownership feature computed during the masking period is biased downward**
- **Confidential treatment gaps** — either exclude the institution during the gap or use the amendment date as effective disclosure time

**Also:** derived relationships like portfolio similarity should be **recomputed quarterly — they are computational artifacts, not disclosed relationships.**

### Leakage-safe protocol — five rules

1. **Split by disclosure time, not event time**
2. **Embargo observations near split boundaries** — prevents leakage through the event-to-disclosure gap
3. **Enforce cutoff filtering in every query path — no exceptions**
4. **Log snapshot hash and extractor version** for replay and audit
5. **Compare against both non-graph (tabular-only) and static-graph baselines**

> **The audit anchor in practice: a snapshot manifest recording the cutoff, window, upstream-extractor identity, and per-file SHA-256.** *In the reference run, ~2,400 timestamped events from 207 companies, a cutoff hiding ~200 events, mean disclosure lag near a week against a mean extraction lag of roughly three years — and verification that no post-cutoff disclosures enter the visible graph.*

**Window policy:** quarterly aligns with fundamental disclosures; shorter windows capture event-driven structure at higher noise and cost. **Once chosen, keep it stable throughout evaluation.**

---

## 7. Engineering

**Engine selection:** Neo4j/Cypher as default for teaching through medium-scale production · managed cloud graph when optimizing for operations · distributed engines for very large analytics. **PostgreSQL with recursive CTEs handles moderate workloads when the graph is narrow and queries rarely exceed 3–4 hops** — avoiding a new database, at the cost of unwieldy syntax for complex paths.

> **The selection rule: choose the engine supporting strict access boundaries, query guards, and stable schema metadata. If those requirements are met, the specific engine matters less than the governance layer built on top of it.**

**Ontology strategy:** FIBO defines **over 1,200 classes** — comprehensive but impractical as a starting point.

> **Teams attempting full FIBO adoption often stall during early iteration because the ontology's breadth obscures the analytical goal.**

**The pragmatic middle path:** align core entity classes with established identifiers (CIK, CUSIP, LEI) where natural · **keep relationship vocabulary compact — most financial KGs use ~8–15 relationship types** · codify type constraints in code rather than ontology management tools. **Add FIBO mapping incrementally when external integration requires it.**

**Schema versioning:** additive changes (new labels, relationship types, properties) are safe and should be the default · **renames or removals require migration scripts and downstream query audits** · version metadata on edges enables coexistence of old and new extraction formats during transitions.

**Minimal production architecture:** ingestion → schema-constrained extraction → canonicalization service → graph database with read/write separation → safe text-to-Cypher retrieval layer → evaluation harness for query validity, provenance coverage, and temporal correctness.

---

## Transferable rules

1. **Restate the question as a path pattern before building a graph.** If it doesn't decompose into relationship chains, use simpler tools.
2. **Never encode entity attributes as relationships.** It complicates queries without adding relational insight.
3. **Treat average node degree below 2–3 as an extraction problem, not a domain property.**
4. **Define the schema before extraction,** so the model emits graph-ready objects rather than text requiring cleanup.
5. **Separate mentions from identities,** key on stable identifiers, and treat corporate actions as first-class identity-updating events.
6. **Store evidence with the edge.** A relationship without source context cannot be verified or corrected.
7. **Make extraction idempotent** — reprocessing must update the same record, not create a parallel copy that inflates path counts.
8. **Monitor schema validity, provenance coverage, duplicate-node rate, and temporal consistency** — standard NLP metrics hide these regressions.
9. **Maintain a frozen gold subset** and regression-test extraction across prompt and model changes.
10. **Prefer parameterized query templates with an LLM router to free-form Cypher generation** in audited deployments.
11. **Make query safety architectural, not optional:** read-only credentials, allowlisted schema, parameterization, execution limits, query logging.
12. **Cite two layers — the graph row and the underlying disclosure text.**
13. **Use multiple centrality measures as separate features** rather than picking one.
14. **Cross-graph interaction features are the distinctive payoff,** because they encode dependencies factor models assume away.
15. **Trust topology metrics from stated relationships more than from estimated correlations,** and match the network filter to the analytical goal.
16. **Start with hand-crafted graph features; add learned representations only on out-of-sample evidence after costs.**
17. **Gate everything on disclosure time,** and split, embargo, and filter accordingly.
18. **Recompute derived relationships on the same cadence as the underlying data,** and treat them as artifacts rather than disclosures.
19. **Log snapshot hash and extractor version** so historical feature values can be replayed.
20. **Keep the relationship vocabulary to ~8–15 types** and defer ontology alignment until integration requires it.

---

## Notebooks

`01_sp100_sec_download.py` (EDGAR acquisition) · `02_supply_chain_kg_construction.py` (extraction, schema, idempotent loading) · `03_graph_rag_qa.py` (text-to-Cypher over the 13F graph) · `04_rag_comparison_benchmark.py` (graph vs. embedding on 10,624 holdings rows, 10 institutions, 250 stocks) · `05_institutional_holdings_kg.py` · `06_gnn_feature_engineering.py` (GAT vs. tabular ridge) · `07_dynamic_kg_temporal.py` (snapshot construction, leakage-safe queries, snapshot manifest) · `08_8k_event_extraction.py` (Qwen2.5-7B with FinReflectKG reflection) · `09_knowledge_graph_features.py` (31-column cross-graph feature matrix) · `10_network_portfolio_construction.py` (MST, centrality weighting, contagion simulation)

---

## Cross-references

Ch. 4 SEC filings, EDGAR, PIT conventions · Ch. 10 entity extraction and identifier crosswalks · Ch. 12 gradient boosting consuming these features · Ch. 14 factor models, where cross-graph features encode dependencies factor models assume independent · Ch. 17 the Herfindahl index and portfolio concentration · Ch. 22 §22.8 the 13F bipartite graph handed forward from RAG; hybrid routing between graph and vector retrieval · Ch. 24 agent workflows built on structured retrieval, memory, and evidence tracking · Ch. 26 governance and schema-versioning discipline

---

## Citations

Antón & Polk (2014), connected stocks and excess comovement · Arun et al. (2025a), FinReflectKG; (2025b), FinReflectKG-MultiHop · Cheng et al. (2020), KG event embedding and supply-chain propagation · Choi et al. (2025), FinDER · Edge et al. (2024), GraphRAG · Elhammadi et al. (2020), pre-LLM financial KG extraction · Greenwood & Thesmar (2011), stock price fragility · Haldane & May (2011), systemic risk in financial networks · Hamilton, Ying & Leskovec (2017), GraphSAGE · Kertkeidkachorn et al. (2023), text-derived network features · Kipf & Welling (2017), GCN · Konstantinov, Aldridge & Kazemi (2023), network-based allocation · Konstantinov & Fabozzi (2025), causal spillover across asset networks · Lewis et al. (2020), RAG · Li & Passino (2024), FinDKG · Mantegna (1999), minimum spanning trees · Marti et al. (2021), correlation networks survey · Miao et al. (2019), temporal relation construction · Peng et al. (2024), Graph RAG survey · Velickovic et al. (2018), GAT · Weber et al. (2019), Elliptic Bitcoin fraud detection · Zehra et al. (2021), financial KG query interfaces

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 23.*
