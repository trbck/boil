# Workflows

Playbooks for the four modes. Read the one you are entering; they exist so the retrieval step is
not improvised and so output is checkable rather than merely plausible.

All four share two obligations: **cite what you assert**, and **name what you could not ground**.
An honest "the corpus does not cover this, here is my own reasoning" is worth more than a confident
paragraph with no IDs.

---

## Mode: research

*"What does the literature say about X?" · "How should I think about Y?"*

1. `cat generated/ROUTER.md` — locate the governing chapters by their **Governs** line.
2. `lookup.py --search "<question>"` — collect candidate rules and sections.
3. `lookup.py --topic <topic>` — load the governing shard if the question is topic-shaped.
4. `lookup.py --section "<ID§n>"` — read the reasoning behind the rules you intend to cite.
5. Check `references/conflicts.md`. If the question touches an entry, present both positions.

**Answer shape:** the direct answer first, then the evidence with IDs, then the caveats. Not a
literature review — the user asked a question.

Say which pack is authoritative on the topic (ROUTER lists this) and flag when you are citing a
pack outside its competence. `derived` rules are labelled as derived, every time.

---

## Mode: design

*"Design a strategy that…" · "Turn this idea into a spec."*

Retrieval first: the governing chapters for the strategy's family, plus the `process` and
`backtesting` shards, which apply to every design.

**The five frozen choices** (`ML4T-01`) must all be answered before anything downstream is worth
writing. Iterating with these unfixed makes results incomparable across attempts:

| # | Choice | Must state |
|---|---|---|
| 1 | Decision-time correctness | What is knowable at each decision point; how every feature is aligned to its availability |
| 2 | Tradability & universe | What can be traded, liquidity and capacity screens, shorting and borrow rules |
| 3 | Label & horizon | The target and the holding period — this is what the model actually optimises |
| 4 | Cost-model class | Which frictions apply: spread, slippage, financing, impact. The *class* is frozen; parameters get estimated |
| 5 | Evaluation protocol | Walk-forward structure, holdout design, trial logging |

If the user has not supplied one, either ask or state an explicit assumption. Never leave one
silently unset.

**Then, for the strategy itself:**

- **Which archetype?** Left-skew (mean reversion) or right-skew (trend following)? This determines
  the failure mode, the right risk metric, and whether stops even apply (`ASSP-09-R2`, `ASSP-09-R3`).
- **What is the edge, as a number?** Gain expectancy decomposed into win rate, average win, average
  loss — and which module you are attacking.
- **Cost sensitivity.** Report the break-even cost against the assumed cost (`ML4T-16-R9`).
- **Capacity and borrow**, if short-side.
- **Exposure envelope** — gross, net, net beta, concentration.

**Output:** a spec with those sections filled, each material choice carrying the rule ID that
motivated it, plus an explicit list of what remains unresolved.

---

## Mode: implement

*"Write it." · "Build the backtest."*

Prerequisite: a design. If there is no spec, do the design pass first — implementing an
unspecified strategy just relocates the ambiguity into code.

1. Load the rule shards governing what you are about to write (`sizing`, `backtesting`, `costs`…).
2. For engine calls, resolve real symbols — `lookup.py --engine vbtpro --symbol …`. Do not write
   vectorbtpro from memory; the API is large and specific.
3. Write the code.
4. Emit the **compliance manifest** (`references/compliance.md`) as a header comment.

**Non-negotiables while writing:**

- Signals shifted forward one bar (`ASSP-05-R7`, `ML4T-16-R4`).
- P&L computed on the existing position *before* any resize (`ASSP-06-R4`).
- Costs present from the first run, not added later (`ML4T-16-R8`).
- Engine defaults treated as assumptions and stated — order sequencing, cash release, share
  granularity, missing-data policy (`ML4T-16-R6`).
- An unflattering baseline built first (`ML4T-16-R7`, `ML4T-17-R9`).

If a rule must be violated — sometimes there is a reason — record it in the manifest with the
reason. The failure this prevents is silent violation, not violation.

---

## Mode: audit

*"Review this." · "What's wrong with my backtest?"*

1. Read the target file(s) fully before judging.
2. Identify what it is: archetype, horizon, universe, engine.
3. Load the governing shards, plus `backtesting` and `costs` — these catch the most common defects.
4. Walk the code against the rules. Look hardest for:

| Defect | Rule |
|---|---|
| Same-bar signal and execution | `ML4T-16-R4`, `ASSP-05-R7` |
| P&L computed after position resize | `ASSP-06-R4` |
| No cost model, or costs added post hoc | `ML4T-16-R8`, `ML4T-16-R9` |
| Full-sample statistics used to build labels or regimes | `ML4T-16-R12` |
| Max drawdown read as a standalone quality measure | `ML4T-16-R10` |
| Sharpe annualised without adjusting for serial dependence | `ML4T-16-R16` |
| Optimised parameters with no out-of-sample confirmation | `ML4T-16-R18`, `ML4T-17-R6` |
| Trials counted nominally rather than effectively | `ML4T-16-R17` |
| Equal weighting with no risk-contribution check | `ASSP-06-R7`, `ML4T-17-R7` |
| Variance-driven allocation across mixed skew | `ASSP-09-R4` |
| Stops on a mean-reversion strategy | `ASSP-09` §2 |
| Borrow, locate, or short-sale restriction ignored | `ASSP-02`, `ASSP-07` |

**Output — a findings table, most severe first:**

| Severity | Location | Finding | Rule | Fix |
|---|---|---|---|---|
| high | `bt.py:88` | P&L accrues after `position += delta`, so today's fill earns today's move | `ASSP-06-R4` | Move the P&L accrual above the resize |

Severity means consequence, not confidence: **high** invalidates results, **medium** biases them,
**low** is hygiene. Distinguish *this is wrong* from *this is undocumented* — and say plainly when
something is fine. An audit that manufactures findings to look thorough is worse than no audit.

---

## Retrieval budget

A good pass is three to six lookups. If you are past ten, the question was probably too broad —
narrow it, or answer the part the corpus actually covers and say which part it does not.
