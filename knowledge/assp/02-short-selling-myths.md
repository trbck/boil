# Ch 2 — 10 Classic Myths About Short Selling

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 2.
**Governs:** which short-side beliefs you are allowed to encode as assumptions — and which market-structure facts constrain what a short book can physically do.
**Thesis:** most objections to short selling are political, not mechanical. Stripped of rhetoric, the chapter yields a small set of hard structural facts (borrow supply, squeeze preconditions, regulatory frictions, institutional-flow dependence) that directly bound strategy design.

*Rhetorical chapter by design — the argument is largely persuasive. Kept here: the falsifiable facts, the market-structure constraints, and the operational rules that survive them.*

---

## 1. The facts that actually constrain design

These are the load-bearing numbers and mechanisms. Everything else in the chapter is framing.

| Fact | Value / mechanism | Design consequence |
|---|---|---|
| **Borrow availability** | Typically **3–5% of free float** (detail in Ch. 7) | Short interest is capacity-capped by construction. Position size must be checked against borrow, not just liquidity. |
| **Days to cover, entire S&P 500** | **< 4 days** | Shorts are a small fraction of sell volume. Short sellers do not move markets; they ride flows. |
| **Index attrition** | Of the original 1957 S&P 500, **53 of 500** remain | Structural supply of short candidates. Deletions, not just drawdowns, are the opportunity set. |
| **Short-sale restriction (SSR)** | Triggers after **−10% from prior close** | Your executable universe shrinks precisely when your signals are strongest. Model this. |
| **Uptick rule** | A short sale may only execute on an uptick in traded price | Fill assumptions on falling prices are optimistic unless modeled. |
| **Locate obligation** | Borrow must be secured before trading (many jurisdictions) | Pre-trade borrow check is part of the signal pipeline, not an afterthought. |
| **Jurisdictional bans** | Many markets still prohibit short selling outright | Universe construction is jurisdiction-dependent. |

Empirical backing on bans: NY Fed, *Market Declines: What Is Accomplished by Banning Short-Selling?* (Battalio, Mehran, Schultz, 2012) — bans "did little to stop the slide," **significantly increased liquidity costs**, and the 2011 US-downgrade decline was **not** driven or amplified by short selling.

---

## 2. The single most operationally important claim in the chapter

> **Making money on the short side is not about spotting stocks that could go down. It is about riding the tail of institutional investors liquidating their positions.**

Short sellers' own firepower is negligible (see the borrow and days-to-cover numbers above). The price damage comes from institutional selling. Therefore:

- Your edge is **detecting and following institutional liquidation**, not forecasting fundamental deterioration.
- This is why the book's signal machinery is **regime- and price-based** (Ch. 4) rather than fundamentals-based, and why fundamental analysis is confined to a narrow role in Ch. 7.

---

## 3. Short squeeze — the two necessary conditions

A squeeze requires **both**:

1. The issue is **heavily shorted AND thinly traded**. (Explicitly: nobody can squeeze a TSLA-scale name.)
2. **Selling pressure is exhausted** — no natural sellers left to absorb demand.

Mechanism once triggered: supply/demand imbalance lifts price → hits resting buy-to-cover orders → pushes price further → triggers more stop losses → self-reinforcing.

**Penny stocks** (down 90%+ from peak) are named as **high-risk, low-reward** on the short side: binary outcomes — either zero, or a corporate action sends the price ballistic. Borrow evaporates exactly when you need it (the KaloBios/KBIO case: short at ~$2, +800% after hours on a 50% ownership disclosure, borrow vanished, forced cover).

**Encodable screen:** exclude names that satisfy (high short interest) ∧ (low ADV / thin float) ∧ (extreme prior decline). This is the concrete form of the "crowded short" filter built in Ch. 7.

---

## 4. Myth #5 dismantled — the loss asymmetry

Claim: prices can rise infinitely but only fall 100%, so shorts have unlimited loss and limited profit.

Rebuttal is not that the payoff shape is wrong — it is that **the payoff shape is irrelevant under a stop discipline**. Unlimited loss is only realized by someone who sits and watches. "There is simply no excuse for bad risk management."

Two rules stated explicitly:

- **Penny stocks are tourist traps.** Tourists ignore borrow quality and chase the story; when a recall hits they scramble to locate, forced covering snowballs into squeezes.
- **Keep emotions out.** *"If you find yourself fantasizing about a stock going bankrupt and counting your profits, cover and move on."* By the time a name reaches the most-hated lists and financial press, the easy money is gone.

---

## 5. The relative-weakness framing as a *political* choice (not just a quantitative one)

The chapter's practical recommendation, which sets up Ch. 3:

- **Do not run confrontational, activist-style short campaigns.** Every pyrrhic public victory builds resentment among corporations, regulators, and the public, and makes the long-term position of short selling worse (bans, uptick rules, borrow restrictions).
- **Instead, short underperformers relative to the benchmark.** Corporates do not object to being called a relative laggard. Executives in defensive sectors (food, utilities) do not expect to beat the benchmark in a bull market and would fire a manager who bought them there.
- Consequence: the **relative series is the socially and operationally sustainable expression of a short book** — which is precisely the method Ch. 3 builds.

Companies with nothing to fear rarely sue short sellers; conversely, short sellers must be careful about facts and wording, and regulators audit shorting across large pension holdings. Compliance is a survival mechanism.

---

## 6. Myths compressed

| # | Myth | Core rebuttal |
|---|---|---|
| 1 | Short sellers destroy pensions | Pension funds did not allocate to short sellers in the GFC. Separately: most active managers underperform (SPIVA), and the penalty structure (outperform → "stock picker"; underperform → "high tracking error" → redemptions) drives **closet indexing**. Passive on the long side + short sellers for downside is the "retire on numbers" conclusion. |
| 2 | Short sellers destroy companies | No short seller has ever sat on the board of a company they shorted. Management makes the decisions. Kodak owned the digital photography patent and buried it. Short sellers "escort obsolescence out." |
| 3 | Short sellers destroy value | Confusion of **intrinsic value** (wealth created by selling products) with **market value** (what participants will pay — the Keynesian beauty contest). Shareholders create no more value than short sellers destroy. |
| 4 | Short sellers are evil speculators | The CEO defense of ignorance is self-defeating: either willfully blind (complicit) or genuinely unaware (incompetent). The antidote to short sellers is to run the company well. Buybacks that hollow out cash created the 2020 cash-stranded episode. |
| 5 | Unlimited loss / limited profit | See §4 — a risk-management failure, not a structural one. |
| 6 | Short selling increases risk | **Not knowing how to short is riskier.** Refusing the fire drill does not remove the fire. Lynch: more money lost *preparing for* corrections than in them. |
| 7 | Short selling increases volatility | NY Fed evidence (§1): bans didn't stop declines, raised liquidity costs. Delta-hedging by options/convertible/index desks requires shorting; restricting it reduces liquidity and product supply. |
| 8 | Short selling collapses prices | Firepower is capped at 3–5% of float; <4 days to cover the whole S&P 500. Institutional selling is the heavy artillery. |
| 9 | Unnecessary in bull markets | Short selling is a muscle that atrophies. The **inner game** takes time to internalize; the wrong time to start is while the long book bleeds and investors are watching. |
| 10 | The "structural short" | Structural shorts are ubiquitous but hard to arbitrage: liquidity, market impact, borrow. The belief that a short needs no maintenance while a long does is an unexamined asymmetry — it is the tell of someone who has not actually shorted. |

---

## 7. Transferable rules

1. **Model the frictions as first-class constraints**: borrow availability (3–5% of float), locate, uptick rule, SSR at −10%, jurisdictional bans. A backtest without them overstates short performance systematically.
2. **Build shorts around institutional liquidation flow**, not around fundamental doom. You are following size, not leading it.
3. **Exclude the squeeze geometry explicitly**: high short interest ∧ thin trading ∧ exhausted selling pressure. Crowded shorts are false positives (Ch. 1 §4).
4. **Never hold a short that requires no maintenance.** The structural short is a myth; every short position needs the same continuous risk process as a long — more, given the adverse weight drift.
5. **Prefer relative underperformance as the short thesis.** Sustainable, non-confrontational, and it is what the rest of the book is engineered around.
6. **Run the short book in bull markets too.** Skill decay is real, and downside protection is the product investors are actually paying for.
7. When a short becomes emotionally satisfying, **that is an exit signal**, not a conviction signal.

---

## 8. Cross-references

Ch. 1 the outcome matrix and over-filtering (crowded shorts as canonical false positives) · Ch. 3 relative weakness method, the operational form of §5 · Ch. 6 position sizing as the answer to Myth #5 · Ch. 7 borrow availability, crowded shorts, high-dividend value traps, beta · Ch. 8 exposure management.

**Named references:** NY Fed / Battalio, Mehran & Schultz (2012) short-selling bans · Owen Lamont, *Go Down Fighting: Short Sellers vs. Firms* · S&P SPIVA reports · Keynes, *General Theory* (beauty contest) · Surowiecki (2015, New Yorker) · Bogle · Lynch · Munger on volatility vs. permanent loss of capital.
