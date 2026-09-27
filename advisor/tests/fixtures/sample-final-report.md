# Cross-sectional momentum decay in small-cap equities

## Method

We ran a width sweep across 40 primary sources on cross-sectional momentum in
small-cap US equities, then investigated two depth loci: transaction-cost
sensitivity and regime dependence. Sources were cross-checked against at least
one independent replication where available.

## Evidence

Momentum ranking on a 6-month lookback, rebalanced monthly, produces a decay
curve that is steep in the first three weeks after formation and flattens
after roughly two months. The effect is materially weaker in small-caps once
a 25bp round-trip cost is assumed, and reverses sign during high-volatility
regimes (VIX > 30).

## Recommendations

1. Use a 6-month formation window with a 1-week skip to avoid the short-term
   reversal contaminating the signal.
2. Cap round-trip cost assumptions at 15bp before trusting a small-cap
   momentum backtest; above 25bp the edge does not survive.
3. Suspend the signal, or flip to a defensive sizing rule, when a realized
   volatility regime filter flags VIX > 30.

## Open questions

Whether the decay half-life is stable out of sample beyond 2024 remains
untested; the width sweep found no source covering 2025 realized returns.
