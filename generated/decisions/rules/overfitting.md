# Rules — Overfitting — when to think and measure less

`17` rules · ~393 words · ~530 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-00 — Introduction: Algorithms to Live By

<sub>Algorithms to Live By</sub>

- **ATLB-00-R4** — **Do not equate rigour with exhaustiveness.** For hard problems the best available methods use approximation, randomness and early stopping *by design*.

### ATLB-07 — Overfitting

<sub>Algorithms to Live By</sub>

- **ATLB-07-R1** — **Judge a model by how it generalises, never by how well it fits what you already have.** Perfect fit is a warning sign, not a result.
- **ATLB-07-R2** — **Test stability under perturbation.** Re-fit with slight noise or a different sample; a model that swings wildly is overfitted regardless of its fit statistics.
- **ATLB-07-R3** — **Add a factor only if it is significantly better, not merely better.** Complexity must earn its place against an explicit penalty.
- **ATLB-07-R4** — **Name the gap between your metric and your goal before optimising.** Every measurement is a proxy; the size of that gap determines how hard you should push.
- **ATLB-07-R5** — **Assume that anything you measure and reward will be optimised — including in ways you did not intend.** Perverse outcomes are usually competent optimisation of a badly chosen target.
- **ATLB-07-R6** — **Cross-validate on held-out data**, and additionally **cross-validate the metric itself** against a different, harder-to-game evaluation applied to a small sample.
- **ATLB-07-R7** — **Treat divergence between your primary metric and your spot-check as the alarm**: rising scores with falling independent assessment means the target has been gamed.
- **ATLB-07-R8** — **Drive weak factors to zero rather than shrinking them.** A short list of things that matter beats a long list of things that might.
- **ATLB-07-R9** — **Prefer a rule that ignores the data when your estimates are unreliable.** A strategy that never fits the data cannot overfit it — which is why 50/50 can beat optimisation.
- **ATLB-07-R10** — **Run the regularize check explicitly**: are the quantities I am relying on hard to estimate, and does my method put heavy weight on them? If yes, simplify.
- **ATLB-07-R11** — **Treat time spent deliberating as a complexity knob.** More time means more factors and more overfitting, not automatically a better decision.
- **ATLB-07-R12** — **Bound deliberation in advance** — to a page, a timebox, a fixed number of factors — and decide when the bound is reached.
- **ATLB-07-R13** — **Trust the first factors you generate.** If the earliest considerations are the most important, later ones mostly add noise.
- **ATLB-07-R14** — **Match your tool's resolution to your certainty.** Use a blunt instrument early; fine detail invites precision you have not earned.
- **ATLB-07-R15** — **Value historical constraint as robustness, not as inefficiency.** Being imperfectly adapted to the present is what survives changes in the present.
- **ATLB-07-R16** — **Discount fast-moving consensus.** Rapid information flow enables rapid overfitting at the scale of a whole culture.

