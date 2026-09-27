# Ch 19 — Risk Management

**Governs:** turning a validated backtest into a tradable system — the constraints, controls, and governance artifacts defining what the strategy may do when conditions deteriorate.
**Thesis:** risk management is system design, not a reporting layer bolted on after research. **A strategy without explicit risk controls is not a tradable system; it is a hypothesis awaiting its first stress test.**

---

## 1. Three governing principles

| Principle | Requirement |
|---|---|
| **No lookahead** | Every adaptive control — volatility scaling, exposure caps, pause rules — uses only information available at decision time. **A risk limit implicitly conditioning on future volatility is the same leakage Ch. 7 and 11 eliminated** |
| **Auditable** | A post-mortem must trace exactly which signals triggered which actions. **"The model decided" is not an acceptable answer** |
| **Documented before deployment** | Explicit thresholds for acceptable drawdown, leverage, concentration, and the conditions under which trading pauses or stops |

| Aspect | Backtested model | Risk-managed system |
|---|---|---|
| Position limits | Implicit, data-driven | Explicit caps by name, sector, factor |
| Leverage | Whatever the optimizer chose | Hard ceiling with **regime-conditional tightening** |
| Drawdown response | **None** | Predefined de-risking triggers |
| Failure mode | **Undefined** | Kill switches with escalation rules |
| Documentation | Research notebook | Risk term sheet, monitoring dashboard |

---

## 2. Four stylized facts that constrain what is estimable

- Daily returns show **little serial correlation** — which is why point prediction is hard and Ch. 11–14 ICs stay modest
- **Squared and absolute returns are strongly autocorrelated** — volatility is more predictable than direction, and this persistence is what makes GARCH and EWMA operationally useful
- **Heavy tails make Gaussian assumptions unreliable exactly where it matters.** Parametric VaR under normality is **not merely imprecise; it is structurally biased in the part of the distribution risk control cares about**
- Distributions become more nearly Gaussian as horizon lengthens — **risk models are generally more reliable at lower frequencies than intraday or daily**

> **The practical consequence is narrow but important: variance is the highest moment of returns that can usually be estimated with confidence from ordinary historical samples. Skewness, kurtosis, and deep quantiles require much more data or stronger assumptions.**

### Risk control matrix

| Risk | Proxy | Control | Frequency |
|---|---|---|---|
| Market | Net beta, duration | Exposure limits, hedges | Daily |
| Factor | Factor loadings | Factor constraints | Weekly |
| **Leverage** | Gross/NAV | Hard caps, vol triggers | **Intraday** |
| Concentration | HHI, max weight | Position limits | Daily |
| Liquidity | ADV coverage, spreads | Capacity limits | Weekly |
| Model | OOS degradation | Re-research triggers | Monthly |
| **Operational** | Error rates | Automated checks | **Continuous** |

> **Market risk is not inherently good or bad — it is intended or unintended.** The same 0.1 beta is irrelevant to a long-biased equity strategy and **a meaningful hedging failure for a market-neutral one.**

> **Concentration wears a costume.** A portfolio of 100 names dominated by five positions is not diversified; **it is five concentrated bets wearing a diversified costume.**

> **Liquidity risk has two faces requiring different controls: exogenous** (market-wide conditions affecting everyone) → regime-aware trading pauses. **Endogenous** (the strategy's own impact) → ADV limits, capacity estimates, turnover ceilings.

> **Operational risk is the category where analytically sound strategies lose money anyway** — a flipped sign in production, a mishandled corporate action. **A short book accidentally converted to long, or a split misread as a price collapse, creates large unintended exposure with no change in the underlying signal.**

---

## 3. Tail risk

**VaR is a threshold, not a prediction of what happens beyond it.** A strategy with 95% VaR of 2% might lose 3% when breached or 20% — **VaR treats those as equivalent.**

**CVaR (Expected Shortfall)** answers the conditional question and has the property VaR lacks: **subadditivity.** Portfolio CVaR cannot exceed the sum of component CVaRs, consistent with diversification benefits — **unlike VaR, which can pathologically increase when combining positions.**

| Method | Trade-off |
|---|---|
| **Historical simulation** | Assumption-free; **answer depends heavily on sample period** |
| **Parametric** | Fast, convenient; **misleading when returns are non-normal** |
| **EVT** | Better for deep-loss estimation; needs careful threshold selection and modeling judgment |

> **Backtest evidence favors historical.** On real SPY returns the Kupiec test at 95% coverage favors **historical VaR (exception ratio 1.11×, p = 0.10)** over **parametric (1.17×, p = 0.012)** and **Cornish-Fisher (1.45×, p < 0.001)** — the Cornish-Fisher polynomial becomes unstable at this confidence level when realized excess kurtosis is in double digits, **which is typical for daily equity index returns.**

### The Cantelli bound — a distribution-free floor

> Requires only finite variance. **A portfolio with Sharpe ratio S has at most 1/(1+S²) probability of a losing period: 50% at S = 1, 20% at S = 2. Gaussian VaR gives 16% and 2.3%.** Far more conservative, but it holds for *any* distribution with finite variance. **When fat tails or regime shifts make parametric VaR unreliable, this gives a hard floor on loss probability from nothing but the strategy's risk-adjusted return.**

### Why both understate real risk

> **Tail events do not occur in isolation.** Liquidity evaporates, so spreads widen and impact spikes **precisely when exit is most urgent.** Correlations break in the wrong direction — **exceedance correlations conditional on both assets experiencing extremes are materially higher in downside tails than upside tails, so diversification shrinks when most needed.** And Ch. 18's cost parameters, estimated from ordinary periods, **can become several times larger in crisis.**

**Regime-conditional estimates:** SPY high-volatility regime **CVaR(95%) of 4.33% ≈ 2.7× the low-volatility 1.63%.**

> **The gap between regimes is larger for CVaR than for VaR — and CVaR is the quantity a risk manager needs when deciding how to de-risk.** Some strategies are strongly asymmetric: stable in calm markets, explosive tails in stress, **so the worst regime combines higher risk with worse compensation.**

> **The most dangerous moments are often regime transitions rather than established crisis periods, because controls calibrated to the old state fail before the new one is fully recognized.**

**Liquidity haircuts:** double or triple spread assumptions, raise impact by the historical crisis-to-normal ratio, reduce assumed ADV. **For strategies with meaningful turnover or position sizes, this can increase effective VaR by 50–100%.**

### Evaluating the volatility model itself

> **True volatility is never observed — and a naive MSE comparison against a chosen proxy can reverse model rankings when a different proxy is used. The model that looks best against squared returns may look worst against 5-minute realized variance.**

**Only two loss functions preserve rankings across arbitrary proxies:**

| Loss | Property | Use for |
|---|---|---|
| **MSE of variance** | **Operates on variance, not volatility — variance MSE is proxy-robust while volatility MSE is not** | Alpha research, where unbiased forecasts matter |
| **QLIKE** | **Asymmetric — penalizes under-prediction of variance more heavily** | **Risk management, where the asymmetry is a feature** |

> **A risk model that systematically underestimates volatility produces over-leveraged portfolios and optimistic cost projections; the pipeline compounds the error downstream.**

---

## 4. Path risk

> **A strategy losing 2% per day for 30 consecutive days may never breach a daily 5% VaR threshold, yet its investors experience a 45% drawdown.**

**The recovery asymmetry is punishing: a 30% drawdown requires a 43% gain; a 50% drawdown requires 100%.**

**Why path risk is decisive operationally:** many institutional allocators face **hard drawdown limits (10–15% common) where breaching triggers mandated redemption regardless of expected recovery** · career risk makes path risk personal — **professionals often cannot survive drawdowns exceeding peer norms even if subsequent performance is excellent** · **capital withdrawn during a drawdown misses the recovery**, so realized investor return is worse than the strategy's theoretical return, and the gap widens with severity · **leverage converts temporary losses into permanent impairment** through forced deleveraging at the worst moment.

| Metric | Measures | Use case |
|---|---|---|
| Maximum drawdown | Worst peak-to-trough | Mandate limits, allocator communication |
| **Drawdown duration** | Time in drawdown | **Investor patience, career risk** |
| Recovery time | Time to regain peak | Capital planning, reinvestment timing |
| **Ulcer Index** | **Quadratic mean of drawdowns — depth *and* duration** | Holistic path-risk comparison |
| Calmar | Return / MDD | Path-focused risk adjustment |

> **Two drawdowns of equal magnitude differ dramatically if one lasts two months and the other two years.** The Ulcer Index reflects the cumulative burden of being underwater, **giving higher weight to prolonged drawdowns.**

### The 150-year record

> **23 peak-to-trough declines exceeding 15% in US equities, 1871–2022, clustering into two types with different hedges: gamma events (fast and sharp — 1987, March 2020) respond well to option protection; delta events (slower and deeper — 2008, the dot-com bust) require duration-based defenses.**

**Calibration anchor:** the 2007–2012 GFC drawdown in SPY reaches **−55.2% over 355 trading days with an 869-day recovery.**

> **Unconditional drawdown statistics understate the tail risk embedded in factor timing.** Momentum showed modest drawdowns for decades, **then experienced 50%+ crashes during market reversals.**

---

## 5. Exposure decomposition

**Unintended exposures are dangerous because** they are not compensated in the investment thesis, they may reverse unexpectedly, and they complicate attribution and risk management. **Separate signal-driven exposures from mechanical exposures arising from portfolio construction.**

> **Exposures drift, and hedges built on static loadings silently become mis-sized.** IWM's rolling one-year HML loading climbs from roughly **0.1 to 0.3 over 2015–2024** — a structural shift an unconditional regression would average away. **The rolling window should be short enough to catch regime transitions but long enough to suppress estimation noise.**

> **The stock-bond correlation, long assumed negative, turned positive during the 2022 inflation shock.** Strategies built on diversification assumptions that held for decades experienced unexpected correlated drawdowns.

> **Apply a factor model that spans every asset class held.** An equity factor model applied to a portfolio holding crypto and commodities **will attribute those exposures to alpha, inflating apparent skill** — crypto carries hidden risk-on/risk-off and liquidity exposures standard equity factors miss.

> **The alpha illusion, quantified.** A representative SPY/QQQ/IWM/VTV/VUG portfolio yields **FF3 R² of 0.995 — systematic factors explain 99.5% of variance, leaving 0.47% annualized unexplained.** Typical for diversified portfolios: **apparent alpha is factor exposure in disguise.** A strategy returning 8% with 6% from factor exposures **is a factor portfolio with modest alpha**, which matters for fees, benchmarking, and expectations.

### Attribution uncertainty — point estimates are not enough

> **"40% of PnL came from momentum" treats a ±25% estimate and a ±5% estimate as equally informative.** Compute **HAC (Newey–West) standard errors** for each component and report **"Momentum contributed +2.3% ± 0.8%."** On the ETF portfolio under FF5, **market dominates the +13.02% annualized contribution while SMB, HML, RMW, and CMA are statistically indistinguishable from zero — a result a point estimate would have hidden.**

> **If the confidence interval on a factor's PnL contribution spans zero, claiming that factor "drove" performance is not supported by the data.** Common in portfolios with few assets, weak factor structure, or short windows.

### Three further diagnostics

- **Residual correlation thresholding** — after removing factor exposures, residuals should be uncorrelated. Flag pairs above ~0.3 to reveal **latent sub-factors: industry sub-sectors, supply-chain linkages, shared unmeasured exposures.** *Even on a tightly-modeled ETF basket this is striking — VTV/VUG and QQQ/VUG residual correlations sit well above threshold under FF5.* **The technique bridges factor modeling and unsupervised ML, identifying structure that contributes to underestimated portfolio risk**
- **Mahalanobis-distance variance** — a **portfolio-independent** precision-matrix diagnostic. If well-calibrated, the squared Mahalanobis distance has expected value equal to dimensionality; **high temporal variance signals instability that will propagate into erratic optimizer weights.** *The ETF basket trips a HIGH flag against an expectation of 5 — a clear warning that the raw precision matrix needs shrinkage before feeding a mean-variance optimizer*
- **Maximal attribution via factor rotation** — when factors are correlated, **rotating the basis changes the decomposition without altering the portfolio or its risk, a sign the attribution reflects mathematical convention rather than economic substance.** Sequentially orthogonalize prioritized factor groups (market → sectors → styles) for a unique hierarchical decomposition. **Most valuable where naive regression produces implausible sign flips depending on which factors are included**

**Trade-level SHAP** closes the loop at position level: backtest → identify failures → explain with SHAP → cluster patterns → generate improvement hypotheses. **Analyzing the worst trades' SHAP profiles reveals recurring error patterns** — momentum reversals, volatility regime mismatches, liquidity artifacts.

---

## 6. Stress testing

| Crisis | Period | Stresses |
|---|---|---|
| GFC | Sep 2008–Mar 2009 | Credit freeze, correlation spike, liquidity collapse |
| Flash Crash | May 6, 2010 | Intraday liquidity vacuum, microstructure failure |
| CNY devaluation | Aug 2015 | EM contagion, volatility spike |
| COVID | Feb–Mar 2020 | Fastest 30% decline in history, V-shaped recovery |
| **Rate shock** | Jan–Oct 2022 | **Stock-bond correlation flip, duration pain** |

> **Use these as regime exemplars, not predictions — samples of the parameter space that reveal vulnerabilities.** A strategy that survived 2008 may fail in 2022 **if its risk profile depends on negative stock-bond correlation.**

**Calibration:** on a balanced 60/40, the GFC replay gives **−29.2%** and COVID **−21.5%**, with the COVID decline concentrated in a shorter window. The 2022 rate shock cost **60/40 −20%, defensive −20%, aggressive −25%, All Weather −26%** — measured portfolio damage, not the ~230 bps headline rate move.

> **Historical replay captures price moves but understates execution damage.** In stress, spreads widen **3–10×**, impact increases, and participation drops. **A strategy showing −15% in historical simulation may show −25% when forced to trade at crisis spreads.**

**Scenario matrix:**

| Scenario | Vol | Spreads | Impact | Correlations |
|---|---|---|---|---|
| Moderate | 1.5× | 2× | 1.5× | +0.2 |
| Severe | 2× | 3× | 2× | +0.3 |
| Crisis | 3× | 5× | 3× | **0.7 universal** |
| **Liquidity crisis** | 1.5× | **10×** | **5×** | +0.2 |

> **The matrix need not be exhaustive — its purpose is to reveal how the strategy degrades as conditions worsen. A strategy that fails only under extreme scenarios is robust. One that fails under moderate stress requires rethinking.**

**Factor stress tests are conditional on current exposures** — map historical factor shocks to current holdings. *2009 Q1 saw roughly −40% momentum factor return; 2022 saw the 10-year yield rise ~230 bps in nine months.* **The same crisis affects different portfolios differently.**

**Reverse stress testing** starts from a defined failure point and works backward: what combination of moves causes this? How plausible? **What would we observe before it happened?** *A market-neutral strategy might appear safe until reverse stress testing reveals a simultaneous value and momentum crash — both factors it holds long — would breach the drawdown limit.*

> **Every stress test revealing a vulnerability must map to one of four outcomes: accepted risk (documented and communicated), hedged exposure, reduced exposure, or a kill-switch trigger. A stress test that reveals problems but triggers no action is wasted effort.**

> **The enforcing discipline: after each quarterly stress test, require a one-page memo documenting the scenarios run, the vulnerabilities identified, and the specific changes made to limits, hedges, or monitoring. If the third section is empty, the stress test failed its purpose.**

---

## 7. Adaptive controls without leakage

> **The governing rule is strict: a control signal at time t may use only information available at t or earlier.** That applies to volatility estimates, regime labels, liquidity proxies, **and any downstream transformation of those inputs.**

**Valid vs. invalid:** lagged realized volatility ✓ / same-day realized volatility ✗ · thresholds on published indicators (VIX, credit spreads) ✓ / ex-post regime labels ✗ · historical depth and quote-based proxies ✓ / same-day execution outcomes ✗.

> **The subtle failure mode is model-inferred regimes.** Hidden-state models leak if fit on the full sample or if smoothed probabilities are used. **Even online implementations leak when the full historical state path is re-estimated after each new observation** — producing a label at time t that depends partly on data from t and beyond.

**Volatility engines:** **EWMA is the anchor-free case reacting quickly to shocks; GARCH's mean-reverting anchor stabilizes longer-horizon baseline estimates.** In production they are combined rather than treated as substitutes.

**Volatility targeting** — choose a trailing window, **enforce a one-step lag, cap the scaling factor in low-volatility states, and keep the rule fixed during evaluation.**

**Short-Term Volatility Updating (STVU)** — **preserves slow correlation structure while scaling volatility with a fast multiplier**, smoothed with short-horizon EWMA and applied to both factor and idiosyncratic components.

> **STVU creates a fast lane for volatility level updates without forcing full covariance re-estimation at crisis frequencies. This matters most for leveraged or vol-targeted books, where stale risk estimates mechanically produce oversized positions** — it can trigger deleveraging materially earlier than slow-only models while preserving the baseline in calm regimes.

**Regime-triggered exposure caps** step down as stress escalates — *typical pattern: ~200% gross in calm, ~150% in elevated, ~100% in severe.*

> **The key requirement is pre-definition. Thresholds and transition rules must be specified before performance evaluation; otherwise the cap logic itself becomes an overfitted strategy parameter.**

**Tighten concentration and turnover as market quality deteriorates** — compress name caps across stress states, reduce turnover ceilings as spreads widen, tighten sector limits when cross-sectional correlations rise. **This reduces the chance a volatility shock and a liquidity shock are taken simultaneously through the same crowded exposures.**

### Position-level exits

**The design variable is stop width: tighter stops reduce loss per trade but increase the probability of premature exit.** ATR-scaled and MAE/MFE-calibrated thresholds beat fixed percentages **because they adapt to the strategy's realized excursion profile.**

> **Performance surfaces over stop-loss and take-profit grids are uneven rather than monotone, and the interaction between the two matters more than either threshold alone. Stop logic should be chosen through a calibration workflow weighing drawdown control against avoidable churn — not from a generic preference for tighter exits.**

> **On learned exits, the asymmetry is the finding: the lift comes from upside selection rather than downside protection.** Top-quintile trades earn meaningfully more on the upside than bottom-quintile trades lose on the downside. **Treat learned exit signals as a tool for sizing winners, not as a substitute for explicit stops on losers.**

> Read the learned-exit evidence as showing that **exit behavior can be conditioned on signal quality — not that a learned exit model outperforms a simpler baseline on a prediction metric like AUC. Judge position-level controls by their effect on realized trade paths, not by generic classification scores.**

**Composition with uncertainty-aware allocators is orthogonal:** the conformal inverse-width allocator (Ch. 17) decides **how much capital each name receives**; the rules calibrated here decide **when an open position exits.**

**Learned hedging policies** optimize a risk objective directly; with transaction costs in the objective they can produce **no-transaction regions consistent with classical asymptotic results.** The benefit is tighter objective-level hedging under realistic frictions; **the governance cost is lower transparency and a higher model-risk burden.**

> **The safest deployment pattern is hybrid: a learned policy inside hard, deterministic envelopes defined by traditional controls.**

### Anti-patterns

Thresholds mined from in-sample performance · control parameters tuned on evaluation windows · **kill switches calibrated with hindsight** · same-day signals violating tradable timing.

> **The common defect is not mathematical sophistication but broken governance. A control that cannot be specified ex ante and reconstructed after the fact is not a valid control.**

**Auditability requirements:** rule logic frozen and documented before deployment · historical signal values reproducible · **each position change traceable to a specific control input** · overrides recorded with explicit rationale.

---

## 8. Kill switches and governance

> **A strategy without explicit failure conditions is forced to improvise under stress — exactly when discretion is least reliable.**

**Three trigger groups:** performance-based (drawdown, rolling underperformance, abnormal loss streaks) · behavior-based (**turnover explosions, execution slippage, widening gap between live and expected tracking**) · market-state (severe spread widening, liquidity withdrawal, stress indicators outside bands).

> **Every trigger needs a metric, a threshold, an action, an escalation path, and a reinstatement condition. Without that surrounding logic, a kill switch is not a governance rule; it is only a number on a dashboard.**

| Level | Trigger | Action | Authority |
|---|---|---|---|
| 1 — Watch | 5% drawdown | Increased monitoring | PM |
| 2 — Caution | 10% drawdown | **50% position reduction** | PM + Risk |
| 3 — Review | 15% drawdown | New positions halted | CIO |
| 4 — Pause | 20% drawdown | Full position unwind | CIO + Board |
| 5 — Terminate | 30% drawdown | Strategy shuttered | Board |

*Illustrative — calibrate to expected volatility and investor tolerance.*

### The drawdown rule paradox

> **Mechanical drawdown rules often lock in losses a subsequent recovery would have erased.** Across ETF and portfolio data 1993–2022, traditional triggers **frequently amplified losses.**
>
> **The asymmetry: drawdown rules trigger when prices are already depressed and expected returns are higher than usual. A sequence of smaller drawdowns followed by repeated forced exits can do more damage than a single managed drawdown allowed to recover.** This argues against a universal cutoff and for **context-aware escalation, cross-asset confirmation, and review of broader market state before capital is removed.**

**Context matters:** a 10% drawdown at elevated VIX carries different implications than the same drawdown in calm conditions. **Simultaneous drawdowns across assets signal systematic risk; isolated single-position drawdowns may be worth riding out.**

**When the model is broken rather than unlucky** — persistent underperformance, a clear change in factor behavior, repeated cost overruns, or structural change in data or market design — **trigger formal re-research. Models have shelf lives, and the process is corrective rather than punitive.**

### Drift detection

**PSI thresholds:** < 0.10 minimal · 0.10–0.25 moderate, warrants investigation · > 0.25 significant, requires retraining. **Rules of thumb, not constants — calibrate on historical regime transitions before deployment.**

> **A real failure mode from the monitoring demo: on the crypto perpetuals panel the domain-classifier AUC saturates near 1.0 because funding and volatility regimes drift continuously.** Per-feature PSI is the more reliable trigger until the AUC threshold is calibrated on the strategy's own data.

### Governance as competitive advantage

> The mechanism is indirect. **Allocators conducting due diligence routinely reject strategies lacking documented risk frameworks — the absence signals operational immaturity regardless of return quality.** Internally, explicit rules replace discretionary judgments, **letting the strategy scale without a proportional increase in human oversight. And the discipline of documenting failure modes before deployment forces clarity about what the strategy actually does, often revealing risks the research process missed.**

---

## Transferable rules

1. **Build every adaptive control from information available at decision time,** and treat model-inferred regimes as a leakage channel unless the state path is never re-estimated.
2. **A control that cannot be specified ex ante and reconstructed afterward is not a valid control.**
3. **Variance is the highest moment you can usually estimate.** Treat skewness, kurtosis, and deep quantiles as requiring stronger assumptions or much more data.
4. **Report VaR and CVaR together,** and prefer historical simulation as the base method — Cornish-Fisher destabilizes at high confidence under realistic kurtosis.
5. **Use the Cantelli bound as a distribution-free floor** when parametric methods are untrustworthy.
6. **Compute tail metrics by regime and present worst-regime CVaR prominently.** Unconditional estimates average over states that differ by ~2.7×.
7. **Apply liquidity haircuts to tail estimates** — the effect can be 50–100% of effective VaR.
8. **Evaluate volatility models with QLIKE for risk and variance-MSE for alpha.** Other loss functions reverse rankings depending on the proxy.
9. **Measure duration and recovery time, not just drawdown depth.** Investors redeem before recovery, and their realized return is worse than the strategy's.
10. **Distinguish gamma from delta drawdowns** — they call for different hedges.
11. **Report factor attribution with HAC confidence bands.** A contribution whose interval spans zero did not "drive" performance.
12. **Span every asset class held in the factor model,** or cross-asset exposures get misattributed to alpha.
13. **Check residual correlations and precision-matrix stability** before trusting a covariance model in an optimizer.
14. **Monitor exposures on a rolling basis.** Static loadings silently mis-size hedges as tilts drift.
15. **Stress costs alongside returns.** Historical replay alone understates execution damage in crisis.
16. **Map every discovered vulnerability to accepted risk, a hedge, reduced exposure, or a trigger** — and enforce it with a written memo.
17. **Run reverse stress tests,** which surface combinations forward scenarios miss.
18. **Pre-define regime thresholds** or the cap logic becomes an overfitted parameter.
19. **Calibrate stops from the strategy's own MAE/MFE excursions,** and judge them by realized exit behavior rather than headline drawdown.
20. **Use learned exits to size winners, not to replace stops on losers.**
21. **Wrap learned policies in hard deterministic envelopes.**
22. **Prefer graduated escalation to a binary cutoff,** because mechanical drawdown rules can lock in losses that would have recovered.
23. **Give every kill switch a metric, threshold, action, escalation path, and reinstatement condition.**

---

## Notebooks

`01_var_cvar` (VaR/CVaR methods, Kupiec backtest, regime-conditional tails, SPY drawdown and recovery) · `02_exit_strategies` (stop-distance comparison) · `03_position_sizing_mae_mfe` (excursion calibration into sizing policy) · `04_factor_exposure` (FF3/FF5 decomposition, rolling loadings, HAC attribution, residual correlation, Mahalanobis diagnostic) · `05_trade_shap_diagnostics` (`TradeShapAnalyzer` forensics) · `06_stress_testing` (historical replay, scenario matrix, Student-t Monte Carlo, regime-conditional volatility) · `07_drift_detection` (PSI and domain-classifier monitoring) · `08_ml_exit_signals` (signal-strength-conditioned barriers) · `09_deep_hedging` (learned policy under transaction costs) · `10_ml4t_backtest_risk_demo` (`ml4t.backtest.risk`) · `11_systematic_risk_sweep` (stop/take-profit grids)

**Production classes:** `StopLoss`, `TrailingStop`, `TighteningTrailingStop`, `ScaledExit` composing via `RuleChain`, `AllOf`, `AnyOf`; `MaxDrawdownLimit`, `DailyLossLimit`, `MaxPositionsLimit`, `GrossExposureLimit` with configurable thresholds and warn/reduce/halt actions.

---

## Cross-references

Ch. 6 the strategy definition this chapter augments with risk thresholds · Ch. 7–9 the validation discipline whose leakage rules apply identically to control signals · Ch. 9 GARCH, EWMA, and regime models as the volatility engines here · Ch. 11 SHAP, applied at trade level · Ch. 14 factor models underlying exposure decomposition; covariance shrinkage flagged by the Mahalanobis diagnostic · Ch. 16 §16.6 regime slicing; drawdown metrics · Ch. 17 §17.4 conformal sizing, which composes orthogonally with these overlays; allocator constraints as risk constraints · Ch. 18 cost parameters that must be stressed alongside returns; capacity as a risk limit · Ch. 20 net-of-cost monitoring in the production loop · Ch. 26 MLOps and model governance

---

## Citations

Alankar et al. (2023), 150 years of drawdowns; gamma vs. delta events · Ang & Timmermann (2011), regime persistence and exceedance correlations · Artzner et al. (1999), coherent risk measures · Bianchi et al. (2023), fat tails and parametric VaR · Bollerslev (1986), GARCH · Brixton et al. (2022), stock-bond correlation regime · Browne et al. (2023), volatility targeting · Buehler et al. (2019), deep hedging · Cont (2001), stylized facts of asset returns · Daniel & Moskowitz (2016), momentum crashes · Federal Reserve (2011), SR 11-7 model risk management · Hansen & Lunde (2006), proxy-robust loss functions · Harvey et al. (2022), crypto factor exposures · Hurst (2010), risk parity · Khang (2022), regime-aware risk forecasting · López de Prado (2018) · Moreira & Muir (2017), volatility-managed portfolios · Paleologo (2025), STVU, attribution uncertainty, robust loss functions · Patton (2011), volatility forecast evaluation · Rockafellar & Uryasev (2000), CVaR optimization · Schwert (1989), time-varying volatility · Shu & Mulvey (2025), regime-conditional risk · Varma (2025), the drawdown rule paradox · Whalley & Wilmott (1997), no-transaction regions · Zumbach & Zumbach (2025), historical episodes as regime exemplars

*Source: Jansen, Machine Learning for Trading, 3rd ed. (Packt, 2026), Ch. 19.*
