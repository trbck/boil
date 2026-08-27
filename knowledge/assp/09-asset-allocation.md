# Ch 9 — Asset Allocation

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 9.
**Governs:** how capital is distributed across strategies, and therefore what shape the equity curve takes.
**Thesis:** **asset allocation is not an optimization problem. It is a survivability problem.** Classic allocators optimize *expected outcomes*; **paths** determine survival. When you combine strategies with opposite skews, **the more sophisticated the allocator, the worse it performs under stress** — sophisticated methods do not merely fail to prevent drawdowns, **they amplify them.** The replacement, **Dynamic Exposure Allocation (DEA)**, is built from failure geometry and governed by a single parameter: **maximum drawdown tolerance.**

---

## 1. Why long/short exists at all

Not leverage (derivatives or borrowing are cheaper). Not returns (ETFs are cheaper). Not exotic access (private equity does that).

> **The value proposition of long/short is the promise of a smoother equity curve.**

And smoothness is not aesthetic — it is **a structural requirement imposed by leverage limits, redemptions, mandates, and human behavior.** The real, often unstated reason investors park money in long/short vehicles is **capital survivability**.

### Smoothness is three drawdown properties, not volatility

| Property | Rule |
|---|---|
| **Depth** | Never test the **stomach** of your investors |
| **Duration** | Never test the **patience** of your investors |
| **Frequency** | Never test the **nerves** of your investors |

> A portfolio can post low volatility and an attractive Sharpe and still be **terminally risky** if it suffers rare catastrophic drawdowns. Conversely, an ugly Sharpe remains investable if drawdowns are shallow and recoveries fast.

### The mirage of uncorrelated returns

Correlations are not static. **"The only thing that goes up in down markets is correlation."** Liquidity constraints, forced deleveraging, and crowding cause apparently independent strategies to fail simultaneously.

> **The true litmus test is how a strategy behaves when correlation spikes and liquidity evaporates.**

### Smoothness costs something — always

Diversification, low net exposure, and low net beta do **not** guarantee smoothness. Smoothing requires one or more of:
- Sacrificing upside potential
- Accepting exposure to rare tail losses
- Tolerating long periods of stagnation
- Relying on diversification that may fail under stress
- Blending incompatible payoffs and risk profiles

---

## 2. The two archetypes and their failure modes

The axis is **which side of the return distribution is open-ended** — determined by the exit rule.

| Attribute | **Left-skew** (Mean Reversion) | **Right-skew** (Trend Following) | **Combined** |
|---|---|---|---|
| Profit side | **Capped** | **Open-ended** | Mixed |
| Loss side | **Open-ended** | **Capped** | Mixed |
| Win frequency | > 50% | ~20–40% | Medium |
| Loss frequency | ~20–40% | > 50% | Medium |
| Mode | **Positive** | **Negative** (peak trades are losers) | Positive |
| Kurtosis | Platykurtic left tail | Leptokurtic profits | — |
| **Dominant risk** | **Tail event** | **Persistent drawdown** | **Correlation & liquidity** |
| **Failure mode** | **Sudden collapse** | **Slow bleed** | **Regime coupling** |
| Equity curve | Smooth until break | Choppy with convex jumps | Smooth, then stressed |

- Left-skew: stop losses are **incompatible with the core premise** of reversion — inefficiencies may widen before reverting, so losses are endured until reversion or catastrophe. *"The captain of the Titanic had a 99.9% win rate."*
- Right-skew: **no single trade may inflict significant damage**, profits have no ceiling. Failure occurs "not through collapse but through the persistence of drawdown." *"Market participants expect to get rejected a lot, but they also know it takes one yes to make a lucky day."*
- **Combined:** the ideal would compound the left skew's frequent small profits *and* capture the right skew's convexity — **plateaus instead of drawdowns.** But these are incompatible payoffs. **Combining skews does not eliminate failure modes; it redistributes them.** Under stress, correlations spike and both archetypes can fail at once. **Contagion is a cause of death in multi-strategy portfolios.**

> **Before asking how to allocate across strategies, be explicit about how each strategy fails.** Allocation frameworks implicitly assume specific failure modes — mean-variance treats volatility as the primary risk and assumes bounded losses, stable correlations, and convex prices. **All three assumptions are violated differently by each archetype.**

---

## 3. Model returns, not prices — the methodological pivot

Most simulations start with **geometric Brownian motion on prices**. The chapter's objection:

> **GBM describes what markets do, not how they are traded.** The shape of a strategy's return distribution is **not an intrinsic property of the underlying asset — it is an emergent property of exit strategies and risk controls.**
>
> **Long/short portfolios do not fail because prices follow the wrong stochastic process. They fail because trading rules impose asymmetric constraints on profits, losses, and holding periods.**

A trend follower and an arbitrageur trade the same instrument with opposite rules and get radically different outcomes. **So the simulator must operate at the strategy-return level.** Modeling prices and layering strategies on top *obscures the very dynamics that determine survival.*

**The simulator is not calibrated to any market or period. Its outputs are not predictions — they are controlled adversarial scenarios.**

| Component | Question it answers |
|---|---|
| **Skew generator** | How does the strategy fail **in isolation**? |
| **Tail injector** | How does it fail **suddenly**? |
| **Persistence** | How does it fail **psychologically**? |
| **Correlation shock** | How does it fail **in a portfolio**? |

### The generators

**Mean reversion — three-regime model, uniform-distributed negative jumps:**

```python
def mean_reversion_log_returns(n, p_win, p_jump, win_mean, win_std,
                               loss_mean, loss_std, jump_min, jump_max, seed=None):
    p_loss = 1 - p_win - p_jump
    rng = np.random.default_rng(seed)
    u = rng.random(n); r = np.empty(n)
    win_mask  = u < p_win
    loss_mask = (u >= p_win) & (u < p_win + p_loss)
    jump_mask = u >= p_win + p_loss
    r[win_mask]  = rng.normal(win_mean,  win_std,  win_mask.sum())
    r[loss_mask] = rng.normal(loss_mean, loss_std, loss_mask.sum())
    r[jump_mask] = rng.uniform(jump_min, jump_max, jump_mask.sum())   # ← tail: bounded, negative
    return r
```

**Trend following — three-regime model, exponentially-distributed positive jumps:**

```python
def trend_following_log_returns(n, p_win, p_jump, win_mean, win_std,
                                loss_mean, loss_std, jump_scale, seed=None):
    p_loss = 1 - p_win - p_jump
    rng = np.random.default_rng(seed)
    u = rng.random(n); r = np.empty(n)
    loss_mask = u < p_loss
    win_mask  = (u >= p_loss) & (u < p_loss + p_win)
    jump_mask = u >= p_loss + p_win
    r[loss_mask] = rng.normal(loss_mean, loss_std, loss_mask.sum())
    r[win_mask]  = rng.normal(win_mean,  win_std,  win_mask.sum())
    r[jump_mask] = rng.exponential(jump_scale, jump_mask.sum())       # ← fat right tail, unbounded
    return r
```

**The distributional asymmetry is the point:** MR's tail is a **bounded uniform on the negative side**; TF's tail is an **unbounded exponential on the positive side.**

**Calibration used (5,000 days):**

```python
mr_params = dict(p_win=2/3,  p_jump=0.008,  win_mean= 0.0010, win_std=0.0001,
                 loss_mean=-0.0015, loss_std=0.0002, jump_min=-0.02, jump_max=-0.007)
tf_params = dict(p_win=1/3,  p_jump=2/30,   win_mean= 0.0016, win_std=0.0030,
                 loss_mean=-0.0012, loss_std=0.0003, jump_scale=0.004)
```

MR: 67% small wins (~+0.15%), regular small losses (~−0.25%), **0.8% of days at −2% to −0.7%**.
TF: 61% small losses (~−0.12%), 33% moderate wins (~+0.18%), **~5.5–6.7% exponential jumps**.

### The shock injectors

```python
def inject_shocks(returns, p_shock, shock_min, shock_max, mode="replace", seed=None):
    """MR failure: single-day jump. mode='replace' overrides normal behavior entirely."""
    rng = np.random.default_rng(seed)
    shocked = returns.copy()
    events = rng.random(len(returns)) < p_shock
    shocks = rng.uniform(shock_min, shock_max, len(returns))
    if mode == "replace": shocked[events]  = shocks[events]
    elif mode == "add":   shocked[events] += shocks[events]
    return shocked

def inject_tf_drawdown_regime(returns, p_regime, duration, dd_mean, dd_std, seed=None):
    """TF failure: a REGIME, not an event. Replaces a whole block of days."""
    rng = np.random.default_rng(seed)
    shocked = returns.copy(); n = len(returns); t = 0
    while t < n:
        if rng.random() < p_regime:
            d = min(duration, n - t)
            shocked[t:t+d] = rng.normal(dd_mean, dd_std, d)
            t += d                    # skip the whole regime
        else:
            t += 1
    return shocked
```

| Strategy | Failure mode | Shock type | Calibration |
|---|---|---|---|
| **Mean reversion** | Liquidity / collapse | **Single-day jump (replace)** | < 1 event/year, −1.5% to −0.8% |
| **Trend following** | Whipsaw / regime decay | **Drawdown persistence** | 2–3 regimes/year, ~20-day duration, ~−0.04%/day |

> **Fighting-sports analogy: mean reversion loses by knockout; trend following loses on points.**

**Portfolio-level (correlated) shocks — applied identically to both strategies:**

| Shock | Probability | Magnitude | Models |
|---|---|---|---|
| **Macro** | 0.2% | −2% to −1% | e.g. the 1995 Kobe earthquake, which exposed Nick Leeson's losses and sank Barings |
| **Crowded trade** | 1% | −0.75% to −0.4% | Crowded unwind — high slippage and transaction costs |

Result: **six scenario pairs** — baseline, MR-collapse + TF-drawdown, MR-collapse only, TF-drawdown only, macro-both, crowded-both.

> **Robustness comes from trend following; smoothness comes from mean reversion. So you must trade both.** The question is how to split finite capital.

---

## 4. Classic allocators — the negative result

### The unstated assumptions

Classic frameworks embed three assumptions in the mathematics without stating them:
1. Assets are convex, or at least not dangerously left-skewed.
2. Downside is bounded and can be summarized by **variance**.
3. Correlations are **stable even under stress**.

> **The critical question classic asset allocation does NOT ask is: how do portfolios fail?**
>
> **Variance is not risk. Ruin is risk.**

### The seven allocators

| Algorithm | Origin | Mechanism | Documented weakness |
|---|---|---|---|
| **Equal Weight** | — | 1/n | Structurally naive — *which turns out to be its strength* |
| **Mean-Variance** | Markowitz 1952 | `Σ⁻¹ @ μ`, normalized by Σ\|w\| | **Sensitivity to noisy estimates** — small variances → extreme allocations |
| **Risk Parity** | Dalio / Bridgewater, late 1990s | `sign(μ) × (1/σ)`, normalized | Treats correlations only **indirectly** |
| **Minimum Variance** | Markowitz descendant | `Σ⁻¹ @ 1`, normalized | **Concentrates in low-vol, highly correlated assets. Sacrifices returns for low volatility.** |
| **Maximum Diversification** | Choueifaty 2008 | Rebuild `Σ = diag(σ) ρ diag(σ)`, then `Σ⁻¹ @ σ` | Sensitive to covariance estimation |
| **Maximum Sharpe** | Markowitz/Tobin | `Σ⁻¹ @ μ` (identical to MeanVar unconstrained) | *"In theory powerful. In practice fragile."* |
| **Hierarchical Risk Parity** | López de Prado 2016 | distance `d = √((1−ρ)/2)` → single-linkage clustering → recursive bisection → `× sign(μ)` | **No matrix inversion** (robust to estimation error) but **clustering inertia** |

All implemented in **rolling form with a 250-day lookback**, **normalized by the sum of absolute weights** so shorts are permitted while gross exposure is maintained, and **shifted +1 day to avoid lookahead bias**. Each run: **$1M initial capital, 200% gross exposure.** Result: 50 columns (8 baselines + 6 pairs × 7 algorithms).

### The findings

> **The most striking result is also the simplest: equal weight outperformed every other allocation method across stress scenarios — not because equal weight is optimal, but because it is structurally naive. It does not attempt to infer risk from unstable statistics and therefore does not rebalance aggressively into failure modes.**
>
> **The more sophisticated the allocator, the worse it performed under stress.**

Specific mechanisms:

- **Skew and tails dominated outcomes** once stress was introduced.
- **Mean-variance** assumed thin tails and stable correlations — both were explicitly tested and it did not hold.
- **Risk parity and minimum variance systematically underpriced left-tail risk.**
- **Max Sharpe and Max Diversification rewarded strategies just before their failure regimes** — *left-skewed strategies have their highest scores immediately before tanking.*
- **Volatility targeting reduced exposure only after losses had already occurred.**
- **Hierarchical methods delayed regime-shift recognition due to clustering inertia.**

**All allocators underperformed the trend-following baseline. Max Sharpe, Risk Parity, and HRP underperformed even mean reversion.**

### The core pathology — worth memorizing

> **As left-skewed strategies enter pre-failure regimes, their recent volatility remains low. Allocators interpret low volatility as low risk and INCREASE allocation — precisely when survivability dictates the opposite. Simultaneously, right-skewed strategies are penalized for their drawdowns, despite those drawdowns being the cost of convexity.**

**No amount of strategy-level risk management can prevent this, because the failure occurs at the portfolio level.** This is why practitioners manually unplug their algorithms during crises.

### The inversion

> **Survivability precedes optimality.** Before asking how to allocate efficiently, decide **which failures are acceptable and which are existential.** Allocation is not a question of efficiency; it is a question of choice.
>
> **Every allocation allows certain failure modes and forbids others.** Classic frameworks make these choices implicitly.

---

## 5. Dynamic Exposure Allocation (DEA)

### Design requirements

1. **Survive opposite skews** — MR: infrequent large losses, small frequent wins; TF: small consistent losses, infrequent large gains.
2. **Cap allocation by failure mode per strategy** — MR: sudden collapse; TF: persistent drawdown.
3. **Deploy capital dynamically** — allow temporary elastic over-deployment when conditions are optimal; **remove leverage faster than it adds it.**
4. **Be intuitive, governed by one dominant parameter. Complexity is fragile.**

### Layer 1 — Strategy failure geometry (upper bands)

```python
def upper_band_limit(st_dd, lt_dd, corr_adj, lt_dd_tolerance, st_dd_tolerance, lqdty_haircut):
    min_dd = min(st_dd_tolerance / st_dd, lt_dd_tolerance / lt_dd)
    return round(min(min_dd * (1 - corr_adj), 1) * (1 - lqdty_haircut), 2)
```

Evaluate **both** short-term and long-term max drawdown for each strategy, take the ratio to its tolerance, **keep the smaller (more binding) number**, **penalize correlation**, then **apply a liquidity haircut for messy exits**.

> These are **hard upper limits**: even if the strategy fails completely, you survive. *"Left skewed strategies often go out of business because they over-leverage."*

### Layer 2 — Portfolio elasticity envelope

The upper bands **do not have to sum to 1**. Worked example from the chapter:

```
upper_band_MR = 0.30
upper_band_TF = 0.86
upper_band_limit = 0.30 + 0.86 = 1.16
gross_exposure_limit = 1.16 × 200% = 232%
```

> **This is not unconstrained leverage.** Elasticity is only available when **both strategies perform, equity is near an all-time high, and the risk oscillator is at peak.**

It is an **endogenous leverage envelope** derived from independent failure modes, heterogeneous (short and long term) drawdown profiles, correlation structure, and liquidity constraints. **This is much stronger than an arbitrary leverage cap — it is derived from failure analysis, not optimism.**

Note the raw split: **86% TF / 30% MR — heavily tilted to the right-skewed strategy**, and far from 50/50.

### Layer 3 — Risk oscillator (equity-state dependent)

Reuses `risk_appetite()` from Ch. 8. **This is the dominant control variable**, justified by Kahneman & Tversky's Prospect Theory (1979): **people react far more strongly to losses than profits.**

```
At peak:   2.0 × 1.16 = 2.32 gross
At trough: 0.5 × 1.16 = 0.58 gross
```

*"In practice, practitioners will probably opt for tighter min and max exposures. It is costly to trim exposure in times of crisis."*

**The drawdown estimate and why DEA beats it:** the back-of-envelope max-drawdown formula for log-equity processes gives a short-term drawdown figure; **empirically peak-to-trough is 2–3× that number.** But:

> **Classic algorithms assume static leverage through thick and thin. DEA aggressively cuts leverage as soon as equity rolls over — before the worst of the drawdown accrues.** Instead of a kiss-of-death 30%, realized drawdowns should land at **23–27%**.

### Layer 4 — Temporary boost

```python
def temporary_boost(series1, series2, boost_val, duration):
    cond1 = series1.pct_change(duration) <  0     # the OTHER strategy is failing
    cond2 = series2.pct_change(duration) >= 0     # THIS strategy is working
    return np.where(cond1 & cond2, boost_val, 1)
```

> **When one strategy performs and the other fails, boost the performer within its acceptable upper limit. When both perform or both fail, turn the boost off.**

Rationale: MR compensates for TF's protracted stagnation; TF performs when MR collapses. *"It would be regrettable to punish one for the sins of the other."* Uses a **rolling monthly average to avoid chaotic exposure fluctuations.** Defaults: `mr_boost_val=2.0`, `tf_boost_val=1.1`.

### Layer 5 — Clip exposures

```python
def calculate_raw_weight(upper_band, boost, gross_exposure):
    return upper_band * boost * gross_exposure

def clip_weight(weight, upper_band, min_exposure, max_exposure):
    return np.clip(weight, upper_band * min_exposure, upper_band * max_exposure)
```

Boosting must never push risk past the failure tolerance.

### The implementation — recursive by necessity

```python
def exposure_allocation(mr_returns, tf_returns, initial_capital,
                        upper_band_MR, upper_band_TF, min_exposure, max_exposure,
                        k, risk_params, curve_shape='linear',
                        mr_boost_val=2.0, tf_boost_val=1.1):
    n = len(mr_returns)
    equity = np.full(n, np.nan); equity[0] = initial_capital
    w_MR_series = np.full(n, np.nan); w_TF_series = np.full(n, np.nan)
    portfolio_returns = np.full(n, np.nan); gross_exp = np.full(n, np.nan)

    mr_boost_series = temporary_boost(tf_returns, mr_returns, mr_boost_val, k)
    tf_boost_series = temporary_boost(mr_returns, tf_returns, tf_boost_val, k)

    for t in range(1, n):
        gross_exposure = risk_appetite(equity[:t], curve_shape=curve_shape,
                                       **risk_params).iloc[-1]      # ← from Ch. 8
        gross_exp[t] = gross_exposure
        w_MR = clip_weight(calculate_raw_weight(upper_band_MR, mr_boost_series[t], gross_exposure),
                           upper_band_MR, min_exposure, max_exposure)
        w_TF = clip_weight(calculate_raw_weight(upper_band_TF, tf_boost_series[t], gross_exposure),
                           upper_band_TF, min_exposure, max_exposure)
        w_MR_series[t], w_TF_series[t] = w_MR, w_TF
        portfolio_returns[t] = w_MR * mr_returns.iloc[t] + w_TF * tf_returns.iloc[t]
        equity[t] = equity[t-1] * (1 + portfolio_returns[t])

    return pd.DataFrame({'equity': equity, 'w_MR': w_MR_series, 'w_TF': w_TF_series,
                         'portfolio_returns': portfolio_returns, 'gross_exposure': gross_exp,
                         'mr_boost': mr_boost_series, 'tf_boost': tf_boost_series},
                        index=mr_returns.index)
```

> **Unlike every other allocator, this one is recursive: `equity[t-1]` determines the allocation at `t`. It is slower, but it captures path dependency — today's allocation depends on yesterday's drawdown state.** Arrays are pre-filled with NaN to avoid look-ahead bias.

Grid tested: 6 scenario pairs × **3 drawdown tolerances (8%, 12%, 18%)** × 1 curve shape (aggressive) = 18 configurations.

### Result

> **DEA consistently outperforms all other algorithms, including the trend-following baseline** — even though outperformance was not the stated objective.

Three reasons given:
1. **Raw allocation is 86% TF / 30% MR — higher than 50/50** and tilted toward the convex strategy.
2. **Drawdowns are shallower thanks to mean-reversion compensation.**
3. **Capital is aggressively reduced during drawdowns.**

*"It may not be as pretty and smooth as we would like. It reaccelerates aggressively after every period of stagnation. More importantly, it does a decent job at preserving capital — upside participation and downside protection."*

---

## 6. The podium — read the split carefully

Top three by metric, median across all scenarios:

| Metric | 🥇 Gold | 🥈 Silver | 🥉 Bronze |
|---|---|---|---|
| **Sharpe** | MinVar 0.71 | MaxDiv 0.71 | EW 0.71 |
| **CAGR** | **DEA tol=0.18** 4.11% | **DEA tol=0.12** 3.94% | MaxDiv 3.87% |
| **MaxDD** | MinVar −13.59% | EW −13.71% | MaxDiv −13.96% |
| **Calmar** | MaxDiv 0.30 | EW 0.30 | MinVar 0.29 |
| **Win Rate** | RP 57.4% | HRP 57.3% | MinVar 56.2% |
| **Gain Expectancy** | **DEA tol=0.18** 1.59 bps | **DEA tol=0.12** 1.53 bps | MaxDiv 1.51 bps |
| **Profit Ratio** | **DEA 0.18** 2.55 | **DEA 0.12** 2.54 | **DEA 0.08** 2.54 |
| **Tail Ratio** | **DEA 0.18** 2.35 | **DEA 0.12** 2.35 | **DEA 0.08** 2.28 |
| **Common Sense Ratio** | **DEA 0.18** 5.99 | **DEA 0.12** 5.97 | **DEA 0.08** 5.81 |

**The split is the finding:** classic allocators win the **comfort metrics** (Sharpe, MaxDD, Calmar, Win Rate). **DEA sweeps every robustness metric** (Gain Expectancy, Profit Ratio, Tail Ratio, Common Sense Ratio) **plus CAGR.**

- **Sharpe is low even for gold-medalist MinVar** — *"the mere presence of trend following will torpedo any well-meaning Sharpe ratio."*
- **MaxSharpe does not appear on any podium** — *"it will systematically penalize volatile, right-skewed strategies."*
- **MinVar looks perfect on paper** — highest Sharpe, lowest max drawdown, highest win rate — **and does not deliver performance.** It sacrifices returns for low volatility.
- **DEA "will keep you alive, even when it does not feel good."**

### Average metrics by algorithm

| Algo | Sharpe | CAGR | MaxDD | Calmar | Win Rate | Profit Ratio | Tail Ratio | Common Sense |
|---|---|---|---|---|---|---|---|---|
| **DEA tol=0.08 agg** | 0.59 | 4% | −17% | 0.23 | 0.30 | **2.55** | **2.30** | **5.88** |
| **DEA tol=0.12 agg** | 0.58 | 4% | −19% | 0.22 | 0.30 | **2.56** | **2.36** | **6.05** |
| **DEA tol=0.18 agg** | 0.59 | 4% | −20% | 0.22 | 0.30 | **2.57** | **2.36** | **6.07** |
| EW | 0.74 | 4% | −14% | 0.30 | 0.41 | 1.63 | 1.90 | 3.10 |
| MaxDiv | 0.74 | 4% | −14% | 0.30 | 0.36 | 2.08 | 2.01 | 4.18 |
| MinVar | 0.74 | 4% | −14% | 0.29 | 0.56 | 0.90 | 1.68 | 1.52 |
| MeanVar / MaxSharpe | 0.39 | 2% | −18% | 0.12 | 0.48 | 1.18 | 1.54 | 1.82 |
| RP | 0.36 | 2% | −15% | 0.11 | 0.57 | **0.79** | 1.26 | 1.00 |
| HRP | 0.33 | 1% | −15% | 0.10 | 0.57 | **0.79** | 1.10 | 0.87 |

Note **RP and HRP have profit ratios below 1** — cumulative losses exceed cumulative profits. High win rate, negative edge. Exactly the left-skew trap.

---

## 7. One ring to rule them all — max drawdown tolerance

> **`max_drawdown_tolerance` is the single unifying principle: the one parameter connecting mathematics, investor psychology, and commercial viability.**

**Why:** clients do not experience risk as volatility. **They experience risk as losses from peak to trough.** A 10% volatility figure carries little emotional weight; **a 20% drawdown triggers panic and redemption.**

**The commercial conversation reduces to one question:** *"How much drawdown can you stomach before pulling the plug?"*

| `max_dd_tolerance` | Implied aggressiveness |
|---|---|
| **−8%** | Very conservative |
| **−12%** | Conservative |
| **−18%** | Growth-oriented |
| **−25%** | Aggressive |

The answer immediately defines **aggressiveness, capital deployment, recovery dynamics, and long-term growth potential.** Lower tolerance → smoother curve, slower compounding. Higher tolerance → greater upside, fatter tails. **The trade-off is explicit, transparent, and honest.**

### Leverage becomes a derived quantity

> **Max drawdown tolerance supersedes leverage as the primary control variable. Leverage is a means, not an objective.**
>
> Traditional risk systems ask *how much leverage can you take on?* **This system asks how much drawdown is acceptable.**

Worked example: set leverage at 300% instead of 200% and returns *and* volatility are magnified → **that triggers the risk appetite oscillator, which regulates exposure. As drawdown worsens, exposure is compressed geometrically until the system stabilizes.**

> **Volatility is a signal, not the target. Leverage is adaptive, not static.**

**Max drawdown tolerance is a governing invariant:** once strategy logic is fixed, this single number determines effective leverage and the shape of the equity curve.

> *"Winning this infinite, complex, random game is done by staying in the game. If the asset allocation algorithm you choose ensures survivability, then you win as long as your strategies have a trading edge."* — closing the loop with Ch. 1.

---

## 8. Transferable rules

1. **Define smoothness as drawdown depth × duration × frequency**, never as volatility or Sharpe.
2. **Simulate strategy returns, not asset prices.** Distribution shape is an emergent property of exit rules, not of the instrument.
3. **Model each strategy's failure mode explicitly** — single-day replace-mode jumps for left skew, block-replacement regimes for right skew — plus correlated portfolio-level shocks.
4. **Never let recent volatility drive allocation.** Left-skewed strategies are at their calmest immediately before failing.
5. **Do not penalize right-skewed strategies for drawdowns.** Drawdowns are the price of convexity.
6. **Among classic allocators, prefer equal weight.** Its naivety is a feature: it does not rebalance into failure.
7. **Derive position caps from failure geometry**: min(st_dd_tolerance/st_dd, lt_dd_tolerance/lt_dd) × (1 − corr) × (1 − liquidity haircut).
8. **Let upper bands sum above 1.** Elasticity that is *earned* — both strategies working, equity near highs, oscillator at peak — is not the same as an arbitrary leverage cap.
9. **Remove leverage faster than you add it.** Asymmetric response is the design goal.
10. **Boost the working strategy when its counterpart fails**, and turn the boost off when both work or both fail. Smooth it monthly.
11. **Path dependency requires recursion.** `equity[t-1]` must determine allocation at `t`; pre-fill arrays with NaN.
12. **Make max drawdown tolerance the single control parameter.** Leverage becomes a consequence, not an input.
13. **Read allocation scorecards in two columns**: comfort metrics (Sharpe, MaxDD, win rate) and robustness metrics (profit ratio, tail ratio, gain expectancy, common sense ratio). Optimize the second.
14. **A profit ratio below 1 with a high win rate is the left-skew trap.** Check both together, always.

---

## 9. Cross-references

Ch. 1 the infinite game and gain expectancy — the closing argument returns here · **Ch. 5 the two archetypes, skew, profit ratio, tail ratio — the direct precursor** · Ch. 6 position sizing (the strategy-level analogue of this chapter's portfolio-level problem) · **Ch. 8 `risk_appetite()` — Layer 3 of DEA, plus gross/net exposure definitions** · Ch. 10 the trading journal.

**Named references:** Markowitz (1952, mean-variance) · Tobin · Ray Dalio / Bridgewater (risk parity) · Yves Choueifaty (2008, maximum diversification) · Marcos López de Prado (2016, HRP) · **Kahneman & Tversky (1979, Prospect Theory)** · Nick Leeson / Barings / 1995 Kobe earthquake.

**Libraries:** `pandas`, `numpy` (`default_rng`), `scipy` (hierarchical clustering, `linkage`, `squareform`), `matplotlib`, `seaborn`.
