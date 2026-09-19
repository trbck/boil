# advisor

A Claude Code skill that answers questions, designs and produces work, and audits existing
artefacts **against indexed corpora distilled from books**, citing a stable rule ID for every
claim. It is multi-domain: each domain carries its own corpus, taxonomy, rule shards and conflict
registry, and the skill's own description is generated from whichever domains are installed.

The repository root *is* the skill, so installing is a clone into your skills directory.

<!-- STATS: rewritten by scripts/build_index.py — do not hand-edit the line below. -->
```
2 domains · 798 rules · 49 book chapters · 26 topic shards
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

One command, on any machine with git and python3:

```bash
git clone <your-remote> ~/src/advisor && ~/src/advisor/bin/advisor-sync
```

`bin/advisor-sync` clones or fast-forwards, rebuilds the generated surface, validates it, and
symlinks the result into `~/.claude/skills/advisor`. It is idempotent — run it again to update. It
refuses to fast-forward over uncommitted work, because the corpus is edited in place.

```bash
bin/advisor-sync                       # install or update
bin/advisor-sync --check               # verify an existing install, change nothing
bin/advisor-sync --copy                # copy instead of symlink, for sandboxes
bin/advisor-sync --checkout ~/code/advisor --skills-dir /tmp/skills
```

A `--copy` install is a snapshot: anything ingested into it is lost on the next sync, so ingest in
the checkout and push.

No dependencies. Python 3.8+, standard library only — deliberately, so it runs identically on a
laptop and on a remote box with nothing installed.

If you keep the engine pack (see **Licensing**), drop your `llms*.txt` files into
`domains/trading/knowledge/vbtpro/` before building. Without them the rest of the corpus works
normally and the validator warns that engine retrieval is unavailable.

### Bundles

For runtimes that cannot clone, export one domain as a self-contained `.skill` zip:

```bash
python3 scripts/package_domain.py --domain decisions      # → dist/advisor-decisions.skill
python3 scripts/package_domain.py --all
```

Engine packs are excluded by default — they are licensed, and they are almost all of the bytes.
The bundle is rebuilt rather than copied, so its `SKILL.md` describes exactly what shipped rather
than advertising domains it does not contain. Output is byte-reproducible.

| Bundle | Size | Files |
|---|---|---|
| `advisor-decisions.skill` | 197 KB | 48 |
| `advisor-trading.skill` | 569 KB | 75 |

## Quickstart

```bash
cat generated/<domain>/ROUTER.md                                            # the map — start here

python3 scripts/lookup.py --search "position sizing under drawdown"
python3 scripts/lookup.py --topic sizing                           # one rule shard
python3 scripts/lookup.py --rule ASSP-09-R7                        # verify a citation
python3 scripts/lookup.py --section "ASSP-09§5"                    # read the reasoning
python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
```

The last line needs the engine pack's licensed sources, which are gitignored and so
absent from a clone. Without them engine retrieval reports itself unavailable rather
than returning nothing — a query that came back empty would read as "the tool cannot
do that", which is not what an absent file means.

## Adding knowledge

**Reports and notes** — drop markdown in `inbox/`, then:

```bash
python3 scripts/ingest.py --domain <id> --dry-run
python3 scripts/ingest.py --domain <id>
```

Sections headed *Key findings* / *Recommendations* / *Takeaways* become citable `derived` rules.
Any skill that emits markdown can write to `inbox/`; the contract is in `inbox/README.md`.

**A whole book** — distil it to the chapter contract in `FORMAT.md`, put the files in
`domains/<domain>/knowledge/<pack>/`, register the pack in `domains/<domain>/packs.json`, rebuild.

## How it works

Three tiers, so the corpus never loads whole:

| Tier | Artifact | Size | When |
|---|---|---|---|
| 1 | `generated/<domain>/ROUTER.md` | ~2k tokens | always |
| 2 | `generated/<domain>/rules/<topic>.md` | 0.4–2k tokens each | per topic |
| 3 | chapter sections, engine slices | on demand | per question |

The full corpus is roughly 280k tokens and growing (the exact figure is stamped into
`SKILL.md` at build time); a typical grounded answer costs 8–15k.

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

**The VectorBT PRO documentation is proprietary.** `domains/*/knowledge/*/llms*.txt` and the derived
byte index are **gitignored by default**, and `validate_pack.py` asserts that no proprietary source
is git-tracked — a directory move silently un-ignores path-shaped rules, so the outcome is checked
rather than the pattern. Redistributing them — especially on a public remote — would
breach the vendor's licence.

If your remote is private and your licence permits it, remove those lines from `.gitignore`.
Otherwise each install supplies its own copy; everything else in the repo works without it, and
`validate_pack.py` will tell you the sources are missing rather than failing obscurely.

The distilled book chapters are your own summaries, not reproductions — but they are derived from
copyrighted works, so consider whether your remote should be private.

## Repo layout

```
SKILL.md            the skill — generated from templates/SKILL.md.tmpl, never hand-edited
FORMAT.md           chapter / note / engine contracts
domains/<id>/       domain.json · packs.json · taxonomy.json · conflicts.md · knowledge/
generated/<id>/     build output — ROUTER.md · rules/ · engines/ · index.json
inbox/              drop zone for new markdown
bin/advisor-sync    install or update from git
scripts/            build_index · ingest · validate_pack · lookup · suggest_* · package_domain
references/         workflows · compliance · maintaining
templates/          SKILL.md.tmpl · modes.default.json
dist/               exported bundles (gitignored)
docs/               design.md — why it is built this way · roadmap.md — where it is going
```

## Maintenance

```bash
python3 scripts/build_index.py     # after any corpus change
python3 scripts/validate_pack.py   # contract check; --strict to fail on warnings
```

Each `ROUTER.md` carries a corpus fingerprint. If it disagrees with the domain's `knowledge/`,
rebuild before trusting an answer. The build is deterministic and timestamp-free, and the
fingerprint is computed over repo-relative paths, so the same corpus yields the same id on any
machine and a clean rebuild produces an empty diff.

`validate_pack.py` recomputes the fingerprint from disk and warns when `generated/` lags, so a
stale index is a reported condition rather than something you have to remember to notice.

## Testing

```bash
python3 -m pytest tests -q                 # contracts, ID stability, documented commands
python3 scripts/rule_baseline.py           # no cited ID has vanished or changed meaning
python3 scripts/eval_retrieval.py --scoped # retrieval quality, one domain per question
python3 scripts/check_citations.py answer.md   # do the IDs in this answer exist? (the skill runs this on every answer)
```

Three things are checked that the corpus itself cannot tell you:

- **The ID contract.** `tests/rule-ids.baseline` pins every rule ID to a content hash. An ID that
  disappears breaks citations that point at it; an ID whose `primary` text changes underneath it
  is worse, because those citations still resolve — to different words. Both fail the build.
  Regenerate deliberately with `scripts/rule_baseline.py --update`, after fixing the citations.
- **The documented commands.** Every read-only command in a ```bash block in the docs is extracted
  and run. Documentation that is never executed drifts silently; this is how the `ingest.py`
  examples were wrong for as long as two domains had been installed.
- **Citations in output.** `check_citations.py` resolves every ID-shaped token in a piece of
  advisor output and reports what does not exist. A fabricated ID is worse than a missing one — it
  imitates the diligence it lacks — and it is the one failure here that a script can catch
  outright. `--require-citations` additionally fails an answer that grounded nothing at all.
