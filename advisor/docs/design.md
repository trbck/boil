# Design record

Why knowledge-advisor is built the way it is. Written at initial implementation; update when a
decision is revisited rather than adding a second account of it.

## Problem

A corpus of distilled trading-book chapters (~120k tokens at the time; ~280k now, growing) needs to support four jobs:
research, strategy design, implementation, and audit of existing code — while staying extensible
along **two** axes: more books, and more capability packs (vectorbtpro first).

Loading the corpus is not an option. Neither is fuzzy recall: the value is in precision, and a
citation nobody can resolve is worse than no citation.

## Decisive observation

The distilled chapters share a rigid skeleton — `**Governs:**`, numbered sections, and a
`## Transferable rules` list. That yielded **551 atomic, imperative, numbered rules**.

That changes the shape of the whole system. Rules with stable IDs are not just retrievable, they
are a **compliance surface**: the same index that answers "what should I do" answers "did this code
do it". Advising and auditing collapse into one mechanism. Every other decision below follows from
protecting that property.

## Decisions

**Files + generated index, not a vector store.** Considered and rejected: LightRAG (already running
locally). The corpus is small, pre-curated and hierarchically organised, so chunk-and-embed would
fracture dense prose and blur citations for no recall benefit. Determinism matters more than
semantic reach here — the same query must return the same IDs in six months, or the citations are
decorative. Revisit if the library reaches a scale where keyword routing genuinely misses.

**Stdlib only, JSON config.** The repo is the master copy and gets installed on remote machines.
Python 3.9 on the dev box has no `tomllib`; PyYAML is present but not guaranteed elsewhere. JSON
plus a deliberately minimal frontmatter parser removes the whole class of "works here, not there".
The frontmatter parser only claims to handle scalars and inline lists — a permissive parser that
silently mis-reads broken YAML would be worse.

**Three retrieval tiers.** Router (~2k tokens, always) → topic rule shard (0.4–2k) → chapter section
or engine slice (on demand). Sharding was forced by arithmetic: 551 rules is ~13k tokens today, and
at four books it would be ~26k — too big to load speculatively. Sharding from day one avoids a
migration later.

**Pack `kind` as the extension hook.** `book` distils to rules; `notes` accepts free-form markdown
and extracts findings; `engine` indexes vendor docs by byte offset without distilling. Adding
vectorbtpro required no change to the core — which is the test the abstraction had to pass.

**Byte offsets for engine packs.** The API reference is 18MB. Heading→offset indexing means a
symbol lookup seeks and slices rather than reading; `Portfolio.from_signals` resolves instantly.

**Conflict registry is hand-curated.** Deciding two rules genuinely disagree needs reading both in
context, so it cannot be generated. It also records **convergences** — where two independent books
agree, the conclusion is better supported than either alone, and that is worth stating.

**Books are never auto-created from the inbox.** A single chapter mints IDs that collide with or
misrepresent a book that isn't there. Ingest refuses and explains.

**Deterministic, timestamp-free builds.** A clean rebuild produces an empty diff, so `generated/`
can be committed and reviewed. Staleness is tracked by a corpus fingerprint instead.

## Bugs found and fixed during implementation

Recorded because each was silent, and each would have quietly degraded retrieval:

1. **Fence desync.** A naive ```` ``` ```` toggle mis-tracked nested and variable-length fences,
   hiding two thirds of the engine's headings (3,670 found vs 9,972 real). Replaced with a
   CommonMark-correct state machine. A related benefit: Python `# comments` inside fenced examples
   are no longer mistaken for headings — `grep` over-counted H1s by 217 for exactly that reason.
2. **Substring keyword matching.** `rag` matched "ave**rag**e" and `metric` matched
   "geo**metric**", misrouting rules. Now anchored at a word boundary, which still permits
   deliberately truncated stems (`simulat`, `psycholog`).
3. **Alphabetical tie-breaks.** Five topics tied at equal score for the position-sizing chapter, and
   the tie fell through to alphabetical order, filing it under `backtesting`. Fixed by scoring
   phrases above single words and title hits above body hits.
4. **Missing `**Source:**` lines** on 25 of 26 ml4t chapters. Rather than editing the corpus, the
   builder synthesises a citation from pack metadata.

## Known limitations

- **Topic assignment is keyword-based** and will misfile occasionally. Mitigations: rules inherit
  their chapter's profile, and any file can pin `topics:` in frontmatter. Rule IDs never depend on
  topics, so a misfiling is cosmetic, not structural.
- **`ML4T` chapter 20 is absent** from the distilled set. Flagged by the validator and in ROUTER.
- **The conflict registry is only as good as its curation** and will drift as packs are added.
- **No evals yet.** Phase 5 below.

## Status

| Phase | Deliverable | State |
|---|---|---|
| 0 | Format contract + validator | done — 0 errors, 1 warning (ch. 20 gap) |
| 1 | Build pipeline, router, rule shards, `research` retrieval | done |
| 2 | Audit workflow + conflict registry | done — registry seeded with 5 conflicts, 7 convergences |
| 3 | Design/implement workflows + compliance manifests | done |
| 4 | vectorbtpro engine pack | done — 10,792 headings indexed |
| 5 | Eval suite + description optimisation | **not started** |

Phase 5 is what remains: realistic prompts, a with-skill/without-skill comparison, and description
tuning so the skill triggers when it should. Until then, triggering quality is unmeasured.
