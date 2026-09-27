---
title: §21 gate audit of the strategies repo — seven changes, two falsified hypotheses
category: audit
source: claude-code-review
date: 2026-08-28
authority: derived
topics: [backtesting, portfolio, costs, process]
---

# §21 gate audit of the strategies repo — seven changes, two falsified hypotheses

Audit of the `strategies` paper-trading repo's §21 quality gate against this corpus's `trading`
domain, 2026-08-28. Every claim below was checked against the code before it was written: each
finding was located in a named file, and two initial hypotheses were **falsified during
verification and dropped** rather than shipped (recorded under *Falsified* so they are not
re-derived). The seven surviving findings were implemented; the full suite went 1468 → 1488 tests,
0 failures.

## Method

Review mode against `references/workflows.md`: read the target (`AGENTS.md`, `docs/RULES.md`,
`docs/VALIDATION.md`, `docs/BACKTEST_STANDARD.md`, `docs/GATE_CALIBRATION.md`, the
`research/` and `sizing/` modules), walk it against the domain review checklist, then confirm each
candidate defect in source before reporting it. Rule IDs verified with `lookup.py --rule` before
citation.

## What the repo already does better than the checklist asks

Two mechanisms have no counterpart in the corpus and are worth naming as prior art. The
**stress-axis vacuity guard**: an override that a `run_fn` silently drops forces its §21 checkbox
to FAIL, because a rubber-stamped box reads as evidence. And the **measured gate calibration**:
4200 null runs establishing the battery's own false-positive rate. Most systematic shops never
learn the error rate of their own gate.

## Key findings

1. **A gate's false-positive rate is a function of sample size, and reporting a verdict without it
   is a category error.** The same §21 battery passes 4.0% of no-edge draws at n≈2500 and 8.5% at
   n≈317 — a 2.1× difference that the verdict line does not carry. Any gate report should print
   its own calibrated error rate for the sleeve's sample regime beside the verdict.

2. **Turnover cost does much of a gate's rejecting, so low-turnover strategies face a materially
   weaker gate.** Switching turnover cost off roughly doubles the null pass rate (4.0% → 9.0%
   daily, 8.5% → 12.5% event) and roughly triples the near-pass rate. A gate's headline size is
   therefore only earned by strategies that actually pay for their turnover.

3. **A block bootstrap cannot generate a left-skew strategy's lethal event, because that event is
   by construction absent from the sample the strategy survived.** Demonstrated: a synthetic
   left-skew sleeve scoring §21 PASS 7/7 shows a −27.9% deepest-decile drawdown and 9% of paths
   negative once single-day replace-mode jumps are injected at 1.5× the worst observed day. The
   clean bootstrap on such a sleeve measures nothing and reads as reassurance.

4. **Anchor a break-even cost ratio to the harshest cost the sweep certifies at, never the
   cheapest tested.** Anchoring to the cheapest row turned a sleeve with 6.7bps break-even into
   "3.3× headroom"; anchoring to the 20bps corner the gate actually certifies at reports 0.3× and
   flags it. Where the sweep never crosses zero, extrapolate the terminal slope and label it
   extrapolated — reporting ">max tested" collapses a Sharpe of 1.7 and a Sharpe of 0.05 into one
   indistinguishable line.

5. **New gate content must ship reported-but-not-gating until every candidate has a reading.**
   Adding a gating checkbox to an established battery retroactively flips the verdict on every
   stored report, which is the mid-stream definition change `ML4T-01` warns against: improvements
   stop being interpretable as stronger signal and become changed definitions. Promotion to a
   gating check is a separate deliberate pass.

6. **Declaration coverage is the honest measure of whether a choice is frozen, and it is usually
   far lower than assumed.** In a repo with a mature gate, 11 of 29 sleeves could be given an
   archetype declaration from their own stated mechanism and only 6 of 29 a holding-period
   declaration; the rest were reported as undeclared rather than guessed. An audit that reports a
   mechanism as "added" without its coverage number has not measured anything.

7. **Guard the switch, not the default.** A configuration whose default is safe can still be
   unsafe to change: the risk lives in the transition, and the effective control is to require the
   governing rule ID in the change's written reason, so the acknowledgement lands in the audit
   journal instead of a dismissed dialog.

## Falsified during verification — do not re-derive

- **"Inverse-vol is the deployed allocator, violating `ASSP-09-R4`."** False. `allocator.scheme`
  defaults to `equal` and `book_allocation` to `budget` (static per-sleeve risk budgets). The
  comment reading "It is the deployed default risk allocator" scopes to *default among the three
  risk allocators*, not to the book. The live exposure is the unguarded **switch**, not the
  default — see finding 7.

- **"Equal-weight sleeve allocation violates `ASSP-06-R7` (never equal-weight)."** False, and a
  level confusion. `ASSP-06-R7` governs position-level sizing within a strategy; sleeve-level
  allocation is governed by conflict **C1**, whose convergence `ML4T-17-R9` says to clear equal
  weight before believing any allocator. The repo's R1 campaign measured exactly that on a
  24-sleeve panel and 1/N won gross and net, so the repo is aligned with the convergence rather
  than in breach of a rule.

## Caveat on authority

These are `derived` observations from one audit of one repo. Findings 1, 2 and 3 generalise as
method; 4 through 7 are engineering conventions that earned their keep here and should be treated
as defaults to argue with, not as book rules. Where any of this appears to contradict a `primary`
rule, the primary rule governs and the disagreement should be surfaced.
