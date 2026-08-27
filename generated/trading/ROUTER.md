# Knowledge Router — Quantitative trading & investment strategy

Always-loaded map of this domain's corpus. Resolve a question to a small number of chapters, sections or rule shards, then load only those.

_Systematic trading: research process, signals, regime detection, position sizing, portfolio construction, risk and drawdown control, transaction costs, backtesting rigour, and live execution._

`domain: trading`  ·  `corpus: ad5d900819a1`

## Packs

| Pack | Kind | Title | Authoritative on |
|---|---|---|---|
| `ml4t` | book | Machine Learning for Trading, 3rd ed. | `process`, `data`, `features`, `modeling`, `backtesting`, `tooling`, `execution` |
| `assp` | book | Algorithmic Short Selling with Python, 2nd ed. | `regime`, `signals`, `sizing`, `portfolio`, `risk`, `costs`, `psychology` |
| `notes` | notes | Research notes & reports | — |
| `vbtpro` | engine | VectorBT PRO documentation | `tooling`, `backtesting` |

When packs disagree, prefer the one authoritative on the topic in question — and say that a disagreement existed. See `domains/trading/conflicts.md`.

## Rule shards

| Topic | Rules | ~Tokens | File |
|---|---|---|---|
| `backtesting` | 85 | ~1825 | `generated/rules/backtesting.md` |
| `costs` | 65 | ~1572 | `generated/rules/costs.md` |
| `data` | 60 | ~1271 | `generated/rules/data.md` |
| `execution` | 77 | ~1629 | `generated/rules/execution.md` |
| `features` | 109 | ~2446 | `generated/rules/features.md` |
| `modeling` | 113 | ~2589 | `generated/rules/modeling.md` |
| `portfolio` | 62 | ~1459 | `generated/rules/portfolio.md` |
| `process` | 52 | ~1084 | `generated/rules/process.md` |
| `psychology` | 17 | ~421 | `generated/rules/psychology.md` |
| `regime` | 23 | ~575 | `generated/rules/regime.md` |
| `risk` | 41 | ~978 | `generated/rules/risk.md` |
| `signals` | 41 | ~926 | `generated/rules/signals.md` |
| `sizing` | 18 | ~398 | `generated/rules/sizing.md` |
| `tooling` | 77 | ~1642 | `generated/rules/tooling.md` |

## Book chapters

| ID | Title | Governs | Topics | Rules |
|---|---|---|---|---|
| `ML4T-01` | The Process Is Your Edge | whether a research project is worth starting, and under what pre-committed rules. | `process` | 9 |
| `ML4T-02` | The Financial Data Universe | what to lock down before any modeling, how to vet a vendor, and where to put the bytes. | `data` | 10 |
| `ML4T-03` | Market Microstructure | how to turn raw market data into modelable observables — and which sampling and execution assumptions your ba… | `costs` `data` `execution` | 13 |
| `ML4T-04` | Fundamental and Alternative Data | building PIT-correct pipelines for revision-prone sources, and deciding whether an alt-data set is worth buyi… | `data` `features` `tooling` | 11 |
| `ML4T-05` | Synthetic Financial Data | whether to generate synthetic paths, which generator, and how to validate it. | `process` `backtesting` `data` | 10 |
| `ML4T-06` | Strategy Research Framework | the invariants you fix before research starts — what is traded, when decisions fire, how scores become positi… | `backtesting` `process` | 12 |
| `ML4T-07` | Defining the Learning Task | label definition, split-aware preprocessing, and the triage gates every candidate feature must clear before i… | `features` `modeling` | 14 |
| `ML4T-08` | Financial Feature Engineering | turning a strategy narrative into a specified, testable feature set — and keeping the search space from explo… | `features` `process` | 15 |
| `ML4T-09` | Model-Based Feature Extraction | features produced by fitted procedures rather than deterministic formulas — filtered states, conditional vari… | `modeling` `features` | 17 |
| `ML4T-10` | Text Feature Engineering | turning documents into backtestable factors — which representation to use, and the timestamp discipline that… | `features` | 16 |
| `ML4T-11` | The ML Pipeline | the regularized linear baseline every later model must beat, plus the three layers wrapped around it — SHAP a… | `modeling` | 19 |
| `ML4T-12` | Advanced Models for Tabular Data | when nonlinear tabular models earn their complexity over the Ch. 11 linear baseline, and which library/object… | `modeling` `tooling` | 15 |
| `ML4T-13` | Deep Learning for Time Series | whether the sequence history adds ranking content beyond lag-feature engineering, and which architecture fami… | `modeling` `features` | 17 |
| `ML4T-14` | Latent Factor Models | extracting low-dimensional structure from return panels, and the distinction between factors that explain cov… | `modeling` `features` `process` | 18 |
| `ML4T-15` | Causal Machine Learning | the multivariate estimation machinery that features surviving Ch. 7's bivariate triage require, plus the refu… | `modeling` | 18 |
| `ML4T-16` | Strategy Simulation | turning a prediction into a falsifiable claim about realized portfolio behavior — the trading protocol, the s… | `backtesting` | 19 |
| `ML4T-17` | Portfolio Construction | the mapping from forecasts to positions — and the constraints, risk estimates, and rebalancing rules that det… | `portfolio` | 19 |
| `ML4T-18` | Transaction Costs | the friction stack that separates gross alpha from realized return, and the guardrails that decide whether a… | `costs` | 21 |
| `ML4T-19` | Risk Management | turning a validated backtest into a tradable system — the constraints, controls, and governance artifacts def… | `risk` `backtesting` | 23 |
| `ML4T-21` | Reinforcement Learning | the financial problems where the action is the optimization target — execution, market making, hedging — and… | `execution` `modeling` `backtesting` | 17 |
| `ML4T-22` | RAG for Financial Research | grounding LLM output in a controlled, inspectable evidence base — the engineering stack from ingestion throug… | `tooling` | 18 |
| `ML4T-23` | Knowledge Graphs | questions whose answers depend on paths between entities rather than properties of entities in isolation — an… | `tooling` | 20 |
| `ML4T-24` | Autonomous Agents | systems that gather evidence, use tools, maintain state, and produce replayable artifacts — the layer upstrea… | `tooling` | 26 |
| `ML4T-25` | Live Trading Systems | the transition from verified backtest to live execution — broker integration, order lifecycle, technical pari… | `execution` | 21 |
| `ML4T-26` | MLOps and Governance | keeping a live system correct after launch — detection, response, and automated safety. | `execution` | 22 |
| `ML4T-27` | The Systematic Edge | what to do after the workflow is learned — career direction, learning practice, and which frontiers deserve a… | `signals` `process` | 10 |
| `ASSP-01` | The Stock Market Game | the objective function of the whole system — what "winning" means, and therefore what any strategy, sizing ru… | `signals` `process` `sizing` | 7 |
| `ASSP-02` | 10 Classic Myths About Short Selling | which short-side beliefs you are allowed to encode as assumptions — and which market-structure facts constrai… | `costs` `portfolio` `execution` | 7 |
| `ASSP-03` | Long/Short Methodologies: Absolute and Relative | the data substrate for the entire book. Every signal, regime, stop, and position size from Ch. 4 onward is co… | `data` `regime` `portfolio` | 10 |
| `ASSP-04` | Regime Definition | the triage layer — which side of the book a name belongs on, computed on both absolute and relative series. | `regime` `data` | 12 |
| `ASSP-05` | The Trading Edge Is a Number, and Here Is the Formula | the objective function you optimize and the metric you report. Everything from Ch. 6 onward is an attack on o… | `signals` | 13 |
| `ASSP-06` | Position Sizing: Money Is Made in the Money Management Module | the money management module of the trading edge — average win and average loss. In practice, the equity curve. | `sizing` | 15 |
| `ASSP-07` | Refining the Investment Universe | which names are tradable as shorts, as distinct from which names should go down. | `data` `costs` | 13 |
| `ASSP-08` | The Long/Short Toolbox | portfolio-level constraints — the limits deliberately omitted in Ch. 6, and the dashboard you actually run th… | `portfolio` | 15 |
| `ASSP-09` | Asset Allocation | how capital is distributed across strategies, and therefore what shape the equity curve takes. | `portfolio` `risk` | 14 |
| `ASSP-10` | The Trading Journal | adherence — the gap between what the system said and what you actually did — plus the post-trade analytics th… | `psychology` | 15 |

## Notes & reports

_None yet. Drop markdown in `inbox/` and run `python3 scripts/ingest.py`._

## Engine packs

| ID | Title | Router | Indexed headings |
|---|---|---|---|
| `vbtpro` | VectorBT PRO documentation | `generated/engines/vbtpro.md` | 10792 |

Engine content is retrieved by symbol, never loaded whole: `python3 scripts/lookup.py --engine <id> --search "<query>"`.

## Standing caveats

- **`ml4t`** — Chapter 20 is absent from the distilled set (numbering jumps 19 -> 21). Treat any Ch. 20 reference as unindexed.
- **`assp`** — ASSP-06 ships DELIBERATE lookahead bias for pedagogy (signal alignment + P&L computed after resize). Never inherit its P&L ordering without fixing both.
- **`assp`** — ASSP-05 pairs-trading thresholds are optimized on a single pair and are explicitly not expected to generalize.
- **`notes`** — Derived material: own research output, agent reports, working conventions. Cite it as such and never let it silently override a book rule -- if it contradicts one, surface the disagreement.
- **`notes`** — Populated by scripts/ingest.py from inbox/. Categories are subdirectories.
- **`vbtpro`** — Licensed material. Raw files are gitignored by default; see README before committing them to a public remote.
- **`vbtpro`** — Docs describe the engine's capabilities, not sound method. Method rules come from the book packs.

## Retrieval

```bash
python3 scripts/lookup.py --domain trading --search "..."
python3 scripts/lookup.py --rule ASSP-09-R7
python3 scripts/lookup.py --chapter ASSP-09
python3 scripts/lookup.py --section ASSP-09§5
python3 scripts/lookup.py --engine vbtpro --search "from_signals stop loss"
```
