# Ch 22 — RAG for Financial Research

**Governs:** grounding LLM output in a controlled, inspectable evidence base — the engineering stack from ingestion through citation verification.
**Thesis:** hallucination is an intrinsic property of next-token prediction, not a bug to be patched, so the response must be architectural. **The model's task is not to know the answer but to articulate what the provided evidence supports.**

---

## 1. Why grounding must be architectural

**Classification has a ceiling.** A fine-tuned FinBERT can tell you a 10-K sentence is negative but cannot explain why, synthesize across sections, answer multi-hop questions, or generate narrative. **The practitioner's interaction is limited to a fixed taxonomy.**

> **Hallucination is not a defect to patch — it is what a probabilistic next-token model does.** In finance a single fabricated revenue figure, invented regulatory requirement, or misattributed quote produces flawed decisions, compliance breaches, or legal liability.

> **Post-hoc fact-checking does not scale and misses the root cause: the generation process is opaque, so correcting one output leaves the underlying logic intact.**

**RAG's move:** replace reliance on *parametric* knowledge (encoded in weights) with *non-parametric* knowledge — an external curated base the system controls and can verify. Three stages: **index** (offline: parse → chunk → embed → store with metadata) · **retrieve** (online: embed query, fetch top-k by similarity) · **generate** (synthesize *only* over retrieved context).

> **The critical caveat stated up front: every claim can *in principle* be linked to a source. Achieving reliable provenance in practice requires the citation-verification techniques of §6 — "designed to be verifiable" and "automatically verified" are different things, and the gap is where production engineering effort concentrates.**

**Orchestration:** LlamaIndex for RAG-centric workflows, LangChain when RAG is part of a broader agent architecture, Haystack as an alternative.

---

## 2. Ingestion — where quality is capped

> **The performance of any RAG system is capped by the quality of its knowledge base. And in financial RAG, ingestion errors are effectively irreversible downstream: once tables, headings, or temporal markers are lost, later retrieval and generation cannot reconstruct them.**

**Fixed-size chunking is semantically destructive:** tables fragment with headers separated from values · section headers divorced from the paragraphs they introduce · risk-factor bullets split across chunks.

> **The result is "context confusion" — the model conflates fiscal years, misattributes statements to wrong sections, or fails to synthesize because necessary context is scattered. Naive chunking violates the premise of RAG.**

### Chunk size is a hyperparameter, not a default

| Size | Gains | Loses |
|---|---|---|
| **200–300 tokens** | Retrieval precision — pinpoints the exact passage | **Context.** *"Revenue grew 15%" is meaningless without segment, period, and whether it was organic* |
| **1,000–2,000 tokens** | Self-contained context, less cross-chunk synthesis | **Dilutes relevance** — the embedding averages relevant and irrelevant content; consumes context budget |

**Starting point: 400–600 tokens with 50–100 overlap for financial documents.** Evaluate retrieval recall across a grid (256, 512, 768, 1024) on an evaluation set before committing.

> **Parent Document Retrieval ("small-to-big") resolves the trade-off: retrieve using small precise chunks, pass the larger parent section to the LLM.** Each paragraph gets its own embedding for precision; on a match, the full subsection is returned. Cost is maintaining a chunk-to-parent mapping.

### Structure-aware parsing

Tools that understand semantic layout — preserving section boundaries, paragraph groupings, table layouts, list hierarchies — rather than treating a PDF as a character stream. **LlamaParse** (vision models + LLMs reconstructing logical structure from visual rendering), **Docling** (open-source hybrid parser), **Marker** (high-fidelity PDF→Markdown).

> **Calibration for what structure-awareness buys:** on ten 10-K filings, **table preservation roughly doubles (0.45 → 0.85) and layout fidelity nearly doubles (0.40 → 0.88), at ~70% higher parse latency.**

> **They are not infallible.** Scanned PDFs need OCR (introducing transcription errors) · nested tables, multi-column sections, and footnotes spanning page breaks confuse even vision parsers · **tables rendered as images are particularly problematic — the parser must detect via OCR and reconstruct structure, a pipeline where errors compound. Validate on representative documents before trusting at scale.**

**Multimodal heuristic: always process tables** (high density, structured output); **process figures selectively** when they contain quantitative data not duplicated in text — each image costs a vision-model call during ingestion.

> **Vision-first retrieval (ColPali) indexes pages as images, sidestepping parsing errors — but sacrifices the structured metadata (section hierarchy, statement type, fiscal periods) that financial RAG depends on for filtered retrieval and verifiable citations.** Text extraction remains the production default.

### Metadata — the non-optional part

**Minimum:** source document, page number, section header. **For finance, temporal metadata is critical:** fiscal year, fiscal quarter, filing date, period end date.

> **Without explicit temporal tagging the system cannot distinguish current from stale information — a particularly dangerous failure mode in finance where outdated data can be worse than no data.**

> **Three temporal fields are not interchangeable: filing publication date, fiscal period referenced, and ingestion timestamp. A 2024 fiscal-period disclosure may only become public in 2025. Historical queries and backtests must filter by publication availability, not period labels alone, to prevent information leakage.**

**Also record structural role** (prose, table cell, footnote, figure caption) and extraction method. **Without modality-aware provenance, citation formatting may appear precise yet still fail claim-evidence alignment.**

*Audit finding worth noting: filing date and ingestion timestamp populate at 100% from the EDGAR listing object, while fiscal_year_end is absent and must be enriched from the document body downstream.*

---

## 3. Domain embeddings

**The gap runs deeper than vocabulary.** "Alpha" means something different in portfolios than in general language; ticker symbols have weak representations. **But the real issue is causal chains: "the Fed raised rates by 75 basis points" is semantically connected to "mortgage affordability pressure" and "duration losses in bond portfolios" — only if the model learned these relationships from financial data.**

**FinMTEB** shows generalist models lag domain-adapted alternatives on retrieval involving financial jargon, cross-document reasoning, or temporal references, **particularly for quantitative concepts and regulatory specifics.**

> **But the ranking is not stable across tasks** — retrieval over filings, news classification, semantic similarity, reranking, and summarization can favor different models. **Treat any published ranking as a shortlist. "Best on public benchmark" is a hypothesis, not a deployment conclusion.**

**Shortlist (mid-2026):** commercial — Voyage (voyage-finance-2, Voyage 4 family), Gemini Embedding, Cohere Embed 4, OpenAI text-embedding-3-large. Open/self-hosted — Fin-E5 (the FinMTEB reference), Qwen3-Embedding and rerankers, BGE-M3, BGE-en-ICL, E5/Mistral derivatives.

**Dimensionality matters operationally.** **Matryoshka embeddings** train the objective to pack useful information into leading dimensions, so truncating to the first 256/512/1024 still yields a usable vector.

> **Naive truncation of a conventionally trained embedding does not behave this way — the property has to be trained in.** Binary quantization gives 32× memory reduction; the accuracy trade-off **depends on corpus and query distribution and must be validated empirically.**

**Evaluation protocol:** 50–100 representative production queries → ground-truth top-10 relevance labels → compare on Recall@k, MRR, latency → **rerun after shifts in corpus composition or query distribution.**

> **The empirical result that justifies the protocol:** on a 191-passage 10-K corpus, bge-large-en-v1.5 leads all-MiniLM-L6-v2 by **14.0% on MRR (0.675 vs. 0.592)**. But the per-query-type breakdown shows the asymmetry — **bge leads on technical (0.90 vs. 0.73) and risk (0.61 vs. 0.48) queries, while MiniLM edges ahead on general business (0.56 vs. 0.51).**
>
> **The 14% aggregate spread between models is comparable to the variance across query types within a single model.**

---

## 4. Hybrid retrieval

**Pure semantic search has a blind spot even with domain embeddings: exact matches.** A query for "Form 4 filings for TSLA" may retrieve general insider-trading passages while missing documents containing the ticker. **In finance, where analysts routinely search for specific companies, dates, and terms, this failure mode is acute.**

**Reciprocal Rank Fusion** scores each document inversely to its rank in each list, summed across methods (smoothing constant typically 60).

> **RRF's characteristic bias, worked through: a document ranking 1st on BM25 but 15th semantically loses to one ranking 10th and 2nd. RRF favors documents well-ranked by *multiple* signals over documents that dominate one and fade in another.**

> **Measured lift: Hybrid RRF reaches MRR 0.443 vs. BM25's 0.349 — a 27% advantage holding on precision and recall too. And a warning in the same experiment: a generic web-trained cross-encoder rerank stage *degrades* MRR by 36% relative to hybrid alone. Off-the-shelf rerankers can be miscalibrated on financial passages.**

**Learned fusion typically offers only marginal improvement while adding complexity.**

### The retrieval architecture spectrum

| Architecture | Mechanism | Trade-off |
|---|---|---|
| **Bi-encoder** | Query and document embedded independently; similarity is a dot product over precomputed vectors | Fast; **loses fine-grained token-level alignment** |
| **Late interaction** (ColBERT) | Per-token embeddings; MaxSim at query time | Token-level matching at a fraction of cross-encoder cost; **index size is substantially larger** |
| **Cross-encoder** | Query-document pair as single input | Most accurate; **pairwise computation cost** |

**Bi-encoder retrieval + cross-encoder reranking is the pragmatic default; evaluate late interaction when single-vector embeddings consistently miss relevant passages despite tuning.**

### Query enhancement

- **Expansion** — domain dictionaries mapping "buyback" → "share repurchase," "capital return"
- **HyDE** — embed an LLM-generated hypothetical *answer* rather than the query. **Adds latency and a specific risk: if the hypothetical answer is wrong, retrieval is biased toward incorrect passages.** Use selectively for complex conversational queries
- **Decomposition** — split multi-hop queries. *"Compare Apple's and Microsoft's R&D spending" becomes two retrievals, because passages simultaneously discussing both may not exist even when the information does*

### Vector DB selection and filtering

**Three durable questions:** does it support metadata filtering *before* ANN search · can it participate cleanly in a hybrid stack · does it fit the existing operational footprint?

> **Pre-filtering vs. post-filtering is not an implementation detail. Pre-filtering preserves recall by searching only the relevant subset; post-filtering searches the full index then discards, which severely reduces recall when the relevant subset is small relative to the corpus.**

> **The concrete risk: an analyst asking "What guidance did management provide for 2024?" without a fiscal-year constraint might retrieve 2022 forward-looking statements that happen to mention 2024 — plausible, well-cited, and dangerously stale.**

---

## 5. Reranking, prompting, and numeric reliability

**Cross-encoder rerank:** retrieve top 50 → score each against the query → pass top 5. **Latency ~100–200ms — acceptable for analytical applications, potentially prohibitive for real-time.**

### Long context is not a substitute for retrieval

> **Three drawbacks:** models show **strong primacy and recency effects rather than uniform use of the full window** · inference cost scales with input tokens · time-to-first-token increases substantially.

> **A 5–10K-token context of precisely relevant chunks typically outperforms a 100K+-token context of loosely relevant material.** The "lost in the middle" effect is model- and version-dependent — benchmark on the target model rather than assuming a specific failure pattern.

### Constraint-based prompting — five elements

Role assignment · **context constraint** ("Answer based ONLY on the provided context") · **uncertainty handling** ("If the context lacks sufficient information, state clearly that it is not available") · citation instruction with explicit format · structured output.

> **Citations are not automatically faithful. LLMs can cite passages that do not support the claim, blend information across chunks, or generate plausible page numbers that do not exist.**
>
> **A lightweight verification step that catches the most common failure without a second LLM call: extract each cited passage by its page/section reference, compute semantic similarity between claim and cited text, and flag pairs below a threshold for human review.**

### Numeric reliability

> **Computation failure is a distinct failure mode: the source passages are correct, but the derived answer is wrong.**

**The reliable pattern — retrieve, extract, compute, narrate:** retrieve evidence including table slices → **extract numbers into a structured schema (cells, units, period, segment)** → **compute via code or tooling, not the LLM** → generate narrative with citations and a reproducible calculation trace.

> **This delegates arithmetic to deterministic tools and constrains the LLM to what it does well: synthesis and explanation.**

**Programmatic validation adds a second layer beyond prompt constraints:** structured output parsing (JSON mode, function calling) · claim-level verification against retrieved context · guardrail frameworks (NeMo Guardrails, Guardrails AI) enforcing topic adherence and format compliance **through code rather than prompt instructions alone.**

> **The prompt is a contract. A vague prompt invites hallucination; a precise, constraining prompt enforces grounding.**

---

## 6. Five failure modes, five different fixes

| Failure | Symptom | Fix |
|---|---|---|
| **Retrieval** (low context recall) | Information exists in the base but wasn't retrieved | Improve embeddings, tune hybrid weighting, refine chunking |
| **Context** (low precision) | Relevant documents found but diluted by noise | Tune reranker thresholds, improve metadata filtering, adjust granularity |
| **Synthesis** (low faithfulness) | Context accurate, answer wrong | Refine prompts, stronger LLM, answer verification |
| **Computation** | **Correct evidence, wrong arithmetic** | **Invisible to standard faithfulness metrics because the cited evidence is correct.** Delegate to code |
| **Abstention** | Fabricates rather than refusing when the answer isn't in the corpus | Evaluate refusal quality as a first-class metric |

**RAGA metrics** map to these: context precision → context failure · context recall → retrieval failure · faithfulness and answer relevance → synthesis · abstention quality → unanswerable queries.

**RAGChecker** decomposes answers into atomic claims and checks entailment, yielding an **unsupported claim rate**.

> **This complements RAGAs: a response may score high on overall faithfulness while containing one unsupported numeric claim that matters most.** Track unsupported claim rate alongside RAGA metrics, and **calibrate LLM-as-judge scores against a human-labeled subset to prevent false confidence.**

> **The harness result showing where to invest first: retrieval scores 0.33 (weakest stage), grounded-answer quality 0.65, abstention F1 0.50, security robustness 0.67 — with an unsupported-claim rate of 0.50 versus an unsafe-action rate of 0.17. Ungrounded text generation is typically the more frequent failure.**

**Five-step diagnostic workflow:** build a 50–100 query evaluation set **stratified by difficulty and document type, with 10–20% unanswerable queries and domain-expert-validated ground truth** (automated generation introduces the same biases the harness should detect) → baseline metrics → isolate the failure mode → **apply targeted fixes to the weakest component rather than untargeted changes** → monitor continuously for corpus drift and new query patterns.

**Add citation traceability as a scored metric in every evaluation cycle.**

### Security belongs in the same harness

> **Reuse the diagnostic metrics — unsupported-claim rate, citation-failure rate, abstention behavior — under adversarial prompts, so a regression in robustness looks the same as a regression in accuracy.**

> **Simple defenses work better than expected: input sanitization plus retrieval-aware refusal drives the unsafe-action rate from 0.50 to 0.00 and cuts unsupported claims from 1.00 to 0.25 — a 75% relative reduction with no model swap. The residual 0.25 diagnoses what the defense stack still misses.**

**Corrective RAG / self-RAG** close the loop automatically: if retrieved context scores below threshold, reformulate, broaden, or switch retrieval strategy before generating. **Cost is latency per correction cycle — limit rounds for interactive use; acceptable for batch analytical tasks.**

---

## 7. RAG vs. fine-tuning

| Dimension | Fine-tuned classifier | RAG Q&A |
|---|---|---|
| Primary output | Numeric scores, labels | Narrative answers with citations |
| Scalability | **High (batch)** | Medium (per-query) |
| Flexibility | Low (fixed taxonomy) | **High (open-ended)** |
| Verifiability | Indirect (model confidence) | **Direct (source citations)** |
| Knowledge updates | **Requires retraining** | Update corpus, no retraining |
| Best use | **Systematic factor construction** | **Fundamental due diligence** |

> **The classifier's limitation is structural: it operates within a fixed taxonomy and cannot explain why. The output is a score, not an evidence trail. RAG's limitation is operational: it requires a maintained corpus, retrieval infrastructure, and stronger controls around citations and abstention — and it does not naturally emit the scalable numeric time series systematic strategies demand.**

> **Sophisticated firms employ both: classification identifies which companies warrant attention; RAG enables understanding what those companies are actually doing.**

**Generation model selection — four criteria:** capability (does it follow grounding constraints reliably?) · cost at expected volume · latency · **data residency (can proprietary documents leave the infrastructure?).**

> **The gap is narrowing: open-weight models increasingly approach commercial API quality for well-constrained RAG tasks where context provides most of the required information.** Many deployments tier — open-weight for high-volume routine queries, commercial APIs for complex synthesis.

### Production lifecycle — where the time actually goes

> **After the demo works, teams spend most of their time on operational concerns the pipeline architecture does not address.**

- **Incremental indexing** — detect new filings, restatements, revisions; update embeddings only for changed spans
- **Corpus versioning** — version the corpus snapshot, embedding model, reranker, prompt templates, and generation model **together**, and store a compact **retrieval bundle** (query, retrieved chunks, evidence spans, model versions, answer) per response
- **Deletions and retention** — tombstoning, legal holds, retention rules with audit logs
- **Caching** — query embeddings, reranker results, frequent answers, **with staleness policies tied to filing update cycles**

> **Build for auditability and provenance from the start. Retrofitting access logs, versioned retrieval bundles, and retention controls into a live system is far more expensive than designing them in.** Involve compliance and model-risk teams early.

**Structured extraction extends the same techniques:** 13F co-ownership graphs capture **slow-moving institutional positioning that price-volume data cannot — when multiple large funds hold concentrated positions in the same stocks, the crowding creates co-liquidation vulnerability invisible to standard momentum or value factors.**

---

## 8. Toward agents

**ReAct loop:** Thought → Action → Observation → Repeat.

**RAG becomes one tool among many** — alongside web search, code interpreter, database query, financial APIs.

> **The value of multi-tool orchestration emerges when a question cannot be answered from documents alone.** *"What is Company X's current EV/EBITDA relative to its five-year average?" requires document retrieval for context, a database query for historical fundamentals, and a calculation. No single RAG pipeline handles all three.*

> **Not every problem requires an agent — well-designed LLM workflows often outperform agents for structured, predictable tasks. Reserve agentic architectures for genuinely open-ended exploration.**

> **On adoption, the honest read: internal research assistants, document triage, and analyst-facing retrieval are in limited production at a growing number of firms. Multi-agent architectures are well-described in the literature, but most deployed agentic systems in regulated finance still hold a human in the loop at every action touching external state — order placement, client communications, account changes. The gap between benchmark demos and audited production pipelines remains substantial.**

---

## Transferable rules

1. **Treat grounding as architecture, not prompting.** Post-hoc fact-checking neither scales nor addresses the cause.
2. **Ingestion errors are irreversible downstream.** Validate parser output on representative documents before trusting it at scale.
3. **Tune chunk size as a hyperparameter** on an evaluation grid, and use parent-document retrieval to get precision and context together.
4. **Track publication date, fiscal period, and ingestion timestamp separately.** Filtering by period labels alone leaks information into backtests.
5. **Record structural role and extraction method per chunk,** or citations can look precise while failing claim-evidence alignment.
6. **Benchmark embeddings on your own corpus and query mix.** Cross-model spread can be no larger than within-model variation across query types.
7. **Combine semantic and lexical retrieval.** Pure vector search fails on tickers, codes, and quoted figures.
8. **Verify rerankers on financial passages before adopting them** — a generic cross-encoder degraded MRR by 36% in the chapter's test.
9. **Pre-filter on metadata before ANN search,** never post-filter.
10. **Prefer focused retrieval to long context,** and benchmark positional effects on the target model.
11. **Never trust a citation without verifying it.** Semantic similarity between claim and cited text is a cheap check.
12. **Delegate arithmetic to code.** Computation failure is invisible to faithfulness metrics because the evidence is correct.
13. **Diagnose which of the five failure modes is binding before changing anything.**
14. **Score abstention quality as a first-class metric,** and include unanswerable queries in the evaluation set.
15. **Put security in the accuracy harness** so robustness regressions surface like accuracy regressions.
16. **Choose RAG for evidence-grounded analysis over changing documents; choose fine-tuning for a repeatable skill over stable labels.**
17. **Version the whole stack together** — corpus, embedder, reranker, prompts, generator — and persist a retrieval bundle per response.
18. **Use an agent only when the question genuinely requires multi-tool orchestration.**

---

## Notebooks

`01_sec_filing_pipeline.py` (EDGAR ingestion for five S&P 100 issuers via edgartools; parser comparison quantifying the structure-aware lift; metadata-integrity audit) · `02_domain_embeddings_comparison.py` (191-passage corpus, 15-query workload, per-query-type MRR breakdown) · `03_hybrid_retrieval.py` (BM25 vs. hybrid RRF vs. reranked) · `04_ragas_evaluation.py` (four-axis harness with unsupported-claim and unsafe-action rates) · `05_10k_rag_assistant.py` (citation-constrained answering, explicit abstention, retrieval/citation diagnostics) · `06_esg_rag_vs_finetune.py` (classifier vs. cited-narrative comparison) · `07_institutional_holdings_graph.py` (13F co-ownership networks and cross-sectional features) · `08_rag_security.py` (prompt injection, retrieval poisoning, action injection stress tests)

---

## Cross-references

Ch. 4 SEC filing structure and EDGAR access · Ch. 10 the classification paradigm this chapter contrasts with; FinBERT, embeddings, chunking, tokenization; **the pinned-model-version discipline applies identically here** · Ch. 23 knowledge graphs, for questions depending on paths and networks rather than narrative evidence; GNNs over the 13F bipartite graph · Ch. 24 the full agent implementation; explainability · Ch. 26 governance, MLOps, audit logging, and retention

---

## Citations

Baltussen et al. (2025), ESG classification · Bowne-Anderson (2025), workflows vs. agents · Choi et al. (2025), FinDER · Cormack, Clarke & Buettcher (2009), RRF · Es et al. (2024), RAGAs · Fang & Moore (2025), Man Group agentic signal generation · Faysse et al. (2025), ColPali · Gao et al. (2023), HyDE · Huang, Wang & Yang (2020), FinBERT · Kong et al. (2024) · Kusupati et al. (2022), Matryoshka embeddings · Lee et al. (2025), LLM bias in investment analysis · Lewis et al. (2020), RAG · Liu et al. (2024), lost in the middle · Lopez-Lira (2023); Lopez-Lira & Tang (2025); Lopez-Lira, Tang & Zhu (2025), memorization contamination · Loughran & McDonald (2011) · Nogueira & Cho (2020), cross-encoder reranking · Reimers & Gurevych (2019) · Robertson & Zaragoza (2009), BM25 · Ru et al. (2024), RAGChecker · Saha et al. (2025) · Tang & Yang (2025), FinMTEB · Vaswani et al. (2017) · Wei et al. (2023), emergent abilities · Weller et al. (2025), hybrid retrieval · Xie et al. (2024) · Yao et al. (2023), ReAct · Yu et al. (2024) · Zhao, Li & Zheng (2020)

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 22.*
