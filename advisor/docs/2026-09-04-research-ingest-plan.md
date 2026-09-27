# `/advisor add` — research that becomes knowledge

**Date:** 2026-09-04
**Status:** plan, not yet built
**One-line:** `advisor add "how do I find a profitable trading strategy"` runs hyperresearch, files the report as a `notes` pack, and the findings become citable rules.

## Why this is mostly wiring

`FORMAT.md` already specifies everything this needs. Its own example frontmatter reads
`source: hyperresearch`. The pipeline exists:

```
inbox/*.md → scripts/ingest.py → knowledge/notes/<category>/ → build_index.py → lookup.py
                                  findings become NOTE-<slug>-R<n> rules, authority: derived
```

What is missing is the front half (running the research and shaping its output) and a way to
search a report's *body* rather than only its findings.

## The split that keeps citations trustworthy

Two stores, two jobs. This is the design decision the rest follows from.

| | holds | retrieval | reproducible | latency |
|---|---|---|---|---|
| **Deterministic index** (existing) | book rules + note **findings** | BM25 | yes, forever | microseconds |
| **Research store** (new, slim-llm-memory) | note **bodies**: method, evidence, reasoning | hybrid BM25 + embeddings | no — model-dependent | ~50-500 ms |

A finding is a sharp claim with a stable ID, so it belongs in the deterministic index and
stays citable in six months. A report body is long prose where the nuance lives; it is worth
semantic search and is not worth an ID. Keeping them apart means adding research never
weakens the promise that `ATLB-01-R3` means the same thing next year.

**Speed follows from the split.** The default lookup path never embeds anything and never
touches Ollama. `--deep` is opt-in.

## Phases

### Phase 1 — shape and file a report (no new dependencies)

`scripts/research_note.py --run <vault_tag> [--domain trading] [--topics a,b] [--dry-run]`

- Reads `research/runs/<vault_tag>/final_report.md` and `query.md`.
- Writes `inbox/<date>-<slug>.md` with the frontmatter `FORMAT.md` already defines:
  `title` (from H1), `category: research`, `source: hyperresearch`, `date`, `topics`,
  `authority: derived`, plus `run: <vault_tag>` and `question:` for provenance.
- Normalises the findings heading to one `ingest.py` recognises (**Key findings**), so the
  numbered items become rules. If the report has no such section, say so and write the note
  without one rather than inventing findings.
- `--dry-run` prints the frontmatter and the findings that *would* become rules.

**Check:** a fixture report in → a note with valid frontmatter out → `ingest.py` files it →
`build_index.py` succeeds → `lookup.py --rule NOTE-<slug>-R1` prints the finding.

### Phase 2 — the command and its status feedback

`advisor add "<question>"` is a documented workflow in `SKILL.md`, not a shell script,
because only the model can invoke the hyperresearch skill. The steps:

1. Confirm the question and the tier (`light` by default — minutes, not an hour).
2. Invoke hyperresearch; it writes `research/runs/<tag>/run.json` and records every step
   transition there.
3. `scripts/research_status.py <tag>` renders that manifest as one line:
   `run efield-a3f9b7 · step 7/16 depth-investigate · 12 sources · 14 min elapsed`.
   Report it between steps; do not poll in a tight loop.
4. On completion run Phase 1's script with `--dry-run`, **show the user the findings that
   would become rules, and get a yes**. `FORMAT.md` is explicit that a sloppy findings
   section pollutes the constitution, so this gate is not optional.
5. Ingest, rebuild, and report the new rule IDs.

**Check:** the status line renders from a fixture `run.json`; the workflow is documented with
the exact commands.

### Phase 3 — searchable report bodies (slim-llm-memory)

`scripts/deep_index.py` builds one `library()` under `generated/research-store/`, one topic
per domain, from note bodies.

```python
from slim_llm_memory import library
db = library("generated/research-store", embedder="ollama:nomic-embed-text")
db.topic("trading").add({note_path: body})     # unchanged notes are hash-skipped
```

`lookup.py --deep "<query>"` queries it and prints hits labelled `research:` with their note
and heading, alongside the usual results. Default lookup is untouched.

- Re-indexing after one new report embeds only that report's chunks (content-hash skip).
- Offline fallback: if Ollama is not reachable, `--deep` uses `mode="keyword"`, which is
  BM25 over the same store and needs no model. It degrades, it does not fail.
- This phase earns its keep at roughly ten reports. Below that, BM25 over findings finds
  everything. Build phases 1 and 2 first and add this when the corpus justifies it.

**Check:** index two fixture reports, confirm a paraphrased query finds the right body
section, and confirm `--deep` adds no latency to the default path.

## Risks worth naming

- **Quality.** Hyperresearch output varies. The Phase 2 confirmation gate and
  `authority: derived` are the defence; advisor already surfaces derived-vs-book conflicts
  rather than silently preferring either.
- **Cost and time.** A full-tier run spawns many agents. Default to `light`, pass a budget,
  and never start one without confirming.
- **Corpus drift.** Research notes age. Record `date:` and `run:` so a stale finding can be
  traced to its run and retired.

## Out of scope

- Promoting a note to `authority: primary` automatically. That stays a human decision.
- Changing book packs or rule IDs.
- Embedding the deterministic index. Book citations stay model-free.
