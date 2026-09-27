# inbox

Drop zone for markdown to be added to the corpus. Anything here is staged, not yet indexed.

```bash
python3 scripts/ingest.py --domain <id> --dry-run   # show where each file would land, change nothing
python3 scripts/ingest.py --domain <id>             # file them, then rebuild the index
```

Originals move to `inbox/processed/` with a timestamp. Nothing is deleted, so a misrouted file is
always recoverable.

## Contract for automated producers

Any skill or process that generates markdown reports can write here. The only hard requirement is
an H1 title; everything else is inferred and can be overridden with frontmatter.

```markdown
---
title: Cross-sectional momentum decay in S&P 500 sectors
category: research
source: hyperresearch
date: 2026-08-27
topics: [signals, costs]
authority: derived
---

# Cross-sectional momentum decay in S&P 500 sectors

## Method
...

## Key findings

1. Sector-relative momentum half-life is ~14 trading days.
2. The effect survives 10bp round-trip costs but not 25bp.
```

| Key | Effect | Default |
|---|---|---|
| `title` | Overrides the H1 | first H1, else filename |
| `category` | Subdirectory under `knowledge/notes/` | `general` |
| `source` | Provenance label — shown in the router | `inbox` |
| `date` | ISO date | file mtime |
| `topics` | Pins taxonomy topics instead of inferring | inferred |
| `authority` | `derived` or `primary` | `derived` |
| `pack` | Route to a specific pack instead of `notes` | — |

## Findings become citable rules

A section headed **Key findings**, **Findings**, **Recommendations**, **Takeaways**, or
**Conclusions** has its numbered or bulleted items extracted as rules with IDs like
`NOTE-momentum-decay-R1`. They join the rule shards alongside book rules, tagged `derived`.

This is how your own research earns a seat at the table — and why a vague findings section is
actively harmful. Write findings as sharp, falsifiable claims with numbers in them, or leave the
section out and let the document be reference prose only.

## What does not belong here

- **Book chapters without a `pack:` key.** A lone chapter mints IDs that collide or mislead, so
  ingest refuses it. Distil the whole book to `FORMAT.md`'s chapter contract, register a pack in
  `domains/<domain>/packs.json`, and place the files directly under `domains/<domain>/knowledge/<pack>/`.
- **Unreviewed model output presented as findings.** Anything ingested becomes citable. If you have
  not checked it, mark it clearly in the title or leave out the findings section.
