# Ch 7 — Refining the Investment Universe

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 7.
**Governs:** which names are *tradable* as shorts, as distinct from which names *should* go down.
**Thesis:** short-side success depends **less on finding good stories and more on weeding out bad setups**. Liquidity evaporates, crowding creates squeeze risk, and corporate actions distort prices for long stretches. This chapter is a set of exclusion filters plus the one place fundamental analysis genuinely earns its keep.

---

## 1. Liquidity — the asymmetry that governs everything

**Long side:** liquidity *increases* as prices rise; early buyers sell into a growing pool. Spreads narrow going up, widen going down. You can build over several days of volume.

**Short side:** when investors liquidate, **it is a one-way street. After a beating they don't come back for round two.** The pool shrinks (the Kübler-Ross grief model, each stage with its own market signature). **Early bear markets are far more liquid than late-stage ones.**

> **Short sellers exit into thinner liquidity than they entered.**

Therefore: **on the short side, liquidity is not about how long it takes to build a position. It is about how easy it is to get out.** Being caught in a squeeze holding a position you cannot cover without market impact is the failure mode.

### Concrete screens

| Screen | Threshold | Reason |
|---|---|---|
| **Average daily trading value** | **well above $1,000,000** | Below this, decent borrow is unlikely to exist |
| **Market cap** | proxy for liquidity | Larger float → more institutional ownership → more lendable supply |

**Why small caps are excluded despite abundant inefficiencies** — two reasons:
1. **Borrow is scarce.** Small free float limits institutional ownership, which limits lending programs.
2. **They are illiquid.** Market efficiency is directly correlated with liquidity; thin volume means the market impact of getting in and out exceeds the inefficiency you were harvesting.

Regime note worth encoding: when risk is **on**, small/mid caps are where the action is; when risk is **off**, participants gravitate to large caps where liquidity remains. **Reversing the long-small/short-large trade is not easy** — shorting small caps in a downturn is "a bloody sport," and *"you can dock a supertanker in the bid/ask spread."*

---

## 2. Crowded shorts — remove them entirely

The author's anecdote is the mechanism, stated as an exploit: in 2007 he built a "squeeze box" that predicted squeezes with high accuracy. **All it took was a long-only manager taking a minuscule speculative long.** The buy/sell equilibrium was already out of balance, so the price rose, tourists frantically covered, that morphed into a squeeze, and the long-only manager exited at leisure with a profit.

> **Rule: eliminate all crowded shorts — issues where borrow utilization exceeds 50% — from your universe. They should not even be on your radar.**

### Borrow utilization — the right metric

```
borrow utilization = borrow taken out for shorting / supply of shares available to borrow
```

**Demand in the numerator, supply in the denominator** — which makes it the most effective single measure of *both* institutional ownership *and* short popularity.

Institutions are stable long-term holders who lend a portion of holdings for fee income. **When they trim, supply dries up.** Simultaneously, as the short thesis gets popular, demand rises. **Utilization north of 50% means shorting appetite exceeds institutional lending programs** — and since institutions are the major lenders, risk/reward has evidently deteriorated.

**Caveat:** utilization varies with ownership structure. Tightly held companies have few shareholders who "often fail to appreciate their babies being the targets of vicious bear raids."

### The two proxies yfinance actually gives you

**yfinance does not expose borrow utilization.** Two substitutes:

| Field | Definition | Verdict |
|---|---|---|
| `shortRatio` | shares shorted ÷ average volume = **days to cover** | Weaker. In theory a longer cover period means a more protracted squeeze; **in practice it fuels one or two days and then reverts to normal.** |
| `shortPercentOfFloat` | shares shorted ÷ **free float** (excludes insiders, governments, strategic holders) | **More interesting.** The better available proxy. |

Screening idiom:
```python
short_float = (sp500_info_df['shortPercentOfFloat'].rank(pct=True)
               .sort_values(ascending=False).index[:10].tolist())
```

### The numbers that kill the "shorts tank prices" myth

- The **most heavily shorted** S&P 500 names sit at **< 1/5 of free float**; beyond the top 10, **< 10%**.
- **S&P 500 average short interest: ~3.5% of free float.**
- **~3.4 days to cover the entire short interest** of the most liquid equity market on the planet.

### Borrow cost and the recall mechanism

Fees range from **general collateral (GC)** on easy-to-borrow names to prohibitive rates on hard-to-borrow/crowded names. **As borrow gets taken out, the quality of the remaining pool deteriorates.** Hard-to-borrow issues are often **callable** — the lender can withdraw on short notice (a **recall**).

**The squeeze cascade:** last-in tourists borrow callable stock without thinking → recall hits → they cannot locate → forced to close → but selling pressure has already climaxed, so the new buying creates a supply/demand imbalance → price rises effortlessly → other shorts hit stops and cover → **full-blown squeeze that flushes out seasoned short sellers too.**

> **Stay away from issues where other short sellers are tapping into low-quality borrow.**

### The counterintuitive finding — crowded shorts don't hedge

**Crowded shorts have *lower* market sensitivity than popular names.** When the market hits an air pocket, crowded shorts barely move while high-flying longs nosedive. **In relative terms, crowded shorts outperform and your longs underperform.**

Proposed explanation: **there is no institutional long money left in crowded shorts, so during a pullback there is nobody left to sell.**

> **Crowded shorts do not hedge long positions when it matters most.** They are the worst of both worlds: expensive, squeeze-prone, and non-protective.

---

## 3. High dividend yields — the fertile ground

**The mechanism:** ex-growth companies raise dividend yield to create **dividend support** for the share price. They know they underperform, so they compensate with generous payout policies. **This deters short sellers from bear campaigns** — but *"while a high dividend yield might stem immediate short-selling pressure, it does not prevent the share price from falling long term."*

That is exactly what makes the high-yielding universe **fertile ground for profitable, peaceful short selling** — peaceful because management does not fight you over a relative call (Ch. 2 §5).

This is the **false negative** archetype from Ch. 1: cheap valuation + dividend support means these names screen out of every short list, yet they don't participate in bull markets and don't protect you in bear ones.

### Sector dividend structure (5-year average yields)

| Sector | 5Y avg yield | Character |
|---|---|---|
| Utilities | **3.34%** | defensive, proudly lags the index |
| Consumer Defensive | **2.78%** | defensive |
| Consumer Cyclical | ~2.1–2.3% | cyclical |
| Technology | ~1.4–1.6% | growth — reinvests earnings |

Growth companies need cash for the business; *"Apple, once the largest market cap in the multiverse, has long sported a stingy dividend policy as a badge of honor."*

### Operational: the dividend calendar

**Dividends are predictable corporate events — use them.**

- **Record date (ex-date)**: **short sellers are liable for the dividend when holding a short through a record date.**
- **Payment date**: same caution.
- Companies often **raise dividends around earnings announcements**.

> **Keep a dividend calendar next to your short positions. Articulate your trading around those dates and you will have a surprisingly pleasant time.**

`yfinance` returns dividend dates as **Unix timestamps** — convert to `YYYY-MM-DD`.

---

## 4. Share buybacks — do not short them

> *"A man generally has two reasons for doing one thing. One that sounds good and the real one."* — J.P. Morgan

Conventional wisdom says corporates buy back when undervalued. **In practice they are as bad at timing as sell-side analysts: buybacks peaked in late 2007 and bottomed in March 2009.** Executive compensation is largely stock options, giving a direct incentive to prop up the price. Buybacks **reduce liquidity, inflate EPS, and drive the price up.**

**The practitioner conclusion is blunt and side-steps the ethics debate entirely:**

> **Corporates have pockets deep enough to artificially levitate share prices. Refrain from shorting companies engaged in buyback programs.**

**The saving grace:** **buybacks are highly correlated with market gyrations — they evaporate exactly when most needed, during corrections.** So a buyback exclusion is a bull-market filter that self-releases in a bear market. (2020 made this explicit: buyback-depleted companies found themselves stranded for cash with fast-dropping share prices.)

---

## 5. Fundamental analysis — the one place it earns its keep

**Reframing the question is the whole contribution:**

| Without regime | With regime |
|---|---|
| *Why **should** this stock go down?* | *Why **is** this stock going down?* |
| Theoretical. Multitudes of possible reasons. Massive timing, reputational, and business risk. Hope the market agrees before investors lose patience. | Practical. **The answer falls into only three buckets.** |

### The three-bucket diagnosis

1. **Temporary mispricing** — regime switched bull → sideways; the stock is consolidating and digesting the advance. **Dead money.**
   → *Action:* **trim.** *"Dead money walking looks a lot better with a vigorous haircut."* Reallocate capital to fresh ideas. If it performs again, there is ample time to restock.
2. **Sector rotation** — several names in a sector underperform in unison.
   → *Action:* **switch horses.** Short the sector that is starting to underperform, go long nascent outperformers. (Ch. 3.)
3. **Stock-specific problems** — one name diverges from its sector.
   → *Action:* **this is where fundamental analysis shines.** This is where real, profitable structural shorts live.

### Value traps

> *"Value traps often go unnoticed because they have all the exterior signs of value stocks."* Generous dividends, a discount to peers, superficially attractive. **They are cheap and stay cheap for a reason. The job of the fundamental analyst is to find out why.**

### Working with a hostile information environment

- **Asymmetry of information:** companies rarely volunteer bad news. Analysts hold "buy" ratings until they read about the bankruptcy filing in the morning press.
- **The exploitable tell:** in the permafrost tundra of Buy ratings, the code word for underperformance is **"Buy for the long-term investors."**
- **Screen for neglect:** look for stocks where **ratings are not refreshed, earnings models gather dust, and even maintenance research is not maintained.** One phone call to confirm "those are stocks for long-term investors" and you are in business.

---

## 6. Valuations — the multiples-compression rule

Use **median, not mean**, for sector `trailingPE`, `forwardPE`, `priceToBook` — avoids outlier distortion.

**How to read the trailing/forward PE gap:** technology sports gravity-defying trailing PEs, **but reasonable forward PEs.** That gap means **earnings momentum is still strong** and justifies the valuation. Defensive sectors trade below market average because *"they have committed the ultimate crime on the markets. They are boring."*

### The core rule

> **Do not short stocks on rich valuations alone. Short high valuations only when earnings momentum decelerates.** That is **multiples compression** — a PE of 35 falling to 20 because the growth premium disappears.

Greenblatt's Microsoft case (*The Little Book That Beats the Market*): Microsoft traded at 50–60× in the early 90s and **delivered year after year** — high growth, high return on capital, dominant products. **When growth slowed in the late 90s, multiples compressed and the stock went nowhere for years.** *A great company can still produce poor investment returns if you pay too high a price for its earnings* — and even continued strong growth would not have made the priced-in expectations attractive.

### Price-to-book as a balance-sheet signal

Expensive PBR means book value per share (equity + retained earnings) is expensive relative to price — i.e. **growth and investment were financed by share issuance or debt.** In accounting terms: **investing cash flow financed by financing cash flow rather than operating cash flow.** This fragilizes the balance sheet.

> **Never keep highly leveraged companies on the long side of the book through a bear market.** *"When the music stops, highly leveraged companies often have a rude encounter with Newtonian physics."*

---

## 7. Beta

```
beta = cov(stock_log_returns, benchmark_log_returns) / var(benchmark_log_returns)
```

Computed as a covariance matrix against the benchmark divided by benchmark variance.

**Implementation choice — resample to month-ends.** A rolling daily beta via `apply` is slow, and **beta does not move much month to month under normal conditions.** So: resample `px_df` to month-end, use a **36-month (3-year) rolling window**, loop through months, and write the result back into ArcticDB per ticker with `ffill()` to give every daily row a `beta` column.

### Sector betas confirm the Ch. 3 taxonomy

| Group | Sectors | Beta |
|---|---|---|
| **High beta / cyclical** | Technology, Consumer Cyclical | > 1 |
| **Low beta / defensive** | Utilities, Consumer Defensive | **sub-1** |

This gives the mathematical foundation for the labels assigned in Ch. 3. Trade implication: **long cyclicals / short defensives in a bull market; keep the same stocks and switch sides in a bear market.**

### High/low beta custom indices — results

Equal-weight average of the two highest-beta sectors vs. the two lowest.

- **Absolute returns:** high beta massively outperforms — **but drawdowns of −20% to −40% are "not commercially viable." Investors will not sit through them.**
- **Relative returns:** high beta and net beta show **positive excess returns**; low beta shows negative. *"High betas will take returns to exhilarating highs but also gut-wrenching lows."*

### The low-beta anomaly

**CAPM says risk correlates positively with return. The data says the opposite** — in long-only portfolios over long horizons, **low-beta stocks tend to generate higher returns.**

> *"CAPM and beta imply that buying riskier stocks should give you higher returns, but the data says the opposite."* — Greenblatt

**In a long/short context it moves differently:** long high beta / short low beta in bullish regimes; same stocks, sides switched, in bearish ones. **The hard part is negotiating regime changes and sideways markets — and the solution is risk management, not stock selection** (→ Ch. 9).

### Top/bottom 5 beta — a negative result

Monthly rebalanced, long the 5 highest betas / short the 5 lowest, no transaction costs.

> **Spectacular in strong bull markets, devastating in every other regime. Not a commercially viable strategy — the volatility is too high to be an investable product.**

### Beta momentum — the interesting result

Instead of beta *levels*, use **month-over-month % change in beta**. Long the 5 largest beta decreases, short the 5 largest increases; monthly rebalance.

> **Rising beta is inversely correlated with returns. The faster beta rises, the worse the returns.**
> **Falling beta is positively correlated with excess returns** — *"once issues fade from the limelight, volatility abates, and they perform better."*

This directly contradicts CAPM. *"Fast rising beta stocks look like the kind of stocks featured on Mad Money — a compelling story in theory, gravitationally challenged in practice."*

**Stated caveats:** survivorship bias, not exhaustive, worth extending to other markets.

### Inverse-beta sizing — and why "market neutral" is secretly bullish

Equalize risk by weighting inversely to beta. Stocks A (β=1.25) and B (β=0.80), both at 0.5% raw fixed risk:

```
A:  1/1.25 × 0.5% = 0.400%
B:  1/0.80 × 0.5% = 0.625%
```

Long A, short B → net exposure = **0.400% − 0.625% = −0.225%**

> **To neutralize beta you need a bigger short book, which mechanically produces a negative net exposure.** This explains why portfolios reported as market-neutral (net exposure ≈ 0) **often carry a residual bullish tilt** — net exposure ≠ net beta.

This is the setup for Ch. 8's central distinction.

---

## 8. The filter stack — summary

Apply in order to go from index to short-ready universe:

| # | Filter | Rule |
|---|---|---|
| 1 | **Liquidity** | ADV well above $1M. Exclude small caps. Judge by exit, not entry. |
| 2 | **Crowding** | Exclude borrow utilization > 50%. Use `shortPercentOfFloat` as the proxy. Exclude callable-borrow names. |
| 3 | **Buybacks** | Exclude active buyback programs — they self-release in corrections. |
| 4 | **Dividends** | **Include** high-yield ex-growth names as short candidates. Track record/payment dates; you owe the dividend. |
| 5 | **Valuation** | Never short on rich multiples alone. Require **decelerating earnings momentum**. Flag expensive PBR as balance-sheet fragility. |
| 6 | **Beta** | Size inversely to beta. Prefer **falling** beta longs / **rising** beta shorts over beta levels. |
| 7 | **Fundamentals** | Only after regime says the stock is already going down, and only to answer *why* — three buckets: mispricing / rotation / stock-specific. |

---

## 9. Transferable rules

1. **Judge short liquidity by the exit, never the entry.** Liquidity is thinner on the way out than the way in, structurally.
2. **Borrow utilization > 50% is a hard exclusion.** Not a caution — an exclusion.
3. **Crowded shorts are anti-hedges.** They outperform in pullbacks because there is no institutional long money left to sell.
4. **Expensive or callable-only borrow is a long signal** (Ch. 3 §7), not a short signal.
5. **High dividend yield is a short *source*, not a short deterrent** — the yield defers the decline, it does not prevent it.
6. **Never short a name doing buybacks.** You are fighting an unlimited, price-insensitive bid.
7. **Short liability for dividends is real.** Maintain a dividend calendar per short position.
8. **Rich valuation alone is never a short thesis.** The thesis is rich valuation + decelerating earnings momentum = multiples compression.
9. **Expensive PBR = investing cash flow financed by financing cash flow.** Never hold those long through a bear market.
10. **Let regime ask the question, let fundamentals answer it.** "Why is it going down?" beats "why should it go down?"
11. **Beta *momentum* beats beta *level*.** Rising beta → worse returns; falling beta → better returns. Both contradict CAPM.
12. **Size inversely to beta**, and understand that beta-neutral implies **negative** net exposure. Net exposure and net beta are different constraints.
13. Resample to month-end for beta — daily rolling beta costs a great deal of compute for no signal.

---

## 10. Cross-references

Ch. 1 the false-negative archetype (dividend value traps) and the false-positive archetype (crowded shorts) · Ch. 2 borrow economics, squeeze preconditions, the 3–5% of float number · Ch. 3 defensive/cyclical taxonomy, sector rotation, callable-borrow rule · Ch. 4 ArcticDB (`beta` column written back per ticker) · Ch. 6 Horseman 1 (liquidity) operationalized, inverse-beta sizing · **Ch. 8 net exposure vs. net beta — the distinction §7 sets up** · Ch. 9 risk management as the answer to regime transitions.

**Named references:** Joel Greenblatt, *The Little Book That Beats the Market* (Microsoft / multiples compression; CAPM critique) · Milton Friedman (shareholder supremacy) · Kübler-Ross grief model applied to liquidity decay · norgatedata.com (survivorship-bias-free data).

**Libraries:** `pandas`, `numpy`, `yfinance` (`yf.Ticker(symbol).info`), `arcticdb`, `matplotlib`.

**yfinance fields used:** `marketCap`, `sharesOutstanding`, 10-day average volume (preferred over plain average), `shortPercentOfFloat`, `shortRatio`, `dividendYield`, `fiveYearAvgDividendYield`, `payoutRatio`, dividend dates (Unix), `trailingPE`, `forwardPE`, `priceToBook`.
