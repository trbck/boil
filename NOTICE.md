# NOTICE

boil — a production-grade iterative dev-firm loop skill for Codex / Claude Code.

Copyright (c) 2026 trbck. All rights reserved (no OSS license is granted yet — add a
LICENSE file to choose one).

## Third-party tools boil integrates

boil *orchestrates and invokes* the tools below when they are present. It does **not**
vendor or redistribute their source — each remains the property of its authors under its
own license, and is installed separately by the operator. Attribution:

- **hound-mcp** — anti-bot web-research MCP fetcher (`mcp_smart_fetch`, browser rendering,
  bot-verification bypass). Author: Bishesh Bhandari. Source:
  https://github.com/dondai1234/master-fetch · PyPI: `hound-mcp`. boil dispatches use it
  as the preferred web-fetch tool (see `references/ticket-system.md` → "Tools available"
  and the "Integration with other skills" section of `SKILL.md`).
- **lsdf-core** (L-SDF codebase index) — https://github.com/ec1980/lsdf-core · PyPI:
  `lsdf-core`. Used for the compact `INDEX.lsdf` repo index at bootstrap when present.
- **superpowers:\*** agent/skill role contracts — referenced as optional dispatch roles
  when the runtime exposes them.

These integrations are by reference (invocation) only; no third-party code is included in
this repository.
