# knowledge-advisor

A Claude Code skill that answers quantitative-trading questions, designs strategies, writes
backtests and audits existing code **against an indexed corpus of trading knowledge**, citing a
stable rule ID for every claim.

The repository root *is* the skill, so installing is a clone into your skills directory.

```
551 rules · 36 book chapters · 14 topic shards · 10k indexed engine symbols
```

## Why it exists

Two failure modes it is built to prevent:

1. **Answering from vague recall.** Trading advice that sounds right and cites nothing is
   unfalsifiable. Here every assertion carries an ID you can look up.
2. **Code that silently violates known rules.** The corpus already states, plainly, that signals
   must be shifted a bar and P&L accrued before resizing. Generated code carries a manifest saying
   which rules it honoured and which it knowingly broke, and why.

Because rules are addressable, advising and auditing are the same operation in opposite directions.

## Install

```bash
git clone <your-remote> ~/.claude/skills/knowledge-advisor
cd ~/.claude/skills/knowledge-advisor
python3 scripts/build_index.py       # regenerate the index (~0.3 s for books, ~10 s with engines)
python3 scripts/validate_pack.py     # expect 0 errors
```

No dependencies. Python 3.8+, standard library only — deliberately, so it runs identically on a
laptop and on a remote box with nothing installed.

If you keep the engine pack (see **Licensing**), drop your `llms*.txt` files into
`knowledge/vbtpro/` before building.

## Quickstart

```bash
cat generated/ROUTER.md                                            # the map — start here

python3 scripts/lookup.py --search "position sizing under drawdown"
python3 scripts/lookup.py --topic sizing                           # one rule shard
python3 scripts/lookup.py --rule ASSP-09-R7                        # verify a citation
python3 scripts/lookup.py --section "ASSP-09§5"                    # read the reasoning
python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
```

## Adding knowledge

**Reports and notes** — drop markdown in `inbox/`, then:

```bash
python3 scripts/ingest.py --dry-run
python3 scripts/ingest.py
```

Sections headed *Key findings* / *Recommendations* / *Takeaways* become citable `derived` rules.
Any skill that emits markdown can write to `inbox/`; the contract is in `inbox/README.md`.

**A whole book** — distil it to the chapter contract in `FORMAT.md`, put the files in
`knowledge/<pack>/`, register the pack in `packs.json`, rebuild.

## How it works

Three tiers, so the corpus never loads whole:

| Tier | Artifact | Size | When |
|---|---|---|---|
| 1 | `generated/ROUTER.md` | ~2k tokens | always |
| 2 | `generated/rules/<topic>.md` | 0.4–2k tokens each | per topic |
| 3 | chapter sections, engine slices | on demand | per question |

The full corpus is ~120k tokens; a typical grounded answer costs 8–15k.

**Rule IDs** are `<PACK>-<CH>-R<n>` (`ASSP-09-R7`), sections `<PACK>-<CH>§<n>` (`ASSP-09§5`). They
derive from chapter and ordinal position, so they stay stable across rebuilds. Renumbering rules in
a published chapter breaks citations — append instead.

**Retrieval is deterministic** — keyword ranking and byte offsets, no embeddings, no server. The
same query returns the same IDs in six months, which is what makes a citation worth anything.

**Engine packs** are indexed rather than distilled. An 18MB API reference is scanned once into a
heading→byte-offset map, then sliced on demand; the file is never read end to end.

## Pack kinds

| Kind | For | Contributes |
|---|---|---|
| `book` | Distilled chapters meeting the chapter contract | `primary` rules |
| `notes` | Research reports, agent output, conventions | `derived` rules |
| `engine` | Large vendor documentation | capability lookup, no rules |

`derived` never silently overrides `primary`; a contradiction is surfaced, not resolved by
precedence.

## Licensing

**The VectorBT PRO documentation is proprietary.** `knowledge/vbtpro/*.txt` and its 3.5MB derived
index are **gitignored by default**. Redistributing them — especially on a public remote — would
breach the vendor's licence.

If your remote is private and your licence permits it, remove those lines from `.gitignore`.
Otherwise each install supplies its own copy; everything else in the repo works without it, and
`validate_pack.py` will tell you the sources are missing rather than failing obscurely.

The distilled book chapters are your own summaries, not reproductions — but they are derived from
copyrighted works, so consider whether your remote should be private.

## Repo layout

```
SKILL.md            the skill: modes, rules of engagement
FORMAT.md           chapter / note / engine contracts
packs.json          pack registry
taxonomy.json       topic keywords used to shard rules
knowledge/          the corpus
generated/          build output — never hand-edit
inbox/              drop zone for new markdown
scripts/            build_index · ingest · validate_pack · lookup · ka_common
references/         workflows · compliance · conflicts
docs/design.md      why it is built this way
```

## Maintenance

```bash
python3 scripts/build_index.py     # after any corpus change
python3 scripts/validate_pack.py   # contract check; --strict to fail on warnings
```

`ROUTER.md` carries a corpus fingerprint. If it disagrees with what is in `knowledge/`, rebuild
before trusting an answer. The build is deterministic and timestamp-free, so a clean rebuild
produces an empty diff.
