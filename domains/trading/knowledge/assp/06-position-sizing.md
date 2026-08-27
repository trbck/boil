# Ch 6 — Position Sizing: Money Is Made in the Money Management Module

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 6.
**Governs:** the money management module of the trading edge — average win and average loss. In practice, the equity curve.
**Thesis:** with identical signals, identical universe, and identical starting capital, **position sizing alone** produces radically different equity curves, drawdowns, and exposures. It is the primary determinant of long-term geometric return, and it is the articulation point between **financial capital and emotional capital**.

**Founding observation:** across the portfolios of managers at the same mutual fund, holdings overlapped heavily but performance and tracking error diverged widely. **Stock picking was not the driver. Position sizing was.**

**Why this bites shorts harder:** longs expand as they work — one Apple redeems a basket of rotten apples, so a bad sizing algorithm survives. **Short sellers have no logarithmic price declines to bail them out.**

---

## ⚠ Deliberate lookahead bias in this chapter's code

The chapter **knowingly retains lookahead bias in two places** and says so explicitly. Rationale: the signals were never optimized (Ch. 4 used arbitrary weights and durations), so honest returns would be underwhelming, and attention would drift to *"let's improve the signal"* instead of *"how does sizing change the equity curve?"*

**Where it lives, and how to remove it:**

1. **Signal alignment** — a `look_ahead` boolean. When `False`, `score_rel` is shifted **+1 day**.
2. **P&L timing** — inside `simulate_position_sizing`, the daily P&L is computed **after** the position update on the same bar. Correct order: **compute daily P&L on the existing position first, then adjust size**. In practice: process today's data, compare to yesterday's position, trade tomorrow.

If you lift this code, fix both. Returns will drop substantially.

---

## 1. The four horsemen of apocalyptic position sizing

### Horseman 1 — Liquidity is the currency of bear markets

> *"You can check out anytime you want, but you can never leave."*

**If you can't exit without damaging market impact, you don't own the position — it owns you.** When redemptions start, managers liquidate **what they can**, not what they want, leaving illiquid debris that perpetuates the cycle.

2007 mechanism, worth encoding as a scenario: multi-strategy funds couldn't liquidate CDOs/CDS → forced to sell equities to meet margin → equity drop → lower portfolio marks → more margin calls. **A liquidity crisis in one market contaminates the others.**

**Capacity test — the practical one:** *"Capacity sets in when inertia creeps in"* (June-Yon Kim). **If you find yourself passing up signals because of market impact, and it feels like the right call — either you are lazy or your asset size is too big.** Either way, it's a wake-up call.

### Horseman 2 — Averaging down

> *"Losers average losers."* — Paul Tudor Jones

Adding to a loser **worsens three of the four trading-edge variables**:

| Variable | Effect |
|---|---|
| Loss rate | ↑ worse |
| Average loss | ↑ worse |
| Win rate | ↓ worse |
| Average win | unaffected (and nobody controls it anyway) |

Worse, the added capital must come from somewhere: fresh cash, or **profitable positions cut short**. Net effect: **"cut your winners, run your losers"** — the exact inverse of the rule.

It is a **martingale**. Three fatal properties: it ignores the theory of runs (independent trials produce 8–10 consecutive losses); it presupposes infinite capital; and **the best possible outcome is breakeven** — everything short of that carries **certainty of ruin**.

Why it persists: **anchoring bias** (Thorp, *A Man for All Markets*). Judgment stays colored by entry cost — "cheap at $10, a bargain at $9." And emotionally: a small bet is low-stress; the second tranche jumps you to the high-roller table, where **the need to be right supersedes the obligation to be profitable.** *Market wizards are synthetically long math and short ego; martingale players are short math and long ego.*

### Horseman 3 — High conviction

Practiced by both the worst **and** the best investors. The difference:

- **Worst:** develop a thesis, broadcast it, size big because it feels good. **T-stat does not confer mental robustness.** Big bets destroy impartiality; the ego craves validation. *Obvious trades that feel good are rarely the most profitable.*
- **Best:** **express conviction in units of risk.** Develop the thesis → **quantify the risk first** → size accordingly. Soros is remembered for the pound trade; less known is that he made traders' bonuses by **cutting losses** during the LTCM debacle.

### Horseman 4 — Equal weight

> *"Portfolio management is not an exercise in democracy."*

Equal weight will not cause ruin, but it prevents you from reaching your objectives. **Not all stocks have the same beta.** Sleepy utilities have a different volatility signature from racy internet names. **By ignoring beta at the position level, volatility resurfaces at the portfolio level** — the volatile names drive total portfolio vol, and investors react to vol.

> *"If you give equal rights to your ideas, this will come with equal lefts to your equity curve."*

---

## 2. The Haghani coin-flip experiment — why sizing is emotional

Victor Haghani (Elm Capital, ex-LTCM). 61 participants — finance students and investment professionals. $25 starting capital, 30 minutes, coin **biased 60% to heads**, bet any amount either way.

| Result | Value |
|---|---|
| Hit the maximum cap | **21%** |
| **Went bust** — with 60% odds in their favor | **28%** |
| Had ever heard of the Kelly criterion | **5 of 61** |

Optimal play on $25 returns north of $3 million after 300 flips. So why doesn't everyone get rich? **Losing streaks.** Coin tosses have no memory. **After 5 consecutive losses only a third of capital remains** — and at some point the brain says stop, regardless of what the math says.

**Four lessons:**

1. Only 5 of 61 knew Kelly. *"Teaching something like the Efficient Market Hypothesis is like teaching Hippocratic body humors to medical students long after penicillin."*
2. **Position size determines the long-term geometric return of any strategy. Bet too small and you don't have a business. Bet too big and you lose your business.**
3. Kelly / optimal-f may maximize geometric return, but that does not mean use it unconditionally. *"Formula 1 cars are the fastest vehicles, but they are not made to fetch milk at the local grocery store."* → **fractional Kelly.**
4. **Financial capital is a complicated problem with an optimal solution. Emotional capital is not — break it and it's game over. In practice, psychology supersedes mathematics.**

Play it: https://elmwealth.com/sizing-games/

---

## 3. The universal structure of every position sizing algorithm

> **Every position sizing algorithm reduces to two variables: (a) how much NAV to allocate, and (b) what denominator to divide it by to get share count.**

Worked example on $1,000,000 with a 2% budget = **$20,000 allocation**:

| Method | Denominator | Shares |
|---|---|---|
| **Fixed %** (no margin) | price = $10 | 20,000 / 10 = **2,000** |
| **Fixed risk** (margin) | stop distance = 10% = $1 | 20,000 / 1 = **20,000** |
| **Volatility** | 2 × ATR = $0.75 | 20,000 / 0.75 = 28,571 → **28,500** (round down) |

**Always round down to the lot multiple. Err on the conservative side of less risk.**

### Primitives

```python
def size_limit(nav_pct, limit_pct):
    return nav_pct.clip(-limit_pct, limit_pct)

def nav_allocation(nav, nav_pct):
    return nav * nav_pct

def nav_signal(nav_pct, nav, signal):
    return np.nan_to_num(np.multiply(nav_pct, np.multiply(nav, signal)))

def shares_target(target_mv, fraction):
    if pd.isna(fraction) or fraction == 0: return 0
    shares = target_mv / fraction
    if math.isinf(shares) or pd.isna(shares): return 0
    return shares

def round_lot(raw_shares, lot_size):
    return math.floor(abs(raw_shares) / lot_size) * lot_size * np.sign(raw_shares)

def trading_value(round_lots, price):            return round_lots * price
def trading_value_local(round_lots, price, fx):  return round_lots * price * fx

def calculate_drawdown(nav_series):
    peak = nav_series.cummax()
    return (nav_series - peak) / peak
```

Note `round_lot` **floors the absolute value then reapplies the sign** — correct behavior for shorts, where naive flooring of a negative would round *up* in size.

### The simulation engine

```python
def simulate_position_sizing(start_K, lot_size, com_rate, pct, look_ahead,
                             fraction_type, constant=None, ratio='_2std'):
    nav = start_K; cash_balance = start_K
    position_dict = {t: 0 for t in tickers_list}
    nav_list, long_mv_list, short_mv_list = [], [], []

    for t in data.index[2:]:
        daily_pl_sum = 0; long_mv = 0; short_mv = 0
        for ticker in tickers_list:
            price_fx      = data.at[t, f'{ticker}_fx']
            price_fx_prev = data[f'{ticker}_fx'].shift(1).at[t]
            signal        = data.at[t, f'{ticker}_signal']

            # --- the denominator switch -------------------------------
            if   fraction_type == 1: fraction = price_fx                                  # fixed %
            elif fraction_type == 2: fraction = price_fx * constant                       # fixed risk
            elif fraction_type == 3: fraction = price_fx * data.at[t, f'{ticker}{ratio}'] # vol as %
            elif fraction_type == 4: fraction = data.at[t, f'{ticker}{ratio}']            # vol in price units
            else:                    fraction = price_fx

            target_mv = nav_signal(pct, nav, signal)
            shares    = shares_target(target_mv, fraction)

            if not look_ahead:                      # ← CORRECT placement
                daily_pl = position_dict[ticker] * (price_fx - price_fx_prev)
                daily_pl_sum += daily_pl

            theoretical_lots = round_lot(shares, lot_size)
            round_lots       = theoretical_lots - position_dict[ticker]   # trade the DIFFERENCE
            trade_value      = trading_value(round_lots, price_fx)
            commission       = abs(trade_value) * com_rate
            position_dict[ticker] += round_lots
            cash_balance -= (trade_value + commission)

            if look_ahead:                          # ← BIASED placement
                daily_pl = position_dict[ticker] * (price_fx - price_fx_prev)
                daily_pl_sum += daily_pl

            if   position_dict[ticker] > 0: long_mv  += position_dict[ticker] * price_fx
            elif position_dict[ticker] < 0: short_mv += position_dict[ticker] * price_fx

        nav += daily_pl_sum
        nav_list.append(nav); long_mv_list.append(long_mv); short_mv_list.append(short_mv)
    return nav_list, long_mv_list, short_mv_list
```

**Exposure definitions used throughout the book:**
```
net   = (long_MV + short_MV) / NAV      # short_MV is negative → directional bias
gross = (long_MV - short_MV) / NAV      # total leverage
```

Simulation constants: `start_K = 1_000_000`, `lot_size = 100`, `com_rate = 0.001` (10bps per trade).

### Continuous position sizing — a change from the 1st edition

The first edition advocated **scale-out**: enter full size, take a small profit early, let the remainder run to the stop. **This edition uses the relative score as a continuous signal instead:**

> **Compare today's theoretical round lots with yesterday's position, and trade the difference.**

- **Pro:** far nimbler at managing risk and volatility. Also non-boring — many traders (algorithmic included) cannot "sit and wait"; some trade because they showed up at work, not because of a signal. **Continuous sizing scratches that itch legitimately.**
- **Con 1:** higher transaction costs.
- **Con 2:** **adversely impacts the average price.** Positions are accounted FIFO; constant in-and-out drags the average price toward the most recent price, i.e. **in the direction of the trend.**

---

## 4. The algorithms, in order of sophistication

### 4.1 Fixed dollar / fixed percentage — `fraction_type = 1`

Allocate a fixed % of NAV per trade; the allocation grows with NAV. Default for retail, typical of no-margin operations. Tested at `pct_list = [0.02, 0.05, 0.10, 0.20]`.

**Findings:**
- Bigger size → higher compounded return. **And drawdowns are a direct function of position size.**
- Universe = 9 stocks, so **equal weight ≈ 11%**. Anything below 11% underutilizes capital.
- At 10% fixed, gross exposure hovers around **50%** — *"the signal does too good of a job at dampening the optimism of the position sizer"* (a continuous signal in [−1,1] scales the allocation down).
- **Net exposure is identical across all sizing levels** — all lines merge. Net exposure is a property of the *signal*, not of the sizing. (Hence not re-plotted for later methods.)

### 4.2 Fixed risk — `fraction_type = 2`

Divide by the **distance to stop loss** instead of the full share price. Chapter uses a flat `dsl = 0.1` (10%).

More capital-efficient → **much larger positions**, so `pct_list` values must be far smaller.

**The 2% rule, and why:** literature back to the 1980s says never risk >2% per trade. Three reasons, the middle one being the quantitative core:

> Trend-following systems win ~⅓ of the time. That implies a **high probability of 25 consecutive losses and routine runs of 10**. At 2% risk per trade, that means **routine drawdowns of 30–50%** — beyond the breaking point of most individuals.

**Key finding: even with the optimistic lookahead-biased signal, the system still wipes out capital when risk is set too high.** At 2% risk and a 10% stop distance, gross exposure sits around 1.0.

### 4.3 Volatility — `fraction_type = 3` (vol as % of price) or `4` (vol in price units)

A flat 10% is a blunt instrument: *"Markets can remain quiet longer than you can stay hysterical, and vice versa."*

```python
def target_vol_daily(annual_target, len_tickers):
    """Translate an ANNUAL vol budget into a per-stock DAILY target."""
    daily_target = annual_target / np.sqrt(252)
    return daily_target / np.sqrt(len_tickers)     # distribute risk across names

def average_true_range(df, _h, _l, _c, n):
    return (df[_h].combine(df[_c].shift(), max)
          - df[_l].combine(df[_c].shift(), min)).rolling(window=n).mean()

def raw_log_volatility(df, _c, n):
    daily_log_returns = np.log(df[_c] / df[_c].shift(1))
    return daily_log_returns.rolling(n).std(ddof=0)
```

**Why translate annual → daily:** *"Investors rarely ponder how much they are willing to fluctuate on a daily basis. They have some idea of how much volatility they can tolerate on an annual basis."* Divide by √252 for the daily target, then by √n_tickers to spread the budget.

| Measure | Input | Behavior |
|---|---|---|
| **Raw log volatility** | log returns, 21-day (1 business month) | moderate spikes |
| **Standard deviation** | *prices*, not returns | **more pronounced spikes** than raw vol. On relative series, must be converted to a percentage. |
| **ATR** | OHLC | **most stable, lowest readings** → largest positions → highest returns |

**Multiplier convention:** practitioners usually use 2 or 2.5 σ / ATR. **Because this book uses a continuous signal with real-time size adjustment, a tighter fit of 1 unit of volatility is used instead of the traditional 2.**

**Findings:** volatility sizing produces a smoother equity curve than fixed risk and keeps drawdowns **well below the annual target** in all cases. But because volatility averages below the flat 10%, positions are bigger → **higher gross exposure with large swings**. And the swings mean turnover: *"transaction costs would considerably erode the equity curve."*

### 4.4 Kelly criterion — the strongest result in the chapter

History: Daniel Bernoulli → rediscovered at Bell Labs in the 1960s (J.L. Kelly Jr.) → applied to blackjack and markets by Ed Thorp. See Poundstone, *Fortune's Formula*.

> Author's note: *"I never really understood how to apply Kelly until recently. Position sizes were either too big or null. Only when the formula was modified to accommodate the short side did it finally make sense."*

```python
def kelly_fraction(returns):
    wins   = returns[returns >  0]
    losses = returns[returns <= 0]
    W = len(wins) / len(returns) if len(returns) > 0 else 0
    avg_win  =     wins.mean()  if len(wins)   > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
    R = (avg_win / avg_loss) if avg_loss > 0 else 0
    return max(W - (1 - W) / R, -1) if R != 0 else 0     # ← floored at -1 for the short side

def rolling_function(returns, function, f_duration):
    return returns.rolling(window=f_duration).apply(function, raw=False)

def kelly_lateral(returns, n):
    """Cross-sectional Kelly across tickers, optionally smoothed."""
    lateral_f = returns.apply(kelly_fraction, axis=1)
    return lateral_f.rolling(n).mean() if n > 1 else lateral_f
```

**The `max(..., -1)` floor is the short-side accommodation** — it caps extreme shorting rather than letting the fraction run unbounded negative.

**Windows: 33, 50, 100 days**, then a simple average of the three. Rationale for the choice: one day is 3% of a 33-day window, 2% of 50, 1% of 100.

**Kelly is not just a sizing rule — it is a signal.**

> Rolled over a dataframe, Kelly gives an optimal bet size at each bar **and** a fully functioning indicator of **direction and strength**.
>
> **"A simple average of Kelly across 3 durations (33, 50, 100 days) generates a more responsive signal than the elaborate Ch. 4 composite score, with far less overhead."**

Observed behavior:
- **Tesla** — captures the wild moves; **better at spotting inflections** than the composite score.
- **BYD** — mirrors the signal, more reactive.
- **Renault (trendless market)** — the critical case. The composite score stays stuck in bullish or bearish territory and bleeds via false starts. **Average Kelly hovers around 0.** Trendless means advances and retreats cancel; **rolling Kelly concludes there is no statistical edge either way and collapses position size to zero.** This is the built-in fix for the "gives back gains in sideways markets" problem flagged in Ch. 5.

**Integration change** — only two lines differ in the simulator (renamed `simulate_kelly_position_sizing`):

```python
signal    = kelly_signal                    # replace score_rel with the Kelly fraction
target_mv = np.multiply(nav, signal)        # was nav_signal(pct, nav, signal)
```

Run with `fraction_type = 1` (divide by price) — **the most conservative choice**. Fractional Kelly can be synthesized by setting `fraction_type = 2` and tuning `constant`.

**Results:**
- **Equity curve: Kelly leaves everything else in the dust, at every iteration.** Phenomenal geometric growth even from the naive 3-duration average.
- **Drawdowns: the surprise.** Kelly dwarfed everyone on return **yet did not produce the worst drawdown.** The worst belonged to **5% fixed risk**. *"All it takes is a losing streak to rapidly erode the equity curve."*
- **Gross exposure: unconstrained, leverage balloons to 3.5× NAV.** *"Clearly not for your average pension fund manager."*
- **Net exposure swings effortlessly from bearish to bullish** — because the Kelly signal is non-uniform, unlike the fixed-% case where net was invariant.

**Related:** Ralph Vince's **optimal f** resizes based on past worst losses. Practical objection: *"any seasoned market participant will tell you the worst loss is yet to come."*

---

## 5. Comparative summary

| Algorithm | `fraction_type` | Denominator | Return | Drawdown | Gross exposure |
|---|---|---|---|---|---|
| Fixed % | 1 | price | scales with pct | scales directly with pct | ~50% at 10% pct |
| Fixed risk | 2 | price × stop distance | higher | **worst of all (at 5%)** | **largest (at 5%)** |
| Raw log vol | 3 | price × rolling σ(log ret) | good | below annual target | large, swings |
| Std deviation | 3 | price × σ(price) | good | subdued | large |
| **ATR** | 3 | price × ATR | **best of the vol family** | subdued | large (ATR reads lowest → biggest size) |
| **Kelly** | 1 | price | **dominant** | **not the worst** | **up to 3.5× NAV** |

---

## 6. Transferable rules

1. **Sizing beats picking.** Same signals + same universe + different sizing = different businesses. Optimize sizing before optimizing signals.
2. **Every sizing algorithm = NAV allocation ÷ denominator.** Make both explicit; the denominator is where the design lives.
3. **Round lots down, sign-preserving.** Naive rounding of negative share counts increases short risk.
4. **Compute daily P&L on the existing position before resizing.** Doing it after is lookahead bias — check for this in any backtest you inherit.
5. **Never average down.** It degrades three of four edge variables and its best case is breakeven.
6. **Express conviction in units of risk**, never in units of feeling.
7. **Never equal-weight.** Volatility ignored at the position level reappears at the portfolio level.
8. **Cap single-trade risk at ~2%.** A ⅓ win rate implies routine 10-loss runs and 25-loss tails → 30–50% drawdowns at 2%.
9. **Translate the annual vol budget to daily** (÷√252) and across names (÷√n).
10. **Prefer ATR** among volatility measures — most stable, lowest readings; but expect higher gross exposure and turnover.
11. **Use rolling Kelly as a signal, not only as a size.** Its collapse to zero in trendless markets is the feature, not a bug.
12. **Trade fractional Kelly.** Full Kelly's drawdowns are survivable mathematically and not psychologically.
13. **Continuous resizing costs you the average price** (FIFO drags it toward the trend) and costs commissions. Budget for both.
14. **Capacity is signaled by inertia**, not by a formula.
15. **Net exposure is a property of the signal; gross exposure is a property of the sizing.** Do not confuse the two knobs.

---

## 7. Cross-references

Ch. 1 gain expectancy — the four variables averaging down destroys · Ch. 4 the composite `score_rel` used as the continuous signal here (and outperformed by average Kelly) · **Ch. 5 the money management module defined; Kelly and expectancy formulas introduced** · Ch. 7 refining the universe (liquidity screens — Horseman 1 operationalized) · **Ch. 8 gross/net/beta exposure limits — the constraints deliberately omitted here** · Ch. 9 asset allocation and Dynamic Exposure Allocation.

**Named references:** Victor Haghani / Elm Capital coin-flip experiment · Edward Thorp, *A Man for All Markets* · William Poundstone, *Fortune's Formula* · Paul Tudor Jones · Ralph Vince (optimal f) · Edwin Lefèvre, *Reminiscences of a Stock Operator* · June-Yon Kim (capacity/inertia).

**Libraries:** `pandas`, `numpy`, `math`, `arcticdb`, `matplotlib`.

**Explicitly deferred to Ch. 8:** correlation between instruments. *"Securities that are highly correlated compound risk instead of reducing it."* No gross or net limits were imposed anywhere in this chapter — that is the next chapter's job.
