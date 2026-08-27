# Ch 24 — Autonomous Agents

**Governs:** systems that gather evidence, use tools, maintain state, and produce replayable artifacts — the layer *upstream* of the clean datasets earlier chapters assume.
**Thesis:** agents are engineering systems, not chat interfaces. **Tool quality sets the ceiling that prompt quality cannot raise, and reliability comes from explicit state, bounded permissions, and replayable artifacts — not from fluent output.**

---

## 1. Scope and the read-only boundary

**Agentic pipelines add an adaptive layer** that inspects evidence, decides what is missing, calls tools to retrieve it, and updates persistent state before producing output. **They extend the pipeline upstream into filings, transcripts, event calendars, policy statements, and market-implied probabilities** — sources that vary in format, arrive on different schedules, and require relevance judgment.

> **"Action" here means *information* actions: calling a market-data API, querying a filing index, retrieving from a vector store, requesting a calculation, writing a structured artifact. Not order execution.**
>
> **This is a design choice with a reason: read-only systems are easier to secure and evaluate.** It also matches the most credible public prototypes — the AIA Forecaster and AlphaAgents both treat agent workflows as research and forecasting systems rather than autonomous execution engines. Even the ~50-agent Self-Driving Portfolio operates at the analysis-and-recommendation boundary.

**Three properties financial decisions impose that generic chatbot applications rarely face:**

- **Outputs should be probabilities with calibration diagnostics, not narratives.** Uncertainty quantification is not optional when capital is at risk
- **The system must respect what was knowable at the decision date** — any leakage invalidates the entire output
- **Every claim must map to specific evidence and tool traces**

### Where agentic workflows do not help

> **When labels are stable and fully structured, the adaptive evidence-gathering loop adds latency and non-determinism without improving accuracy. When the task is latency-critical, LLM inference overhead is prohibitive. When no external retrieval is required and decisions are fixed transformations, the reasoning loop is unnecessary machinery.**
>
> **Agents are an additional layer for evidence-rich tasks, not a default replacement for existing model stacks.**

**Autonomy levels:** L0 passive summarization → L1 decision support with probability estimates → L2 constrained actions gated by human approval → L3–L4 progressively autonomous.

> **Most financial deployments remain at L1–L2 because the economics are asymmetric: a forecasting error is expensive, but a policy-free execution error can be catastrophic.**

**Relation to Ch. 21:** RL agents learn *what to do* from environment interaction; this chapter's agents decide *what to know* before producing output. **Complementary — a research agent might feed probability estimates to an RL sizing policy.**

---

## 2. Reasoning patterns

| Framework | Mechanism | Best for |
|---|---|---|
| **ReAct** | Thought → Action → Observation loop | **Default.** Interactive research, due diligence |
| **Tree of Thoughts** | Parallel path exploration with scoring and pruning | Scenario analysis, portfolio alternatives |
| **Reflexion** | Post-run critique persisted as compact lessons | Iterative workflow refinement |

**ReAct's main benefit is traceability** — each claim links to a specific tool call and observation.

**Four predictable ReAct failure modes:** repetitive tool loops (agent can't tell it already retrieved the evidence) · **premature synthesis** from a single observation · **brittle routing from vague tool schemas** with overlapping descriptions · **hidden contradictions** where early and late observations conflict and are never reconciled.

**ToT branches at decision points** — *an agent analyzing a rate decision branches into hawkish and dovish scenarios, retrieving different evidence for each.* **Without branching, the agent commits to a single narrative early and retrieves only confirming evidence.** Cost is compute multiplied by branching factor.

> **Reflexion helps only when memory policies are explicit.** Lessons need provenance metadata, **a validity horizon** (a regime-change observation from a rising-rate environment should not persist into a low-rate regime), decay and pruning rules, and a rollback mechanism.
>
> **Without these controls, Reflexion converts temporary heuristics into durable analytical blind spots.**

**Selection rule:** ReAct as baseline → ToT only for branch-heavy decisions → **Reflexion only after the evaluation pipeline is stable enough to identify which lessons are worth persisting.**

> **Keep composition shallow — one layer of each — unless evaluation shows clear gains. Deeply nested compositions increase trace complexity and make failure analysis substantially harder.**

> **Define a maximum reasoning budget per run:** cap total tool calls, limit branch count, ceiling on reconciliation rounds. **When exhausted, return a bounded output with explicit uncertainty rather than continuing indefinitely.**

---

## 3. Memory

| Layer | Scope | Contents |
|---|---|---|
| **Working** | Current reasoning step | Prompt, state fields, recent tool outputs, retrieved evidence |
| **Short-term** | Task session | Attempted actions, unresolved questions, temporary conclusions, recent failures |
| **Long-term** | Across sessions | Retrieval indices, run artifacts, scored outcomes, calibration history |

> **The engineering risk is conflating layers. Long-lived facts kept only in context windows break reproducibility — the same question in a different conversation yields a different answer because evidence scrolled out. Transient reasoning written to long-term memory without validation accumulates stale assumptions that bias future runs.**

### Why implicit chat history fails

> **A conversation transcript mixes instructions, evidence, reasoning, and tool outputs into an undifferentiated stream. Extracting the evidence that supported a particular probability estimate requires parsing free text — fragile and unreproducible.**

**Minimal state schema:** run and question identifiers · **`as_of_date` and `cutoff_date` enforcing point-in-time discipline** · structured evidence records with source metadata and timestamps · unresolved sub-tasks · tool-call trace with status codes and error messages · intermediate probability estimates with confidence · decision artifact status (draft / under review / finalized).

**Checkpoint at decision boundaries, not intervals:** after initial evidence collection · after contradiction resolution · before final synthesis · before any high-impact downstream handoff.

### The replay protocol — the core debugging mechanism

> **Because LLMs are stochastic, a failing run cannot be reproduced by re-running the same prompt. The objective of replay is to isolate changes in model behavior from changes in evidence.**
>
> **Protocol: freeze the tool outputs from the target run → restore state from a checkpoint → rerun with updated prompts or policies while holding evidence constant → compare trace and evaluation deltas → accept only changes that improve defined metrics.**
>
> **Without this discipline, teams routinely mistake evidence drift for prompt improvements — concluding a reworded system prompt fixed a problem when the underlying data shifted.**

**Memory governance:** retention windows per artifact type · eviction rules retiring stale lessons **before they become persistent bias** · provenance sufficient to verify point-in-time validity · **conflict-handling policy specifying what happens when a new observation contradicts stored material.**

**Every checkpoint carries an explicit schema version with migration rules,** so historical artifacts remain comparable across refactoring boundaries.

> **Memory quality and evaluation are coupled in an easy-to-underestimate way. Calibration requires historical forecast-outcome pairs stored with enough resolution to verify that events rated 70% occurred roughly 70% of the time. Ablation requires preserved intermediate artifacts. If persistence is incomplete, evaluation shifts from systematic analysis to anecdotal review — rendering claimed accuracy unverifiable.**

**Three quality gates before synthesis:** **coverage** (all required evidence types present) · **freshness** (evidence within the allowed window) · **consistency** (ticker mismatches and post-cutoff leakage).

---

## 4. Tool integration — where quality is actually determined

> **In finance, tool design is often the dominant determinant of agent quality, outweighing prompt engineering and even model selection.**

**Four tool classes:** market data · document access · search (subject to source controls) · **deterministic calculation tools for statistics and transformations that should not depend on LLM stochasticity.**

### Contracts

A tool contract specifies purpose and scope, typed arguments with allowed ranges, **error semantics distinguishing transient from permanent failures**, and provenance fields every response must carry.

> **Weak contracts push complexity into prompt text: if the model must infer from a vague description whether a tool returns adjusted or unadjusted prices, it will sometimes guess wrong. Strong contracts move constraints into typed interfaces checked statically before dispatch.**

**High-quality descriptions have three parts: what the tool returns, when to call it, and when *not* to call it.**

> **The negative guidance matters because tool-selection failures are among the most common agent bugs:** selecting a broad tool when a scoped alternative exists · repeating calls after definitive errors · **calling with incomplete arguments that trigger silent defaults rather than explicit failures** · mixing stale and current evidence without checking timestamps.

### Context engineering

> **The anti-pattern is sending full accumulated context into every step.** Each step should expose only the state fields relevant to its task, make available only the tools appropriate for its phase, restrict evidence sources to the current point-in-time boundary, and require a specific output schema downstream steps can parse deterministically.

**This applies at every scale** — within a ReAct loop the system prompt specifies which tools are active for that phase; across a multi-agent pipeline each specialist receives only evidence relevant to their perspective, not the full dossier.

### Structured output and provenance

**Enforcement mechanisms move validation into the generation loop:** JSON mode · tool-use forcing · schema-validated generation.

> **When a model cannot satisfy the schema because evidence is insufficient or the question is ambiguous, the enforcement layer should surface a structured error or abstention object rather than silently falling back to unstructured text.**

**Response provenance schema:** source identifier · publication and retrieval timestamps · document span or record key · policy flags such as allowlist status · quality annotations.

> **These fields answer three operational questions quickly: Was this evidence available at the decision date? Which tool and source produced this value? Can the claim be reproduced from stored artifacts? When provenance is absent, errors propagate silently and are expensive to diagnose after the fact.**

**Source policy** enforces date constraints **at the tool level rather than relying on the model to self-police.**

**Graceful degradation** distinguishes transient failures (retry) · persistent tool failures (fallback path) · policy violations (deny and escalate) · **missing critical evidence (explicit abstention rather than a fabricated answer).**

---

## 5. Framework selection

> **The binding constraints are not benchmark accuracy but state visibility, replay capability, and policy enforcement.**

> **The principles — explicit state, typed contracts, replay support — outlast any specific library. If a framework enforces these properties with less boilerplate, adopt it; if it obscures them, avoid it regardless of benchmark claims.**

| Need | Style |
|---|---|
| Minimal overhead, full control | Native SDK with typed schemas |
| Quick ReAct/tool orchestration | Lightweight agent framework |
| Retrieval-centric | Retrieval-first abstractions |
| **Explicit state and durable execution** | **State-graph framework with persistence and replay** |
| Complex multi-role collaboration | Multi-agent orchestration with role models |

**Migration sequence that reduces rework:** minimal baseline with native SDK and typed schemas → explicit state objects and trace capture → checkpoints and replay hooks → **multi-agent orchestration only when evaluation shows specialist diversity or debate produces measurable improvement over the single-agent baseline.**

**Four anti-patterns:** adopting multi-agent abstractions before a single-agent baseline shows feasibility · relying on framework defaults for security controls that should be explicit · postponing observability until after deployment · **treating framework migration as a substitute for evaluation methodology.**

> **Framework changes improve ergonomics but rarely fix weak state design or poor scoring practices.**

**Team-operating implications:** explicit graph orchestration **improves code review and incident triage because state transitions are visible in the graph definition rather than buried in conversation history.** Implicit orchestration accelerates prototyping but **increases debugging costs when failures occur in opaque internal routing.**

---

## 6. Single-agent research capstone

**Design:** one tool (web search), **cutoff enforced at the tool boundary**, two-action JSON schema (search or forecast).

> **The two-action schema is minimal by design: it eliminates the tool-selection ambiguity that causes routing failures in richer tool sets.** Limiting to a single tool class simplifies the contract surface **and focuses evaluation on reasoning quality rather than tool-routing accuracy.**

**Step limit (default five)** — if exhausted without forecasting, **record a forced default with explicit uncertainty rather than manufacturing confidence.**

**Rich extraction beyond the probability:** confidence (explicit or inferred from probability extremity) · sentiment on a five-level scale · key findings and uncertainties from the rationale · evidence quality from query and source counts.

> **The trace isolates failure points.** If forecast quality is poor, it reveals whether the cause was insufficient queries, irrelevant results, JSON parsing failures, or flawed reasoning. **The most common failures are search queries that miss key evidence, outputs that fail JSON parsing, and rationales that ignore retrieved evidence in favor of prior knowledge.**

> **Debug in this order: tool contracts and search quality first, then JSON parsing and output extraction, then prompt wording. Most reliability failures originate in tool and parsing design, not language generation.**

**Acceptance criteria before escalating to multi-agent:** stable task success across repeated runs · evidence groundedness above threshold · low forced-default rate · reproducible artifacts from stored traces · reasonable token efficiency.

---

## 7. Multi-agent forecasting

**Six layers:** intake (records decision timestamp and cutoff) → parallel research → aggregation (+ optional debate) → supervisor reconciliation → calibration → **persistence and scoring, without which the system cannot learn from its own history.**

### Forecast spread is a property of the question, not a tunable

> **The empirical finding worth internalizing.** On a *one-directional* question (US recession by end-2026), three agents' search paths differed — one weighted current model readouts, others leaned on historical base rates — **yet forecasts clustered at 0.12, 0.22, 0.22, near the market price of 0.175.**
>
> On a *genuinely contested* question (Fed hike in 2026), the same setup returned **0.35, 0.58, 0.38, with assigned bull and bear roles holding a gap near 0.4 across three rounds without consensus.**
>
> **The condition to debug is the opposite of either outcome: identical search results, identical reasoning, and an identical forecast across agents would signal a broken sampling temperature or a structural bug. Similar numbers on a one-directional question are not a bug.**
>
> **Forecast spread tracks how contested a question's evidence is, not a sampling setting the operator can turn up on demand.**

> **Consequently, debate and role specialization are configuration choices to evaluate against the target question set, not fixes for a failure mode.** They incur latency on two-sided questions where surfacing disagreement moves the aggregate; **on one-directional questions they add cost without changing the answer.**

### Aggregation encodes dependence assumptions

**Neyman extremization factor** under an equicorrelated model depends on forecaster count and average pairwise correlation.

> **When agents are perfectly independent, extremization is aggressive. When highly correlated, the mean passes through unmodified — correctly reflecting that correlated agents contribute less independent information.**
>
> **The design tension this exposes: adding more agents improves forecasts only if they bring genuinely diverse evidence, not just different phrasings of the same analysis.**

**Expose aggregation choices as configuration rather than burying them in prompts** — mean, median, trimmed mean, and extremization as explicit policies.

### Supervisor and calibration

> **Supervisor override must be policy-bound — the supervisor may replace the aggregate only when it returns high confidence. That rule prevents the last model call in the pipeline from automatically dominating the rest of the evidence.**

**LLMs are "fundamentally miscalibrated for probabilistic prediction under uncertainty" and hedge toward base rates.** Platt scaling is the common post-hoc fix.

> **Aggregation and calibration interact dangerously. If aggregation already extremizes, applying Platt scaling on top can compound overconfidence unless the calibration window is disjoint from the aggregation training data.** Production systems should warn when both are enabled.

**Calibration workflow:** fit on a reserved historical window only → evaluate on a disjoint holdout → **monitor drift with an explicit refit cadence.**

**Four pitfalls:** too few resolved events · overlapping calibration and evaluation windows · recalibrating too frequently without drift evidence · **interpreting improved ECE as overall improvement when sharpness has collapsed.**

### Evaluation

**Core metrics:** Brier, log score, ECE, reliability diagnostics, sharpness.

> **Higher sharpness is desirable only when calibration remains acceptable. A sharp but miscalibrated system is dangerous.**

**Ablation baselines:** raw agent probabilities · aggregated pre-calibration · aggregated post-calibration · no-supervisor variant · fewer-agents variant · **market baseline.**

> **Two cautions on the market comparison.** For *unresolved* questions, both market price and agent forecast estimate the same future probability — **neither can be declared correct in advance without assuming the market is ground truth.** For *resolved* panels, **contamination is the dominant operational risk: search tools may retrieve articles dated after the question's natural cutoff, so apparent outperformance can reflect leakage rather than skill.**

> **The defensible workflow: evaluate on time-disjoint windows with explicit cutoff enforcement, report ranges across calibration variants and seeds rather than point estimates, and treat single-panel "wins" as illustrative of methodology rather than definitive evidence.**

**Retention rubric per component:** Does it improve resolved-outcome metrics? Is the improvement stable across event subsets? Is cost and latency acceptable? Does it increase policy risk? **Components that fail should be demoted or removed.**

> **Aggregate metrics hide systematic errors.** Examine error concentration by event type, overconfidence rates in high-probability bins, **the contribution of supervisor overrides to large misses**, and agent-disagreement patterns preceding failures.

---

## 8. The research operator — a different agent shape

**Why the forecasting shape doesn't transfer:** every case study has its own follow-up, and it is rarely a parameter sweep — **it is a small amount of code wiring the chapter's libraries against a real run-log registry. Pre-enumerating the catalog of moves a researcher might make would either grow without limit or constrain the agent from making the moves that matter.**

**The operator:** ~880 lines, **10 general-purpose tools** (read/write files, run bash, query a SQLite registry, read Parquet, list and read skills). **The model accesses them via `run_bash` when it decides the moment has come.**

### Skills as the task-specific knowledge layer

**56 concept-first Markdown files** in nine categories, each with a problem statement, a **WRONG/CORRECT example pair**, and a **Production Implementation block naming the exact library function to call.**

> **The operator's prompt embeds none of this.** Two tools — `list_skills` and `read_skill` — let the agent fetch methodology on demand when a method-choice decision arises.
>
> **This is the inversion that makes the pattern work: the agent's prompt stays short and stable while the corpus it can consult grows with the methodology.**

> **The forecasting workflows don't need this layer because their action space is bounded by the search and forecast schemas. The workflow agent is exactly where skills earn their cost.**

### Two runs, two honest outcomes

| | **ETFs — clean negative** | **US Firms — quantified concern** |
|---|---|---|
| Task | Ensemble GBM + tabular DL + CAE predictions, check against LSTM baseline | Filter universe to top three market-cap quartiles |
| Result | **Highest IC in the case study (0.065 vs. LSTM 0.052) but *lower* validation Sharpe (0.56 vs. 0.92)** | **Sharpe collapses 4.27 → 2.24; max drawdown deepens −15% → −52%; IC falls 0.074 → 0.048** |
| Diagnosis | **Per-fold IC instability (3 of 9 folds negative) amplified by the score-weighted top-k allocator, eroding the IC advantage at the portfolio level** | **Turnover unchanged, confirming a signal-level filter rather than a construction artifact** |
| Cost | 39 turns, ~$1.25 | 27 turns, ~$0.95 |

> **The US Firms run converts a qualitative claim into a quantified one: the strategy retains genuine alpha after the capacity filter (PBO near zero), but roughly half the reported Sharpe is a small-cap residual the static cost assumption did not absorb.**

> **A methodological caveat the agent surfaced itself: the registry carries holdout predictions only for the LSTM, so the ETF validation comparison cannot displace the holdout ranking. Promoting the ensemble would require retraining or generating holdout predictions for its three constituents.**

> **What makes the pattern portable: extending it to another case study is one registry entry and one parameter. The same loop, tool surface, and skills repo handle both runs without code changes — because the methodology is not in the operator. It is in the libraries the bash subprocess imports and the skills the model reads when a method choice arises.**

**Model-side failure modes to watch:** a confabulated improvement · a `done()` declared before the experiment finished · **an overaggressive interpretation of an inconclusive result.**

> **Structural protections — sandboxed writes, a read-only registry copy, bounded turn count, fixed model — are necessary but not sufficient.**

---

## 9. Production controls

### Reliability is process control, not single-run confidence

**Bounded retries classified by failure type** · fallback strategies producing explicit low-confidence outputs **instead of fabricating answers** · checkpoint recovery · deterministic validators catching schema violations before they propagate.

> **The target is stable workflow behavior under variation, not exact token-level reproducibility.**

**Trace requirements:** run identifiers and timestamps · input prompt and policy context · **every tool call with arguments and outputs** · state transitions and gate outcomes · model outputs and structured artifacts · latency and token telemetry · final status with error classification.

**Two separate observability views:** an **engineering view** (tool failures, latency spikes, state-transition anomalies) and a **research view** (calibration drift, baseline deltas, ablation sensitivity).

> **Separating them prevents conflating operational incidents with model-quality issues.**

> **Prompts, retrieval corpora, and model versions must be treated as regulated artifacts — an LLM-assisted output that cannot be reproduced months later creates compliance risk regardless of its accuracy.**

### Contamination-resistant evaluation

> **LLMs can appear to forecast economic variables pre-cutoff by memorizing realized outcomes from training data, rendering pre-cutoff evaluation fundamentally non-identifiable.**

**Controls:** strict temporal splits with a gap · **time-shift tests assessing whether performance degrades as the evaluation window moves further from training data** · event windows avoiding post-event coverage leakage · baseline comparisons on the same event set.

> **When contamination analysis and demo performance disagree, the contamination analysis takes precedence.**

**Statistical testing** uses repeated trials with distribution-aware thresholds: success rate across runs, policy-violation rate, **variance of forecast outputs under controlled inputs**, calibration stability over rolling windows.

### Metric stack — three dimensions

| Dimension | Metrics |
|---|---|
| **Research agent quality** | Task success rate, **citation faithfulness**, tool-call validity, abstention quality when gates fail, latency and cost per successful run |
| **Forecasting quality** | Brier, log score, ECE, reliability, sharpness |
| **Operational health** | Incident rate, policy-violation rate, **replay pass/fail rate**, drift alerts |

> **Benchmark calibration:** across 42 financial datasets and 24 tasks, **extraction and classification are relatively reliable while forecasting and numeric reasoning remain weak.** Useful for setting expectations by task type.

> **But static benchmarks measure isolated LLM capability, not agent behavior. Evaluating agents is fundamentally harder because outputs depend on dynamic tool interactions, state transitions, and multi-step chains that vary across runs.** Resolution-based scoring against real outcomes is the more rigorous protocol.

### Cost and deployment fit

> **Current LLM latency makes agent workflows unsuitable for microsecond-sensitive execution. The near-term fit is research support, event forecasting, and lower-frequency decision preparation.**

**Model cascading** is the most effective lever: **evidence extraction, formatting, and tool-argument construction suit smaller faster models, while probability synthesis, contradiction resolution, and supervisor reconciliation benefit from frontier capability.** Monitor per-phase error rates to detect when a cheaper tier degrades quality.

**Other controls:** caching with **cutoff-aware keys** · context compression · early-exit on sufficient confidence · per-forecast budgets.

> **Cost optimization that degrades calibration or increases policy violations is not a valid trade.**

**Release protocol:** replay and ablation checks on a fixed validation panel → compare score, calibration, and policy metrics against the prior release → **explicit sign-off for any regression** → canary or shadow deployment.

> **A governance shortcut worth knowing: the Investment Policy Statement — already a legal and regulatory requirement for institutional investors — can serve as the operational boundary for an entire multi-agent pipeline, analogous to the operational design domain in autonomous driving. Repurposing an existing artifact reduces adoption friction and aligns agent constraints with the same document that constrains human PMs.**

### Collective effects

> **LLM agents built on similar foundation models exhibit correlated behavior in market simulations, producing bubbles and liquidity crises that would not emerge from heterogeneous agents.** This motivates clear action boundaries, explicit approvals for high-impact decisions, and **monitoring for correlated failure patterns across agent instances.**

---

## 10. Security

### Threat model by layer

| Layer | Attack surface |
|---|---|
| **Input** | Malicious prompts, malformed queries |
| **Retrieval** | **Prompt injection embedded in documents, poisoned indices — amplified in finance because retrieved text often contains imperative language and speculative narratives** |
| **Tool** | Excessive permissions, argument abuse, **tool shadowing** |
| **State** | Corrupted artifacts, stale memory reuse, provenance loss |
| **Output** | Unsupported claims, overconfident probabilities, policy bypass |

> **A risk cutting across all layers: latent model bias.** LLMs exhibit **systematic investment preferences — favoring certain sectors, styles, or contrarian positions — and display confirmation bias when evidence conflicts with these preferences. These are invisible to standard accuracy metrics** and require stress tests presenting the same evidence framed from opposing perspectives.
>
> **Agent diversity partly mitigates this, but only if agents use different foundation models or receive deliberately varied framing.**

**Injection defenses:** strict separation of instructions from retrieved data · content sanitization before evidence enters context · **evidence gating verifying that synthesis-phase claims link to retrieved artifacts rather than injected instructions** · citation verification that every referenced source exists in the evidence store · **allowlists reducing the set of documents that can reach the model at all.**

**Retrieval poisoning** targets the pipeline rather than the prompt — mitigated by **index governance: source controls on corpus entry, ingestion provenance checks, periodic integrity scans.**

### Least privilege and the Warden

> **If a workflow requires read-only data access, write and execution privileges should not exist in that runtime.** Read-only credentials · scoped API keys per tool domain · argument constraints · domain allowlists · network and filesystem sandboxing. **Verify through automated policy checks, not documentation.**

**The Warden pattern** interposes a policy proxy between agent output and runtime execution for any state-changing operation: validates against an allowlist, rejects blocklisted patterns, validates argument ranges, enforces resource limits, **logs every allow/deny decision to immutable storage.**

*Reference implementation: a no-write policy blocking trade-execution tools, a domain-allowlist policy rejecting queries containing misuse indicators, and rate limiting — tested across benign and adversarial calls, plus five injection payloads covering role override, tool-call injection, and data exfiltration.*

> **The sensible order: first prove the forecasting workflow under bounded permissions, then add stronger action controls only if the use case truly requires side effects.**

**Human-in-the-loop:** approval queues · threshold gates on risk, cost, or exposure · dual sign-off for exceptional overrides · **anomaly escalation flagging unusual action sequences.**

> **For a read-only forecasting workflow, the practical approval points are release management and publication — configuration changes, provider changes, and publication policies should be reviewed even when the system does not execute trades.**

**Security metrics:** prompt-injection success rate (**ideally zero but monitored continuously**) · unsupported-claim rate · policy-violation attempt rate · blocked privileged-call rate · **false-positive rejection rate for valid calls** · mean time to incident diagnosis from trace data.

> **These integrate with the same run artifacts used for forecasting evaluation — security monitoring does not require separate infrastructure.**

---

## Transferable rules

1. **Keep agents read-only unless the use case demands side effects.** Read-only systems are easier to secure and evaluate, and match every credible public prototype.
2. **Use agents only for evidence-rich tasks.** With stable structured labels, the adaptive loop adds latency and non-determinism without accuracy.
3. **Start with ReAct; add ToT only for branch-heavy decisions; add Reflexion only once evaluation can identify which lessons are worth keeping.**
4. **Give every persisted lesson a validity horizon,** or Reflexion converts temporary heuristics into durable blind spots.
5. **Cap the reasoning budget** and return bounded output with explicit uncertainty when exhausted.
6. **Use typed state objects, not chat history.** Transcripts cannot be queried for the evidence behind a specific estimate.
7. **Checkpoint at decision boundaries, not intervals.**
8. **Replay by freezing tool outputs and varying only prompts or policies,** or you will mistake evidence drift for prompt improvements.
9. **Tool quality sets the ceiling prompt quality cannot raise.** Debug tool contracts and parsing before prompt wording.
10. **Write tool descriptions with explicit negative guidance** — when *not* to call.
11. **Expose only phase-relevant state, tools, and sources at each step.**
12. **Enforce cutoffs at the tool boundary, never in the model narrative.**
13. **Prefer structured abstention to unstructured fallback** when the schema cannot be satisfied.
14. **Choose frameworks on state visibility, replay, and policy enforcement,** not benchmarks.
15. **Prove the single-agent baseline before adding agents,** against explicit acceptance criteria.
16. **Read forecast spread as a property of the question.** Uniform outputs across agents are the bug; similar outputs on one-directional evidence are not.
17. **Make aggregation and calibration explicit, disjoint, and versioned** — extremizing then Platt-scaling compounds overconfidence.
18. **Monitor sharpness alongside ECE.** Improved calibration with collapsed sharpness is not improvement.
19. **Treat search-retrieved post-cutoff evidence as the dominant contamination risk** on resolved panels, and let contamination analysis override demo performance.
20. **Apply a retention rubric to every component** and remove those that fail it.
21. **Keep methodology in libraries and a retrievable skills corpus, not in the agent prompt.** The prompt stays short and stable; the corpus grows.
22. **Separate engineering and research observability views.**
23. **Version prompts, corpora, and models as regulated artifacts.**
24. **Cascade models by phase and measure per-phase error rates,** never assuming the saving.
25. **Reuse existing governance artifacts (the IPS) as the agent's operational boundary** rather than inventing new ones.
26. **Test security adversarially with specified expected allow/deny behavior and required log fields** — converting posture from narrative assurance to measurable behavior.

---

## Notebooks

`01_react_reasoning` (provider-agnostic `LLMClient` protocol, structured JSON decisions, thought-action-observation traces) · `02_tool_contracts` (`ToolDefinition` exporting typed schemas in both Anthropic and OpenAI formats, provenance-enriched results, domain allowlist with logged denials) · `03_state_and_memory` (`AgentState` dataclass, three quality gates, checkpoint round-trip serialization) · `04_research_agent` (`ResearchAgent` on live prediction-market questions, `AgentForecastArtifact`) · `05_aggregation_math` (Neyman extremization and Platt scaling sensitivity) · `06_multi_agent_research` (three agents on the recession question) · `07_adversarial_debate` (bull-bear with consensus detection) · `08_forecasting_pipeline` (`AIAForecaster` with token-cost analysis) · `09_evaluation_and_governance` (ten-question resolved panel; Brier/log/ECE/sharpness, reliability curve, ablations, Warden, injection tests) · `10_framework_comparison` (executable native SDK plus CrewAI- and LangGraph-style pseudocode) · `11_research_operator` (both ML4T runs replayable from saved traces; `REPLAY_TRACE = False` runs live at ~$1 and ~8 minutes)

**Companion:** the `aia-forecaster` repository wraps the pipeline in configuration profiles, prediction-market connectors, persistent run/forecast storage, scheduled evaluation, and a publishing layer emitting forecast feeds and evidence ledgers.

---

## Cross-references

Ch. 20 §20.9 the per-case next steps the research operator executes · Ch. 21 policy learning under reward signals — the complementary layer · Ch. 22 RAG as an agent tool; retrieval quality as a binding constraint; structured output enforcement · Ch. 23 knowledge graphs as structured retrieval with provenance · Ch. 16–19 the simulation and risk stages that consume agent outputs · Ch. 25 execution and order routing, the stricter operational layer this chapter deliberately excludes · Ch. 26 MLOps and governance frameworks scaling these control patterns

---

## Citations

Aldridge et al. (2025), agentic AI in finance survey · Alur et al. (2025), AIA Forecaster · Ang, Azimbayev & Kim (2026), Self-Driving Portfolio and IPS-as-boundary · Choi et al. (2025), FinDER · Fabozzi & López de Prado (2025), regulated artifacts · Fang & Moore (2025) · Kong et al. (2024), LLMs in investment management · Korinek (2025) · Lee et al. (2025), latent investment bias and confirmation bias · Li et al. (2025), reasoning architectures survey · Lopez-Lira (2025), correlated agent behavior and market fragility · Lopez-Lira, Tang & Zhu (2025), memorization contamination · OWASP (2025), LLM security · Shinn et al. (2023), Reflexion · Wei et al. (2023), chain-of-thought · Xie et al. (2024), FinBen · Yao et al. (2023a), ReAct; (2023b), Tree of Thoughts · Yu et al. (2024), FinCon; (2025), FINMEM · Zhao et al. (2025), AlphaAgents

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 24.*
