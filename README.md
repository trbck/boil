# boil

A Claude Code skill: a production-grade iterative dev-firm loop with parallel skilled subagents, an inter-agent ticket system, and a **mandatory user-visible demo** at the end of every iteration.

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
   - **Cross-LLM review** via [`roborev`](https://roborev.io) when installed — a different LLM (codex by default) critiques the iteration's code; findings become next-iteration tickets
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

User-wide (Claude Code reads skills from `~/.claude/skills/`):

```bash
git clone https://github.com/trbck/boil.git ~/.claude/skills/boil
```

That's it. Next time you start Claude Code, the `boil` skill and `/boil` slash command are available.

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

To deploy on a remote machine where you also use Claude Code:

```bash
rsync -avz --delete --exclude='.git' -e ssh ~/.claude/skills/boil/ remote:.claude/skills/boil/
```

## Layout

```
boil/
├── SKILL.md                          Main entry — phases, hard rules, integration
├── commands/boil.md                  /boil slash command
├── references/
│   ├── brainstorm-questions.md       Phase 0 question pool for fuzzy goals
│   ├── state-files.md                Templates for goal/memory/implementation/bugs/iter
│   ├── ticket-system.md              Ticket schema + dispatch prompt + handoff rules
│   ├── specialty-routing.md          ~60 specialties → subagent_type registry
│   ├── demo-formats.md               9 recipes: web UI, API, CLI, library, bug fix,
│   │                                 test-only, performance, docs, refactor
│   ├── rubrics.md                    Semantic LLM-as-judge layer for non-deterministic
│   │                                 checklist items
│   └── stories.md                    User-experience contracts (BPM-style): functional +
│                                     quant + UX assertions in one file, replayed by
│                                     scripts/story-run.py
└── scripts/
    ├── story-run.py                  v0 runner — HTTP lane fully implemented,
    │                                 SQL/Redis/UX/rubric require project adapters
    └── story-run.sh                  thin wrapper for the .sh-style invocation
```

`SKILL.md` is loaded into context whenever the skill triggers. The `references/` files are loaded on demand by the orchestrator as needed.

## How it works (one-paragraph version)

The skill treats the session as a small software firm. The orchestrator (the main Claude session) keeps a ticket pool on disk; each ticket has a `specialty` field. Each iteration the orchestrator picks ready tickets, looks up the right specialist subagent in `routing.md`, dispatches them all in parallel (one assistant message, multiple `Agent` tool calls), collects their reports, verifies the changes really landed, runs tests, runs an adversarial second-angle test, and produces a demo. When agents discover work outside their specialty mid-task they file new tickets rather than doing it themselves — the orchestrator routes the new tickets on the next cycle. The loop only stops when the `goal.md` checklist is green and the user has signed off on the latest demo.

## Hard rules

These are non-negotiable inside the loop:

1. **No iteration without a demo.** If you can't demo, you can't claim progress.
2. **No completion claims without fresh verification output.** Run the command, paste the line, then claim — see the [`superpowers:verification-before-completion`](https://github.com/obra/superpowers) skill.
3. **Always re-test from a different angle.** The implementer's own tests don't count as adversarial.
4. **Parallel dispatch goes in one assistant message.** Multiple `Agent` tool calls in a single turn so they actually run concurrently.
5. **Agents file tickets, the orchestrator dispatches them.** Specialists never recruit each other directly.
6. **`goal.md` is sacred.** Scope changes go through an explicit edit + re-confirm with the user.
7. **Honesty over progress theater.** If a cycle made no real progress, say so.
8. **Cross-LLM review every iteration that ships code.** Step 2d Pass 4 (roborev + codex) — findings become next-iteration tickets, never silently dismissed.
9. **User-perceivable work goes through a story.** Step 2d Pass 0 replays every story this iteration's tickets claim to close via `scripts/story-run.py`. Stories are the spec written *before* the code; the runner is the only authority on "the user can actually do this." A green Playwright + selftest endpoint without a green story is not a finished feature.

## Integration with other skills

`boil` orchestrates — it doesn't replace specialist skills:

- **[`superpowers`](https://github.com/obra/superpowers)** — `brainstorming`, `verification-before-completion`, `dispatching-parallel-agents`, `systematic-debugging`, `test-driven-development` are all referenced from inside the loop.
- **[`ralph-wiggum`](https://github.com/obra/ralph-wiggum)** — `boil` does the iteration internally rather than relying on a stop-hook loop, but you can wrap it with `/loop` for unattended runs.
- **[`roborev`](https://roborev.io)** — Step 2d Pass 4 enqueues a `roborev review --agent codex` per iteration when roborev is installed in the repo, so a second LLM critiques each iteration's code. Findings become next-iteration tickets, never silently dismissed. Outside boil, `/milestone-review` is the self-driven Claude-side equivalent.
- **`/loop` and `/schedule`** — wrap `boil` invocations for hands-off recurring runs.

## Subagent routing

The default routing table in [`references/specialty-routing.md`](references/specialty-routing.md) maps specialties (e.g., `frontend`, `backend`, `qa`, `debugger`, `performance`, `database`, `nlp`, `ml`, `mobile`, `blockchain`, `docs`) to subagent types from the `voltagent-*` family and the built-in `Plan`, `Explore`, and `general-purpose` agents. The table is copied to `.boil/routing.md` at bootstrap so you can adapt it per project (collapse it for single-language repos, add custom specialties, point at your own custom subagents).

If a ticket references a specialty not in the routing table, the orchestrator falls back to `general-purpose` and adds a TODO at the bottom of `routing.md`.

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
