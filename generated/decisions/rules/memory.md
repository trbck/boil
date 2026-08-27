# Rules — Caching, retention and what to forget

`19` rules · ~450 words · ~607 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-01 — Optimal Stopping

<sub>Algorithms to Live By</sub>

- **ATLB-01-R4** — **Expect to fail ~63% of the time and do not treat that as evidence the method is broken.** Optimal play still misses the best option most of the time.
- **ATLB-01-R11** — **If passed options can be recalled, look longer** (61%) and keep an explicit fallback to the best one that got away.

### ATLB-04 — Caching

<sub>Algorithms to Live By</sub>

- **ATLB-04-R1** — **Build a hierarchy rather than choosing between fast and large.** Small-and-fast backed by large-and-slow beats either alone, and applies to physical storage as much as digital.
- **ATLB-04-R2** — **Have a cache even if you cannot manage it well.** Random eviction is far better than nothing; do not let policy debates block the basic structure.
- **ATLB-04-R3** — **Evict by Least Recently Used, not First In First Out.** "When did I last use it?" is a much better question than "how long have I had it?", though both sound equally sensible.
- **ATLB-04-R4** — **Assume temporal locality unless you know otherwise** — what was just used is most likely to be used next, and the longest-untouched is the safest to discard.
- **ATLB-04-R5** — **Treat recency as your substitute for clairvoyance.** Where the future is unknown, the reversed past is the best available predictor.
- **ATLB-04-R6** — **Cache by proximity, not just by speed.** When nearness is the scarce resource, keeping copies near the point of use is the whole win.
- **ATLB-04-R7** — **Place items in the cache closest to where they are used**, even when that violates category logic. Vacuum bags behind the couch beats vacuum bags with the cleaning supplies.
- **ATLB-04-R8** — **Add levels above and below your main cache**, and demote between them by LRU.
- **ATLB-04-R9** — **Do not group like with like by default.** Content-based grouping costs sorting time and delivers no retrieval guarantee.
- **ATLB-04-R10** — **Always return a used item to the front.** This bounds your worst-case search time at twice the theoretical optimum — a guarantee no other placement rule provides.
- **ATLB-04-R11** — **Recognise a working pile as a self-organising structure**, not disorder to be corrected. Reorganising it by category makes retrieval worse.
- **ATLB-04-R12** — **Display collections by last-accessed rather than alphabetically**, wherever the interface allows it.
- **ATLB-04-R13** — **Surface what was recently *used*, not what was recently *added*.** Most displays privilege new arrivals; recency of use is the better predictor of demand.
- **ATLB-04-R14** — **Predict aggregate demand rather than individual demand** when pre-positioning resources — the law of large numbers makes the group tractable where the person is not.
- **ATLB-04-R15** — **Expect retrieval to slow as expertise grows, and do not read it as decline.** A larger store is a harder search problem; the lag is evidence of the size of the archive, not the failure of the mechanism.

### ATLB-05 — Scheduling

<sub>Algorithms to Live By</sub>

- **ATLB-05-R18** — **Refuse work whose working set will not fit**, before the collapse rather than after.

### ATLB-06 — Bayes's Rule

<sub>Algorithms to Live By</sub>

- **ATLB-06-R8** — **Calibrate surprise to the distribution.** Under a power law, be *most* alarmed when a long-running thing has run longest; venerability is not safety.

