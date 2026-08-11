# NOTICE

boil — a production-grade iterative dev-firm loop skill for Codex / Claude Code.

Copyright (c) 2026 trbck. All rights reserved (no OSS license is granted yet — add a
LICENSE file to choose one).

## Third-party text boil reproduces

- **Clanker Constitution** — © 2026 Kenn Software LLC, licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Canonical source:
  https://github.com/kenn-io/constitution · introduced in Wes McKinney's post
  https://wesmckinney.com/blog/clanker-constitution/. boil reproduces the constitution
  **unmodified** in `references/clanker-constitution.md` (attribution and license notice
  retained inline) and adopts it as the baseline conduct layer for the orchestrator and
  every dispatched subagent (see `SKILL.md` → "Baseline conduct" and hard rule 26).
  Condensed restatements appear in `references/ticket-system.md`,
  `scripts/boil-dispatch-packet.py`, and the `AGENTS.md` written by
  `scripts/boil-sync-agents.py`; these are adaptations under the same license, and the
  commentary/mapping around the text is boil's own, not Kenn's.

## Third-party tools boil integrates

boil *orchestrates and invokes* the tools below when they are present. It does **not**
vendor or redistribute their source — each remains the property of its authors under its
own license, and is installed separately by the operator. Attribution:

- **hound-mcp** — anti-bot web-research MCP fetcher (`mcp_smart_fetch`, browser rendering,
  bot-verification bypass). Author: Bishesh Bhandari. Source:
  https://github.com/dondai1234/master-fetch · PyPI: `hound-mcp`. boil dispatches use it
  as the preferred web-fetch tool (see `references/ticket-system.md` → "Tools available"
  and the "Integration with other skills" section of `SKILL.md`).
- **claudish-to-english** — Claude Code plugin that renders assistant messages (and,
  opt-in, Markdown files) into plain English via a local ollama model. Author: Georgy
  Vozdvizhev. Licensed MIT. Source: https://github.com/gvzdv/claudish-to-english. boil
  documents it as an optional operator reading aid and defines its safe scoping
  (`references/plain-english-output.md`); no plugin code is vendored here.
- **lsdf-core** (L-SDF codebase index) — https://github.com/ec1980/lsdf-core · PyPI:
  `lsdf-core`. Used for the compact `INDEX.lsdf` repo index at bootstrap when present.
- **superpowers:\*** agent/skill role contracts — referenced as optional dispatch roles
  when the runtime exposes them.

These integrations are by reference (invocation) only; no third-party code is included in
this repository.
