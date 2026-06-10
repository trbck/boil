# boil

A Codex/Claude Code skill: a production-grade iterative dev-firm loop with parallel skilled subagents, an inter-agent ticket system, and a **mandatory user-visible demo** at the end of every iteration.

## What it does

You say something like:

```
boil a better dashboard till the conversion chart loads under 200ms
```

`boil` then:

1. **Crystallizes the goal.** If the request is fuzzy, it asks 2–5 targeted brainstorming questions and writes a `.boil/goal.md` you confirm before any work starts.
2. **Bootstraps a workspace** — `.boil/` with `goal.md`, `memory.md`, `implementation.md`, `bugs.md`, a `tickets/` pool, and a `routing.md` mapping specialties to subagent types.
3. **Loops** — each iteration:
   - Picks ready tickets from the pool
   - Dispatches them in parallel to **specialist subagents** (frontend, backend, qa, debugger, …) based on a routing table covering ~60 specialties
   - Verifies with the project's real test/lint/build commands
   - Re-tests **from a different angle** than the implementer used (adversarial pass)
   - **Cross-LLM review** via [`roborev`](https://roborev.io) when installed — a different LLM than the implementer critiques the iteration's code; findings become next-iteration tickets
   - Produces a **30-second demo** the user can verify (URL, screenshot, curl + response, terminal output, diff snippet, green test)
   - Posts a 10-line summary and asks: continue / refine / pivot / stop
4. **Terminates** when the goal checklist is fully green AND the user accepts the demo, OR when the user says stop.

The demo at the end of every iteration is the cornerstone — it's what makes this different from a black-box loop. If the iteration's work can't be demoed, the skill files a `demo-prep` ticket and tries again rather than claiming progress.

## Trigger phrases

The skill auto-triggers on:

- `boil X till Y` / `boil X until Y`
- `keep iterating until …`
- `loop until done`
- `run a dev firm on this`
- `build X with full verification`
- `self-correct until X is true`
- `ralph this`
- Any request shaped as: a desired end-state + repeated try-test-fix cycles + the user wanting to see proof at each step

You can also invoke `/boil <goal>` explicitly.

## Install

User-wide for Codex:

```bash
git clone https://github.com/trbck/boil.git ~/.codex/skills/boil
python3 -m pip install --user -r ~/.codex/skills/boil/requirements.txt
```

User-wide for Claude Code:

```bash
git clone https://github.com/trbck/boil.git ~/.claude/skills/boil
python3 -m pip install --user -r ~/.claude/skills/boil/requirements.txt
```

That's it. Next time you start Codex or Claude Code, the `boil` skill is available. The `/boil` slash command is available in clients that load `commands/boil.md`.

### Updating an installed local skill

If you develop `boil` in a separate checkout and want Codex to use that exact
version, install from the committed checkout:

```bash
tmp="$(mktemp -d)"
git -C /path/to/boil archive HEAD | tar -x -C "$tmp"
rsync -a --delete --exclude='.git' --exclude='.susi-human-blockers' \
  "$tmp/" ~/.codex/skills/boil/
rm -rf "$tmp"
```

Restart Codex after updating the installed skill so the refreshed `SKILL.md`
is loaded into new sessions.

### Optional: install `lsdf-core` for cheap codebase navigation

`boil` will use [L-SDF](https://github.com/ec1980/lsdf-core) when
present to maintain a compact index of the source tree (`INDEX.lsdf`
+ `INDEX.detail.lsdf`) so subagent dispatch contexts navigate by
index instead of full file reads. Typical compression on a Python
repo: ~13× source → index tokens.

```bash
pipx install lsdf-core      # preferred
# or, if pipx isn't installed:
pip install --user lsdf-core
```

Skill behavior is feature-detected: if `lsdf` isn't on PATH, boil
runs unchanged. Full protocol in `references/lsdf-codebase-index.md`.
Currently Python-first; TS / Go / Rust generators are on the
upstream roadmap.

To deploy on a remote machine where you also use the same agent client:

```bash
# Codex
rsync -avz --delete --exclude='.git' -e ssh ~/.codex/skills/boil/ remote:.codex/skills/boil/

# Claude Code
rsync -avz --delete --exclude='.git' -e ssh ~/.claude/skills/boil/ remote:.claude/skills/boil/
```

## Layout

```
boil/
├── SKILL.md                          Main entry — phases, hard rules, integration
├── commands/boil.md                  /boil slash command
├── requirements.txt                   Python dependency for story-run.py
├── references/
│   ├── brainstorm-questions.md       Phase 0 question pool for fuzzy goals
│   ├── state-files.md                Templates for goal/memory/implementation/bugs/iter
│   ├── ticket-system.md              Ticket schema + dispatch prompt + handoff rules
│   ├── specialty-routing.md          specialty → platform dispatch profile
│   ├── demo-formats.md               9 recipes: web UI, API, CLI, library, bug fix,
│   │                                 test-only, performance, docs, refactor
│   ├── rubrics.md                    Semantic LLM-as-judge layer for non-deterministic
│   │                                 checklist items
│   └── stories.md                    User-experience contracts (BPM-style): functional +
│                                     quant + UX assertions in one file, replayed by
│                                     scripts/story-run.py
└── scripts/
    ├── story-run.py                  v0 runner — HTTP lane implemented,
    │                                 SQL/Redis/UX require project adapters;
    │                                 rubric requires judge verdict files
    ├── story-run.sh                  thin wrapper for the .sh-style invocation
    ├── boil-doctor.py                validates a `.boil/` workspace
    ├── ticket-lint.py                lints ticket schema, blockers, and secrets
    ├── vibe-check.py                 flags summaries without proof/demo/next steps
    └── boil-verify-iteration.sh      gates one iteration directory
```

`SKILL.md` is loaded into context whenever the skill triggers. The `references/` files are loaded on demand by the orchestrator as needed.

## How it works (one-paragraph version)

The skill treats the session as a small software firm. The orchestrator (the main agent session) keeps a ticket pool on disk; each ticket has a `specialty` field. Each iteration the orchestrator picks ready tickets, looks up the right specialist subagent in `routing.md`, dispatches them all in parallel using the current client’s subagent API, collects their reports, verifies the changes really landed, runs tests, runs an adversarial second-angle test, and produces a demo. When agents discover work outside their specialty mid-task they file ticket proposals rather than doing it themselves — the orchestrator routes the new tickets on the next cycle. The loop only stops when the `goal.md` checklist is green and the user has signed off on the latest demo.

## Hard rules

These are non-negotiable inside the loop:

1. **No iteration without a demo.** If you can't demo, you can't claim progress.
2. **No completion claims without fresh verification output.** Run the command, paste the line, then claim — see the [`superpowers:verification-before-completion`](https://github.com/obra/superpowers) skill.
3. **Always re-test from a different angle.** The implementer's own tests don't count as adversarial.
4. **Parallel dispatch goes in one assistant message.** Multiple `Agent` tool calls in a single turn so they actually run concurrently.
5. **Agents file ticket proposals, the orchestrator assigns IDs and dispatches them.** Specialists never recruit each other directly.
6. **`goal.md` is sacred.** Scope changes go through an explicit edit + re-confirm with the user.
7. **Honesty over progress theater.** If a cycle made no real progress, say so.
8. **Cross-LLM review every iteration that ships code when a different reviewer is available.** Step 2d Pass 4 (roborev + a non-implementer reviewer) — findings become next-iteration tickets, never silently dismissed.
9. **User-perceivable work goes through a story.** Step 2d Pass 0 replays every story this iteration's tickets claim to close via `scripts/story-run.py`. Stories are the spec written *before* the code; the runner is the only authority on "the user can actually do this." A green Playwright + selftest endpoint without a green story is not a finished feature.
10. **TDD plus 99% evidence confidence.** New behavior starts with RED proof, implementation follows, and a ticket cannot be `done` unless requirements understood, implementation match, and verification working are each `>=99/100` with concrete evidence and no remaining uncertainty.

## Integration with other skills

`boil` orchestrates — it doesn't replace specialist skills:

- **[`superpowers`](https://github.com/obra/superpowers)** — `brainstorming`, `verification-before-completion`, `dispatching-parallel-agents`, `systematic-debugging`, `test-driven-development` are all referenced from inside the loop.
- **[`ralph-wiggum`](https://github.com/obra/ralph-wiggum)** — `boil` does the iteration internally rather than relying on a stop-hook loop, but you can wrap it with `/loop` for unattended runs.
- **[`roborev`](https://roborev.io)** — Step 2d Pass 4 enqueues a `roborev review --agent <different-reviewer>` per iteration when roborev is installed in the repo and a reviewable diff exists, so a second LLM critiques each iteration's code. Findings become next-iteration tickets, never silently dismissed.
- **`/loop` and `/schedule`** — wrap `boil` invocations for hands-off recurring runs.

## Subagent routing

The default routing guidance in [`references/specialty-routing.md`](references/specialty-routing.md) maps specialties (e.g., `frontend`, `backend`, `qa`, `debugger`, `performance`, `database`, `nlp`, `ml`, `mobile`, `blockchain`, `docs`) to the subagent types available in the current client. Codex usually collapses many specialties to `worker` / `explorer`; Claude installs with richer custom agents may use `voltagent-*` routes. The table is copied to `.boil/routing.md` at bootstrap so you can adapt it per project.

If a ticket references a specialty not in the routing table, the orchestrator falls back to the current platform default (`worker` on Codex, `general-purpose` on Claude-style rich-agent installs) and adds a TODO at the bottom of `routing.md`.

## Guardrail scripts

These scripts are the mechanical layer that pushes boil away from "vibe coding"
and toward agentic looped development:

```bash
python3 scripts/boil-doctor.py --root /path/to/project
python3 scripts/ticket-lint.py --root /path/to/project
python3 scripts/vibe-check.py /path/to/project/.boil/iterations/iter-001/summary.md
bash scripts/boil-verify-iteration.sh iter-001 /path/to/project
python3 -m unittest discover -s tests
```

The minimal fixture in `examples/minimal-loop/` shows the expected state shape
without committing a real `.boil/` workspace to this skill repo.

## Human blockers, Susi To Do, and Pushover

When a boil loop is blocked by something only the user can do — API keys,
OAuth approval, billing setup, DNS, hardware access, or a product decision —
the loop creates a `human-action` ticket instead of burying the blocker in
chat. The ticket stores only a secret-free `safe_summary`.

If the local ignored bridge exists at `.susi-human-blockers/add_blocker.py`,
boil can create a Susi/Microsoft To Do task for the blocked project and send a
Pushover notification after the To Do item is created. The bridge returns a
normalized contract:

```json
{
  "ok": true,
  "susi_sync_status": "created",
  "susi_task_id": "<task id>",
  "pushover_status": "sent",
  "errors": []
}
```

The bridge directory is intentionally ignored by Git because it may contain
local URLs, session cookies, Pushover tokens, and logs. Do not commit bridge
config or generated payloads.

## When to use

Good fit:

- Multi-iteration features where the user wants to see incremental proof
- Bug-hunting loops where each cycle ships a fix and you want adversarial re-testing
- Quality-bar pushes ("get this to green", "get the p95 under 200ms")
- Greenfield builds where the user wants to verify direction every cycle
- Maintenance loops you want to leave running with a demo at each step

Wrong fit:

- One-shot, well-defined tasks (just do them — don't spin up the firm)
- Tasks where the user can't or doesn't want to verify each iteration
- Tasks with no observable success criteria — the brainstorming questions try to flush these out, but if the user truly doesn't know what "done" looks like, brainstorm with `superpowers:brainstorming` first

## License

[MIT](LICENSE) — © 2026 trbck

## Contributing

Issues and PRs welcome. The skill itself was iteratively refined; if you find a phase that drifts, an instruction that gets ignored, or a demo recipe that doesn't fit your domain, open an issue with a concrete repro and a proposed change.
