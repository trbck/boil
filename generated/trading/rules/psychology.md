# Rules — Behaviour, adherence & journaling

`17` rules · ~312 words · ~421 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ASSP-02 — 10 Classic Myths About Short Selling

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-02-R7** — When a short becomes emotionally satisfying, **that is an exit signal**, not a conviction signal.

### ASSP-10 — The Trading Journal

<sub>Algorithmic Short Selling with Python, 2nd ed.</sub>

- **ASSP-10-R1** — **Log missed trades and overrides, not just fills.** The executed log is the surviving fleet; the missed signals are the planes that never came back.
- **ASSP-10-R2** — **Classify with a single outer merge on (date, ticker, broker)** using `indicator=True`. Three categories fall out of one operation.
- **ASSP-10-R3** — **Never let missed/override records mutate the portfolio.** They are pure audit rows, tagged for separate study.
- **ASSP-10-R4** — **Preserve intent fields (price, stop, target, risk) on missed trades** — that is the data that reveals *why* you didn't act.
- **ASSP-10-R5** — **FIFO with per-lot patching** handles pyramids, partial exits, and reversals in one code path. Pro-rate commission across closed lots; carry the position sign into the P&L calculation.
- **ASSP-10-R6** — **Store lots as separate portfolio rows with their own `entry_date`** or FIFO cannot work.
- **ASSP-10-R7** — **Make every write idempotent** (check-before-append, patch-same-values). Nightly jobs get re-run.
- **ASSP-10-R8** — **Design against friction first.** Pre-populated defaults, dropdowns, phone forms. Automation everywhere data already exists.
- **ASSP-10-R9** — **Reward completeness, not performance.** Score the process out of 120; compound a streak multiplier at `1 + streak/20`; forgive one missed weekday.
- **ASSP-10-R10** — **Track directional accuracy (`bulls_eye`) *with* the stated reasoning.** Correct calls with bad reasoning are luck; that distinction is the whole point.
- **ASSP-10-R11** — **Prompt the AI to analyze behavior, never P&L.** Good psychology can produce a bad week and vice versa.
- **ASSP-10-R12** — **Ask whether kaizen entries evolve or merely repeat.** A recurring unchanged intention is a signal to make a structural change, not to try harder.
- **ASSP-10-R15** — **Watch the pre-vs-post mindset delta.** Sitting at 3 is the goal, not sitting at 5.

### ML4T-10 — Text Feature Engineering

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-10-R14** — **Prefer abstention to a low-confidence record,** and validate at the pipeline boundary.

### ML4T-15 — Causal Machine Learning

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-15-R3** — **More controls is not safer.** Mediators change the estimand, colliders open closed paths, treatment descendants introduce post-treatment bias.

### ML4T-24 — Autonomous Agents

<sub>Machine Learning for Trading, 3rd ed.</sub>

- **ML4T-24-R26** — **Test security adversarially with specified expected allow/deny behavior and required log fields** — converting posture from narrative assurance to measurable behavior.

