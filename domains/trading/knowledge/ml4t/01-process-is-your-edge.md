# Ch 1 — The Process Is Your Edge

**Source:** Jansen, *Machine Learning for Trading*, 3rd ed. (Packt, 2026), Ch. 1.
**Governs:** whether a research project is worth starting, and under what pre-committed rules.
**Thesis:** durable performance comes from a disciplined research-to-production loop, not from picking a better model. No model stays optimal across regimes; the differentiator is the ability to validate, monitor, and retire without improvising.

---

## 1. Core claims

- Three forces have raised the value of process over model sophistication: market behavior shifts (abruptly and gradually), modeling capacity has grown (more researcher degrees of freedom → overfitting is easier to produce and harder to detect), and tooling has accelerated both good iteration and fast data mining.
- 2020–2025 supplied four stress tests of assumptions calibrated to the 2010s — a pandemic liquidity shock, a sentiment/meme-stock shock, an inflation/macro regime shift, and an equity-concentration crowding shock. The book's framing: these are recurring categories, not special cases.
- The objective is not predictive accuracy. It is risk-adjusted performance after costs under changing conditions. This distinction drives almost every downstream design choice.
- Grounded in Lo's Adaptive Markets Hypothesis: efficiency is an evolutionary outcome, not a permanent state. Risk premia, correlations, and execution costs move with the participant mix. Edges decay as they are exploited and sometimes revive.
- Process framing borrowed from CRISP-DM / CRISP-ML(Q) and López de Prado's "alpha factory" — a repeatable pipeline that generates, evaluates, deploys, and monitors under explicit constraints.

---

## 2. Vocabulary — use these precisely

These four are routinely conflated and they imply different responses.

| Term | Definition | What it answers |
|---|---|---|
| **Structural break** | Abrupt change point in the data-generating process | *When* the system changed |
| **Regime** | Persistent state; properties stable within, materially different across | *What kind* of environment we are in |
| **Data drift** | Input feature distribution shifts | Model-side symptom |
| **Concept drift** | Feature→target relationship changes | Model-side view of a structural break |
| **Online detection** | Identifying change in real time using only decision-time information | The only version that is tradable |

Operational rule: **drift is a flag, not a diagnosis.** It triggers an investigation into data integrity, feature validity, execution conditions, and regime exposure. A backtest may tolerate ex-post regime labels; a live strategy cannot.

---

## 3. The ML4T workflow — structure

Two layers, plus a gate.

**Layer 1 — Data infrastructure (Ch. 2–5).** A standing investment, not a stage. Establishes shared semantics so results are comparable across projects:
- Sourcing and coverage: vendors, identifier verification, missing data, documented sampling and revision policy
- Time semantics: event time vs. publish time; features aligned to what was knowable at the decision point; stable ordering on tied timestamps
- Asset-class mechanics: corporate actions and fundamental revisions (equities), roll/stitch conventions (futures), venue and funding rules (digital assets)
- Quality invariants: survivorship, stale quotes, broken adjustments, identifier-mapping errors — and reproducibility such that a dataset can be regenerated exactly

**Layer 2 — Strategy research loop (Ch. 6–21).** Cyclical, not linear. Each module emits artifacts consumed downstream; live results feed back into revised hypotheses.
1. Research/evidence framework (Ch. 6)
2. Feature and label engineering (Ch. 7–10) ⇄ model development (Ch. 11–15, 21) — a *nested* loop; diagnostics in each update the other
3. Strategy design (Ch. 16–20)
4. Deployment and monitoring (Ch. 25–26)

Ch. 22–24 (RAG, knowledge graphs, agents) are research *tooling* that cuts across all layers rather than sitting in one.

Note: the workflow is model-agnostic. Signals can be discretionary, rule-based, or learned — the structure is unchanged.

---

## 4. The five things you freeze before iterating

This is the highest-value operational content in the chapter. Fix these up front; iterate everything downstream without revising them.

1. **Decision-time correctness** — what information exists at each decision point; every feature aligned to its availability
2. **Tradability and universe rules** — what can be traded, liquidity/capacity screens, shorting rules
3. **Label and horizon definitions** — target and holding period (this is what the model actually optimizes)
4. **Cost-model class** — which frictions apply (spread, slippage, financing, impact). The *class* is frozen even though parameters get estimated
5. **Evaluation protocol** — walk-forward structure, holdout design, trial logging

The point is not to prevent iteration. It is to keep improvements interpretable as stronger signals rather than as changed definitions.

---

## 5. The evidence boundary

The central discipline mechanism. Two modes:

- **Exploration** — ideas develop; use available data freely for diagnostics; **log every trial in a research ledger** so the search can be counted and characterized
- **Confirmation** — sealed holdout untouched during exploration, frozen specification, predefined metrics, selection-adjusted inference accounting for the trial count

The goal is *not* pre-committing to a fixed number of trials. It is being able to say how much searching produced this result. Credibility = countable search + untouched data.

---

## 6. Named failure modes

**Research-level (§1.1):**

| Failure | Signature |
|---|---|
| Data mining / narrative overfitting | Hypothesis generated after seeing outcomes |
| Leakage / non-point-in-time data | Revisions, survivorship, corporate actions, timestamp errors |
| Multiple testing and selection bias | Search variants until one "works," then treat noise as signal (Harvey, Liu, Zhu 2016) |
| Ignoring implementability | Confusing predictability with edge after costs |
| Sunk cost / delayed exit | Keeping a decayed strategy because it once worked |

**Solo-specific (§1.5)** — these are the ones institutions partially avoid through enforced friction:

| Failure | Signature | Counter |
|---|---|---|
| **Goalpost drift** | Redefining success after seeing results (accepting lower Sharpe for smaller DD) | Write the success criterion before running |
| **Assumption stacking** | Optimistic fills + end-of-bar execution + understated costs + ignored capacity + favorable sample. Each harmless alone; together they manufacture performance | Enumerate assumptions explicitly; audit as a set |
| **Flexibility without accounting** | Large feature sets and heavy tuning without treating the result as conditional on the search | Research ledger |
| **Late tradability discovery** | Weeks of signal refinement on something that can't survive spreads/latency/capacity | Run the tradability check early |

**Generative-AI-specific (§1.3):** hallucination in event summaries and backtest "explanations"; **leakage by construction** (future info entering via the LLM's own training data — a leakage channel that doesn't exist for classical features); complexity inflation.

---

## 7. Checklists

### Scoping check — implementability first
- [ ] Written decision point and information set: what arrives when
- [ ] Why might this be slow to price? What friction prevents immediate arbitrage?
- [ ] **Stop criteria** recorded up front: turnover level at which costs dominate; capacity incompatible with intended size; instability across obvious regime slices

### Data integrity check
- [ ] "What the model knew at time *t*" is unambiguous
- [ ] Point-in-time semantics, corporate actions, revisions, timestamps, session alignment all resolved before modeling

### Signal check — robustness before cleverness
Question is not "is it significant" but "does it survive variation":
- [ ] Different walk-forward splits
- [ ] Plausible regime slices
- [ ] Modest preprocessing changes
- [ ] Conservative cost assumptions

Signals that work only in a narrow configuration stay in exploration.

### Tradability check — fragility audit
Sensitivity tests carry more information than point estimates:
- [ ] Does the edge persist at 2× costs?
- [ ] With execution delayed by seconds/minutes?
- [ ] With position size or participation capped?
- [ ] With entry/exit timing shifted within the bar?

**Decision rule: a strategy that degrades gracefully beats one that needs a precise set of optimistic assumptions.**

### Monitoring check — diagnosis maps to action
Minimum viable requirement: separate **signal decay** from **operational failure**. When performance drops, distinguish (a) weakened signal, (b) degraded data pipeline, (c) rising execution costs — each implies a different response.

Without that separation you react to noise, and *intervention is itself a source of overfitting.*

---

## 8. Regimes — the correct use

**Rule: regimes are a risk lens, not a return-timing tool.**

Three tasks, different evidentiary standards:

| Task | Purpose | Standard |
|---|---|---|
| Ex-post labeling | Vocabulary for when the strategy struggled | Descriptive; full sample OK |
| Backtest conditioning | Stress test performance by state | Must prevent regime labels leaking into decision-time features |
| Live monitoring | Early warning + risk control | Decision-time info only; walk-forward evaluation |

The dominant misuse is treating ex-post labels as if they were known in real time.

**Empirical anchors from the chapter's notebooks:**
- `factor_regimes.ipynb` — GMM on AQR's Century of Factor Premia (1927–2024). Fits K=2..6; two-state is most stable and interpretable. **AIC prefers K=6 but silhouette ≈ 0 and the partition fragments after 1950 — a direct warning that AIC alone is a bad selection criterion when you want an interpretable regime map.**
- Risk-Off vs Risk-On: vol 19.1% vs 8.6% (2.2×); equity Sharpe 1.11 → 0.12; max DD −77% vs −23%. Value is countercyclical (+5.3% vs +1.6%); carry (−0.6%) and defensive (−0.5%) turn negative *exactly when diversification is needed*.
- 267 transitions over 98 years ≈ one every 4 months — too noisy for tactical timing. This is the empirical argument for the risk-lens-only rule.
- `macro_regimes.ipynb` — 4 monthly FRED series (`UNRATE`, `DFF`, `T10Y2Y`, `CPIAUCSL`), CPI converted to YoY because the level is non-stationary and would dominate clustering; standardized, 4-component GMM; silhouette as separation diagnostic. Hierarchical pass gives cophenetic correlation 0.710; Ward/GMM/K-Means agree. Macro regimes separate **volatility and drawdown** more cleanly than they separate mean returns.

**Regime pitfalls:** look-ahead (fitting/labeling on full history then using labels in trading logic); degrees of freedom (sensitive to features, preprocessing, window length, state count); over-interpretation (regimes summarize, they don't explain).

**Reframe the question:** not "what regime is the market in?" but "how does *this strategy* behave when these conditions arise?" e.g. momentum under correlation spikes and clustered reversals; carry under funding stress and policy pivots; mean reversion when vol rises and liquidity thins.

---

## 9. Two entry points, two deliverable types

- **Prediction-first (complexity-tolerant):** start from a forecast target and broad features; high capacity is legitimate when the objective is economic value. Kelly & Malamud (2025): high complexity can coexist with strong OOS performance via regularization and ensemble diversification. Only valid under leakage-resistant protocols, walk-forward validation, and statistical budgeting.
- **Mechanism-first (structure-imposing):** start from an economic rationale that bounds the search space and defines what should break under drift. Not anti-ML — a response to limited effective sample size and winner's-curse dynamics (Arnott et al. 2018).

**Litmus test for which you're in:** if being wrong means "it doesn't make money after costs" → *signal* territory. If being wrong means "the estimate is biased or misleading" → *measurement* territory (premia estimates, risk attribution, hedge construction; see Ch. 19). Misspecified measurements produce "factor mirages" — precise-looking and causally wrong.

---

## 10. Causal inference and generative AI — where they sit

- **Causal inference** is a *discipline-enforcing lens*, not a requirement. Value: constrains scoping, avoids bad controls and spurious predictors, sharpens decay diagnosis by linking it to mechanism-relevant conditions. When identification is weak — which is common in trading — treat it as a diagnostic (what to control for, what *not* to, what to monitor) rather than a claim. Robust OOS evidence and implementability remain the arbiters. (Ch. 9, 15)
- **Generative AI** broadens usable data (unstructured text, documents) and accelerates iteration. It amplifies the workflow that employs it in both directions. The practitioner role shifts from implementer to **supervisor and validator**. Automated outputs are candidates subject to identical evaluation safeguards. (Ch. 22–24, governance in Ch. 26)

New-in-3rd-edition additions slotted into the workflow: conformal prediction for uncertainty quantification, false-discovery control, regime-aware modeling incl. HMMs, deep learning for time series where empirically justified, agentic automation.

---

## 11. Independent vs. institutional — where to compete

**Avoid where institutional advantage is structural:**
- Speed/microstructure — if being first matters, it's not viable. Favor economics that tolerate seconds-to-minutes of delay and still survive costs.
- Expensive data as a *prerequisite* — prefer problems where information is accessible and interpretation/discipline are the differentiators.

**Independent advantages:**
- **Capacity-constrained opportunities** — many effects don't scale; large funds ignore them because they can't deploy size without impact. Treat small-size viability as a strategy class, not a flaw — provided capacity is modeled honestly.
- **Tighter iteration loops** — the advantage is not more configurations tried; it's cleaner diagnostics and reusable tooling lowering the marginal cost of the next experiment.

**Highest-leverage infrastructure investment (compounds across strategies):**
- Dataset versioning + point-in-time pipelines
- Standardized backtest/evaluation harnesses (Ch. 16)
- Shared cost and slippage models with sensitivity tests (Ch. 18)
- Monitoring templates mapping failure modes → actions (Ch. 19, 25)

---

## 12. Transferable rules — condensed

1. Freeze the five evaluation-defining choices before iterating; iterate only downstream of them.
2. Log every trial. Unlogged search is uncountable, and uncountable search cannot be adjusted for.
3. Run the tradability check *early*, not after signal refinement.
4. Prefer graceful degradation over optimal point estimates.
5. Regimes gate risk posture, never entry timing.
6. Drift is a flag; always follow it with a four-way diagnosis (data / feature / execution / regime).
7. Monitoring must distinguish signal decay from operational failure, or intervention becomes another overfitting channel.
8. AIC and similar in-sample criteria are unreliable for selecting interpretable structure — check separation diagnostics too.
9. Model-agnostic: this whole loop applies to rule-based systems as well.

---

## 13. Cross-references

Ch. 2–5 data infrastructure · Ch. 6 research framework · Ch. 7–10 features/labels · Ch. 11–15 modeling · Ch. 11 HMMs and Wasserstein k-means regime work · Ch. 16 backtest harness · Ch. 18 cost models · Ch. 19 risk, monitoring, measurement deliverables · Ch. 21 RL · Ch. 25 live ops · Ch. 26 MLOps and governance.

**Key citations:** Lo (2004) Adaptive Markets · López de Prado (2018) alpha factory · Studer et al. (2021) CRISP-ML(Q) · Harvey, Liu & Zhu (2016) multiple testing · Arnott et al. (2018) · Kelly & Malamud (2025) complexity · Ilmanen et al. (2021) Century of Factor Premia · Botte & Bao (2021, Two Sigma) GMM style regimes · Horváth et al. (2021) Wasserstein k-means · Pearl (2019), Schölkopf et al. (2021) causality.
