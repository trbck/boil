# Ch 4 — Regime Definition

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 4.
**Governs:** the triage layer — which side of the book a name belongs on, computed on both absolute and relative series.
**Thesis:** regime is **triage, not prediction**. The purpose is not to forecast where a stock is headed but to allocate limited research resources by actively listening to what the market already said. No single method wins; a **weighted blend of eight methods** is more robust than any one of them.

**The chapter's technical centerpiece is fractals** — a parameter-free, scale-invariant swing detector that folds across timeframes and asset classes, from which the floor-and-ceiling and higher-highs regimes are derived.

---

## 1. Why regime definition matters for shorts specifically

> "The difference between a short selling guru and the dreaded tap on the shoulder is 6 months. Short internet stocks in 1999 and you'll be teaching math to bored university students in 2000. Short the same stocks in late January 2000 and a new short selling star is born."

Regime definition is the antidote to the fundamental short seller's chronic disease: **arriving too early**.

It also fixes a common incoherence: trading **trends on the long side** (ride outperformers) while trading **mean reversion on the short side** (expecting expensive stocks to revert). That is two contradictory models in one book. Regime definition imposes one symmetric model on both sides.

---

## 2. The six methods

All operate on both absolute and relative OHLC. Regime output is `+1` bull / `−1` bear (or `0` neutral).

### 2.1 Breakout / breakdown — oldest and simplest

```python
def regime_breakout(df, _h, _l, n):
    hl = np.where(df[_h] == df[_h].rolling(n).max(),  1,
         np.where(df[_l] == df[_l].rolling(n).min(), -1, np.nan))
    return pd.Series(index=df.index, data=hl).ffill()
```

New n-period high → bullish; new n-period low → bearish; `ffill()` propagates until the opposite extreme. Popular n: **252, 100, 50**. Book default `bo_list = [20, 50, 100]`.

- **Works best** breaking out of consolidation/sideways markets — "pent-up energy released along the line of least resistance."
- **Pro:** computational simplicity, stability.
- **Con:** built-in lag from the lookback (politely called *confirmation*), and giving back large profits.
- **Fix offered:** re-introduce a **partial time exit** — halve size for positions that have failed to make new highs/lows after half the duration. *"Stocks late on their rent should either be reduced or kicked out."*

### 2.2 Simplified Turtle — asymmetric durations

```python
def turtle_trader(df, _h, _l, st, lt):
    _lt = regime_breakout(df, _h, _l, lt)   # slow: direction
    _st = regime_breakout(df, _h, _l, st)   # fast: trailing stop
    return pd.Series(index=df.index,
        data=np.where(_lt ==  1, np.where(_st ==  1,  1, 0),
             np.where(_lt == -1, np.where(_st == -1, -1, 0), 0)))
```

Slow duration gives direction, fast duration is the stop loss; **mismatch → neutral (0)**. Principle: *deliberate to confirm trends, quick and decisive to cut losses.* Original Turtles: enter on 50-day highs, exit on 20-day lows.

- **Con:** elevated trading frequency, transaction costs, turnover; poor in sideways/choppy markets.
- The author explicitly flags it as **educational only — "do not do this at home"**: realistic enough to teach, too simplistic for real money. It is nonetheless recycled as the demo strategy for the rest of the book.

### 2.3 Moving average crossover

```python
def regime_sma(df, _c, st, lt):
    sma_st = df[_c].rolling(st).mean()
    sma_lt = df[_c].rolling(lt).mean()
    return np.sign(sma_st - sma_lt)

def regime_ema(df, _c, st, lt):
    ema_st = df[_c].ewm(span=st, min_periods=st).mean()
    ema_lt = df[_c].ewm(span=lt, min_periods=lt).mean()
    return np.sign(ema_st - ema_lt)
```

Regime = `sign(fast − slow)`. Simple, universal, computationally cheap. The book's warning elsewhere: **"nothing is more costly than flip-flopping around a moving average."**

### 2.4 Fractals — the core primitive

Mandelbrot-derived. **A fractal low is a low surrounded by two higher lows; a fractal high is a high surrounded by two lower highs.** In TA vocabulary: swings. Swings alternate — a fractal high follows a fractal low.

```python
def avg_px(df, _h, _l, _c):
    return df[[_h, _l, _c]].mean(axis=1)

def fractal(px, lvl):
    max_lvl = np.minimum(2, lvl)
    return px[(px <= px.shift(-1)) & (px < px.shift(+1)) &
              (px <= px.shift(-max_lvl)) & (px < px.shift(+max_lvl))]
```

**Critical design decision — the input series.** A bar can print a local high and a local low simultaneously, but the market cannot print a fractal high and a fractal low at once. Two candidate inputs were tested:

- `Close` only → the highest/lowest Close does not coincide with the true local High/Low; fractals land a few bars away from the real turn.
- **`mean(High, Low, Close)` → adopted by convention.** Rationale: *"Markets may err on the way up and down during a session, but where it chooses to end gives us a clue as to how things are going next."*

**Recursion — levels of abstraction:**

```
_h,_l,_c  →  Hi1, Lo1      (level 1: from price; very noisy)
Hi1, Lo1  →  Hi2, Lo2      (level 2: noise filtered — swing trading)
Hi2, Lo2  →  Hi3, Lo3      (level 3: regime changes — trend following)
Hi3, Lo3  →  Hi4, Lo4      (level 4: structural long-term trends)
```

Interpretation on daily bars: L1 = indecision / short-term supply-demand · L2 = minor trend inflections · L3 = regime changes · L4 = structural trends.

**Three properties that make fractals the book's preferred primitive:**

1. **Work across timeframes** — same algorithm on 1-minute and weekly bars.
2. **Work across asset classes** — treasuries, equities, crypto, electricity load, real estate.
3. **No parameterization.** Unlike RSI(14) or MACD(12,26), whose parameters do not translate across timeframes or markets. What fractals return instead of parameters is **levels of abstraction**.

**Four functions:**

| Function | Purpose |
|---|---|
| `avg_px(df, _h, _l, _c)` | HLC average — the single series fractals are computed on |
| `fractal(px, lvl)` | Identify fractals at one level |
| `fractals_df(df, col, col_name)` | Swing highs/lows at **all** levels — iterates while `hilo_df` length > 3, separates lows from highs by negating the high series, forward-fills the hilo columns |
| `fractals_dates(df, col, col_name)` | **When** each level's fractal was discovered |

**`fractals_dates` — the Matryoshka problem.** A level-5 fractal requires 3 level-4s, each requiring 3 level-3s, down to the price bar that triggered level 1. Rather than looping bar by bar, the function **slices and reduces** the dataframe level by level. Shift convention: `shift(s)` with **s=1 at level 1** (the bar after the peak/trough) and **s=3 for every subsequent level**. This is why levels 3, 4, 5 are discovered *months later*.

Two output suffixes:
- `'_chg'` — the **price** at the time the fractal was discovered
- `'_fc'` — the **fractal price** at the time it was discovered

**Fractals alone do not confer regime.** They are just swings. Combinations of swings define regime — the next two methods.

### 2.5 Higher highs, higher lows

Uptrend = higher highs *and* higher lows; downtrend = lower lows *and* lower highs.

```python
def higherhighs_df(df, _c, col_name, shft=2):
    v = 1
    while (f'{col_name}Lo{v}' in df.columns) & (f'{col_name}Hi{v}' in df.columns):
        lh = pd.DataFrame()
        hl  = f'{col_name}HiLo{v}_hl'
        lhv = f'{col_name}LoHi{v}'
        lh[lhv] = df[f'{col_name}Lo{v}'].sub(df[f'{col_name}Hi{v}'], fill_value=0).dropna()
        # bearish: lower low then lower high
        lh.loc[(np.sign(lh[lhv]) < 0) & (np.sign(lh[lhv]*lh[lhv].shift()) < 0)
               & (-lh[lhv] < -lh[lhv].shift(2)) & (lh[lhv].shift(1) < lh[lhv].shift(3)),
               hl] = -lh[lhv].shift(shft)
        # bullish: higher high then higher low
        lh.loc[(np.sign(lh[lhv]) > 0) & (np.sign(lh[lhv]*lh[lhv].shift()) < 0)
               & (lh[lhv] > lh[lhv].shift(2)) & (-lh[lhv].shift(1) > -lh[lhv].shift(3)),
               hl] =  lh[lhv].shift(shft)
        df[hl] = lh[hl].reindex(df.index).ffill()
        df[f'{col_name}HiLo_HH{v}'] = np.sign(df[_c].sub(df[hl], fill_value=0))
        v += 1
    return df.loc[:, ~df.columns.duplicated(keep='last')]
```

**Requires three conditions met sequentially** (lower low, then lower high, in that order) — which only works in orderly markets. Three noise-handling decisions, each an explicit trade-off:

1. **Interrupted pattern** (higher high + lower low): options are drop to neutral, or do nothing. **Choice: keep the regime as-is until the opposite side's pattern appears.**
2. **Which high to trail?** Closest, prior, or the highest high. Too tight → noisy; too loose → irrelevant.
3. **False positives** when price pierces a lower high / higher low — temporary noise or early regime change. **Default: `shft=2`, the penultimate swing** — more stability.

> "There is no solution, only trade-offs. Tighter stops = higher transaction costs. Looser rules = giving back more profit."

**Advantage: counter-trend entries and objectively defined stops.** Long: buy on a low, exit on a high, stop at the higher low. Short: sell on a high, exit on a low, **stop at the lower high**.

**Known weakness:** lag at high abstraction levels. In the Nissan example, levels 2 and 3 had turned bearish while level 4 stayed bullish deep into the bear phase. **Fix: weight lower levels more heavily in the blend.**

### 2.6 Floor and ceiling — the author's preferred method

A variation on higher-highs that focuses **exclusively on the right shoulder** of a head-and-shoulders. There would be no head without a left shoulder, so only the right one carries information.

**Only ONE condition is needed for a regime change** (vs. three sequential conditions for higher-highs):

- **Bearish:** a swing high lower than the peak.
- **Bullish:** a swing low higher than the bottom.

These are **necessary and sufficient**, valid across every timeframe and asset class.

**Two exception-handling modes:**

| | **Conservative** — anchor on floors/ceilings | **Aggressive** — anchor on the *discovery swing* |
|---|---|---|
| Bear → bull | price crosses over the **ceiling** | price crosses over the **discovery swing high** |
| Bull → bear | price crosses under the **floor** | price crosses under the **discovery swing low** |

**Only two regimes: bull or bear.** A sideways market is a *pause within* a broader bull or bear context, never its own state. This is deliberate: **stability lets you manage positions instead of flip-flopping.**

```python
def floorceiling_df(df, _c, col_name):
    rg_FC_dict = {}; v = 2
    while f'{col_name}HiLo{v}' in df.columns:
        if f'{col_name}HiLo{v}_chg' in df.columns:      # 1. price at discovery (most lag → most nervous)
            base = df[f'{col_name}HiLo{v}_chg']
        elif f'{col_name}HiLo{v}_fc' in df.columns:      # 2. floor/ceiling price at discovery
            base = df[f'{col_name}HiLo{v}_fc']
        else:                                            # 3. PRODUCTION DEFAULT: fractal price
            base = df[f'{col_name}HiLo{v}']
        rg_FC_dict[f'{col_name}HiLo_FC{v}'] = np.sign(df[_c].rolling(2).mean().sub(base, fill_value=0))
        v += 1
    df = pd.concat([df, pd.DataFrame(rg_FC_dict)], axis=1)
    return df.loc[:, ~df.columns.duplicated(keep='last')]
```

Regime = `sign( rolling-2-mean(Close) − baseline )`. The three-tier baseline fallback is the important part:

- **`_chg`** (price at discovery) sits closest to current Close → **most nervous regime, most stops.** Deliberately models trading with imperfect information under stress.
- **`_fc`** (fractal price at discovery) — middle ground.
- **fractal price** — the **production default with continuous real-time prices**. Logic: recompute fractals on every new bar; if price penetrates the fractal, it was never a valid swing to begin with.

> Trade-off named explicitly: the natural stop (`_chg`) induces a lot of stops; defaulting to fractal price in production means **smaller position sizes and reduced risk appetite**.

---

## 3. The composite score — "no one signal to rule them all"

A deliberate reversal from the first edition, which crowned floor-and-ceiling the winner. Second-edition position: **signals are like French wines — Châteauneuf-du-Pape blends 13 varietals.** A simple average of methods beats any single method.

> "The strength of the signal increases as more methods turn either bullish or bearish. Conversely, it weakens as the methods disagree." — Surowiecki's wisdom of crowds.

**Two-step blend.**

```python
def dict_fractal(col_name, rg_method, fractal_dict):
    """col_name: 'abs'|'rel'; rg_method: 'HiLo_FC'|'HiLo_HH'; fractal_dict: {1:0.1, 2:0.4, 3:0.3, 4:0.2}"""
    return {f'{col_name}{rg_method}{v}': fractal_dict[v] for v in fractal_dict}

def rg_dict_blend(df, rg_dict):
    blend = np.zeros(len(df)); n = 0
    for rg in rg_dict:
        if rg in df.columns:
            if rg_dict[rg] > 0:
                blend += df[rg] * rg_dict[rg]; n += rg_dict[rg]
            else:
                blend += df[rg]; n += 1
    return round(blend / max(n, 1), 2)
```

**Step 1 — blend fractal levels within a method.** `fractal_dict = {1: 0.1, 2: 0.4, 3: 0.3, 4: 0.2}` — note level 2 carries the most weight, level 1 the least (noisiest).

**Step 2 — blend the eight methods, per series:**

```python
rg_cols_dict = {
    f'{col_name}BO{st}'      : 0.1,    # breakout 20
    f'{col_name}BO{lt}'      : 0.2,    # breakout 50
    f'{col_name}BO{xlt}'     : 0.1,    # breakout 100
    f'{col_name}TT{st}/{lt}' : 0.2,    # turtle
    f'{col_name}SMA{st}/{lt}': 0.2,
    f'{col_name}EMA{st}/{lt}': 0.2,
    f'{col_name}HiLo_HH'     : 0.25,   # higher highs (already level-blended)
    f'{col_name}HiLo_FC'     : 0.25,   # floor & ceiling (already level-blended)
}
df['score_abs'] = rg_dict_blend(df, score_abs_dict)
df['score_rel'] = rg_dict_blend(df, score_rel_dict)
df['score']     = rg_dict_blend(df, {**score_abs_dict, **score_rel_dict})   # composite
```

Three scores result: **`score_abs`** (intrinsic moves), **`score_rel`** (benchmark-adjusted), **`score`** (holistic). Output range roughly −1 to +1, continuous.

> Honest caveat from the author: *"We assigned random weights and semi-random durations… Still, the weighted average comes back with something half decent."* The robustness comes from averaging, not from tuned weights.

**Forward pointer:** *"Multiply this score by a position sizing algorithm and you have strength-adjusted position sizing in real time."* → Ch. 6/8.

The chapter also suggests going further: include **counter-trend / mean-reverting signals** to capture euphoria and depression.

---

## 4. The universe pipeline

Complete per-ticker loop, applied identically to the autos universe and the full S&P 500:

```python
fractal_dict = {1: 0.1, 2: 0.4, 3: 0.3, 4: 0.2}
df_dict = {}; last_row_list = []

for ticker in tickers_list:
    raw_df = yf_droplevel(multiIndex_raw_data, ticker)
    _o,_h,_l,_c = rohlc(raw_df, relative=False)
    df = rel_fx(raw_df, _o,_h,_l,_c, bm_df, bm, ccy_df,
                tickers_fx_dict[ticker], start, end, rebase=True, mult=1)

    for rel in rel_list:                       # [True, False] — relative FIRST
        _o,_h,_l,_c = rohlc(df, rel)
        col_name = col_name_abs_rel(rel, name_abs='abs', name_rel='rel')

        for slt in sorted(bo_list):            # [20, 50, 100]
            df[f'{col_name}BO{slt}'] = regime_breakout(df, _h, _l, slt)
        df[f'{col_name}TT{st}/{lt}']  = turtle_trader(df, _h, _l, st, lt)
        df[f'{col_name}SMA{st}/{lt}'] = regime_sma(df, _c, st, lt)
        df[f'{col_name}EMA{st}/{lt}'] = regime_ema(df, _c, st, lt)

        col = f'avg_{col_name}'
        df[col] = avg_px(df, _h, _l, _c)
        df = fractals_df(df, col, col_name)
        df = fractals_dates(df, col, col_name)
        df = floorceiling_df(df, _c, col_name)
        df[f'{col_name}HiLo_FC'] = rg_dict_blend(df, dict_fractal(col_name, 'HiLo_FC', fractal_dict))
        df = higherhighs_df(df, _c, col_name, shft=2)
        df[f'{col_name}HiLo_HH'] = rg_dict_blend(df, dict_fractal(col_name, 'HiLo_HH', fractal_dict))

    df['score_abs'] = rg_dict_blend(df, score_abs_dict)
    df['score_rel'] = rg_dict_blend(df, score_rel_dict)
    df['score']     = rg_dict_blend(df, score_dict)
    df = round(df, 2)

    library.write(ticker, df)                                    # ArcticDB
    last_row_list.append(last_row_cols_dict(df, ticker, df.columns))   # snapshot
    df_dict.update({ticker: df.copy()})

multiIndex_df = multiindex_from_dict(df_dict, yf_format=False).round(2)
```

**Runtime: < 3 minutes for 500+ securities × 10+ years of daily data**, including fractals *and* discovery dates.

Chapter settings:
```python
batch_size = 51; start = '2015-01-01'; end = None
bm_ticker = 'SP500'; ccy = 'local'
st, lt, xlt = 20, 50, 100; bo_list = [st, lt, xlt]; sma_list = [lt, st]; n = 30
rel_list = [True, False]                 # relative processed first
score_list = ['score', 'score_rel', 'score_abs']
```

### Triage output

`last_row_cols_dict()` produces a per-ticker snapshot of the latest non-null values (with a date column when the last row is null). Collected into a scoreboard sorted by composite score:

| ticker | score | score_rel | score_abs |
|---|---|---|---|
| RNO.PA | −0.90 | −0.92 | −0.88 |
| VOW3.DE | −0.82 | −0.88 | −0.75 |
| 7201.T | −0.53 | −0.58 | −0.48 |
| 005380.KS | −0.07 | 0.41 | −0.55 |
| 7203.T | −0.07 | 0.55 | −0.68 |
| F | 0.72 | 0.62 | 0.82 |

`pd.concat([top_3, worst_3])` gives the working list. Note how `score_rel` and `score_abs` **diverge** for Toyota and Hyundai — the composite hides a genuine disagreement between absolute and relative regimes, worth inspecting.

> **"Fundamental short selling starts where algorithmic short selling ends."** The quantitative triage is done; the detective work begins. The job is to understand *why* the market fails to reward Renault and Volkswagen.

### Sector rotation at index scale

Pull `score_rel` for every S&P 500 ticker from ArcticDB → average by sector → join to the benchmark with an **`inner` join pegged to the benchmark** ("much easier to harmonize around the index than to let any component dictate the index"). This is the production-grade version of Ch. 3's rotation chart.

---

## 5. ArcticDB

Man Group's quant-designed columnar store; open source since 2023, fast, simple. **Known limitation: does not work on Apple M-series processors.**

- `initialise_adb_library_local()` — connects via local LMDB, creates the library if missing.
- Storage layout is `{ticker: df}`. **To pull one field across the whole DB you must query ticker by ticker:**

```python
def adb_concat_single_column(library, symbols, column_name):
    symbols_list = [s for s in symbols if s in library.list_symbols()]
    return pd.concat(
        [library.read(s, columns=[column_name]).data.rename(columns={column_name: s})
         for s in symbols_list], axis=1)
```

Two parallel stores are maintained: ArcticDB (`{ticker: df}`) and an in-memory multiindex df. `multiindex_from_dict(df_dict, yf_format=False)` gives ticker at level 0 (easy single-security access); `yf_format=True` reorders to yfinance's layout (easy single-field-across-population access).

**Data source note:** Wikipedia scraping carries survivorship bias. For survivorship-adjusted data the book recommends **norgatedata.com**; for long-history 1-minute data, **eodhd.com** (30 years, entire S&P 500) — "what Bloomberg is to institutions." Free 1-minute sample data: **oneminutedata.com**.

---

## 6. Fractals in production

`fractals_df` is a **snapshot at bar t — no history, no memory.** `fractals_dates` reconstructs discovery times from history but **is irrelevant in production**.

**The production pattern is dramatically simpler:**

1. Run `fractals_df` on the refreshed data.
2. Compute the composite score.
3. **Compare the new last row to the previous one.** If it changed, a fractal was discovered.

```python
last_row_cols_dict(df, ticker, df_cols=list(df.columns))
```

This recaptures all fractals and regime changes and is "the fastest and most accurate method" in production. It matters most for **high abstraction levels (3, 4+), which are discovered long after they occur** and are otherwise hard to detect.

Collating per-bar snapshots into a `continuous_df` turns discrete fractal dots into **continuous lines** — which is how the production charts are drawn.

---

## 7. Multi-timeframe folding — the 20-year result

**Conjecture:** fractals at a fast timeframe fold into slower durations. A level-1 fractal on a 5-minute bar leads to a level 5/6/7 that is the equivalent of a level-3 daily fractal.

**Method:** 1-minute SPY data (2009–2024), resampled across 13 intervals with a single `resample_ohlcv` function:

```python
ohlcv_dict = {'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}
ohlcv_dict.update({c: 'mean' for c in remaining_indicator_columns})
interval_list = ['1min','2min','3min','4min','5min','10min','15min','20min','30min','1h','4h','1d','1W']
```

Then compute avg_px → fractals → floor-and-ceiling → higher-highs for **every** interval, with weights `{t: round(t*0.1, 1) for t in range(1, 16)}`.

**Result — confirmed.** 5-minute levels 5 and 6 look like daily levels 3 and 4, **discovered on the same day at the same price.** The 5-minute chart at levels 4–6 is visually near-identical to the daily chart at levels 2–4. There is **integrity along the time continuum**: 5-minute charts fold neatly into 15m, 30m, 1h, 4h, and daily.

The bar that triggered the bear avalanche is findable.

> The closing provocation: if you trade the same strategy with the same parameters on the same instrument across timeframes, **what asset class are you trading? TIME.**

---

## 8. Transferable rules

1. **Regime is triage, not forecasting.** Its job is to allocate research effort, not to predict.
2. **Use the same regime model on both sides.** Trend-following longs plus mean-reverting shorts is two contradictory models.
3. **Compute fractals on `mean(H, L, C)`, never on Close alone.** Close-based fractals land several bars off the true turn.
4. **Prefer parameter-free primitives.** Fractals port across timeframes and asset classes; RSI(14) and MACD(12,26) do not.
5. **Blend methods; do not crown one.** A weighted average of eight regime methods beats the best single one. Robustness comes from averaging, not from tuning weights.
6. **Weight lower fractal levels more heavily** (`{1:0.1, 2:0.4, 3:0.3, 4:0.2}`) — high levels lag badly at regime turns.
7. **Floor and ceiling only needs one condition** (a lower high, or a higher low) vs. three sequential conditions for higher-highs. It is more stable and it is the method of choice.
8. **Only two regimes.** Sideways is a pause inside a bull or bear context. Stability beats responsiveness for position management.
9. **In production, detect fractals by diffing the last row**, not by recomputing history.
10. **Choose your floor/ceiling baseline consciously**: `_chg` = nervous with many stops; fractal price = the production default with smaller sizes and lower risk appetite.
11. **The composite score is a sizing input**, not just a filter — multiply it into the position sizing algorithm for strength-adjusted sizing.
12. **Long-lookback breakouts need a time exit.** Halve size when a position has not made new extremes after half the duration.

---

## 9. Cross-references

Ch. 3 relative series (`rel_fx`, `rohlc`, `col_name_abs_rel`) consumed directly here · Ch. 3 sector rotation, upgraded here to ArcticDB scale · **Ch. 5 turns these signals into a measurable trading edge** · Ch. 6 position sizing (where `score` becomes a size multiplier) · Ch. 7 universe refinement · Ch. 8 the integrated portfolio engine.

**Named references:** Benoit Mandelbrot (fractals) · Richard Dennis / Turtle Traders · James Surowiecki, *The Wisdom of Crowds*.

**Libraries:** `pandas`, `numpy`, `yfinance`, `matplotlib`, **`mplfinance` (mpf)** for multi-panel charts, **`arcticdb`** (LMDB local storage).

**Charting helpers:** `mpf_score` (fill by regime sign), `mpf_relative` (relative Close as a line — treated as an indicator, not OHLC bars), `mpf_fill` (four-way fill: bull_profit / bull_loss / bear_profit / bear_loss), `mpf_fractals` (triangle markers whose size and opacity scale with abstraction level).
