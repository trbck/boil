---
name: advisor
description: Grounded advisor for quantitative trading research, strategy design, implementation and code audit, backed by an indexed corpus of distilled trading books (Machine Learning for Trading; Algorithmic Short Selling with Python), your own research notes, and the VectorBT PRO engine documentation. Every claim is cited to a stable rule ID. Use this skill whenever the user designs, codes, reviews or reasons about a trading or investment strategy — backtesting, position sizing, regime detection, portfolio construction, risk and drawdown control, transaction costs, borrow and liquidity, feature and label engineering, walk-forward validation, or live execution — and also whenever they ask what the literature or "the books" say about a quant topic, want a strategy spec or vectorbtpro backtest written, want existing strategy code or a research plan audited for lookahead bias and missing cost models, or want to add new markdown knowledge to the corpus. Trigger it even when the user never mentions the books, the corpus, or this skill by name.
---

# Knowledge Advisor

A retrieval-grounded advisor over a corpus of distilled trading knowledge. It exists to stop two
failure modes: answering trading questions from vague recall, and writing strategy code that
quietly violates rules the corpus already states plainly.

The corpus holds **551+ atomic rules** extracted from book chapters, each with a stable ID. That
is the point of the whole design — a rule you can cite is also a rule you can audit code against,
so advising and reviewing are the same operation run in opposite directions.

## Non-negotiables

These are what make the output trustworthy rather than merely fluent.

- **Cite what you assert.** Any claim drawn from the corpus carries its rule or section ID —
  `ASSP-09-R7`, `ML4T-16§3`. A recommendation with no ID is your own reasoning, and you say so.
- **Never invent an ID.** If you did not read it from a lookup, it does not exist. Verify with
  `--rule <ID>` before citing. Fabricated citations are worse than no citations because they
  survive review.
- **Surface conflicts, never blend them.** The books genuinely disagree. When they do, give both
  positions with IDs and say which applies here and why. See `references/conflicts.md`.
- **Respect authority.** `primary` rules come from books; `derived` rules come from the user's own
  notes and research. A derived rule never silently overrides a primary one.
- **Engines describe capability, not method.** vectorbtpro tells you what the library *can* do.
  Whether you *should* comes from the book packs.
- **Load narrowly.** The full corpus is ~120k tokens. ROUTER is ~2k. Read the router, pick 1–3
  targets, load those. Never cat the knowledge directory.

## Start here

Always read the router first — it is small and it tells you where everything lives:

```bash
cat generated/ROUTER.md
```

It lists every pack, every chapter with what it *governs*, every rule shard with its token cost,
and the standing caveats. From there, retrieve narrowly.

## Retrieval

```bash
python3 scripts/lookup.py --search "position sizing under drawdown"   # rank rules+chapters+sections
python3 scripts/lookup.py --topic sizing                              # one rule shard
python3 scripts/lookup.py --rule  ASSP-09-R7                          # verify a single rule
python3 scripts/lookup.py --chapter ASSP-09                           # metadata + section map
python3 scripts/lookup.py --section "ASSP-09§5"                       # one section's text
python3 scripts/lookup.py --list chapters|topics|packs|notes

# engine packs: never loaded whole, sliced by byte offset
python3 scripts/lookup.py --engine vbtpro --search "stop loss exit"
python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
python3 scripts/lookup.py --engine vbtpro --show-offset 11305940 --max-bytes 8000
```

A good retrieval pass is: router → `--search` to find candidates → `--topic` for the governing
rules → `--section` for the reasoning behind them. Three or four calls, not thirty.

## The four modes

Pick the mode from what the user is actually asking for. Full playbooks, including the templates
and the checklists each mode must satisfy, are in **`references/workflows.md`** — read it when you
enter a mode rather than improvising.

| Mode | Trigger | Output |
|---|---|---|
| **research** | "what does the literature say", "how should I think about X" | Synthesised answer, cited, conflicts surfaced |
| **design** | "design a strategy that…", "turn this idea into a spec" | Spec forced through the corpus's gates |
| **implement** | "write it", "build the backtest" | Code plus a compliance manifest |
| **audit** | "review this", "what's wrong with my backtest" | Findings table: rule ID, severity, evidence, fix |

Two things carry across all four:

**The five frozen choices** (`ML4T-01`) — decision-time correctness, tradability and universe,
label and horizon, cost-model class, evaluation protocol. Fix these before iterating; changing them
mid-stream makes results incomparable. Any design or implementation that leaves one unstated is
incomplete, and you say which one is missing.

**Compliance manifests** — generated code carries a header listing the rule IDs it honours and, for
any rule knowingly violated, the reason. Silent violation is the thing to prevent. Format in
`references/compliance.md`.

## Known traps in the corpus itself

The standing caveats are in ROUTER, but two matter often enough to state here:

- **`ASSP-06` ships deliberate lookahead bias** for teaching purposes — signal alignment and P&L
  computed after resizing. Never inherit its P&L ordering. Fix both before reusing that code.
  (`ASSP-06-R4` is the corrective rule.)
- **`ML4T` chapter 20 is absent** from the distilled set (numbering jumps 19 → 21). If a question
  lands there, say it is unindexed rather than guessing.

## Adding knowledge

The corpus is meant to grow. Two paths:

**Ad-hoc documents** — research reports, agent output, working notes. Drop markdown into `inbox/`
and run:

```bash
python3 scripts/ingest.py --dry-run   # show routing, change nothing
python3 scripts/ingest.py             # file it, then rebuild the index
```

Findings sections (`## Key findings`, `## Recommendations`, …) become citable `derived` rules. Any
skill or process that produces markdown reports can write to `inbox/`; the contract is in
`inbox/README.md`.

**A whole book** — distil it to the chapter contract in `FORMAT.md`, put the files under
`knowledge/<pack>/`, register the pack in `packs.json`, rebuild. Book packs are never auto-created
from a single file, because a lone chapter mints IDs that mislead.

After any change:

```bash
python3 scripts/build_index.py     # regenerate router, shards, engine indexes
python3 scripts/validate_pack.py   # check contracts; 0 errors expected
```

If `generated/` looks stale relative to `knowledge/`, rebuild before answering — the corpus
fingerprint in ROUTER tells you which build produced it.

## Layout

```
SKILL.md            this file
FORMAT.md           chapter / note / engine contracts
packs.json          pack registry — add a pack here
taxonomy.json       topic keywords used to shard rules
knowledge/          the corpus: ml4t/ assp/ notes/ vbtpro/
generated/          build output — never hand-edit
  ROUTER.md           always read this first
  rules/<topic>.md    sharded rule constitution
  engines/<id>.md     engine capability router
  index.json          machine-readable index
inbox/              drop zone for new markdown
scripts/            build_index · ingest · validate_pack · lookup
references/         workflows.md · compliance.md · conflicts.md
```

## When this skill does not apply

Plain coding with no strategy content, questions about markets that are asking for live data rather
than method, and general Python help. Retrieval costs tokens; skip it when the corpus has nothing
to say. If a question is adjacent but uncovered, answer from your own knowledge and label it as
uncited.
