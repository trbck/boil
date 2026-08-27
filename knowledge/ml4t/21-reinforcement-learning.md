# Ch 21 — Reinforcement Learning

**Governs:** the financial problems where the *action* is the optimization target — execution, market making, hedging — and the simulation-to-reality gap that separates a promising simulator result from a deployable policy.
**Thesis:** RL earns its place only where the reward is directly measurable against an economic objective. **Reward engineering, not algorithm choice, is what aligns the learned policy with the financial goal — and the chapter's own notebooks mostly fail to establish dominance over classical benchmarks.**

---

## 1. Scope — why not alpha

RL collapses "predict then act" into one optimization targeting the financial objective rather than an intermediate proxy, and solves the **temporal credit assignment problem** — attributing a final outcome to the sequence of actions producing it — through the value function.

> **"Model-free" means only that the algorithm does not require a transition model. State design, reward shaping, and simulator construction still embed substantial modeling choices.**

**Why this chapter avoids alpha-seeking RL:** non-stationarity erodes learned patterns across regimes · **exploration-driven market impact is costly and irreversible** · **rewards based on short-window Sharpe invite overfitting and reward hacking.** Simplified trading demonstrations serve as proofs of concept but remain far from deployable decision problems.

> **RL's comparative advantage is where the action itself is the optimization target and the reward is well-defined and directly measurable: implementation shortfall, inventory-penalized spread capture, hedging PnL. Alpha generation belongs to the Ch. 11–14 predict-then-act pipeline on firmer ground.**

> **Exploration in finance must run through simulators, offline data, or strict risk controls — never unconstrained live trading.**

---

## 2. MDP design — where the leverage is

> **State design, reward shape, and action granularity determine what the agent can learn more than the algorithm does.**

**Markets are not Markovian.** Current price and volume alone do not capture regime, momentum, or microstructure dynamics. Practitioners stack recent observations and add rolling statistics (volatility, spread averages, order flow momentum) that summarize the relevant past.

**And they are partially observable** — the agent cannot see other participants' intentions, dark-pool liquidity, or pending news.

> **This is why state engineering carries so much weight. Richer state representations do more than improve performance; they bring the problem closer to the fully observable MDP that algorithms assume.** Recurrent architectures offer the alternative: internal memory implicitly constructing a belief state from the observation sequence.

**Three state categories:**

| Category | Contents |
|---|---|
| **Public market data** | Spread, multi-level depth, order flow imbalance — **the most informative predictors of short-term price dynamics for execution and MM** |
| **Private agent information** | Inventory, unrealized PnL, time remaining — **path-dependent, essential for risk-aware decisions** |
| **Regime indicators** | Rolling volatility, spread levels, depth ratios, time-of-day |

> **Including regime indicators means the optimal policy is inherently regime-conditioned: the agent learns to trade passively in fragile conditions and aggressively in deep conditions without explicit regime-switching logic.**

**Action space structure determines which algorithms apply** — discrete sets suit value-based methods; continuous quantities (slice size, limit price, weights) require actor-critic.

> **Hard constraints — kill switches, regulatory limits — should never rely solely on learned behavior.**

### Reward engineering

> **The agent will optimize whatever this signal rewards.**

- **Naive PnL** is intuitive but noisy and **encourages high-variance strategies chasing expected return without regard for risk**
- **Risk-adjusted** (Sharpe, Sortino, Calmar) aligns the objective with the institutional risk-return trade-off
- **Task-specific** matches the application: implementation shortfall (execution), inventory-penalized spread capture (MM), terminal risk measure (hedging)

> **The theoretical anchor: a quadratic per-step reward penalizing deviations of the wealth increment from its mean, scaled by risk aversion, produces agents that approximately maximize mean-variance utility.** The equivalence holds beyond Gaussian returns — **covering all elliptical distributions and certain asymmetric families.** It also **makes the Q-function analytically tractable, enabling solutions without neural approximation** (the QLBS insight).

> **For market making, asymmetrically dampened rewards — penalizing speculative gains more than spread-capture gains — discourage trend-following and improve learning stability.**

**Discount factor near 1.0 (0.99–0.999) encourages the far-sighted optimization execution and hedging require.**

---

## 3. Algorithm selection

| Algorithm | Type | Policy | Actions | Sample efficiency | Best use |
|---|---|---|---|---|---|
| **DQN** | Value-based | Off-policy | Discrete | Moderate | Simple trading, discretized execution |
| **PPO** | Actor-critic | **On-policy** | Both | **Lower** | Portfolio allocation, execution, general trading |
| **DDPG/TD3** | Actor-critic | Off-policy | Continuous | Higher | Execution, hedging, continuous allocation |
| **SAC** | Actor-critic | Off-policy | Continuous | **Highest** | **Market making, dynamic hedging, microstructure** |

**Actor-critic dominates because execution sizes, portfolio weights, and hedge ratios are continuous.**

> **The on-vs-off-policy choice is a stability-versus-efficiency trade: SAC's sample efficiency dominates when a high-fidelity simulator makes data generation cheap; PPO's robustness is preferable with limited historical data.** PPO's clipped surrogate objective prevents the performance collapse common in unconstrained policy gradients, but **on-policy learning discards past experience after each update — a real cost when high-quality financial data is scarce.**

> **SAC's entropy term encourages exploration and produces policies resilient to perturbation, but the entropy coefficient and learning rates require careful calibration — especially in non-stationary environments where PPO's simpler update rule is more forgiving.**

**Hybrid workflow: off-policy pre-training in simulation, on-policy fine-tuning for deployment.**

### Risk-aware extensions

| Approach | Mechanism | Limitation |
|---|---|---|
| **Mean-variance RL** | Variance penalty absorbed into the reward, so standard machinery applies | **Penalizes upside and downside deviations equally** |
| **CVaR-based** | Optimizes tail risk directly; aligns with institutional risk evaluation | Generally requires deep function approximation |
| **Distributional** (QR-DQN, IQN) | Learns the **full return distribution** | **Any risk measure computable at decision time — risk preferences become configurable without retraining** |

**Model-free vs. model-based split in practice:** execution and market-making agents are model-free. **Deep hedging is model-based — it learns policies for a *given* stochastic process (Heston, SABR), so changing the simulation model requires retraining, a dependency model-free approaches avoid.**

---

## 4. Execution — the most mature application

**The trade-off:** market impact from executing too quickly vs. timing risk from executing too slowly. **Minimizing implementation shortfall requires dynamically balancing them as conditions evolve** — which is precisely what Almgren-Chriss cannot do, since it assumes constant impact parameters, constant volatility, and a predetermined schedule.

> **Reward design is the central difficulty: misaligned penalties produce policies that satisfy the coded reward but make no economic sense.**

### Industry evidence, read carefully

> **J.P. Morgan's LOXM has optimized equity order execution since 2017, trained on billions of historical and simulated trades. The mandate is deliberately narrow: it decides *how* to execute an order, not what to buy or sell, and runs inside existing electronic trading risk controls.**
>
> **But the accounts leave training details and independent performance evidence proprietary. Useful as a signal of institutional interest, not as a source of reproducible benchmark numbers.**

### Simulator requirements

Training on simple price replay is insufficient. The simulator must model **order book mechanics, market impact, queue priority, partial fills, and latency.**

> **Without these, the agent may learn policies exploiting unrealistic assumptions — instantaneous fills at the bid or ask — that fail in live markets.**

Multi-agent simulators (ABIDES) populate the market with algorithmic and noise traders, so the agent learns under **reflexive** impact where other traders react to its orders.

### Results, with the caveats the book attaches

> **PPO achieves the lowest mean implementation shortfall of the three — about 44 bps vs. 53 for TWAP and 52 for Almgren-Chriss** — following a schedule between the uniform TWAP profile and the more back-loaded AC path. The policy combines a **constrained action space with a soft penalty for deviations from a reference schedule**, keeping it paced rather than allowing instantaneous liquidation.
>
> **Read as modest positive evidence that state-dependent pacing can improve on simple schedules in a compact simulator — and as a reminder the result is sensitive to simulator design.**

> **The seed caveat is specific and important: pinning the seed makes a run reproducible, but the policy's *character* — uniform, back-loaded, or in between — varies across seeds. The published figure is one fixed point on that distribution.** An under-constrained reward yields policies that undertrade early, overtrade early, or oscillate between extremes.

**Crypto extension:** the learned policy shows **clear premium conditioning — ~4.4 shares/hour during high-premium periods vs. 3.7 during low-premium, and 3.6 within two hours of funding settlement vs. 4.4 outside it.** A reproducible demonstration that microstructure features carry signal for an execution policy; **the benchmark is too small to support production claims.**

---

## 5. Market making

**Two complications beyond spread capture:** inventory risk (**a 1000-share long can be erased by a 1% drop, wiping out dozens of trades' worth of spread profit**) and adverse selection (**fills from informed counterparties are not random — they are exploiting stale quotes**).

**Avellaneda-Stoikov** gives closed-form quotes via a **reservation price** that deviates from mid as a function of inventory: when long, the reservation price shifts below mid, producing more aggressive sells and less aggressive buys. It requires explicit assumptions about arrival rates, volatility dynamics, and inventory-quote relationships that real markets violate.

> **In high-frequency market making, latency is a first-order concern: encoding order hold times and placement timing into the state and action spaces teaches the agent that a quote's value depends not only on its price but on how quickly it reaches the exchange.**

### The result is honest and negative

> **The main qualitative finding is not dominance but policy shape.** The learned policy responds to inventory in the right direction — shifting its quote center away from current inventory, echoing reservation-price logic — **yet carries somewhat more residual inventory and much larger wealth dispersion than the analytical baselines.**

> **And the aggregate statistics are weaker than the single-path figure suggests.** Average quote-center offsets are small (within roughly a few bps across all inventory buckets) and **only weakly and noisily related to inventory rather than cleanly monotonic** — the peak positive offset falls in the moderately short buckets while the most-short and long buckets sit near or below zero.

> **After 300K training steps, PPO reaches average liquidated wealth comparable to reservation-price baselines, but with much larger dispersion and somewhat larger terminal inventory. The implementation illustrates adaptive quote control; it does not prove the learned policy reliably dominates a well-specified analytical benchmark.**

**Production deployment remains proprietary — market makers have strong incentives not to disclose. Public evidence is concentrated in academic simulators.**

---

## 6. Deep hedging

**Classical delta hedging achieves perfect replication only under continuous rebalancing, zero transaction costs, and correct volatility specification. All three fail in practice.**

> **The shift is from exact replication to control of residual risk: instead of matching the option payoff path by path, find the hedge policy minimizing a chosen risk measure of terminal PnL after costs.**

**Rewards differ from typical RL:** deep hedging is **episodic**, and the economically relevant signal is terminal PnL, **so the objective is a risk measure of the terminal distribution rather than a dense step-by-step reward.** CVaR is the natural choice when downside tail risk drives capital allocation.

### The no-transaction band

> **Cost-aware policies tolerate small deviations from a reference hedge and trade only when the expected risk reduction justifies the cost.** Classical approaches derive such bands only in restricted settings — Whalley-Wilmott asymptotics require small proportional costs and strong assumptions. **Learned hedging extends the same logic to richer dynamics and more complex payoffs.**

### QLBS — the value-based alternative

| Aspect | Deep Hedging | QLBS |
|---|---|---|
| Method | Direct policy optimization | Value-based Q-learning |
| Learns | Hedging policy directly | Q-function → derives policy |
| **Price** | **External input** | **Emergent from hedging cost** |
| Reward | General (CVaR, variance) | **Quadratic (mean-variance)** |
| Tractability | Requires neural networks | **Analytical in simple cases** |

> **QLBS learns price as a byproduct of optimal hedging — option value tied to the optimal hedging strategy under the agent's risk preferences and costs rather than derived solely from frictionless replication.**

### The notebook result is not a win

> **Under the notebook's transaction-cost assumptions, discrete delta hedging is the strongest method for dispersion and 5% CVaR, with deep hedging competitive but not dominant.** Against the fuller benchmark set, deep hedging improves on the tabular Q-learning baseline and **sits between delta hedging and Whalley-Wilmott on the reported risk metrics.**
>
> **The lesson is not that deep hedging always produces the lowest dispersion or CVaR, but that fair comparison requires matched accounting, a friction-aware benchmark set, and an objective aligned with the reported statistics.**

> **Deep hedging becomes most informative when the problem departs materially from the Black-Scholes idealization: richer dynamics, stronger frictions, additional hedge instruments, or objectives targeting tail risk rather than variance alone.**

---

## 7. Inverse RL

**Given observed behavior, infer the reward function that rationalizes it.** MaxEnt IRL resolves the ill-posedness by finding the reward making demonstrations most likely **while remaining maximally non-committal about unobserved behavior.** GAIL frames imitation as a generator-discriminator game; AIRL extends it to explicitly recover a *transferable* reward.

**Three limitations of behavior cloning that IRL addresses:**

| Limitation | Mechanism |
|---|---|
| **Distribution shift** | A small mistake enters states the expert never visited, and **errors cascade** |
| **No reward recovery** | Copies actions, not objectives — **environment changes (new transaction costs) require entirely new demonstrations** |
| **Suboptimal experts** | Faithfully reproduces mistakes; **ranked-demonstration methods (T-REX) can recover rewards exceeding any individual demonstrator** |

**Financial applications:** strategy identification from order flow (**Gaussian Process IRL clustering HFT algorithms into momentum, mean-reversion, and inventory-management types from order flow alone, without access to actual strategies**) · goal-based wealth management inferring client preferences from revealed choices · imitation learning for market making via flow matching.

**Success depends on three factors:** demonstration quality (**noisy or irrational experts produce unreliable rewards**) · reward parameterization (**the feature basis constrains what objectives can be expressed — linear models miss the nonlinear preferences that matter in microstructure**) · computational cost (**MaxEnt IRL solves a full RL problem in its inner loop**).

> **Read inferred reward weights qualitatively as a decomposition of incentives, not as a uniquely identified structural reward. Action-distribution comparison against the expert is a behavioral sanity check, not proof the latent objective has been recovered.**

**IRL complements standard RL: one infers what to optimize, the other optimizes it.**

---

## 8. The simulation-to-reality gap

### Four sources of failure

| Source | Mechanism |
|---|---|
| **Non-stationarity** | Regime shifts **violate the MDP assumption of a stationary transition function** |
| **Overfitting** | Deep networks' parameter space makes it easy to overfit training patterns — **a complex form of data snooping** |
| **Market impact and reflexivity** | Backtests assume the agent is a passive observer; **in reality trades move prices and other participants react** |
| **Latency** | An agent trained assuming zero latency **decides on stale information and receives worse fills** |

### RL-specific backtesting pitfalls

- **State information leakage** — *including the day's closing price in an intraday agent's state is the classic example*
- **Reward hacking** — *an agent penalized for negative returns may learn to avoid trading entirely, earning zero returns and zero penalties*
- **Ignoring market impact** — training without it lets the agent place arbitrarily large orders **because it never experiences the price moving against it**
- **Order fill assumptions** — instant complete fills at the quoted price ignore queue priority and partial fills

### Narrowing the gap

**Domain randomization** varies impact coefficients, latency distributions, spread dynamics, and fee schedules across episodes.

> **Instead of calibrating a single "correct" environment, train across a distribution of plausible market conditions.** Fast vectorized simulators make this practical.

**Offline RL** learns from static historical archives without live interaction. **The central challenge is distributional shift — historical data came from past strategies that may differ from the optimal policy sought.** Practical methods penalize out-of-distribution actions or constrain learning toward well-supported behavior. **Decision Transformers** reframe this as sequence modeling with return-to-go conditioning, reusing mature infrastructure but **inheriting the usual dependence on data coverage and objective specification.**

### The impact demonstration — the chapter's most transferable result

> **Same long-only momentum strategy, same $5M order, real US equities 2010–2016, across stocks spanning five orders of magnitude in daily volume.** Square-root impact scaling with participation rate.
>
> **For the mega-cap, the order is roughly 1.5% of daily volume and the strategy stays clearly profitable even under the strongest impact assumption. For the micro-cap, the same order is many times daily volume, and the strongest assumption turns a large paper gain into a near-total loss.**
>
> **Below a liquidity threshold a profitable strategy becomes a reliable loser: across a sample of profitable-on-paper names, the strong impact assumption flips essentially every thin-stock winner — those whose orders exceed a day's volume — into a loser, while most liquid-stock winners survive. This is the documented reason small-cap alpha resists scaling.**

*Scoped to names where the signal is profitable before costs, so it shows impact on a strategy that works on paper; names are representative of liquidity tiers rather than selected on outcome. A diagnostic of how impact interacts with liquidity, not a calibrated estimate of deployable size.*

### Deployment checklist

| Phase | Requirements |
|---|---|
| **Pre-flight** | OOS testing across distinct regimes; realistic-impact simulator; **offline policy evaluation (importance weighting, doubly robust)**; independent model review |
| **Staged** | Paper trading, then limited capital with strict limits; **quantitative go/no-go criteria defined before scaling** |
| **Real-time** | **Hard risk limits the agent cannot override**; manual kill switch; monitoring of latency and realized slippage **versus simulation assumptions**; human authority to halt |
| **Ongoing** | Retraining cadence matched to horizon and regime-shift frequency; decay alerts; **complete model versioning for regulatory audit** |

**Regulatory context:** MiFID II Articles 17 and 48 require resilient systems, testing, controls, and monitoring for automated trading. **The EU AI Act introduces broader AI governance, but algorithmic trading is not singled out as a separate high-risk category in Annex III.** Partial transparency via SHAP on state-action mappings, surrogate decision trees, and counterfactual trajectory analysis.

---

## Transferable rules

1. **Use RL where the action is the optimization target and the reward is directly measurable** — not for generic alpha discovery.
2. **"Model-free" describes the algorithm, not the modeling burden.** State design, reward shaping, and simulator construction carry the assumptions.
3. **Reward engineering, not algorithm choice, determines whether the learned policy matches the financial objective.**
4. **Include regime indicators in the state** and the policy becomes regime-conditioned without explicit switching logic.
5. **Never let hard constraints depend on learned behavior.**
6. **Choose on-policy vs. off-policy on the stability-efficiency trade:** cheap simulator data favors SAC; scarce historical data favors PPO.
7. **Use distributional RL when risk preferences may change** — it makes them configurable without retraining.
8. **Treat seed variation as a policy-character question, not just a performance variance question.** The same reward can produce uniform, back-loaded, or oscillating policies across seeds.
9. **Constrain the action space and penalize deviation from a reference schedule** to keep execution agents economically coherent.
10. **A simulator without queue priority, partial fills, impact, and latency will teach the agent to exploit assumptions that do not survive contact with live markets.**
11. **Inspect policy *shape* against the analytical benchmark before comparing performance** — inventory-responsive quoting is the diagnostic, not one episode's PnL.
12. **Require matched accounting and a friction-aware benchmark set** before claiming a learned hedge beats delta hedging.
13. **Prefer IRL to behavior cloning when the environment may change,** since cloning copies actions rather than objectives.
14. **Read inferred rewards qualitatively.** The feature basis constrains what objectives can be expressed.
15. **Randomize the domain rather than calibrating one "correct" environment.**
16. **Check participation rate before believing any strategy result.** Above roughly one day's volume, strong impact assumptions flip essentially every paper winner into a loser.
17. **Run offline policy evaluation before any capital,** and define go/no-go criteria before staged scaling.

---

## Notebooks

`algorithms_comparison` (DQN, PPO, A2C on a standardized discrete-action environment — **position-occupancy patterns differ visibly, so algorithm choice shapes policy style even before richer environments**) · `02_optimal_execution_ppo` (PPO vs. TWAP and Almgren-Chriss in Gymnasium) · `03_market_making_ppo` (PPO vs. reservation-price policies at fixed spread widths) · `04_crypto_execution_rl` (premium-index features on Binance hourly) · `05_deep_hedging_pfhedge` (expected-shortfall objective vs. delta, Whalley-Wilmott, tabular Q-learning) · `inverse_reinforcement_learning` (behavior cloning and linear MaxEnt IRL on TWAP demonstrations) · `backtest_with_impact` (the liquidity-spectrum impact demonstration)

**Tooling:** ABIDES for multi-agent simulation with explicit exchange mechanics and latency · pfhedge (PyTorch) for deep hedging with GBM/Heston processes, exotic instruments, and expected-shortfall training.

---

## Cross-references

Ch. 3 microstructure, inventory risk, adverse selection, LOB mechanics · Ch. 11–14 the predict-then-act pipeline that handles alpha on firmer ground · Ch. 13 recurrent architectures as belief-state constructors under partial observability · Ch. 17 the fourth forecast formulation — direct allocation learning — which shares the end-to-end objective framing · Ch. 18 §18.6 Almgren-Chriss in depth; impact models and TCA · Ch. 19 §19.7 deep hedging as a learned risk control inside deterministic envelopes; CVaR objectives · Ch. 22 grounded language systems · Ch. 24 explainability for autonomous agents · Ch. 25 live trading infrastructure and staged deployment

---

## Citations

Almgren & Chriss (2001) · Arora & Doshi (2021), IRL survey · Avellaneda & Stoikov (2008) · Buehler et al. (2019), deep hedging · Byrd, Hybinette & Balch (2020), ABIDES · Chen et al. (2021), Decision Transformer · Dixon & Halperin (2020), G-Learner and GIRL · Haarnoja et al. (2018), SAC · Hafsi & Vittori (2025), RL execution deployment · Halperin (2019), QLBS · Halperin, Kolm & Ritter (2025) · Hambly, Xu & Yang (2023), RL in finance survey · Ho & Ermon (2016), GAIL · Kearns & Nevmyvaka (2013) · Kolm & Ritter (2019), mean-variance equivalence of quadratic rewards · Konda & Tsitsiklis (1999), actor-critic · Li et al. (2025), FlowHFT · Millea (2021) · Mnih et al. (2015), DQN · Nevmyvaka, Feng & Kearns (2006) · Schulman et al. (2017), PPO · Snoswell et al. (2020), MaxEnt IRL foundations · Sun et al. (2023) · Sutton & Barto (2018) · Sutton et al. (2000), policy gradient · van Hasselt et al. (2015), Double DQN · Wang et al. (2016), Dueling DQN · Yang et al. (2015), GP-IRL on HFT order flow · Zheng, He & Yang (2023) · Ziebart et al. (2008), MaxEnt IRL

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 21.*
