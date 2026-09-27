# Ch 10 — Text Feature Engineering

**Governs:** turning documents into backtestable factors — which representation to use, and the timestamp discipline that decides whether a text signal survives at all.
**Thesis:** the NLP model is rarely the binding constraint. Availability timestamps, entity resolution, revision handling, and **model training cutoffs** determine whether a text feature is tradable; representation quality only matters after those are settled.

---

## 1. The representation ladder — what each level preserves and loses

| Level | Preserves | Loses |
|---|---|---|
| **Lexical (BoW / TF-IDF)** | Term identity, interpretability, speed | Word order, synonymy, context, negation |
| **Static embeddings** (Word2Vec, GloVe) | Semantic similarity, analogy, generalization to new vocabulary | **Context — one vector per word regardless of sense** |
| **Sequential (RNN/LSTM)** | Order, contextual state | Parallelism; long-range memory still decays; unidirectional by default |
| **Transformers** | Contextual per-token representations, parallel training, long-range access | Compute per document; auditability; hard sequence limits (512–8,192 tokens) |

### Lexical baselines are not obsolete

> **Don't skip the TF-IDF baseline — it's a diagnostic, not a formality.** If a complex encoder fails to beat a well-regularized TF-IDF model, the problem is more likely **label quality, temporal alignment, or task definition** than model capacity. In small samples, narrow domains, and formulaic document types, lexical models remain hard to beat.

**Dictionary choice matters more than method.** Nearly **three-quarters** of "negative" words in the Harvard General Inquirer are not negative in financial contexts — "liability" is a neutral balance-sheet term; "tax," "vice," and "capital" appear neutrally in filings. Use the Loughran–McDonald lists.

| LM category | Financial reading |
|---|---|
| Negative / Positive | Adverse / favorable events |
| **Uncertainty** | Hedging, risk disclosure |
| **Litigious** | Legal exposure |
| **Strong modal** (will, must, always) | Commitment |
| **Weak modal** (could, might, may) | Hedging intent |

> The **strong/weak modal split is the underused one.** Executives who consistently say "will" rather than "might" reveal different confidence in forward-looking statements — a signal that pure polarity scoring discards.

**Two finance-specific lexical failure modes** beyond the generic ones (semantic blindness, synonymy, polysemy, negation, sparsity):

- **Boilerplate dilution** — 10-K risk-factor boilerplate dominates term frequencies, drowning incremental disclosure
- **Amendment leakage** — amended filings and updated articles contaminate historical features without timestamp discipline

### Static embeddings generalize beyond text

Word2Vec's assumption — items in similar contexts share properties — applies wherever meaningful co-occurrence exists. Treating each 13F portfolio as a "sentence" and each stock as a "word" learns institutional-ownership structure that no fundamental database captures.

> **Calibration for how much signal is really there.** On 2024 Q3 13F data (500 largest institutions, 1.32M holdings, 9,167 stocks after min-count 5): Apple's nearest neighbors are Microsoft (0.914), Amazon (0.913), NVIDIA (0.906). On masked-asset prediction, embeddings reach **30.6% Hits@5 on top-decile portfolio positions vs. a 0.055% analytical random baseline — a 229× lift** (95% CI 217–241×, 1,000-iteration bootstrap). **But the lift attenuates to ~6% on positions 11–50 and below 1% on positions 51–200,** where individual fund preference dominates the co-occurrence signal. The embedding captures conviction holdings, not the tail of a portfolio.

**The polysemy problem is acute in finance**, and static embeddings have no answer: prime broker vs. subprime · interest rate vs. interest in acquiring · earnings guidance vs. regulatory guidance · operating margin vs. margin loan. A single vector, dominated by the most frequent sense.

---

## 2. Transformers — what actually matters for features

Self-attention projects each token into **Query** (searching for relevant context), **Key** (advertising relevance to others), and **Value** (information contributed when attended to). Similarity of query to keys → normalized weights → weighted average of values → new contextual representation.

> **Attention weights are internal routing weights, not explanations.** They can be informative but should not be treated as faithful attributions without separate validation. Don't ship an "explainability" story built on attention maps alone.

**Positional information is required** because self-attention is permutation-invariant — without it the model cannot distinguish "assets exceed liabilities" from "liabilities exceed assets."

> **The quadratic bottleneck is the practical constraint.** The attention matrix is L×L, so cost scales quadratically in sequence length. Fine for headlines; it is *the* problem for earnings transcripts, 10-Ks, and research reports. Sparse/local attention, better kernels, longer-context positional schemes, and chunking don't change the equation — they determine which documents you can afford to process.

**Architecture choice for feature engineering:**

| Type | Examples | Best for |
|---|---|---|
| **Encoder-only** | BERT, FinBERT, DeBERTa, ModernBERT | **Default here** — embeddings, classification, retrieval, entity extraction, regression features |
| Decoder-only | GPT-style, LLaMA-style | Generation; extraction/classification via prompting or fine-tuning |
| Encoder-decoder | T5, BART | Translation, conditional generation, some summarization |

### FinBERT is not one model

> `ProsusAI/finbert` (Reuters TRC2 adaptation, Financial PhraseBank sentiment head) and `yiyanghkust/finbert-tone` (analyst-report tone, different training data and labels) are **not interchangeable.** The correct checkpoint depends on document genre and label definition. Treating "FinBERT" as a single artifact is a common and expensive mistake.

**Selection rule:** use a domain-specific checkpoint when its *corpus and labels* match the target task; otherwise start from a strong modern encoder and fine-tune on task-specific financial labels. For long documents, context length and aggregation strategy are **modeling design decisions, not implementation details.**

### Benchmark: what each rung is actually worth

Financial PhraseBank `sentences_allagree` (2,264 sentences; 1,391 neutral / 570 positive / 303 negative; **majority-class baseline 61.4%**), ~1,600 fine-tuning examples, 70/15/15 split:

| Method | Accuracy | Macro F1 |
|---|---|---|
| TF-IDF + logistic regression | 83.2% | 0.742 |
| **GloVe + logistic regression** | **80.6%** | 0.709 |
| FinBERT-tone (zero-shot) | 93.2% | 0.917 |
| **FinBERT (fine-tuned)** | **97.1%** | 0.955 |
| DeBERTa-v3 (fine-tuned) | 94.4% | 0.932 |
| ModernBERT (fine-tuned) | 96.5% | **0.962** |

Three readings:

- **Static embeddings lose to TF-IDF (80.6% vs. 83.2%).** Averaging GloVe vectors discards order and negation; bigram TF-IDF partially recovers them. The semantic-similarity gain is more than offset by the word-order loss.
- Zero-shot FinBERT-tone beats both lexical baselines by ~10pp — the analyst-report → financial-news shift is mild on this clean subset.
- **Domain pre-training buys little once a strong base encoder is fine-tuned.** FinBERT (97.1%) and ModernBERT (96.5%) are within a point on a clean short-sentence benchmark.

> **And the benchmark number is nearly meaningless out of distribution.** FinBERT, with published in-domain PhraseBank accuracy of **87.0%, scores 49.4% on FinMarBa market-labeled headlines — a 37.6pp collapse to near-random.** Same model, same label *names*, different text distribution and different implicit definition of what counts as positive. **Domain adaptation does not rescue a model when fine-tuning and inference corpora disagree on the labels.** Always run a cross-dataset evaluation before trusting a benchmark figure.

---

## 3. The text-to-signal pipeline contract

Define this **before** selecting a model or writing extraction code.

- [ ] **Timestamp definition** — publication time, scrape time, and vendor timestamp are three different quantities. **Only one defines when you could have acted.** Choose explicitly; index backtests on it, not the document's date label.
- [ ] **Publication lag** — form-type and filer-status dependent for SEC filings (large accelerated filers have shorter deadlines); seconds-to-hours for news; same-day to next-day for transcripts. **Measure empirically for your source.**
- [ ] **Entity resolution** — map every mention to a tradable identifier (ticker, CIK, FIGI). Handle ambiguous names, subsidiaries, and M&A transitions where identifiers change mid-series.
- [ ] **Deduplication** — syndicated news, wire updates, and editorial revisions count the same information repeatedly. TF-IDF similarity within (ticker, date) groups removes near-duplicates.
- [ ] **Sampling unit** — sentence, paragraph, or document; define per-firm-day aggregation **before modeling, not after**.
- [ ] **Universe construction** — news coverage is **endogenous**. Heavily covered firms differ systematically from lightly covered ones, and coverage itself may predict returns.
- [ ] **Pre-training horizon** — verify every model's training cutoff predates the backtest period.

> **The lookahead nobody checks: the model itself.** A checkpoint trained on 2024 web crawls has *seen* the news you're using to predict 2023 returns. The same applies to batch LDA, which estimates topics over the entire corpus including future documents — use online LDA that processes sequentially. **Verify every pipeline component, not just the final model.**

### Four safeguards beyond standard walk-forward

| Safeguard | Requirement |
|---|---|
| **Purged CV** | Exclude documents within *k* days of the prediction boundary. **Gap depends on decay horizon** — a 1-day sentiment signal needs a small *k*; a monthly topic-drift signal needs a much larger one |
| **Rolling fine-tuning windows** | Track **both document dates and model training dates**. A model retrained on January data cannot score December documents in a backtest. |
| **Revision leakage** | Snapshot documents at **first availability**; flag and exclude revisions. The `amendment_leakage` field should **default to reject** unless the revision timeline is explicitly verified. |
| **Event-study alignment** | A document at *t* predicts returns over [t+δ, t+h]. **δ must reflect actual availability** — minutes for earnings calls, hours to days for 10-K vendor processing |

---

## 4. Pre-train → adapt → fine-tune

| Stage | What happens | Cost | You run it? |
|---|---|---|---|
| **1. General pre-training** | MLM on Wikipedia/web/books — syntax, semantics, world knowledge | Thousands of GPU-hours | **No** — download a checkpoint |
| **2. Domain adaptation** | Resume MLM on filings, transcripts, analyst reports, financial news — learns vocabulary ("EBITDA," "covenant"), phrasing ("guidance raised to"), co-occurrence ("margin expansion" near "operating leverage") | **Hours, not days** | Sometimes |
| **3. Task fine-tuning** | Add classification/regression/tagging head, train on labels | **Thousands of examples, not millions** | Usually |

### When to fine-tune

| Situation | Recommendation |
|---|---|
| A few hundred labels | Frozen embeddings, prompt-based labels, or parameter-efficient tuning — full fine-tuning overfits |
| **1,000–10,000 labels** | **Fine-tune with early stopping — the sweet spot** |
| Domain-specific vocabulary | Domain adaptation or supervised fine-tuning, depending on whether the gap is vocabulary, genre, or *label definition* |
| Latency-critical | Fine-tune a smaller model (FinBERT-base over an LLM) |
| Nuanced reasoning required | LLM + prompting — fine-tuning may not capture complex logic |

> **The workaround that converts row 1 into row 2:** use an LLM to synthetically label thousands of examples, then fine-tune a compact encoder on those labels. This is the standard route out of the small-label regime.

**Practical settings:** 3–5 epochs, batch size 16–32, small learning rate. **LoRA** updates a small fraction of weights while freezing the rest — **60–80% memory reduction** with modest quality loss, often acceptable when hundreds of task-specific models must coexist.

### Tokenization traps

Subword tokenizers fragment finance-specific terms: "Non-GAAP" → three tokens; "$94.8B" → five or more, **splitting the number across subwords**.

Two consequences: documents near the 512-token limit **lose content at truncation** (switch to an 8,192-token model or chunk explicitly), and **numeric expressions are poorly represented** — extract numbers separately before embedding the text.

### Pooling

| Strategy | Use for |
|---|---|
| **[CLS]** | **Classification default** — token trained to aggregate sequence information |
| **Mean pooling** (attention-mask weighted) | **Retrieval and similarity default** — Sentence-BERT with mean pooling consistently beats raw [CLS] |
| Max pooling | Most-activated feature per dimension |
| Attention pooling | More expressive; needs task-specific training |

---

## 5. Embedding selection and long documents

| Trade-off | Guidance |
|---|---|
| **Bi- vs. cross-encoder** | Bi-encoders (Sentence-BERT, E5, BGE, GTE) embed independently → scales linearly. Cross-encoders jointly process pairs → higher accuracy, higher cost. **Production pattern: bi-encoder retrieval, cross-encoder rerank on the top 50–100.** |
| **Context length** | 512 tokens covers headlines and short paragraphs. Earnings calls (8,000–12,000 words) and 10-K sections need chunking or 8,192-token models. **Justify longer context with measured quality gain on your eval set.** |
| **Size vs. throughput** | Distilled models (MiniLM) offer **~5× faster inference** with modest quality loss for millions of documents daily. Reserve large encoders for high-value extraction. |

Modern families (E5, BGE, GTE) are **instruction-tuned** — embeddings depend on a task prompt ("represent this query for retrieval"). For English financial text these generally outperform older Sentence-BERT checkpoints.

> **Pin model versions.** When an embedding model changes, the *meaning of its vectors* changes — silently invalidating cached embeddings and every downstream model trained on them. Cache embeddings indexed by **document hash + model identifier.**

### Long-document strategies

| Strategy | Mechanics | Trade-off |
|---|---|---|
| **Chunking + pooling** | Overlapping chunks, typically **256–512 tokens with 64-token overlap**, encode independently, mean or attention-weighted aggregation | Simple, robust, parallelizable; discards intra-document structure. Overlap prevents boundary loss. |
| **Hierarchical encoding** | Encode sentences/paragraphs, feed the embedding sequence to a light document-level model | Preserves structure flat pooling loses |
| **Long-context models** | 8,192-token native windows | Still insufficient for full 10-Ks (50,000+ words); needs section selection or hierarchy |

> **Chunk within a filing, never across filings.** Mixing sentences from different time periods into one chunk introduces lookahead directly into the representation.

---

## 6. Text signal families

| Family | What it captures | Note |
|---|---|---|
| **Sentiment** | Positive/negative/neutral tone | **Increasingly commoditized** — edge comes from speed and coverage breadth, not model sophistication |
| **Novelty / surprise** | Semantic distance from a recent baseline | Catches narrative shifts **invisible to sentiment** |
| **Attention** | Coverage intensity, source diversity, headline prominence | **Predicts volatility even when tone is neutral** — 50 articles vs. 2 is a different risk regime regardless of polarity |
| **Events** | Structured extraction (guidance, buybacks, litigation, executive departures) | Schema-based → reliable aggregation |
| **Entity relations** | Who is mentioned with whom — supply chain, competitive, regulatory | Feeds knowledge-graph pipelines |
| **Topic exposure** | Subject categorization; topic-attention series | Narrative factors from 180 news topics explain **~25% of aggregate return variance** (Bybee et al., 2023) |

### Embedding-based factor construction

Two things turn an embedding into a factor:

1. **Aggregation unit** — one embedding per document, then aggregate to a **firm-day** vector (mean pooling weighted by recency or source reliability)
2. **Baseline** — rolling-average embedding over the prior 20 news days = the firm's *expected narrative*

**Three factor patterns:**

- **Semantic novelty** — cosine distance between the firm-day embedding and its 20-day baseline. Spikes when coverage shifts abruptly (sudden regulatory mentions after months of growth discussion) **regardless of whether the new coverage is positive or negative**
- **Peer-relative positioning** — distance from the firm's embedding to its peer-group centroid; cross-sectional dispersion in that distance is a second factor
- **Narrative drift** — treat the embedding series as a time series: period-over-period change, rolling volatility of the trajectory, decay rate of similarity to older embeddings. **Drift in framing often matters more than levels** — markets adapt to stable narratives and respond when framing changes

> **Two research-integrity safeguards.** (1) Never fit global transforms (PCA, clustering) on the full corpus — that leaks future distributional information into past features; implement them walk-forward. (2) Version the embedding model *and* the preprocessing pipeline.

> **Coverage bias in the baseline itself.** A 20-day lookback counts **news-days, not trading days.** Tickers with fewer than 21 covered days in the window get dropped, biasing the factor toward high-attention stocks. Handle sparse coverage explicitly: impute from sector-level baselines, flag as missing, or **model coverage as its own signal.**

### Evaluating text signals — three dimensions beyond Ch. 7

| Diagnostic | Question | Interpretation |
|---|---|---|
| **Decay analysis** | IC at 1, 5, 20 days | Strong 1-day IC with negligible 5-day IC = short-term **attention**, not fundamental information. Useful for short horizons, misleading for monthly rebalancing. |
| **Coverage-conditional** | IC separately for high- and low-coverage stocks | Works only on dense-coverage names → capturing attention dynamics, which changes portfolio construction |
| **Event-time alignment** | Shift the availability timestamp by 30 min / 1 hour / next-day open | **IC that collapses with a 1-hour delay is pricing speed, not information** |

> **Worked calibration on 10-Q filings** (50-symbol sample, cluster bootstrap by symbol, 1,000 iterations). Narrative change (embedding cosine distance between consecutive filings): **IC = −0.151 at 5 days** (95% CI [−0.226, −0.074], p < 0.001, n = 671 across 47 symbols), attenuating to **+0.059 at 20 days** (CI [−0.021, +0.138], p = 0.154). FinBERT sentiment on MD&A sections: **no predictive power at 5 days** (+0.055, CI [−0.036, +0.160], p = 0.264) and a directionally contrarian but inconclusive −0.082 at 20 days. **Same document source, and only the narrative-change signal clears conventional significance** — and only at the short horizon, in the negative direction. Horizon selection isn't a tuning detail; it selects which hypothesis you're testing.

---

## 7. Extract-to-schema

Embeddings measure similarity and change. Many questions need explicit structure — not how similar today's language is to yesterday's, but **whether the company announced a buyback and for how much.**

`"Board authorizes $10B share repurchase program through 2027"` → `{event: "buyback", magnitude: 10e9, currency: "USD", horizon: "2027", confidence: 0.95}` → buyback intensity = announced buyback ÷ market cap over trailing 90 days.

**Why bother:** the structured signal is testable with standard IC analysis, combinable with other factors, and **fully auditable** — properties raw sentiment scores lack.

**Four schema field groups:**

1. **Entity** — issuer and counterparties on stable identifiers (CIK, FIGI, ticker); must handle subsidiaries, M&A, ambiguous mentions
2. **Event** — **controlled vocabulary** (guidance, buyback, issuance, litigation, regulatory action, executive change). Fixed vocabularies are what make aggregation across documents and time reliable.
3. **Attribute** — direction, magnitude, units, horizon. Turns qualitative events into quantitative features.
4. **Uncertainty** — modality (hedging language), confidence, **abstention flag**. Below the confidence threshold, **emit no record rather than a noisy one.**

**Implementation options:** fine-tuned encoders for high throughput · prompt-constrained LLMs with JSON-mode decoding for complex or rare event types · a cascade using cheap encoders for coverage and reserving LLM extraction for high-novelty or low-confidence regions.

> **Schema-guided decoding buys format reliability, not factual correctness.** Constraining generation to a JSON schema, enumeration, regex, or grammar removes brittle post-processing — but extracted entities, dates, magnitudes, and units **still require validation against the source text** plus downstream sanity checks.

**Two safeguards:**

- **Validate at the pipeline boundary** — reject records with missing required fields, out-of-vocabulary event types, or magnitudes failing sanity checks. **Invalid extractions that slip through corrupt aggregated features silently.**
- **Separate extraction from aggregation.** Extraction is document-level with a deterministic model version and an availability timestamp; aggregation is firm-day level using only records available at that point. This lets you **re-extract with a new model without rebuilding the entire feature history.**

---

## Transferable rules

1. **The timestamp contract, not the model, decides whether a text feature is tradable.** Publication ≠ scrape ≠ vendor timestamp; pick the one you could have acted on.
2. **Verify the model's training cutoff predates the backtest period** — for the encoder, the topic model, and every other fitted component.
3. **Always run the TF-IDF baseline.** Failure to beat it points at labels, alignment, or task definition rather than capacity.
4. **Benchmark accuracy does not transfer across text distributions.** Run a cross-dataset evaluation; expect drops of tens of points when label conventions differ.
5. **"FinBERT" names several incompatible checkpoints.** Match corpus *and* label definition to your task.
6. **Snapshot documents at first availability and reject revisions by default.**
7. **Deduplicate syndicated and revised content within (ticker, date)** before aggregation, or you count the same information many times.
8. **Sizing the purge gap is a function of the signal's decay horizon,** not a fixed constant.
9. **Pin embedding model versions and key caches by document hash + model ID.** Vector meaning changes when models change.
10. **Chunk within documents, never across them,** and never fit global transforms on the full corpus.
11. **Coverage is endogenous** — evaluate IC conditional on coverage, and consider modeling coverage as its own signal.
12. **Test the signal against a realistic availability delay.** IC that dies with a one-hour lag is a speed edge, not an information edge.
13. **Attention weights are routing, not explanation.**
14. **Prefer abstention to a low-confidence record,** and validate at the pipeline boundary.
15. **Separate extraction from aggregation** so models can be upgraded without rebuilding feature history.
16. **Reserve LLMs for ambiguous, rare, or schema-rich tasks;** high-volume daily features should use encoders or distilled models unless the LLM adds measurable value after latency, cost, and validation constraints.

---

## Notebooks

| Notebook | Covers |
|---|---|
| `01_word2vec_training.py` | Word2Vec training on financial corpora |
| `02_asset_embeddings.py` | 13F portfolio embeddings, masked-asset benchmark, Hits@5 lift analysis |
| `03_sentiment_evolution.py` | TF-IDF vs. GloVe vs. transformers on the same task |
| `04_bert_finetuning.py` | Fine-tuning on PhraseBank, 70/15/15 split, zero-shot vs. tuned comparison |
| `05_financial_ner_finetuning.py` | Token-level entity extraction and downstream feature engineering |
| `06_finbert_cross_dataset.py` | Cross-dataset collapse (PhraseBank → FinMarBa) |
| `07_news_return_signals.py` | Deduplication, FinBERT scoring, daily narrative-surprise factor |
| `08_text_feature_evaluation.py` | IC/ICIR, decay curves, coverage-conditional diagnostics |
| `09_filing_text_signals.py` | 10-Q sentiment and narrative-change signals with PIT anchoring and cluster bootstrap |

---

## Cross-references

Ch. 4 alternative-data PIT pipelines, entity identifier crosswalks, and M&A identifier transitions · Ch. 5 synthetic data generation for LLM-labeled training sets · Ch. 6 decision-schedule and admissible-information definitions that the pipeline contract instantiates · Ch. 7 §7.3 IC/ICIR diagnostics these signals inherit; §7.4 multiple testing across signal families · Ch. 8 §8.4 event and calendar encodings that text events feed · Ch. 9 fitted-object discipline, of which embedding-model versioning is a special case · Ch. 13 transformer architectures in depth · Ch. 22 RAG pipelines and chunking strategy · Ch. 23 knowledge graphs built from entity-relation extraction · Ch. 24 agentic LLM extraction with schema validation

---

## Citations

Araci (2019), FinBERT · Bhargava et al. (2023), narrative shifts and short-horizon returns · Bybee et al. (2023), online LDA and news-topic narrative factors · Devlin et al. (2019), BERT · Firth (1957), distributional hypothesis · Gabaix et al. (2025), asset embeddings from institutional portfolios · Hochreiter & Schmidhuber (1997), LSTM · Hu et al. (2022), LoRA · Huang, Wang & Yang (2023), analyst-report tone · Loughran & McDonald (2011, 2020), financial sentiment dictionaries · Mikolov et al. (2013), Word2Vec · Pennington et al. (2014), GloVe · Reimers & Gurevych (2019), Sentence-BERT · Robertson & Zaragoza (2009), BM25 · Tetlock (2007), news tone and market outcomes · Vaswani et al. (2017), transformer · Warner et al. (2024), ModernBERT · Wu et al. (2023), BloombergGPT

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 10.*
