# Rules — Tooling, infrastructure & LLM workflow

`77` rules · ~1217 words · ~1642 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R10** — **Chunk within documents, never across them,** and never fit global transforms on the full corpus.

### ML4T-12 — Advanced Models for Tabular Data

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-12-R1** — **Choose the GBM library on operational criteria** — training throughput, inference latency, categorical leakage safety, ecosystem — because post-tuning accuracy differences are noise.
- **ML4T-12-R2** — **Verify GPU actually helps before assuming it does.** Precision support and dataset scale can make GPU slower than CPU.
- **ML4T-12-R3** — **Match the objective to where trading occurs.** Rank objectives pay in high-breadth cross-sections where only tails trade; they cost calibration you may need downstream.
- **ML4T-12-R4** — **Use monotonic constraints as theory-driven regularization,** and verify via constrained-vs-unconstrained SHAP dependence that they cost no IC.
- **ML4T-12-R5** — **Tune regularization before tree structure.** It has the larger out-of-sample effect in low-SNR regimes.
- **ML4T-12-R6** — **Cap trial budgets at 50–100.** More trials find validation noise, and that is the most common backtest-to-live failure.
- **ML4T-12-R7** — **Try multi-objective search even when you only care about one objective** — constraining a second can reach parameter regions single-objective search misses.
- **ML4T-12-R8** — **Prefer TreeSHAP to native importance for any decision,** and use exact interaction values to detect mechanisms that shift by regime beneath a stable-looking average.
- **ML4T-12-R9** — **Monitor SHAP drift as a leading indicator,** but confirm with outcome metrics before acting.
- **ML4T-12-R12** — **Audit retrieval-augmented models for temporal isolation** before believing any reported number.
- **ML4T-12-R13** — **Flexibility extends signal; it does not create it.** Where the linear baseline is flat, expect the interval to stay on zero.
- **ML4T-12-R15** — **Treat early stopping as a tuned outcome** — the optimal tree count varied by 10× across case studies.

### ML4T-22 — RAG for Financial Research

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-22-R1** — **Treat grounding as architecture, not prompting.** Post-hoc fact-checking neither scales nor addresses the cause.
- **ML4T-22-R2** — **Ingestion errors are irreversible downstream.** Validate parser output on representative documents before trusting it at scale.
- **ML4T-22-R3** — **Tune chunk size as a hyperparameter** on an evaluation grid, and use parent-document retrieval to get precision and context together.
- **ML4T-22-R4** — **Track publication date, fiscal period, and ingestion timestamp separately.** Filtering by period labels alone leaks information into backtests.
- **ML4T-22-R5** — **Record structural role and extraction method per chunk,** or citations can look precise while failing claim-evidence alignment.
- **ML4T-22-R6** — **Benchmark embeddings on your own corpus and query mix.** Cross-model spread can be no larger than within-model variation across query types.
- **ML4T-22-R7** — **Combine semantic and lexical retrieval.** Pure vector search fails on tickers, codes, and quoted figures.
- **ML4T-22-R8** — **Verify rerankers on financial passages before adopting them** — a generic cross-encoder degraded MRR by 36% in the chapter's test.
- **ML4T-22-R9** — **Pre-filter on metadata before ANN search,** never post-filter.
- **ML4T-22-R10** — **Prefer focused retrieval to long context,** and benchmark positional effects on the target model.
- **ML4T-22-R11** — **Never trust a citation without verifying it.** Semantic similarity between claim and cited text is a cheap check.
- **ML4T-22-R12** — **Delegate arithmetic to code.** Computation failure is invisible to faithfulness metrics because the evidence is correct.
- **ML4T-22-R13** — **Diagnose which of the five failure modes is binding before changing anything.**
- **ML4T-22-R14** — **Score abstention quality as a first-class metric,** and include unanswerable queries in the evaluation set.
- **ML4T-22-R15** — **Put security in the accuracy harness** so robustness regressions surface like accuracy regressions.
- **ML4T-22-R16** — **Choose RAG for evidence-grounded analysis over changing documents; choose fine-tuning for a repeatable skill over stable labels.**
- **ML4T-22-R17** — **Version the whole stack together** — corpus, embedder, reranker, prompts, generator — and persist a retrieval bundle per response.
- **ML4T-22-R18** — **Use an agent only when the question genuinely requires multi-tool orchestration.**

### ML4T-23 — Knowledge Graphs

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-23-R1** — **Restate the question as a path pattern before building a graph.** If it doesn't decompose into relationship chains, use simpler tools.
- **ML4T-23-R2** — **Never encode entity attributes as relationships.** It complicates queries without adding relational insight.
- **ML4T-23-R3** — **Treat average node degree below 2–3 as an extraction problem, not a domain property.**
- **ML4T-23-R4** — **Define the schema before extraction,** so the model emits graph-ready objects rather than text requiring cleanup.
- **ML4T-23-R5** — **Separate mentions from identities,** key on stable identifiers, and treat corporate actions as first-class identity-updating events.
- **ML4T-23-R6** — **Store evidence with the edge.** A relationship without source context cannot be verified or corrected.
- **ML4T-23-R7** — **Make extraction idempotent** — reprocessing must update the same record, not create a parallel copy that inflates path counts.
- **ML4T-23-R8** — **Monitor schema validity, provenance coverage, duplicate-node rate, and temporal consistency** — standard NLP metrics hide these regressions.
- **ML4T-23-R9** — **Maintain a frozen gold subset** and regression-test extraction across prompt and model changes.
- **ML4T-23-R10** — **Prefer parameterized query templates with an LLM router to free-form Cypher generation** in audited deployments.
- **ML4T-23-R11** — **Make query safety architectural, not optional:** read-only credentials, allowlisted schema, parameterization, execution limits, query logging.
- **ML4T-23-R12** — **Cite two layers — the graph row and the underlying disclosure text.**
- **ML4T-23-R13** — **Use multiple centrality measures as separate features** rather than picking one.
- **ML4T-23-R14** — **Cross-graph interaction features are the distinctive payoff,** because they encode dependencies factor models assume away.
- **ML4T-23-R15** — **Trust topology metrics from stated relationships more than from estimated correlations,** and match the network filter to the analytical goal.
- **ML4T-23-R16** — **Start with hand-crafted graph features; add learned representations only on out-of-sample evidence after costs.**
- **ML4T-23-R17** — **Gate everything on disclosure time,** and split, embargo, and filter accordingly.
- **ML4T-23-R18** — **Recompute derived relationships on the same cadence as the underlying data,** and treat them as artifacts rather than disclosures.
- **ML4T-23-R19** — **Log snapshot hash and extractor version** so historical feature values can be replayed.
- **ML4T-23-R20** — **Keep the relationship vocabulary to ~8–15 types** and defer ontology alignment until integration requires it.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R1** — **Keep agents read-only unless the use case demands side effects.** Read-only systems are easier to secure and evaluate, and match every credible public prototype.
- **ML4T-24-R2** — **Use agents only for evidence-rich tasks.** With stable structured labels, the adaptive loop adds latency and non-determinism without accuracy.
- **ML4T-24-R3** — **Start with ReAct; add ToT only for branch-heavy decisions; add Reflexion only once evaluation can identify which lessons are worth keeping.**
- **ML4T-24-R4** — **Give every persisted lesson a validity horizon,** or Reflexion converts temporary heuristics into durable blind spots.
- **ML4T-24-R5** — **Cap the reasoning budget** and return bounded output with explicit uncertainty when exhausted.
- **ML4T-24-R6** — **Use typed state objects, not chat history.** Transcripts cannot be queried for the evidence behind a specific estimate.
- **ML4T-24-R7** — **Checkpoint at decision boundaries, not intervals.**
- **ML4T-24-R8** — **Replay by freezing tool outputs and varying only prompts or policies,** or you will mistake evidence drift for prompt improvements.
- **ML4T-24-R9** — **Tool quality sets the ceiling prompt quality cannot raise.** Debug tool contracts and parsing before prompt wording.
- **ML4T-24-R10** — **Write tool descriptions with explicit negative guidance** — when *not* to call.
- **ML4T-24-R11** — **Expose only phase-relevant state, tools, and sources at each step.**
- **ML4T-24-R12** — **Enforce cutoffs at the tool boundary, never in the model narrative.**
- **ML4T-24-R13** — **Prefer structured abstention to unstructured fallback** when the schema cannot be satisfied.
- **ML4T-24-R14** — **Choose frameworks on state visibility, replay, and policy enforcement,** not benchmarks.
- **ML4T-24-R15** — **Prove the single-agent baseline before adding agents,** against explicit acceptance criteria.
- **ML4T-24-R16** — **Read forecast spread as a property of the question.** Uniform outputs across agents are the bug; similar outputs on one-directional evidence are not.
- **ML4T-24-R17** — **Make aggregation and calibration explicit, disjoint, and versioned** — extremizing then Platt-scaling compounds overconfidence.
- **ML4T-24-R18** — **Monitor sharpness alongside ECE.** Improved calibration with collapsed sharpness is not improvement.
- **ML4T-24-R19** — **Treat search-retrieved post-cutoff evidence as the dominant contamination risk** on resolved panels, and let contamination analysis override demo performance.
- **ML4T-24-R20** — **Apply a retention rubric to every component** and remove those that fail it.
- **ML4T-24-R21** — **Keep methodology in libraries and a retrievable skills corpus, not in the agent prompt.** The prompt stays short and stable; the corpus grows.
- **ML4T-24-R22** — **Separate engineering and research observability views.**
- **ML4T-24-R23** — **Version prompts, corpora, and models as regulated artifacts.**
- **ML4T-24-R24** — **Cascade models by phase and measure per-phase error rates,** never assuming the saving.
- **ML4T-24-R25** — **Reuse existing governance artifacts (the IPS) as the agent's operational boundary** rather than inventing new ones.
- **ML4T-24-R26** — **Test security adversarially with specified expected allow/deny behavior and required log fields** — converting posture from narrative assurance to measurable behavior.

