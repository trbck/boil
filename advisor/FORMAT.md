# Knowledge format contracts

Two contracts. The **chapter contract** is strict and yields citable rules — use it for distilled books. The **note contract** is loose and accepts almost anything — use it for research reports, agent output, and working conventions.

Run `python3 scripts/validate_pack.py` after adding files. It reports drift without modifying anything.

---

## 1. Chapter contract (`kind: book`)

One file per chapter. Filename `NN-slug.md`, zero-padded, matching the book's own chapter number so IDs stay stable.

```markdown
# Ch 9 — Asset Allocation

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 9.
**Governs:** how capital is distributed across strategies, and therefore what shape the equity curve takes.
**Thesis:** asset allocation is not an optimization problem. It is a survivability problem.

---

## 1. Why long/short exists at all
...

## 5. Dynamic Exposure Allocation (DEA)
...

## Transferable rules

1. Define smoothness as drawdown depth x duration x frequency, never as volatility or Sharpe.
2. Simulate strategy returns, not asset prices.
...

## Cross-references

Ch. 5 the two archetypes ... **Named references:** Markowitz (1952) ...
```

### Required

| Element | Rule | Why |
|---|---|---|
| H1 | `# Ch <N> — <Title>` (em dash, en dash or hyphen accepted) | Supplies the chapter number that forms the stable ID |
| `**Governs:**` | One line, present | The single most useful routing signal — it says what decisions this chapter controls |
| Sections | At least one `## ` heading | Sections are the retrieval unit |
| Rules section | `## Transferable rules` — a leading `N. ` and a trailing `— condensed` are both tolerated | The rules are the compliance surface |
| Rules | Numbered `1.` … `N.`, one imperative claim each, continuation lines allowed | Each becomes an addressable, citable rule |

### Optional but recommended

`**Source:**`, `**Thesis:**`, `## Cross-references`, `## Citations`, `## Notebooks`.

### Conventions that make retrieval work

- **Write rules as imperatives with their reason attached.** "Shift signals forward one bar — signal today, trade tomorrow" beats "Avoid lookahead bias." The reason is what lets the advisor judge whether the rule applies to a novel situation.
- **Keep one claim per rule.** Compound rules can't be cited precisely or checked mechanically.
- **Put numbers in the rules.** `Cap single-trade risk at ~2%` is checkable; `size positions conservatively` is not.
- **Name the failure mode.** Rules that say what breaks are far more useful during an audit.
- Fenced code blocks are ignored by the parser, so `#` comments inside them are safe.

### Stable IDs

| Thing | Form | Example |
|---|---|---|
| Chapter | `<PREFIX>-<NN>` | `ASSP-09` |
| Section | `<PREFIX>-<NN>§<n>` | `ASSP-09§5` |
| Rule | `<PREFIX>-<NN>-R<n>` | `ASSP-09-R7` |

IDs derive from the chapter number and the rule's ordinal position. **Renumbering rules inside a published chapter breaks existing citations** — append instead.

---

## 2. Note contract (`kind: notes`)

For research reports, agent output, and your own conventions. The only hard requirement is an H1 title. Everything else is inferred, and anything you declare explicitly wins over inference.

```markdown
---
title: Cross-sectional momentum decay in S&P 500 sectors
category: research
source: hyperresearch
date: 2026-08-27
topics: [signals, features]
authority: derived
---

# Cross-sectional momentum decay in S&P 500 sectors

## Method
...

## Key findings

1. Sector-relative momentum decays with a half-life of ~14 trading days.
2. The effect survives a 10bp round-trip cost assumption but not 25bp.
```

### Frontmatter

Optional. A minimal `key: value` subset — scalars and inline lists `[a, b]` only. Unknown keys are preserved as metadata.

| Key | Effect |
|---|---|
| `title` | Overrides the H1 |
| `category` | Target subdirectory under `knowledge/notes/`. Defaults to `general` |
| `source` | Provenance — e.g. `hyperresearch`, `manual`, a URL |
| `date` | ISO date; otherwise the file mtime is used |
| `topics` | Pins taxonomy topics instead of inferring them |
| `authority` | `derived` (default) or `primary`. Only set `primary` for something you'd defend as strongly as a book |

### Findings become rules

If a note contains a section whose heading matches **Key findings**, **Findings**, **Transferable rules**, **Recommendations**, **Takeaways**, or **Conclusions**, its numbered or bulleted items are extracted as rules with IDs like `NOTE-momentum-decay-R1`.

This is the mechanism by which your own research joins the constitution. It also means a sloppy findings section pollutes it — write findings as sharp, falsifiable claims or omit the section entirely.

### Authority

Note rules carry `authority: derived` and are always labelled as such. When a derived rule contradicts a book rule, the advisor surfaces the conflict rather than silently preferring either. Promote a note to `primary` only when you have independently validated it.

---

## 3. Engine packs (`kind: engine`)

Large vendor documentation, indexed rather than distilled. No contract is imposed on the content — the pack declares its files and the indexer records headings with byte offsets so sections can be sliced without loading the file.

```json
"sources": { "manifest": "llms.txt", "docs": "llms-docs.txt", "api": "llms-full.txt" }
```

- `manifest` — optional curated link list (`- [Title](url): description` under `## Section` headings). Becomes the engine's router.
- `docs` — narrative documentation. Indexed by H1/H2/H3.
- `api` — API reference. Indexed by H1/H2, with the symbol taken from the text before the first `|`.

Engine packs contribute **capability knowledge, never method rules**. What the engine *can* do comes from here; whether you *should* comes from the book packs.

---

## 4. The inbox

`inbox/*.md` is the drop zone. Another skill or a manual copy puts files there; `scripts/ingest.py` classifies each one, files it into the right pack, and rebuilds the index.

Detection order:

1. Frontmatter `pack:` — explicit, wins.
2. Matches the chapter contract (`# Ch N — Title` + a rules section) → routed to the book pack named by frontmatter `pack:`, or rejected if ambiguous. Books are never auto-created, because a chapter without its siblings produces misleading IDs.
3. Everything else → `notes`, filed under `category`.

Ingest is non-destructive: originals move to `inbox/processed/` with a timestamp, never deleted.
