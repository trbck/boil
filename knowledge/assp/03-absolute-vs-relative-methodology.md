# Ch 3 — Long/Short Methodologies: Absolute and Relative

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 3.
**Governs:** the **data substrate** for the entire book. Every signal, regime, stop, and position size from Ch. 4 onward is computed on the series chosen here.
**Thesis:** "long strength, short weakness" is the right idea applied to the wrong dataset. Switching from absolute prices to **currency-adjusted relative prices** (price ÷ benchmark ÷ FX) expands the short universe from ~10–20% of the index to ~50%, strips benchmark correlation arithmetically, and turns the problem from *timing the market* into *tracking sector rotation*.

**This is the single most consequential architectural decision in the book.** Get it wrong and nothing downstream works.

---

## 1. Definitions

| Series | Definition |
|---|---|
| **Absolute** | The OHLC prices from any vendor, adjusted for dividends/splits/corporate actions |
| **Relative** | Absolute series ÷ benchmark close, **adjusted for currency** |

Relative series = **excess return over benchmark, in fund currency**. Dividing by the index arithmetically removes the benchmark's effect from the entire population. **Only two factors remain: currency impact and stock-specific performance.**

---

## 2. Why the absolute method fails — five documented defects

The absolute method ("buy what goes up, short what goes down") is intuitive and universally spoken, but the product does not do what it says on the tin.

**1. Ineffective at decreasing correlation with the benchmark.**
In a bull market, 80–90% of constituents sit in the bullish regime; the remaining 10–20% bearish names stand out and become **crowded shorts** — elevated borrow utilization, illiquid, volatile, expensive, squeeze-prone. Squeeze fear caps bet size → **atrophied short book**. Long books become overdeveloped → structurally high positive net exposure → "directional hedge funds." In bear markets, short ideas are plentiful but exposures rarely cross into negative territory: investors cushion the blow and still lose money.

**2. Ineffective at reducing volatility.**
Fewer short ideas → the short book must be supersized to balance exposures → diluted low-vol long book + a few concentrated structural shorts. Crowded shorts spike. **Short-side volatility drives the entire portfolio.** Underwhelming return ÷ high residual vol = unattractive risk-adjusted return.

**3. Little historical downside protection.**
In the GFC, net beta hovered around **+0.5** — residually bullish while talking a defense game. Practitioners reduced exposure by cutting longs and hoarding cash, not by shorting. Years of bull market had atrophied the short muscle.

**4. Lesser investment vehicle.**
Makes less than index funds in bull markets; only loses less in bear markets. After fees, compounds less than a plain-vanilla index fund, with less transparency and less liquidity.

**5. Laggard indicator.** ← *the mechanical core of the argument*

Stocks do not fall out of the sky. The decay sequence is:

```
lag immediate competitors
  → trail the industry
    → fall behind the sector
      → underperform the index
        → finally drop in absolute value
```

**The absolute series fires at the last step.** By the time a name appears on an absolute screen, most of the value is already gone.

---

## 3. The relative weakness method — the structural payoff

Indices are market-cap-weighted averages of their constituents ⇒ **roughly half of all names underperform at any time**, by arithmetic.

| Metric | Absolute series | Relative series |
|---|---|---|
| % of names in bull/bear regime | Swings **20% → 80%** with the market | Oscillates **~40–60%**, mean-reverting |
| Correlation with index | High | Low |
| Short universe | Rarefied crowded shorts | ~half the index |
| Need to time tops/bottoms | Critical | **Not critical anymore** |
| Borrow cost | Expensive, deteriorating | Near general collateral |
| Scalability | Poor (illiquid names) | Good (low concentration as AUM grows) |

> As breadth narrows, **underperformers can outnumber outperformers** — the exact opposite of the folk belief that short ideas are scarce. Megacap-driven markets mean most well-managed companies underperform.

### The mirror-image rule

Once you switch to relative series, **you must use the same prices and signals on both sides.** The long book must be a mirror image of the short book's strategy and series. Do not run absolute longs against relative shorts.

A long/short portfolio is then the net sum of two relative books: a classic mutual-fund-style long book of outperformers, plus a short book of underperformers benchmarked against the inverse of the index. Performance = **the spread**.

---

## 4. The relative series implementation

### Core transform

```python
def rel_fx(df, _o, _h, _l, _c, bm_df, bm, ccy_df, ccy, start, end,
           rebase=True, mult=1000):
    df[ccy] = ccy_df.loc[start:end, ccy].copy().ffill()
    df[bm]  = bm_df.loc[start:end, bm].copy().ffill()
    for i in [_o, _h, _l, _c]:
        df[f'r{i}'] = df[i].div(df[ccy])              # 1. to fund currency
        if rebase:                                     # 2. divide by benchmark
            df[f'r{i}'] = df[f'r{i}'].div(df[bm]).mul(
                df[df[bm].notna()].iloc[0, list(df.columns).index(bm)])
        else:
            df[f'r{i}'] = df[f'r{i}'].div(df[bm]) * mult
    return df
```

Three steps: **pull benchmark + FX → convert OHLC to fund currency → divide by benchmark.**
Note it transforms **all four OHLC legs**, not just the close — every downstream regime primitive (breakout, fractal, floor/ceiling) needs relative highs and lows.

### rebase=True vs rebase=False — a real design fork

| | `rebase=True` (anchor to first date) | `rebase=False` (constant multiplier) |
|---|---|---|
| Best for | A fixed start date for all calculations | Rolling windows (1/3/5 years), continuous series |
| **Pro** | System **builds memory** over time; deeper understanding of the journey | Lightweight — store/process only the window; **no historical restatement needed** on corporate actions |
| **Con** | Requires constant historical restatement; changing the start date invalidates prior work | System is **amnesiac by definition**; must be thoroughly tested before production |

Author's guidance: use `rebase=True` while developing, tweaking, and building confidence (long runway of memory); switch to rolling windows once the system is production-worthy and tested.

### Supporting utilities (recycled through the whole book)

- `batch_px_df(tickers_list, batch_size, start, end)` — batched yfinance download of `['Close']`; batching avoids errors on large pulls
- `dict_swap(dct)` — swap keys/values
- `df_from_dict(batch_size, dct, start, end)` — download from dict keys, rename columns to values, `tz_localize(None).ffill()`
- `rohlc(df, relative=False)` — instantiate `_o,_h,_l,_c` names with or without the `r` prefix
- `yf_droplevel(batch_download, ticker)` — flatten a multiindex download to a single-ticker df
- `returns_table(daily_log_returns, range_days)` — 1D/1W/1M/3M/6M/1Y/2Y/3Y/Max returns + a **range score** = `(cumsum.tail(1) − cumsum.min()) / (cumsum.max() − cumsum.min())`, i.e. where price sits in its window range, 0–1
- `heatmap(df, subset_cols, clrmap='RdYlGn')` — `style.background_gradient`, with a try/except fallback for the pre-3.13 `set_precision` API

### Returns computation idiom used throughout

```python
daily_log_returns = np.log(px/px.shift())
cumul = daily_log_returns.expanding().sum().apply(np.exp) - 1     # expanding(), not cumsum()
daily_rel = daily_log_returns.sub(daily_log_returns[bm], axis=0)  # relative = subtract bm log returns
```

**Use `expanding().sum()` rather than `cumsum()`** to tolerate missing values.

### Regime primitive used for the universe counts

252-day high/low breakout, forward-filled:

```python
bo = pd.DataFrame(
    np.where(df >= df.rolling(252).max(),  1,
    np.where(df <= df.rolling(252).min(), -1, np.nan)),
    index=df.index, columns=df.columns).ffill()
```

Prints a 252-day high → bullish (+1); a 252-day low → bearish (−1); regime persists until the opposite extreme prints.

---

## 5. Survivorship bias — and why it cuts in the short seller's favor

Scraping current S&P 500 constituents from Wikipedia gives no historical inclusions/deletions. Losers are deleted; the surviving set has a built-in bullish drift.

**Key asymmetry:** survivorship bias **hurts long backtests but does not invalidate short backtests.** "If we run backtests on surviving constituents, we benchmark our survival against the fittest issues." A short strategy that works on survivors will work better on the real, attrition-including universe.

---

## 6. Sector rotation — what the relative series is actually for

In the absolute method the objective is to time market tops and bottoms — futile. In the relative method the objective becomes **sector rotation**: buy nascent outperformers, short early underperformers.

- On absolute series, **all sectors are correlated with the index**. When everything moves together you cannot discriminate, so you add filters — and the default filter, valuation, is treacherous.
- **Valuation is regime-dependent, per sector.** Machinery stocks rise and fall on order books: when order books are empty and filling, PBR looks *expensive*; when full and declining, PBR looks *cheap*. **So you sell machinery when it looks cheap.** Retail correlates to YoY monthly sales change. There is no one-size-fits-all valuation rule — and tracking every sector's driver in absolute terms is near impossible.
- On relative series, **sectors decorrelate from the index**. You let the market do the heavy lifting: just track which sectors begin to out/underperform. No satellite imagery of parking lots required.

### Cyclicals vs. defensives, and the rotation indicator

- **Cyclicals** (emblematic: consumer discretionary, technology) expand and contract with the economy; risk appetite finances riskier businesses in good times.
- **Defensives** (emblematic: consumer staples, utilities) are impervious to recessions. **In relative terms they are inversely correlated with the market** — they fall less, so they outperform on the way down.

```
rotation = mean(cyclicals) − mean(defensives)        # computed on both abs and rel series
```

| | Absolute rotation indicator | **Relative rotation indicator** |
|---|---|---|
| Behavior | Took off *before* the GFC as a reverse indicator; bottoms **after** the index | Peaked 2007 (GFC onset); bottomed **early 2009, before** the market |
| Verdict | Lagging — "would have put any righteous market participant out of business" | Slightly leads or coincides with tops and bottoms |

**Two uses of the relative rotation indicator:**
1. Major peaks/troughs lead or coincide with market tops/bottoms.
2. **When it turns negative → adopt defensive positioning.**

*Mechanism:* defensives carry high dividend yields creating **dividend support** — a safety net where every dip attracts patient yield buyers, preventing abrupt descents. Cyclicals/growth have no such cushion and lead on the way down.

The author flags this indicator as promising but **not yet production grade**; it is revisited under Beta in Ch. 7.

Operational takeaway: **you can broadly keep the same stocks and just swap sides when the market turns.** Bull market leaders attract late-cycle momentum players — the weakest hands, no game plan, who bail at the first trouble, causing sudden performance disgorgement.

---

## 7. The other structural advantages

**Reduces borrow cost — and the callable-stock warning.**
Lending fees = f(supply from long holders, demand from shorts). Institutional holders liquidate on persistent underperformance, so supply shrinks exactly as demand rises. Lending desks then tap **callable stock** — short-term pools, the borrow of last resort.

> **Rule: whenever the only available inventory is expensive or callable, play the short squeeze as a quick LONG trade.** Callable inventory means every short is already positioned and every long holder has already lent. One recall triggers the scramble — that is the genesis of a squeeze.

Relative shorts, by contrast, sit in names with inertia where borrow is near general collateral. When bad news finally lands and absolute players arrive, **the relative short seller passes the baton** — moving on to cheap, easy-to-borrow names while the absolutists chew on expensive hard-to-borrow ones.

**Scalability.** 2007 taught quant funds the hard way that crowded issues have a hard capacity limit. Ample two-sided supply lets concentration stay low as AUM grows.

**Nonconfrontational.** Defensive-company management understands their stock should underperform in a bull market; tech founders know bear markets are not IPO season. Nobody takes offense at a relative call.

**Currency adjustment becomes an advantage.** For regional/global mandates, converting everything to fund currency relative to a global benchmark puts all stocks on one playing field — **no separate macro view, currency hedging, or FX risk layer needed**. Worked example: Japan soared while JPY devalued ~40%; JPY-denominated managers did well, USD-denominated managers holding *identical stocks* fared poorly. In the global autos example (Toyota, VW, Renault, Ford, Tesla, GM, Hyundai), Toyota clearly led in local currency and **sank once restated in USD**; Renault led, and Ford/GM/Hyundai emerged as short candidates.

> The cost: **everything must be adjusted** — entry, exit, and position sizing all computed in currency-adjusted relative prices. Vendor charts in absolute local currency "answer questions that relative market participants should never be asking themselves."

**Other participants cannot guess your levels.** Stops placed at relative, FX-adjusted levels are invisible to sniper algorithms that hunt round numbers and support/resistance. **Flipside: stops must be actively managed** — an order at a relative level cannot be filled by the exchange, so it must be translated and worked.

**Lead the market.** Entering a short on relative weakness is mildly painful for a while, but looks prescient to absolute observers (the Disney example: relative deterioration well before the absolute breakdown). Getting in early gives a **margin of safety** against bear-market rallies. It matters even more on the exit: volume thins as shorts get crowded, and the relative seller has ample time to cover while absolute short sellers double down and get caught by the recovery that starts imperceptibly, then stubbornly, then defiantly.

---

## 8. The triage workflow (heatmap → research → decision)

Heatmaps compress a returns table into a one-second visual judgment ("bypass the slow left brain"). But that is the *beginning* of research, not the end:

1. **Triage** — the heatmap tells you who belongs on which side.
2. **Fundamental research** — find out *why*; do fundamentals justify the performance?
3. **Investment decision** — if the research matches what the market is saying, pull the trigger. If not: abstain, or knowingly fight the tape.

> "The market is always right. Sometimes, we haven't figured out why just yet."

---

## 9. Transferable rules

1. **Compute everything on the relative, currency-adjusted series** — OHLC, not just close. This is the substrate; every downstream module assumes it.
2. **Never mix series across sides.** The long book must mirror the short book's series and signals.
3. Choose `rebase=True` for development (memory) and rolling/`rebase=False` for tested production (lightweight, corporate-action-proof). Know which one you are running.
4. **Use `expanding().sum()` over `cumsum()`** for cumulative log returns; compute relative returns by subtracting benchmark log returns.
5. **Survivorship bias in a short backtest is conservative**, not disqualifying — you are testing against the fittest survivors.
6. **Treat valuation as sector- and regime-conditional.** Cheap PBR in machinery is a sell signal, not a buy.
7. Track **sector rotation**, not market tops and bottoms. Use `cyclicals − defensives` on the relative series; negative → defensive posture.
8. **Expensive or callable-only borrow is a long signal, not a short signal.**
9. Enter shorts on relative weakness early — the margin of safety matters more at the exit than the entry.
10. Relative stop levels are invisible to hunting algorithms but **require active management** to be fillable.

---

## 10. Cross-references

Ch. 1 over-filtering and the wide-net principle · Ch. 2 borrow economics, squeeze conditions, non-confrontational framing · **Ch. 4 regime definition — consumes the relative series built here** · Ch. 5 the trading edge formula · Ch. 6 position sizing in relative terms · Ch. 7 beta, crowded shorts, dividend traps, and the return of the rotation indicator · Ch. 8 exposure management.

**Named references:** Howard Marks, *Mastering the Market Cycle* · GICS sector taxonomy · yfinance / pandas `read_html` for constituent scraping.

**Libraries:** `yfinance`, `pandas`, `numpy`, `matplotlib`, `requests`, `pathlib`, `datetime`, `dateutil.relativedelta`, `io.StringIO`.
