# Plain-English output — claudish-to-english

> **Load when:** you are wiring the optional claudish-to-english plain-English layer. Purely optional; boil's own report block is already written in plain English.

boil generates a lot of prose for a human: the Step 2f narrative, `demo.md`, `STATUS.md`,
`escalation.md`, `FINAL.md`, PR bodies. All of it is written by an LLM, and LLM prose has a
house style — hedged, padded, fond of "comprehensive" and "robust" — that costs the
operator attention exactly where boil is trying to save it (the Step 2e report block and
the ADHD-friendly orientation contract).

[**claudish-to-english**](https://github.com/gvzdv/claudish-to-english) (Georgy Vozdvizhev,
MIT) is a Claude Code plugin that fixes this at the display layer: two hooks that pass
assistant messages, or written Markdown files, through a **local** ollama model and give
you a plain-English version. It is optional, external, and boil never requires it.

Two properties make it safe to put next to a boil loop:

- **It fails open.** ollama down, model not pulled, timeout, missing `jq` — you get the
  original text, unchanged, plus a one-time notice. It can't swallow or corrupt an answer.
- **It runs locally.** No conversation content leaves the machine, which matters because
  boil dispatch context routinely contains file contents and tool output. Do **not** point
  `CLAUDISH_OLLAMA` at a hosted endpoint while running boil — that turns every iteration's
  context into egress.

## Install

```bash
# in Claude Code
/plugin marketplace add gvzdv/claudish-to-english
/plugin install claudish-to-english@gvzdv-plugins
```

Requires a running `ollama serve`, a pulled model, `jq`, and `curl`. Warm the model once
per boot — the first call is a slow cold load. Full setup, model sizing, and the complete
env-var table are in the plugin's README; this file only covers the boil-specific wiring.

## Hook 1 — display rewrite (recommended)

`CLAUDISH_MODE=append` appends a `💬 In plain English:` block after each assistant message.
Nothing on disk changes, Claude's own reasoning and the transcript keep the original text,
and a failed rewrite just means no extra block. For a long unattended boil run this is the
cheap win: the iteration report block arrives twice, once in boil's
voice and once in plain English.

```json
{
  "env": {
    "CLAUDISH_MODEL": "<your pulled ollama tag>",
    "CLAUDISH_MODE": "append"
  }
}
```

Use `append`, not `replace`, while boil is running. `replace` suppresses the original
stream and shows only the local model's version — which means a small local model is now
the only thing standing between you and the loop's proof output. boil's honesty rules
(hard rules 3, 8, 18) are about what *you* read; a paraphrase is not the evidence.

Note the env-block rules from the plugin README, both of which bite in practice: settings
`env` does **not** merge across scopes (the highest-precedence file supplies the whole
block), and the value is captured at launch, so restart Claude Code after editing it.

## Hook 2 — Markdown file rewrite (opt-in, and scope it carefully)

`rewrite-md.sh` changes bytes on disk. It does nothing unless `CLAUDISH_MD_DIR` is set, and
only touches `*.md` resolving inside that directory. Where you point it is the whole
decision.

**Point it at the narrative surfaces:**

```json
{
  "env": {
    "CLAUDISH_MD_DIR": "/ABS/PATH/TO/PROJECT/.boil/iterations",
    "CLAUDISH_MD_MODE": "sibling"
  }
}
```

`sibling` mode writes `summary.plain.md` next to `summary.md` and never touches the
original. You get a plain-English `demo.md` and `summary.md` per iteration for a returning
operator, while every file boil's own tooling reads stays byte-identical.

### Never point it at these

| Path | Why |
|---|---|
| `.boil/tickets/` | Ticket bodies carry `Proof / tests:` output. A paraphrase of a test result is not a test result — hard rule 3. Frontmatter survives (it is re-attached verbatim), the evidence does not. |
| `.boil/loops/` | Owned exclusively by `boil-loop.py`. Nothing else writes there, ever. A rewritten `escalation.md` is a corrupted human packet. |
| Anything named by a ticket's `answer_key` | The T3 answer key is read-only for the duration, and "weakening counts as editing." A local model rephrasing a checklist key is tampering, whether or not it meant to be. |
| `.boil/stories/`, `.boil/rubrics/` | These are specs and measures. Rewriting a rubric's `eval_steps` or a story's assertions moves the ruler under the thing being measured. |
| `.boil/goal.md` | `goal.md` is sacred (Phase 0) and changes only through an explicit user-confirmed edit. |
| Repo source docs, in `overwrite` mode | The plugin's own README says a weak model can degrade real docs. Same warning, louder, for anything a judge or a reviewer will read. |

**Never use `overwrite` mode anywhere under `.boil/`.** Sibling mode only. The state
directory is boil's evidence record; the plain-English layer is a reading aid for humans,
and a reading aid does not get write access to the evidence.

### The derived-sibling rule

A `.plain.md` sibling is a **rendered copy with no authority**. It closes no checkbox,
satisfies no `proof_strategy`, and is never what a judge reads — the judge sees the key,
the artifacts, and the diff (see `references/self-correcting-loop.md`). If a demo or a proof exists only in a rewritten
sibling, it does not exist.

`ticket-lint.py` skips any file whose stem contains a dot (`T-0001.plain.md`), so a sibling
landing in `.boil/tickets/` is ignored rather than linted as a malformed ticket. That is a
safety net for a misconfigured `CLAUDISH_MD_DIR`, not permission to point the hook there.

## What it does not replace

The Step 2e report block is still written by boil in plain English itself. It is a required
output, and its job — *what moved toward the goal,
what fraction is done, what is next, what went wrong* — is a judgment about the work that a
downstream rewriter cannot make from the text alone. claudish-to-english makes that
narrative easier to read. It does not get to be the narrative.
