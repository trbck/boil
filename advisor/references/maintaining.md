# Maintaining the corpus

How knowledge gets in, and what to run afterwards. This is the maintainer half of the skill;
`SKILL.md` keeps only what is needed to answer a question. Read this when the user wants to add a
document, a research run, a book or a whole domain — or when `generated/` looks stale.

## Adding knowledge

The corpus is meant to grow. Two paths:

**Ad-hoc documents** — research reports, agent output, working notes. Drop markdown into `inbox/`
and run:

```bash
python3 scripts/ingest.py --domain <id> --dry-run   # show routing, change nothing
python3 scripts/ingest.py --domain <id>             # file it, then rebuild the index
```

Findings sections (`## Key findings`, `## Recommendations`, …) become citable `derived` rules. Any
skill or process that produces markdown reports can write to `inbox/`; the contract is in
`inbox/README.md`.

**A whole book** — distil it to the chapter contract in `FORMAT.md`, put the files under
`domains/<domain>/knowledge/<pack>/`, register the pack in `domains/<domain>/packs.json`, rebuild.
Book packs are never auto-created from a single file, because a lone chapter mints IDs that
mislead.

### `advisor add` — research that becomes knowledge

`advisor add "<question>"` runs deep research and files the result so its findings become
citable rules. Only the model can invoke the `hyperresearch` skill, so this is a workflow, not
a script:

1. Confirm the question and the tier with the user (`light` by default — minutes, not an hour).
2. Invoke the `hyperresearch` skill in the research root. It writes
   `research/runs/<vault_tag>/run.json` and records every step transition there.
3. Report progress between steps with `scripts/research_status.py <vault_tag>` — one line, e.g.
   `run efield-a3f9b7 · light · step 10 (2/5 done) · running · 6 sources · $0.14 · 9 min elapsed`.
   Do not poll in a tight loop; check it between steps.
4. On completion, run `scripts/research_note.py --run <vault_tag> --dry-run`. **Show the user the
   findings that would become rules and get an explicit yes** — `FORMAT.md` is explicit that a
   sloppy findings section pollutes the constitution, so this gate is not optional.
5. Run `scripts/research_note.py --run <vault_tag>` for real, then `scripts/ingest.py --domain
   <id>` — `--domain` is required whenever more than one domain is installed, and
   `research_note.py --domain` does not carry through, it only records frontmatter. Report the
   new rule IDs (`NOTE-<slug>-R1` …).

```bash
python3 scripts/research_status.py <vault_tag> --research-root ~/.advisor-research
python3 scripts/research_note.py --run <vault_tag> --dry-run
python3 scripts/research_note.py --run <vault_tag>
python3 scripts/ingest.py --domain <id>
```

The note carries `run:` and `question:` frontmatter back to the manifest that produced it, so a
stale finding can always be traced to the run that made it.

**A whole domain** — create `domains/<id>/domain.json` and `packs.json`, then bootstrap the
taxonomy rather than hand-authoring it:

```bash
python3 scripts/suggest_taxonomy.py --domain <id>   # writes taxonomy.suggested.json — relabel it
python3 scripts/suggest_conflicts.py --domain <id>  # candidate registry entries, needs 2+ packs
```

Both write to review files and never touch `taxonomy.json` or `conflicts.md`, because topic labels
and conflict resolutions are judgement calls.

After any change:

```bash
python3 scripts/build_index.py     # regenerate routers, shards, engine indexes, this file
python3 scripts/validate_pack.py   # check contracts; 0 errors expected
python3 -m pytest tests -q            # ID contract, documented commands, citations
```

If `generated/` looks stale relative to a domain's `knowledge/`, rebuild before answering — the
corpus fingerprint in each ROUTER tells you which build produced it.

## Layout

```
SKILL.md                    the skill — generated, never hand-edited
FORMAT.md                   chapter / note / engine contracts
domains/<id>/
  domain.json               title, summary, scope — feeds this file's description
  packs.json                pack registry — add a book here
  taxonomy.json             topic keywords used to shard rules
  conflicts.md              conflict & convergence registry, hand-curated
  knowledge/<pack>/         the corpus
generated/<id>/             build output — never hand-edit
  ROUTER.md                   always read this first
  rules/<topic>.md            sharded rule constitution
  engines/<id>.md             engine capability router
  index.json                  machine-readable index
inbox/                      drop zone for new markdown
scripts/                    build_index · ingest · validate_pack · lookup · suggest_*
references/                 workflows.md · compliance.md · maintaining.md (this file)
templates/                  SKILL.md.tmpl · modes.default.json
```
