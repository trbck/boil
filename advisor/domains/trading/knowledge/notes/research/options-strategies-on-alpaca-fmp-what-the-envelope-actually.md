---
title: Options Strategies on Alpaca + FMP: What the Envelope Actually Allows
category: research
source: hyperresearch
date: 2026-09-05
authority: derived
topics: [options, costs, data, execution, risk]
domain: trading
question: What do Alpaca's options API and FMP's data actually support for systematic options trading, and which options strategy archetypes are viable inside those limits?
run: alpaca-fmp-options-feasibility-747fe6
---

# Options Strategies on Alpaca + FMP: What the Envelope Actually Allows

Asked which profitable options strategies to add, the honest answer starts one
step earlier. Alpaca and FMP impose three independent constraints — on data, on
execution, and on what can be simulated as evidence — and those constraints,
not the strength of any published edge, determine what is worth building. The
ranking that follows is therefore ordered by **how little machinery an archetype
needs**, not by headline Sharpe. That ordering is itself the finding: the
options literature's own numbers say execution quality and turnover decide
whether an edge survives, and those are precisely what this stack constrains.

## 1. Alpaca Options API Surface and Its Limits

**Approval levels.**

| Level | What it unlocks |
|---|---|
| 1 | Covered calls and cash-secured puts [4] |
| 2 | Adds long calls and long puts [4] |
| 3 | Adds spreads, straddles, butterflies, iron condors and other multi-leg structures [4] |
| 4 | Required for uncovered short options [1][15] |

Level 4 sits above the multi-leg tier — an important asymmetry, since a Level 3
account can trade four-leg condors but not a single naked call [1][15].

**Order surface.** Multi-leg orders use `order_class="mleg"` with a `legs[]`
array; a documented four-leg iron condor confirms four legs submit as one
instruction [1]. Order `type` may be market, limit, stop or stop_limit, but
**stop and stop_limit are restricted to single-leg orders** [3]. Quantities must
be whole numbers; notional sizing and extended-hours execution are not available
for options [3].

Two structures are permitted that are often assumed blocked. **Ratio spreads are
allowed** — the only constraint is that leg ratios reduce to lowest terms, so 1:2
is accepted and 4:2 rejected, a normalisation rule rather than a prohibition [1].
**Calendars and diagonals are allowed**, with a documented roll-across-expirations
example submitting as a single order; the restriction is narrower than *same
expiry*, applying to European-style legs, which leaves American-style equity
options unbound [1][2].

**The binding execution constraint is coverage, not direction.** An `mleg` order
is rejected unless all legs are covered within that same order — two naked short
legs in one order reject, even though each could be submitted individually [1].
This bites hardest on lifecycle management rather than entry: an uncovered short
cannot be rolled, and a calendar cannot be rolled if the transaction momentarily
leaves a leg uncovered [1]. An archetype that is enterable but not rollable is a
trap, and the ranking in section 3 filters on it. FINRA's heightened suitability
regime for uncovered writers is the plausible regulatory origin [42].

**Chain and snapshot endpoints.** The option chain endpoint returns, for every
contract on an underlying, the latest trade, latest quote, implied volatility and
greeks [7]; the snapshot endpoint returns the same bundle for explicitly queried
contract symbols. Both are **latest-state surfaces with no date-range
parameters** — there is no way to ask either what a chain looked like on a past
date [7]. Responses are large: a single liquid underlying can return thousands of
contracts across dozens of expirations, so any universe scan must budget response
size against the tier's rate limit [8]. This shape is why the greeks limitation
below is structural rather than incidental: the chain is a snapshot API by
design, and no historical endpoint replaces it.

**Greeks and implied volatility are live-snapshot only.** This is the most
consequential limit in the stack. Alpaca computes greeks and IV via
Black-Scholes from the *latest* quote and trade, bundling them into the chain and
snapshot responses [6][7]. There is no historical greeks endpoint, no such method
in the Python SDK [9], and no greeks or IV fields anywhere in the real-time
stream schema [11]. Alpaca's own wheel tutorial computes IV and delta locally
with a SciPy root-finder rather than reading a served field [15].

The consequence is not inconvenience but correctness: **any signal conditioned on
IV or a greek cannot be reconstructed at a past decision time from Alpaca data as
served.** Two escapes exist, both with costs. Recompute greeks locally from
historical bid/ask and underlying bars — the inputs do exist — and you own the IV
solver and its failure modes. Or capture live snapshots point-forward, in which
case usable history starts today. Two documented solver limits matter here:
**0DTE contracts never receive greeks** (division by zero), and deep-OTM or
near-expiry contracts frequently fail IV convergence against a 100-iteration cap
[6]. Any 0DTE archetype is greek-blind by construction.

**History depth.** Alpaca serves historical option data **from February 2024**
[5]; the repo's own tooling treats the boundary as approximately 2024-01
(`strategies/tools/data/options.py`). Either way this is roughly two and a half
years spanning one broadly benign volatility regime. One widely-cited SDK docstring restriction, stating that data is available
"up to 7 days ago" [9], conflicts with the official history
page, which states no such cap [5]. It also conflicts with named Alpaca staff,
who describe the only free-tier restriction as a 15-minute delay [10]. The weight of evidence —
two official sources, staff testimony, and the repo's own cache spanning
2024-01→2026-07 — indicates the docstring is stale or narrowly scoped.

**Feed quality and cost.** The free `indicative` feed is a randomised derivative
of OPRA with delayed trades, which Alpaca states should not be used for live
trading [8]. A randomised series cannot support a realistic fill or cost model
either, so honest options work requires the OPRA feed via the paid data tier — a
standing cost any archetype must clear. Rate limits are 200 requests/minute on
the basic tier against 10,000 on the paid tier [8]. **Open interest is absent
from every documented options endpoint** [7][9] — never denied, never provided —
which removes the conventional OI-based liquidity screen and forces universe
selection onto spread width and volume.

**Exercise, expiration and multi-leg settlement.** Exercise is requested through
a dedicated positions endpoint, and contracts at least $0.01 in the money are
auto-exercised at expiration. Requests submitted between the close and midnight
are rejected, and same-day requests must clear a 3:30pm ET cutoff [3][15].
Out-of-the-money contracts may still be force-liquidated in fast markets [2].

Multi-leg positions do **not** settle as a unit: atomicity is a property of the
*order*, not of the resulting position. Once filled, each leg lives and expires
independently and can be assigned on its own. A short leg assigned before its
paired long leg expires converts a defined-risk structure into an underlying
position plus a residual option — the mechanism by which a condor stops being
defined-risk in practice. Settlement type is never labelled in the
documentation; that exercise triggers an underlying buy or sell implies physical
settlement for equity options, but this is inference from behaviour rather than
a documented statement.

Two further gaps deserve naming. **Assignment is never
pushed over the websocket**; it must be discovered by polling REST [3]. And on
paper accounts, exercise, assignment and expiration sync only the following day,
even though balances and positions update immediately [3]. Any strategy reacting
to assignment therefore behaves differently on paper than live in a way unrelated
to fill quality.

**Paper trading is a logic test, not an edge measurement.** Alpaca's simulator
performs no market-impact, slippage or queue-position modelling and does not
check order size against available liquidity [13]. Practitioners additionally
report IEX-versus-SIP divergence of 5–50 basis points on liquid names and worse
on illiquid ones [14]. For options, where the spread is a large fraction of
premium rather than of notional, this understates cost severely.

**Borrow constraints are undocumented.** No Alpaca options page fetched here
discusses short-stock or borrow restrictions. This is a documented silence rather
than a permission: borrow binds on the *underlying* leg after assignment, not on
the contracts, which likely explains the omission. The repo's existing practice of
checking `shortable` and `easy_to_borrow` before shorting a name remains the right
control.

**One unresolved documentation conflict**, carried rather than settled: whether
equity legs may be combined with option legs in a single `mleg` order. The Level 3
page states this is "not supported at this time" [1], while the newer overview
documents a 422 error implying equity legs are permitted alongside a corresponding
quantity of call contracts [2]. This decides whether covered calls and collars open
atomically or must be legged in — a real execution-risk difference worth one test
order to resolve.

A related apparent contradiction *is* resolvable. A practitioner source reports
that Alpaca's options data endpoints reject paper credentials [41], seemingly
against documentation saying paper options are enabled by default [3]. Both are
correct about different things: market-data entitlement is a separate axis from
the paper/live trading distinction. Alpaca's historical data client takes its own
credentials and has no paper parameter at all — visible in the repo's own
`strategies/tools/data/options.py`, which constructs a `TradingClient` with
`paper=` alongside an `OptionHistoricalDataClient` without it.

## 2. FMP Fields Usable as Options Signals

FMP is best described as current-view first: it leans toward latest available
figures, so enforcing a reporting lag and avoiding restatement-driven lookahead
is work the developer adds manually [26]. But *not point-in-time* is too coarse a
verdict. The endpoints fail decision-time correctness in three distinct ways, and
some do not fail at all. **The tiering is the finding.**

| Endpoint | Temporal identity | Verdict |
|---|---|---|
| Dividends calendar / company [16][17] | declaration, ex-dividend, record, payment dates + amount; forward-looking | **Usable** |
| Stock grades [21] | event log: date, firm, previous grade, new grade, action | **Usable** |
| Stock news [22] | hourly crawl; published-vs-ingestion time undocumented | Usable with care |
| Earnings calendar [24][25] | single mutable record; `lastUpdated` is a bare write stamp | **Unsafe** |
| Financial estimates [18] | `date` is fiscal-period end, not as-of; "updated regularly", no versioning | **Unsafe** |
| Price target consensus [19] | **no date field at all** | **Unusable historically** |
| Price target summary [20] | rolling windows computed relative to query time | **Unusable historically** |
| Social sentiment [23] | legacy endpoint, third-party provenance | Avoid |

**The dividends endpoints work, and they are the most valuable thing FMP offers
this stack.** The schema carries declaration date, ex-dividend date, record date,
payment date and amount, and is forward-looking [16]. A worked example shows the
declaration roughly eleven days ahead of the ex-date [17], so at any decision
point the upcoming ex-date and amount are genuinely knowable. That is exactly
what a short-call early-assignment check requires. Constraints are a 90-day
maximum query range and a paid tier [16].

**Stock grades are the one analyst-side signal that survives**, because they are
shaped as an append-only event log with each event stamped when it occurred [21].
An upgrade or downgrade can be reconstructed as of a past date. Estimates and
price targets cannot.

**The earnings calendar is the trap.** There is no distinct *confirmed* flag.
Confirmation is inferable only from a non-null actual EPS, and the legacy
confirmed endpoint has been folded into a single mutable record whose
`lastUpdated` field carries no versioning or audit trail [24]. Nothing
demonstrates that the historical calendar preserves what was knowable earlier. For
an earnings-timed options strategy this is decisive: **the announcement date read
today is the realised date, not the date one would have believed on entry day.**
Scheduled dates move routinely. A sleeve entering *the day before earnings* off
this calendar can enter on a day it could not have chosen — and the error is
invisible in a backtest, because it produces better fills rather than an
exception.

**Price targets fail in two further ways.** Consensus has
no date field whatsoever [19], so the question *what was consensus then* is not
expressible in the schema. Summary reports rolling windows computed relative to
query time [20], so the field's *meaning* shifts with when it is asked — a
backtest against it compares incomparable quantities across dates.

For news, the hourly crawl cadence bounds ingestion lag at roughly an hour [22],
but whether the timestamp is publication or ingestion time is undocumented. For an
intraday signal that ambiguity is material. Useful calibration: point-in-time is
a spectrum, not a binary. Even Sharadar, the point-in-time-by-design contrast
case with as-reported dimensions and survivorship-bias-free history, indexes on
the form-10 filing date, which can lag actual market disclosure [27].

## 3. Archetypes That Fit the Envelope

Before ranking, the cost model must be right, because it decides every verdict
below. **A notional-basis-points model is wrong for options.** The correct class
is a fixed per-contract commission plus the bid-ask spread expressed as a
fraction of *premium*.

The literature is genuinely split on whether the volatility risk premium survives
that cost, and the split is informative rather than an impasse. Gross figures are
strong:

- a 26%/yr, Sharpe 1.16 backtest [33];
- short-variance information ratios above 3 in a paper that never mentions
  transaction costs [32];
- cross-asset VRP Sharpes from roughly 0.6 to 1.5 [34];
- zero-beta at-the-money straddles losing roughly 3% per week, which is that
  premium seen from the buyer's side [35].

Against that, **Bakshi & Kapadia give the
number that matters most**: the average ATM delta-hedged gain from selling was
about $0.43 per call against a mean bid-ask spread of about $0.375 [28]. The
entire premium is roughly one round-trip cost — costs are the same order of
magnitude as the edge, not a haircut on it.

**Muravyev & Pearson explain who actually pays what**, and this resolves the
disagreement. Quoted spreads averaged 8.1 cents; conventionally measured
effective spreads 6.2 cents; but for *timed* trades that exploit predictable
quote movement, the adjusted effective spread was just 1.3 cents [29]. Patient,
sophisticated execution costs roughly a fifth of naive spread-crossing. Traders
who cannot time this way — which includes a scheduled bot placing marketable
multi-leg orders — bear the full conventional effective spread [29]. The edge
survives at 1.3 cents and does not at 6.2.

Bondarenko's rebuttal is real and consistent with this: buy-and-hold put selling
crosses the spread once rather than weekly, making turnover-based costs
immaterial [30]. Broadie, Chernov and
Johannes add a separate caution — naked put returns are not statistically
significant against standard models once correct non-normal sampling
distributions are used, while straddle and delta-hedged returns are more
trustworthy [31].

So the disagreement is about **turnover and execution style, not whether the
premium exists.** That yields the ranking.

**Tier A — buildable now, minimal machinery.**

**A1. Covered calls and cash-secured puts on a small, liquid, dividend-aware
universe.** Single-leg, so no atomicity problem; Level 1, so no approval risk;
held to expiry, so turnover is minimal.

- *Edge and who pays:* the volatility risk premium, paid by buyers of protection
  and convexity who accept a negative expected return for insurance [34][35].
- *Why it persists:* the demand is structural rather than a mispricing — hedging
  mandates and loss-aversion keep it bid regardless of who has noticed it [34].
- *Net-of-cost expectancy:* the archetype where the evidence is strongest,
  because Bondarenko's argument applies at full force — a buy-and-hold seller
  crosses the spread once rather than weekly, so turnover-based costs stay
  immaterial [30]. Temper it with Broadie, Chernov and Johannes: naked put
  returns specifically are not statistically significant against standard models
  once non-normal sampling distributions are used [31].
- *Cost model:* fixed per-contract commission plus one round-trip spread as a
  fraction of premium, calibrated to the conventional effective spread [29].
- *Failure mode:* left-skew. Assignment into a falling name, capital trapped at
  a loss, and premiums decaying linearly through a sustained downtrend. Stops do
  not help, since the premise is that the position is held to expiry.
- *Validation data:* underlying bars plus option premium bars — both available
  from February 2024 [5], and no greeks required, which is what makes this the
  only Tier A entry that is backtestable today without new infrastructure.

**A2. A dividend-aware early-assignment filter.** A risk control rather than a
standalone edge, which improves every short-call structure including the existing
condor sleeve.

- *Edge and who pays:* no premium is harvested. It prevents a transfer *to* the
  early exerciser, who takes the dividend when doing so is rational.
- *Why it persists:* mechanical, not behavioural. Exercise is rational whenever
  the dividend exceeds the corresponding put's price [36], so the risk recurs
  every dividend cycle and cannot be arbitraged away.
- *Net-of-cost expectancy:* avoided loss rather than earned return, sized at
  roughly the dividend per assigned contract — a worked case puts about $28 per
  contract at stake on a $0.72 dividend against a $0.44 put [36].
- *Cost model:* zero incremental cost when it merely gates entry; one round-trip
  spread when used to close a position ahead of the ex-date [37].
- *Failure mode:* false positives closing profitable positions unnecessarily,
  and misses where a dividend is declared inside the holding window.
- *Validation data:* FMP's dividend calendar for forward ex-dates and amounts
  [16][17], joined to short-call position state. This is the one place where an
  FMP field is both reliably point-in-time and directly decision-relevant.

**A3. Volatility-premium capture via an ETP proxy.** Captures similar economics
with no options data, no multi-leg execution and no per-contract accounting.

- *Edge and who pays:* the same volatility risk premium, reached through a
  volatility-linked ETP gated on term structure rather than through contracts.
- *Why it persists:* identical structural demand [34]; the access route changes,
  the source of the premium does not.
- *Net-of-cost expectancy:* not directly supported by the options literature
  cited here — the ETP wrapper changes the return path enough that option-return
  studies do not transfer cleanly. Treat expectancy as requiring its own
  evidence.
- *Cost model:* **the one archetype where basis-points-of-notional is correct**,
  since it trades as equity. A useful contrast with every other entry here.
- *Failure mode:* levered-ETP path decay, no defined risk, and gap risk — the
  2018 inverse-VIX collapse is the standing precedent for how this ends.
- *Validation data:* daily equity bars only. **The one archetype not bounded by
  the February 2024 options-history limit**, so it can be tested across multiple
  volatility regimes including a real tail event.

**Tier B — buildable, materially more machinery.**

**B1. Defined-risk verticals and iron condors.**

- *Edge and who pays:* the volatility risk premium with a capped tail, financed
  by giving up the far wing; bought by the same structural hedging demand [34].
- *Why it persists:* as A1, with the defined-risk wrapper trading some premium
  for a bounded loss — which is also what makes it tradable at Level 3 [1][4].
- *Net-of-cost expectancy:* weaker than A1 on the same evidence, because four
  legs mean four commissions and four spreads per round trip. This pushes the
  structure toward the regime where the premium is comparable to the cost of
  trading it [28][29].
- *Cost model:* per-contract commission and spread **multiplied by leg count** —
  the single most common underestimate in condor backtests.
- *Failure mode:* an unsampled tail. Wings bound the loss, but a sample drawn
  from one benign regime never exercises that bound, so the cap is asserted
  rather than observed [5].
- *Validation data:* option bars for every leg, plus a fill model honouring
  all-or-none semantics — which the mandated engine does not provide natively
  [38]. Evidence, not execution, is the obstacle here.

**B2. Calendars and diagonals.**

- *Edge and who pays:* the term structure of implied volatility — selling
  richer near-dated premium against cheaper far-dated, paid by demand
  concentrated in short-dated contracts.
- *Why it persists:* short-dated demand is persistent and largely
  event-motivated, keeping the front of the curve bid.
- *Net-of-cost expectancy:* not established by the sources gathered here. Stated
  as a gap rather than assumed favourable.
- *Cost model:* per-contract and spread per leg, plus recurring roll costs,
  making this the most turnover-sensitive entry in Tier B.
- *Failure mode:* the coverage rule constrains rolling, so a position can be
  enterable but not adjustable [1] — and management properly wants greeks that
  have no historical form [6][9].
- *Validation data:* requires a local IV and greeks pipeline before it can be
  evaluated at all.

**Tier C — outside the envelope.** For these the feasibility verdict is
dispositive: an archetype that cannot be entered, or whose signal cannot be
reconstructed at a past decision time, does not need an expectancy analysis to
be excluded.

- **Naked short puts and calls** require Level 4 and are rejected at Level 3 [1].
- **Any historically-conditioned greek or IV signal** is unbacktestable without a
  local solver [6][9].
- **Anything needing an open-interest liquidity screen** is unbuildable as
  specified, since OI is not served [7].
- **0DTE greek-based strategies** are doubly excluded, since greeks are never
  computed for same-day expiries [6].

## 4. Implications for Existing Sleeves

The feasibility analysis materially changes how three existing sleeves should be
regarded.

**Earnings-timed sleeves may carry a lookahead their gate cannot see.** The
straddle, strangle and iron-condor sleeves are timed off earnings dates. If those
dates were sourced from FMP's mutable calendar, the samples inherit the defect in
section 2 — entering relative to a date corrected after the fact [24]. This
warrants a direct check of provenance, and if confirmed, re-timing against a
source that preserves what was knowable then. The failure flatters results
silently, so its absence should be demonstrated rather than assumed.

**The evidence engine cannot represent atomic multi-leg fills.** vectorbtpro
supports short positions natively and cash-shared grouped portfolios [38][40],
and — usefully — `fixed_fees` is a first-class per-order parameter alongside
percentage fees [38]. A per-contract options commission can therefore be
expressed correctly without a workaround. But the grouping mechanism carries an explicit
warning: grouped orders are presumed to execute within the same tick and retain
their price "even though they depend upon each other and thus cannot be executed
in parallel". A rejected order may still let later orders execute and strand them
without funds [38]. Order status is per-order, with no
cross-order atomicity concept [40].

The mismatch is structural: Alpaca's `mleg` is all-or-none, while the simulator
fills legs independently and sequentially. A backtested condor can therefore
report a fill pattern the venue would never produce — three legs on and one
rejected, leaving an uncovered short that Alpaca's coverage rule would have
refused to open [1]. Neither conservative nor consistent. There is also no native
options instrument: no strike, expiry, exercise or assignment concepts appear in
the API reference, and the 100x multiplier can only be encoded as a generic
scalar [38][39]. Handling this properly means custom simulation callbacks. Note
that vectorbtpro's deeper documentation is not public, so this rests on the open
reference and the PRO feature pages — a licensed user can settle it directly.

**The one-regime problem is already acknowledged and remains the ceiling.** With
history starting in 2024 [5], every options sleeve here is validated on roughly
two and a half years of one broadly benign volatility regime with an unsampled
tail. Deflated-Sharpe and combinatorial cross-validation machinery cannot see a
tail that never occurred in the sample. This is a limit on what the evidence can
support, not a defect to fix by better statistics. A completeness check is also
warranted: entire morning sessions are missing from historical option trades on
2024-02-26 and 2024-03-15 across all contracts [12], near the start of history.

Finally, one internal inconsistency worth resolving: the short-vol sleeve's
premise records that Alpaca has "empty historical option bars", while the newer
iron-condor sleeve builds on cached Alpaca option bars spanning 2024-01→2026-07.
The former appears stale. If so, a class of strategies was excluded on an
obsolete constraint.

## Key findings

1. **Greeks and implied volatility are served only as live snapshots**; no
   historical greeks exist in the API or SDK, so any IV- or greek-conditioned
   signal is unbacktestable without locally recomputing from bid/ask and
   underlying bars [6][7][9][11][15].
2. **Options history begins February 2024**, giving roughly two and a half years
   covering one benign volatility regime with an unsampled tail [5].
3. **Level 3 permits four-leg atomic `mleg` orders but not uncovered shorts**,
   which require Level 4; the binding rule is that all legs must be covered
   within the same order, which constrains rolling more than entry [1][4].
4. **Ratio spreads, calendars and diagonals are permitted**, contrary to common
   assumption; the leg-ratio rule is a normalisation, not a prohibition [1][2].
5. **Open interest is absent from every options endpoint**, removing the
   conventional liquidity screen [7][9].
6. **FMP's earnings calendar is a mutable record with no versioning** and no
   distinct confirmed flag, so historical dates are realised dates — a silent
   lookahead for any earnings-timed strategy [24].
7. **FMP's dividend endpoints and stock-grade events are genuinely
   point-in-time**, while estimates, price-target consensus and price-target
   summary are not; consensus carries no date field at all [16][17][19][20][21].
8. **The volatility risk premium is roughly the size of one round-trip cost**:
   about $0.43 per ATM delta-hedged call against a $0.375 mean spread [28].
9. **Execution style decides survival** — 1.3 cents effective spread for timed
   trades against 6.2–8.1 cents for naive spread-crossing, and a scheduled bot
   is firmly in the second group [29].
10. **The mandated backtest engine has no atomic multi-leg fill semantics** and
    no native options instrument, though it does support fixed per-contract fees
    correctly [38][39][40].
11. **Paper trading performs no liquidity or market-impact modelling** and lags
    live on assignment reporting by a day, so it validates logic, not edge
    [3][13][14].

## Recommendations

1. **Rank by turnover and execution patience, not gross Sharpe.** The cost
   evidence says this is the axis that determines survival [28][29]. Prefer
   low-turnover, held-to-expiry structures.
2. **Start with single-leg, Level 1 structures** — covered calls and
   cash-secured puts on a small liquid universe. They avoid the atomicity
   mismatch, the approval ceiling and the greeks gap simultaneously.
3. **Audit the earnings sleeves' date provenance immediately.** If dates came
   from FMP's mutable calendar, the samples carry lookahead that flatters results
   invisibly [24]. This is the highest-value check available right now.
4. **Build the dividend early-assignment filter next.** It is mechanical [36][37],
   uses the one FMP endpoint that is reliably point-in-time [16][17], and
   improves every short-call structure including the existing condor sleeve.
5. **Model costs as per-contract commission plus spread as a fraction of
   premium**, calibrated to the conventional effective spread rather than the
   sophisticated-trader figure [29]. Report break-even cost against assumed cost.
6. **Decide explicitly about greeks.** Either build a local IV/greeks pipeline
   from historical bid/ask and underlying bars — accepting ownership of the
   solver, including its documented 0DTE and deep-OTM failures [6] — or exclude
   greek-conditioned archetypes. Do not leave this implicit.
7. **Resolve the multi-leg simulation gap before gating any new multi-leg
   sleeve**, via custom simulation callbacks or an explicit all-or-none
   pre-check, so simulated fills cannot violate the venue's coverage rule [1][38].
8. **Budget the paid OPRA data tier** as a fixed cost of doing options work; the
   indicative feed is randomised and unsuitable for both live trading and
   realistic cost modelling [8].
9. **Settle two open questions cheaply**: whether equity and option legs combine
   in one `mleg` order [1][2], and whether the short-vol sleeve's "empty
   historical option bars" premise is now stale. Both are single test orders or
   single queries.
10. **State the one-regime limitation in every options gate.** With an unsampled
    tail, deflated-Sharpe and cross-validation machinery cannot see the risk that
    matters most [5][12].

## Sources

[1] Options Level 3 Trading. https://docs.alpaca.markets/us/docs/options-level-3-trading
[2] Options Trading Overview. https://docs.alpaca.markets/us/docs/options-trading-overview
[3] Options Trading. https://docs.alpaca.markets/us/docs/options-trading
[4] What option levels or tiers do you provide? https://alpaca.markets/support/what-option-levels-or-tiers-do-you-provide
[5] Historical Option Data. https://docs.alpaca.markets/us/docs/historical-option-data
[6] Market Data FAQ. https://docs.alpaca.markets/us/docs/market-data-faq
[7] Option chain. https://docs.alpaca.markets/us/reference/optionchain
[8] About Market Data API. https://docs.alpaca.markets/us/docs/about-market-data-api
[9] Historical Data — Alpaca-py. https://alpaca.markets/sdks/python/api_reference/data/option/historical.html
[10] Data source for option historical bars? Alpaca Community Forum. https://forum.alpaca.markets/t/data-source-for-option-historical-bars/17704
[11] Real-time Option Data. https://docs.alpaca.markets/docs/real-time-option-data
[12] Missing morning session in historical option trades — 2024-02-26 and 2024-03-15. https://forum.alpaca.markets/t/missing-morning-session-in-historical-option-trades-2024-02-26-and-2024-03-15-opra/19028
[13] Paper Trading. https://docs.alpaca.markets/us/docs/paper-trading
[14] Paper-trading with Alpaca: the gotchas nobody mentions. https://hmmtrade.com/blog/alpaca-paper-gotchas
[15] The Options Wheel Strategy (How to Trade in Python). https://alpaca.markets/learn/options-wheel-strategy
[16] Dividends Calendar API. https://site.financialmodelingprep.com/developer/docs/stable/dividends-calendar
[17] Dividends Company API. https://site.financialmodelingprep.com/developer/docs/stable/dividends-company
[18] Financial Estimates API. https://site.financialmodelingprep.com/developer/docs/stable/financial-estimates
[19] Price Target Consensus API. https://site.financialmodelingprep.com/developer/docs/stable/price-target-consensus
[20] Price Target Summary API. https://site.financialmodelingprep.com/developer/docs/stable/price-target-summary
[21] Stock Grades API. https://site.financialmodelingprep.com/developer/docs/stable/grades
[22] Stock News API. https://site.financialmodelingprep.com/developer/docs/stable/stock-news
[23] Historical Social Sentiment API (Legacy). https://site.financialmodelingprep.com/developer/docs/social-sentiment-api
[24] FMP API Trading Guide: Mastering Earnings Surprises and Calendar Data. https://site.financialmodelingprep.com/how-to/fmp-api-trading-edge-mastering-earnings-surprises-and-calendar-data
[25] Earnings Calendar API. https://site.financialmodelingprep.com/developer/docs/stable/earnings-calendar
[26] Financial Modeling Prep vs Sharadar for Quant Backtests. https://pickuma.com/for-dev/financial-modeling-prep-vs-sharadar-fundamental-data-api/
[27] Documentation — Fundamentals. https://sharadar.com/docs/fundamentals
[28] Bakshi, G. & Kapadia, N. Delta-Hedged Gains and the Negative Market Volatility Risk Premium. Review of Financial Studies 16(2), 2003. https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf
[29] Timing Option Trades to Suppress Trading Frictions (on Muravyev & Pearson, Option Trading Costs Are Lower Than You Think, RFS 2020). https://www.cxoadvisory.com/equity-options/timing-option-trades-to-suppress-trading-frictions/
[30] Bondarenko, O. Why Are Put Options So Expensive? https://www3.gmu.edu/schools/vse/seor/studentprojects/graduate/2009Fall/ISG/Investment_Optimization/Resources_files/Bondarenko-Puts.pdf
[31] Broadie, M., Chernov, M. & Johannes, M. Understanding Index Option Returns. http://www.columbia.edu/~mnb2/broadie/Assets/EOR_20080618.pdf
[32] Carr, P. & Wu, L. Variance Risk Premiums. Review of Financial Studies, 2009. https://engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf
[33] Volatility Risk Premium Effect. Quantpedia. https://quantpedia.com/strategies/volatility-risk-premium-effect
[34] The Variance Risk Premium is Pervasive. Alpha Architect. https://alphaarchitect.com/the-variance-risk-premium-is-pervasive/
[35] Coval, J. D. & Shumway, T. Expected Option Returns. https://scholarsarchive.byu.edu/facpub/9281/
[36] Dividend Assignment Risk: Short Call Options. Option Alpha. https://optionalpha.com/learn/dividend-assignment-risk
[37] Dividends and Options Assignment Risk. Fidelity. https://www.fidelity.com/learning-center/investment-products/options/dividends-options-assignment-risk
[38] Portfolio base API reference. VectorBT. https://vectorbt.dev/api/portfolio/base/
[39] Portfolio. VectorBT PRO. https://vectorbt.pro/features/portfolio/
[40] Portfolio enums. VectorBT. https://vectorbt.dev/api/portfolio/enums/
[41] Options Chain API: AlphaVantage vs Alpaca for Quant Traders. https://oyamori.com/learning/options-data-api-alphavantage-alpaca/
[42] FINRA Rule 2360: Options. https://www.finra.org/rules-guidance/rulebooks/finra-rules/2360
