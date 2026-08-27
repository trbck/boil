# Ch 5 — The Trading Edge Is a Number, and Here Is the Formula

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 5.
**Governs:** the objective function you optimize and the metric you report. Everything from Ch. 6 onward is an attack on one of its four inputs.
**Thesis:** the trading edge is not a story, a thesis, or a proprietary dataset. It is **gain expectancy** — middle-school arithmetic — and it decomposes cleanly into two engineerable modules: **signal** (win/loss rate) and **money management** (average win/loss). Casinos advertise randomness and print money; funds claim foresight and post lumpy returns. The difference is that casinos *engineer* their edge.

---

## 1. The three kinds of edge

| Edge | Verdict |
|---|---|
| **Technological** | Democratized. Retail today has more compute and data than a top institution 10 years ago; hedge-fund-grade cloud costs <$50/month. But *"everyone wants to be Jim Simons, no one wants to take care of the plumbing"* — a third of programmatic traders name data processing, storage, and server management as their #1 problem. **You cannot vibe-code your way to a robust edge.** |
| **Information** | **Gets arbitraged away, faster every year.** If information were the edge, the institutions with corporate access on speed dial would beat index funds. They have not, for every year on record. "Information wants to be democratized." |
| **Statistical** | **Does not get arbitraged away. It exists and persists by design.** It is not *what* you trade but *how*. |

The book's whole program: not how to pick stocks differently, but **how to squeeze more juice out of the ones you already picked.**

---

## 2. The three formulas

All three take the **same three inputs** — win rate, average win, average loss — and cook them differently.

```python
def expectancy(win_rate, avg_win, avg_loss):
    """Arithmetic gain expectancy. avg_loss is negative."""
    return win_rate * avg_win + (1 - win_rate) * avg_loss

def geometric_expectancy(win_rate, avg_win, avg_loss):
    """Profits and losses compound geometrically — closer to true robustness."""
    return (1 + avg_win)**win_rate * (1 + avg_loss)**(1 - win_rate) - 1

def kelly(win_rate, avg_win, avg_loss):
    """Position size that maximizes geometric growth rate."""
    return win_rate / np.abs(avg_loss) - (1 - win_rate) / avg_win
```

- **Arithmetic expectancy** — the default when practitioners say "edge." Easy to grasp and compute.
- **Geometric expectancy** — mathematically closer to expected robustness, because P&L compounds.
- **Kelly** — Bernoulli → J.L. Kelly Jr. → Edward Thorp (*Beat the Dealer*, *Beat the Market*). **In practice use a partial Kelly — one-third or one-half.** Mathematically optimal sizing routinely exceeds a human's psychological tolerance.

> **"Nothing happens until the gain expectancy turns positive. Sharpe, Sortino, Jensen, Treynor, and information ratios are all well and good, but they come *after*."**

### The two-module decomposition — the chapter's organizing idea

| Module | Governs | Where it is engineered |
|---|---|---|
| **Signal** | **Win rate / loss rate** — returns from entry and exit signals | Ch. 4 (regime), Ch. 5, Ch. 7 |
| **Money management** | **Average profit / average loss** — returns × bet size | **Ch. 6 (position sizing), Ch. 8** |

*"This demystifies the trading edge as something that can be engineered from the ground up."*

---

## 3. Measuring the edge in practice

### The rudimentary strategy (used for demonstration throughout the book)

Recycles the Ch. 4 composite score straight out of ArcticDB. **No optimization of parameters or weights whatsoever:**

```python
library_SP500 = initialise_adb_library_local('data', 'SP500')
px_df = adb_concat_single_column(library_SP500, library_SP500.list_symbols(), 'Close')

# signal:  score_rel > 0.5 → long (+1);  score_rel < -0.5 → short (-1);  else flat (0)
# then SHIFT +1 day: a signal today can only be traded tomorrow
```

**No transaction costs, no slippage.** The shift is the one realism concession — it removes look-ahead bias. Known weakness, stated up front: **the strategy gives back a lot of gains in sideways markets — many false positives erode the equity curve.**

Long/short simulation idiom: assign +1/−1, multiply the shifted signal by the return, sum.

### Splitting wins from losses

```python
def daily_profits(returns): return returns.copy().mask(returns < 0)   # losses → NaN
def daily_losses(returns):  return returns.copy().mask(returns > 0)   # gains  → NaN
```

Then compute over a rolling window (e.g. 100 days): rolling win rate, loss rate, average win, average loss → feed into `expectancy`, `geometric_expectancy`, `kelly`. **`.ffill()` is required** because the strategy is not always active — the pieces must be stitched together.

**Reading the diagnostics:**
- Win rate above loss rate ≠ profitable. You must superimpose average win vs. average loss.
- Average profits consistently larger than average losses, and the biggest profit larger than the worst loss → the strategy is **right skewed**.

### Use two durations — an operational rule

| Duration | Purpose |
|---|---|
| **Long** | Establishes the strategy makes money **over time**. *It does not have to make money all the time.* |
| **Short** | Captures **cyclicality** → used for **asset allocation**. E.g. this strategy bleeds in sideways markets, so reduce exposure there. |

This is the seed of Dynamic Exposure Allocation in Ch. 9.

---

## 4. The signal module

### The 51% myth, killed

> "You will make money as long as you are right 51% of the time." **Wrong.**

Top performers with decade-long records openly report unimpressive win rates. **LTCM boasted an exceptionally high win rate right up to its blowup.** You make money if and only if gain expectancy is positive.

False positives cannot be eradicated (Ch. 1). **Randomness is a feature, not a bug.** Every basket has bad apples; the job is a policy for spotting and removing them before they spoil the basket.

### Entries: stock picking is vastly overrated

> "The stock market is the only competitive sport where people hand out medals before the race starts."

90% of participant energy goes into making the right calls; 90% of participants fail to beat their benchmark five years running. **They predictably fail because they consistently focus on the wrong thing: entry.**

Long-term market return is ~+7% (Siegel) — that leaves little room for pleasantries on the short side. *"Ideas are cheap and plentiful… the difference between ideas and profits is called execution."* Short sellers fail because they enter **when ideas germinate, not when they are ripe**.

**Two moments where probabilities must be checked:**

1. **Stock selection** — short only stocks in **sideways or bear regimes**. Shorting a name in a bull regime is a bet against a bull market; eventually you get the horns. Because shorting is a relative game (absolute decline is a laggard indicator), regime change usually shows up as **sector rotation**.
2. **Entry timing** — the long-side habit of buying breakouts **does not transfer**. Almost everyone is in the market to buy; sidelined buyers wait for dips, so fast falls are followed by rapid bear-market rallies.

> **The best time to enter a short is when a bear market rally rolls over.**

### Exits: where paper becomes money

- *"The only soldiers who walk into battle without an exit strategy are called kamikaze."* Develop the exit **before** entering.
- **The only time you know how much real money was made or lost is after closing.** Everything before that is paper profit.
- **Bad entries can be salvaged. Bad exits cannot.** (Marriage/divorce analogy: bad marriages can be turned around; bad divorces cannot.)
- **5 of the 7 steps to increase the trading edge deal with losses** (Ch. 7 onward).
- Personal-finance analogy: with variable earnings, keep a low fixed cost base and pocket the difference. You get the same big paydays as everyone else, but **you don't need them to stay afloat**. That is "cutting your losses short."

---

## 5. There are only two strategies

**Not entries — exits determine your strategy type.** Mean reversion closes when the inefficiency corrects; trend following rides winners. Value investors buy undervalued, then pass the baton to growth investors who ride into the sunset. (Counterexample: Buffett, the ultimate *value trend follower*.)

Only three things can happen to a position: price goes up, down, or nowhere — **you make, lose, or waste money. You need a plan for each**: realize profits, mitigate losses, deal with freeloaders.

### Trend following

| Property | Detail |
|---|---|
| **Win rate** | **30–50%.** The *mode* of the distribution sits in the loss-making region. For every Alphabet/Amazon/Apple there are countless Netscapes, Ataris, MySpaces. |
| **Alpha source** | A few big winners offset many small losses. **Losses are dealt with quickly; winners take time to mature** — an inherent lag between profit accrual and loss realization. |
| **Skew** | **Right.** Favorable tail ratio; winners bigger than losers. The visual form of "cut your losers, ride your winners." |
| **Cyclicality** | Markets do not trend all the time; styles fall out of favor and losses mount. |
| **Turnover** | **Relatively low** — a function of cyclicality. "Money is made in the sitting and waiting" (Livermore). Turnover rises when the style is out of favor. |
| **Volatility** | High — long stretches of lackluster returns. |
| **Core risk** | The **aggregate weight of losses over profits**. |

**Relevant metric: gain-to-pain / profit factor** (Schwager) — cumulative profits ÷ |cumulative losses|:

```python
def profit_ratio(wins, losses):   # rolling or cumulative
    return (wins.sum() / losses.abs().sum()).ffill()
```

Must be **> 1** long-term. Compute both a **rolling** (100-day) and a **cumulative** version; divergence between them reveals edge stability. The rolling ratio can sit below 1 for extended stretches (2019–2020 in the GE example).

> "Profits only look big to the extent that losses are kept small."
> Turtle traders amassed hundreds of millions **with a 30% win rate.** They took trades expecting them to fail, and satisfied the need to be right by being exceptional risk managers rather than better pickers.

### Mean reversion

| Property | Detail |
|---|---|
| **Win rate** | **Often > 50%.** The mode sits in the profit region. |
| **Alpha source** | High turnover; compounds many small profits by arbitraging inefficiencies — it captures **the time it takes for an inefficiency to correct**. |
| **Skew** | **Left.** Unfavorable tail ratio; losers bigger than winners. The visual form of "you can't go broke taking profits" — *you probably can, if losses are too big.* |
| **Key assumption** | **Stationarity** — stability of the relationship / autocorrelation. |
| **Stop losses** | **Not enforced**, by design: the premise is that the inefficiency must correct. This is exactly what produces rare, devastating blows. |
| **Fails during** | **Regime changes** and tail events. Long high-beta / short low-beta works beautifully in a bull market and gives it all back in the transition. Short-gamma funds performed for years, then blew up in three weeks in 2008. |
| **Recovery** | **Slow** — many small wins are needed to offset a few large losses. |

> "The captain of the Titanic had a 99% win rate."

**Relevant metric: tail ratio** — right-tail quantile ÷ |left-tail quantile| (e.g. 95th ÷ |5th|), in rolling and expanding versions, **`clip`ped to `[-limit, +limit]`** to prevent inf/NaN from near-zero division. >1 → right skewed; <1 → left skewed.

### The complementarity

> **"Trend following strategies start to perform well right around the time mean reversion strategies falter."**

Opposite payoffs, opposite risk profiles. This is the foundation of Ch. 9's asset allocation.

---

## 6. Pairs trading — worked mean-reversion example

**Design decision that differs from most public scripts:** do **not** data-mine the whole universe for pairs. **Search within GICS sectors.** "Nothing resembles a utility stock more than another utility stock." Autocorrelation found by brute force across unrelated names breaks down.

### Pipeline

1. **Universe** — scrape S&P 500 constituents, normalize tickers (`.`→`-`), **filter to symbols actually present in ArcticDB** (index additions/deletions otherwise throw errors), group by sector.
2. **Cointegration** — pairwise Engle-Granger over a **3-year window**, per sector, **with the benchmark `^GSPC` prepended** to each sector list. p-value cutoff **0.05**. Cointegration ≠ correlation: it means the pair does **not diverge over time**.
   - Benchmark pairs are captured separately (`bm_pairs_list`) for market-hedged strategies. **Caveat: index relationships are notoriously unstable — retest periodically.**
3. **Result: 688 pairs from 501 stocks** — larger than the index itself, unmonitorable. Needs further reduction.

| Sector | #Stocks | #Pairs |
|---|---|---|
| Communication Services | 23 | 9 |
| Consumer Discretionary | 47 | 101 |
| Consumer Staples | 36 | 16 |
| Energy | 22 | 77 |
| Financials | 76 | 123 |
| Health Care | 60 | 109 |
| Industrials | 79 | 166 |
| Information Technology | 70 | 45 |
| Materials | 26 | 15 |
| Real Estate | 31 | 6 |
| Utilities | 31 | 21 |
| **Total** | **501** | **688** |

4. **Stationarity (ADF)** — for each pair compute **both** the OLS regression spread and the price ratio; run ADF on both; **accept if the average ADF p-value ≤ 0.05.** Reduces 688 → **~160 pairs**.
   - **Historical spread vs. price spread:** the historical spread assumes a constant relationship with a fixed coefficient and is what you test for stationarity; the price spread is the raw price difference.
5. **Z-scores** — `(spread − rolling mean) / rolling std` over `duration_list = range(20, 101, 20)` = **[20, 40, 60, 80, 100]** days, on both spread and ratio → 10 z-score frames. Snapshot the last row of each, transpose, concat → a **screening table** of every pair's current positioning across all 10 representations.
6. **Pick a boring pair.** *"If you trade for thrills, you are in the wrong business."* Sort Utilities by `adf_avg` ascending → **(CMS, PPL)** at 0.0031.

| pair | adf_spread | adf_ratio | adf_avg |
|---|---|---|---|
| (CMS, PPL) | 0.0000 | 0.2051 | **0.0031** |
| (DTE, DUK) | 0.0017 | 0.0158 | 0.0051 |
| (^GSPC, CEG) | 0.0001 | 0.8116 | 0.0100 |
| (CMS, DTE) | 0.0110 | 0.0132 | 0.0121 |

### The trading simulator

```python
# state machine on the z-score series
# flat  & z >  entry_threshold  → short (-1)
# flat  & z < -entry_threshold  → long  (+1)
# long  & z > -exit_threshold   → flat  (0)
# short & z <  exit_threshold   → flat  (0)
```

Positions shifted **+1 day** and forward-filled. Spread daily log returns × position → `cumsum()` → `np.exp() - 1`.

### Threshold optimization — and the headline result

Grid: **entry ∈ [1.7, 3.1] step 0.1** (14) × **exit ∈ [0.1, 1.6] step 0.1** (15) = 210 combinations × 6 z-score series = **1,260 strategies**. Metrics: final cumulative return, max drawdown (`cummax()` comparison), Sharpe = `mean/std × √252`. Pivot → seaborn heatmap (entry on y, exit on x).

> **Result: entering around 1.7σ and exiting below 1.2σ produces the highest Sharpe. When z-scores reach extremes (>2σ), Sharpe declines.**
>
> **Moral: arbitrage frequent small inefficiencies and close early.** Do not wait for extremes.

Top-10 vs. bottom-10 equity curves are plotted with the **x-axis constrained to the cointegration window** — never apply a relationship outside the period it was tested on. Tight clustering of the top curves vs. divergence in the bottom ones indicates parameter robustness.

### The honest overfitting discussion

The chart is **too optimistic for production**: no slippage, no transaction costs, no dividends received or paid, and **optimized on one pair**. The standard fix is out-of-sample testing across other pairs.

**But:** *"Overfitting may however be the right approach in the specific case of pairs trading."* The behavior being traded is **pair-specific**. There may be commonalities across pairs but no universality. **What must be stable is the relationship, not the parameters.**

Corollary rule: **stop losses do not work for mean reversion** — positions are entered near peak inefficiency and expected to overshoot before reverting. Therefore the **stationarity test is the risk control**. As soon as stationarity breaks, stop trading that pair. *"No one wants to be caught long MySpace and short Facebook, hoping for a reversion to the mean."*

---

## 7. Transferable rules

1. **Report gain expectancy first.** Sharpe, Sortino, and friends are meaningless until expectancy is positive.
2. **Compute all three formulas** (arithmetic, geometric, Kelly) from the same three inputs. Use **partial Kelly (⅓–½)** in production.
3. **Decompose every improvement into signal vs. money management.** Know which module you are working on.
4. **Track two durations**: long for "does it make money over time," short for cyclicality → exposure allocation.
5. **Win rate is not the target.** A 30% win rate with right skew beats a 99% win rate with left skew.
6. **Match the risk metric to the skew**: trend following → **profit factor / gain-to-pain**; mean reversion → **tail ratio**.
7. **Shift signals forward one bar.** Always. Signal today, trade tomorrow.
8. **Short only in sideways or bear regimes**, and enter when a **bear-market rally rolls over** — not on breakdowns.
9. **Design the exit before the entry.** Bad exits are unrecoverable.
10. **Search pairs within sectors**, not across the universe. Require cointegration *and* ADF stationarity on both spread and ratio.
11. **In mean reversion, stationarity is the stop loss.** When it breaks, stop trading the pair.
12. **Moderate z-score thresholds beat extremes.** Enter ~1.7σ, exit ~1.2σ.
13. **Constrain evaluation windows to the period the relationship was tested on.**

---

## 8. Cross-references

Ch. 1 gain expectancy introduced, false positives, over-filtering · Ch. 4 the composite `score_rel` consumed as the demo signal, ArcticDB retrieval · **Ch. 6 the money management module — position sizing, and Kelly implemented properly** · Ch. 7 the remaining signal-module refinements (5 of 7 deal with losses) · Ch. 8 the integrated toolbox · **Ch. 9 asset allocation across left- and right-skewed strategies — direct continuation of §5**.

**Named references:** Edward Thorp, *Beat the Dealer* / *Beat the Market* · J.L. Kelly Jr. · Daniel Bernoulli · Jack Schwager (gain-to-pain ratio, Market Wizards) · Jeremy Siegel (+7% long-run return) · Jesse Livermore · John Bogle (reversion to the mean) · LTCM as the high-win-rate counterexample.

**Libraries:** `pandas`, `numpy`, `arcticdb`, `statsmodels` (Engle-Granger cointegration, ADF), `seaborn` (heatmap), `matplotlib`.
