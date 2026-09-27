# Rules — Sorting, ranking and comparison cost

`18` rules · ~399 words · ~538 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-03 — Sorting

<sub>Algorithms to Live By</sub>

- **ATLB-03-R1** — **Expect dis-economies of scale in any ordering task.** Doubling the batch more than doubles the work, which inverts the usual instinct to batch things up.
- **ATLB-03-R2** — **Reduce the batch before optimising the method.** Sorting more often in smaller quantities beats a cleverer algorithm most of the time.
- **ATLB-03-R3** — **Analyse the worst case, not the average or the best,** whenever you need to make a guarantee.
- **ATLB-03-R4** — **Judge cost by growth class, not by constants** — but remember Big-O deliberately ignores constants, so it misleads at small n.
- **ATLB-03-R5** — **Never sort what you will not search.** Sorting the unsearched is total waste; searching the unsorted is merely inefficient. Given uncertainty, **err toward messiness**.
- **ATLB-03-R6** — **Justify heavy up-front sorting against three conditions**: it will certainly be searched, repeatedly, and sort time is cheaper than search time. Google clears all three; your bookshelf and inbox clear none.
- **ATLB-03-R7** — **As search gets cheaper, sorting loses value.** Reassess filing habits whenever search improves, rather than carrying them forward.
- **ATLB-03-R8** — **Use coarse buckets before fine ordering**, and derive the buckets from the known distribution — good buckets split the load evenly, bad ones achieve nothing.
- **ATLB-03-R9** — **Do not confuse a single-elimination winner with a ranking.** Such a format determines first place and leaves everything else unsorted; second place is not evidence.
- **ATLB-03-R10** — **Under noisy comparison, prefer robust methods over efficient ones.** Efficiency moves items far per comparison, so early errors become permanent.
- **ATLB-03-R11** — **Trust accumulated round-robin standings over knockout results.** The long tally is the fault-tolerant measurement; the bracket is a lottery weighted by skill.
- **ATLB-03-R12** — **Compute how much a series result actually establishes** before treating it as evidence of quality — six 70% rounds confer only ~12% confidence.
- **ATLB-03-R13** — **Minimising comparisons is not always the objective.** Where the comparisons themselves have value, or where sustained uncertainty is the product, more of them is correct.
- **ATLB-03-R14** — **Expect conflict to grow super-linearly with group size**, and treat capping group size as a legitimate intervention.
- **ATLB-03-R15** — **Do not remove a group's means of resolving rank** and expect less conflict; an unfinishable sort produces more.
- **ATLB-03-R16** — **Replace comparison with measurement wherever possible.** Any shared benchmark — however crude — converts a fight into a race and collapses the cost of establishing status from linearithmic to constant.

### ATLB-04 — Caching

<sub>Algorithms to Live By</sub>

- **ATLB-04-R9** — **Do not group like with like by default.** Content-based grouping costs sorting time and delivers no retrieval guarantee.

### ATLB-07 — Overfitting

<sub>Algorithms to Live By</sub>

- **ATLB-07-R13** — **Trust the first factors you generate.** If the earliest considerations are the most important, later ones mostly add noise.

