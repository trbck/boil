---
title: Alpaca Index Options (SPX/VIX/XSP) — Envelope, and a Correction to R1
category: research
source: manual
date: 2026-09-09
authority: derived
topics: [options, data, execution, risk]
domain: trading
question: Does Alpaca support index options such as VIX and SPX, and how does that change the equity-options envelope previously recorded?
---

# Alpaca Index Options (SPX/VIX/XSP) — Envelope, and a Correction to R1

The prior note `NOTE-options-strategies-on-alpaca-fmp` mapped Alpaca's options envelope but
covered only **American-style equity and ETF options**. Its scope line claimed "US-listed equity
and index options" while section 1 never treated index options at all, so several of its rules are
either silent on or wrong about them. This note corrects that.

## Method

Verified two ways on 2026-09-09: Alpaca's own product documentation, and direct read-only queries
against a live Alpaca paper account (`options_approved_level: 3`) using
`get_option_contracts` and `get_option_chain`. Contract counts below are actual API responses, not
documentation claims. No orders were submitted, so order-acceptance for index options is asserted
by Alpaca's documentation only and remains unverified by a fill.

## What is available

Alpaca supports Cboe-listed index options: **SPX, SPXW, VIX, VIXW, DJX, XSP**. They are
**cash-settled** and **European-style**, confirmed per contract by the API (`style=european`,
`size=100`). The default roots returned are the weeklies — a `VIX` underlying query returns
`VIXW` contracts, and `SPX` returns `SPXW`. Alpaca's announcement cites a **$0.50 per contract**
fee for US-listed index options against $0.65 for equity options; that figure is from the product
announcement and is not verified against a fill.

## The greeks gap — measured, not inferred

Live chain snapshots, whole-chain counts from the API:

| Underlying | Contracts | With greeks | With IV | With quotes |
|---|---|---|---|---|
| VIX | 1,120 | 0 | 0 | 1,120 |
| SPX | 9,126 | 0 | 0 | 9,126 |
| XSP | 15,968 | 0 | 0 | 15,968 |
| SPY | 11,966 | 9,624 | 9,624 | 11,966 |

Index options receive **no greeks and no implied volatility at all** — not live, not historical —
while quotes are served for every contract. Equity options receive Alpaca-computed
Black-Scholes greeks on roughly 80% of contracts.

## History depth

Index option bars reach back comparably to equity options, bounded by the same ~2024 floor and by
each contract's listing date: `SPX250117C05000000` returns 189 daily bars from 2024-03-07,
`VIX250122C00020000` 180 bars from 2024-04-30, against `SPY250117C00500000` at 251 bars from
2024-01-18. Index options are therefore no less backtestable than equity options.

## Key findings

1. **Alpaca supports Cboe index options — SPX, SPXW, VIX, VIXW, DJX and XSP — cash-settled and European-style, confirmed per contract by the API (`style=european`, `size=100`).** The prior note's envelope covered only American-style equity and ETF options and should not be read as excluding index options.
2. **Index options receive NO greeks and NO implied volatility from Alpaca — zero of 26,214 sampled VIX/SPX/XSP contracts carried either, while quotes were served for all of them.** This corrects `NOTE-options-strategies-on-alpaca-fmp-R1`, which recorded greeks as "live-snapshot only": that is true for equity options but optimistic for index options, where none exist in any form.
3. **Local implied-vol inversion is mandatory rather than optional for index options**, since there is no served field to fall back on even at decision time.
4. **VIX options must be priced off VIX futures forwards, not spot VIX.** Inverting implied vol against spot VIX with a Black-Scholes helper returns a confidently wrong number, so equity-option greeks code is not transferable to VIX without substituting the forward.
5. **European-style, cash-settled index options carry no early-assignment risk at all**, so a dividend early-assignment guard is irrelevant to them; such a guard remains necessary for American-style equity and ETF short calls.
6. **Cash settlement removes assignment into the underlying**, eliminating the "assignment into a falling name" failure mode that dominates cash-secured-put and covered-call archetypes on equities.
7. **Multi-leg calendars and diagonals are blocked on index options**, because Alpaca's `mleg` rule requires European-style legs to share an expiration; the permission to trade calendars applies only to American-style equity options.
8. **Index option history reaches back to at least March 2024, comparable to equity options**, so index archetypes are no less backtestable than equity ones.
9. **Index options carry a ×100 multiplier against the index level, so contract notional dwarfs a small account** — one SPX contract near a 6,400 index level is roughly $640,000 of notional. VIX, at an index level typically in the teens, is the only one of these whose per-contract notional is small enough for a five-figure account.
10. **Alpaca's index-option order acceptance is documented but unverified by a fill here**, unlike the equity multi-leg path, where a real 4-leg order was accepted and a naked short was rejected with code 40310000.

## Recommendations

1. **Treat `NOTE-options-strategies-on-alpaca-fmp-R1` as scoped to equity and ETF options.** For index options the stronger statement holds: no greeks or IV are served at all.
2. **Do not reuse spot-based Black-Scholes IV inversion for VIX options.** Substitute the VIX futures forward for spot, or exclude VIX from any greek-conditioned archetype.
3. **Drop the dividend early-assignment guard from index-option designs** and keep it for American-style equity short calls, where the risk is real and mechanical.
4. **Prefer index options where the archetype's main risk is assignment path** rather than direction, since cash settlement removes that risk entirely.
5. **Verify index-option order acceptance with one small paper order before designing around it**, mirroring how the equity multi-leg envelope was established by a real accepted order rather than by documentation.
6. **Size index-option positions off the ×100 multiplier against the index level, not against an equity-scale notional assumption.**
