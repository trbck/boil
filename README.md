# boil

A Codex/Claude Code skill: a production-grade iterative dev-firm loop with parallel skilled subagents, an inter-agent ticket system, and a **mandatory user-visible demo** at the end of every iteration.

## What it does

You say something like:

```
boil a better dashboard till the conversion chart loads under 200ms
```

`boil` then:

1. **Crystallizes the goal.** If the request is fuzzy, it inspects the workspace first, then asks targeted questions until the goal, constraints, tradeoffs, and success criteria are clear before writing a `.boil/goal.md` you confirm.
2. **Bootstraps a workspace** — `.boil/` with `goal.md`, `memory.md`, `implementation.md`, `bugs.md`, a `tickets/` pool, and a `routing.md` mapping specialties to subagent types.
3. **Loops** — each iteration:
   - Picks ready tickets from the pool
   - Dispatches them in parallel to **specialist subagents** (frontend, backend, qa, debugger, …) based on a routing table covering ~60 specialties
   - Runs a **self-correcting loop** per behavior ticket — a builder attempts it, an independent judge checks it against an external answer key frozen beforehand, and a deterministic manager decides revise / finish / escalate. Three failed revisions stop the loop and hand a human the full history
   - Verifies with the project's real test/lint/build commands
   - Re-tests **from a different angle** than the implementer used (adversarial pass)
   - **Cross-LLM review** via [`roborev`](https://roborev.io) when installed — a different LLM than the implementer critiques the iteration's code; Claude implementations prefer Codex review and Codex implementations prefer Claude review; findings become next-iteration tickets
   - Produces a **30-second demo** the user can verify (URL, screenshot, curl + response, terminal output, diff snippet, green test)
   - Posts a 10-line summary and asks: continue / refine / pivot / stop
4. **Terminates** when the goal checklist is fully green AND the user accepts the demo, OR when the user says stop.

The demo at the end of every iteration is the cornerstone — it's what makes this different from a black-box loop. If the iteration's work can't be demoed, the skill files a `demo-prep` ticket and tries again rather than claiming progress.

## The self-correcting loop

Inside each iteration, every behavior ticket runs a bounded correction cycle with three roles:

- **builder** — makes the attempt (a specialist subagent)
- **judge** — checks it against an **answer key**, and nothing else. Context-isolated: it never sees the builder's chat, self-report, or confidence scores
- **manager** — [`scripts/boil-loop.py`](scripts/boil-loop.py), deterministic. Decides revise, finish, or escalate

The judge is the part that matters, and it only works if its answer key lives **outside the builder's own reasoning**. boil accepts exactly three kinds — a **test suite**, a **source document**, or a **written checklist** — authored by the orchestrator, the user, or an upstream source, and hashed before the first attempt. Without that, the system is only asking the same model to agree with itself.

Four properties make it safe to run unattended:

| Property | Mechanism |
|---|---|
| The key can't be gamed | Its hash is frozen before attempt 1; if it moves, or its files appear in the builder's diff, the loop aborts as a tamper event — no revision offered |
| The judge can't wave things through | A PASS citing no key evidence is auto-downgraded to INVALID; the builder's confidence block is not an input to any decision |
| The loop can't run forever | Hard limit of **3** revisions. Two identical failure signatures, or a blown budget cap, stop it sooner |
| A human always gets the full story | On any terminal state it writes `escalation.md` — every attempt, what stayed constant, and the one question a human has to answer — and converts the ticket to a blocked P0 `human-action` item |

`ticket-lint.py` errors on a behavior ticket with a missing, self-authored, unprotected, or unfrozen key, and `boil-loop.py audit` fails an iteration where a ticket closed without a satisfied key.

Before trusting it unattended, run the four-scenario red-team suite in [`references/self-correcting-loop.md`](references/self-correcting-loop.md): an **unsolvable task**, a **confidently wrong answer**, a **shared model blind spot**, and the **most expensive possible run**. If it catches real errors and stops cleanly on all four, you have something you can run without watching every step.

## Status logging — watch it live in helm

Every state transition is logged, so a long run isn't opaque:

```bash
python3 scripts/boil-helm-log.py sync --root /path/to/project              # .boil/STATUS.md
python3 scripts/boil-helm-log.py link --root /path/to/project --stem <helm goal>
```

boil always writes `.boil/status.jsonl` (append-only) and `.boil/STATUS.md` (rendered). When [helm](https://github.com/trbck/helm) is installed, the same snapshot is registered as a first-class helm object, so `helm boil` and the helm dashboard show the running session — its tickets, each ticket's frozen answer key, the judge's reasoning per attempt, and every manager decision with its reason — live and reviewable afterwards. No helm, no problem: the project-local files are the canonical record either way. See [`references/helm-status.md`](references/helm-status.md).

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
git clone https://github.com/trbck/boil.git
cd boil
python3 scripts/install-codex-skill.py
```

User-wide for Claude Code:

```bash
git clone https://github.com/trbck/boil.git ~/.claude/skills/boil
python3 -m pip install --user -r ~/.claude/skills/boil/requirements.txt
```

That's it. Next time you start Codex or Claude Code, the `boil` skill is available. The `/boil` slash command is available in clients that load `commands/boil.md`.

### Updating an installed local skill

If you develop `boil` in a separate checkout and want Codex to use that exact
working tree, run the installer from the checkout:

```bash
python3 scripts/install-codex-skill.py
```

The installer detects `$CODEX_HOME` or falls back to `~/.codex`, backs up the
previous install under `skills/.backups/`, syncs the checkout into
`skills/boil`, excludes `.git`, and preserves the local ignored
`.susi-human-blockers/` bridge. Restart Codex after updating the installed
skill so the refreshed `SKILL.md` is loaded into new sessions.

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
│   ├── clanker-constitution.md      Baseline conduct layer — the Clanker Constitution
│   │                                 verbatim (CC BY 4.0) + mapping to boil's hard rules
│   ├── plain-english-output.md      Optional claudish-to-english wiring + scoping rules
│   ├── brainstorm-questions.md       Phase 0 question pool for fuzzy goals
│   ├── state-files.md                Templates for goal/memory/implementation/bugs/iter
│   ├── ticket-system.md              Ticket schema + dispatch prompt + handoff rules
│   ├── specialty-routing.md          specialty → platform dispatch profile
│   ├── demo-formats.md               9 recipes: web UI, API, CLI, library, bug fix,
│   │                                 test-only, performance, docs, refactor
│   ├── self-correcting-loop.md       builder/judge/manager triad: answer-key contract,
│   │                                 handoff formats, decision table, retry limit,
│   │                                 escalation packet, red-team suite
│   ├── helm-status.md                Status logging: event kinds, the session object,
│   │                                 and how boil sessions render in helm
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
    ├── boil-loop.py                  the manager: freezes answer keys, applies the
    │                                 decision table, enforces the retry limit,
    │                                 writes escalation packets
    ├── boil-helm-log.py              status logging + the helm session bridge
    ├── boil-doctor.py                validates a `.boil/` workspace
    ├── ticket-lint.py                lints ticket schema, answer keys, blockers, secrets
    ├── vibe-check.py                 flags summaries without proof/demo/next steps
    ├── boil-verify-iteration.sh      gates one iteration directory
    ├── boil-run-iteration.sh         runs doctor/lint/story/test/iteration gates
    ├── boil-sync-agents.py           writes AGENTS.md, Cursor rules, routing
    ├── boil-dispatch-packet.py       writes compact per-ticket agent packets
    ├── boil-debug-mode.py            creates systematic-debugging worksheets
    ├── boil-pr-summary.py            generates a PR body from boil state
    └── install-codex-skill.py        installs/updates this checkout in Codex
```

`SKILL.md` is loaded into context whenever the skill triggers. The `references/` files are loaded on demand by the orchestrator as needed.

## How it works (one-paragraph version)

The skill treats the session as a small software firm. The orchestrator (the main agent session) keeps a ticket pool on disk; each ticket has a `specialty` field. Each iteration the orchestrator picks ready tickets, looks up the right specialist subagent in `routing.md`, dispatches them all in parallel using the current client’s subagent API, collects their reports, verifies the changes really landed, runs tests, runs an adversarial second-angle test, and produces a demo. When agents discover work outside their specialty mid-task they file ticket proposals rather than doing it themselves — the orchestrator routes the new tickets on the next cycle. The loop only stops when the `goal.md` checklist is green and the user has signed off on the latest demo.

## Hard rules

These are non-negotiable inside the loop:

1. **Clarity before plan or code.** Inspect available context, then interview until the goal, constraints, tradeoffs, decision dependencies, and observable success criteria are clear. Do not guess or execute while the plan still depends on unresolved ambiguity.
2. **No iteration without a demo.** If you can't demo, you can't claim progress.
3. **No completion claims without fresh verification output.** Run the command, paste the line, then claim — see the [`superpowers:verification-before-completion`](https://github.com/obra/superpowers) skill.
4. **Always re-test from a different angle.** The implementer's own tests don't count as adversarial.
5. **Parallel dispatch goes in one assistant message.** Multiple `Agent` tool calls in a single turn so they actually run concurrently.
6. **Agents file ticket proposals, the orchestrator assigns IDs and dispatches them.** Specialists never recruit each other directly.
7. **`goal.md` is sacred.** Scope changes go through an explicit edit + re-confirm with the user.
8. **Honesty over progress theater.** If a cycle made no real progress, say so.
9. **Cross-LLM review every iteration that ships code when a different reviewer is available.** Step 2d Pass 4 (roborev + a non-implementer reviewer; Claude implementations prefer Codex review, Codex implementations prefer Claude review) — findings become next-iteration tickets, never silently dismissed.
10. **User-perceivable work goes through a story.** Step 2d Pass 0 replays every story this iteration's tickets claim to close via `scripts/story-run.py`. Stories are the spec written *before* the code; the runner is the only authority on "the user can actually do this." A green Playwright + selftest endpoint without a green story is not a finished feature.
11. **TDD plus 99% evidence confidence.** New behavior starts with RED proof, implementation follows, and a ticket cannot be `done` unless requirements understood, implementation match, and verification working are each `>=99/100` with concrete evidence and no remaining uncertainty.
12. **No judge without an answer key outside the builder's reasoning.** Every behavior ticket carries a suite / document / checklist key, authored elsewhere and frozen before the first attempt. A key the builder wrote is the builder grading itself.
13. **The retry limit is three, and it is hard.** Three failed revisions escalate to a human with the full history. No fourth attempt, no reinterpreting the ticket to make attempt 3 pass. An honest escalation is a success of the system.
14. **The answer key is read-only for the duration.** Editing, skipping, xfailing, loosening, or narrowing it aborts the loop as a tamper event. Whoever is being measured never owns the ruler.
15. **Every state transition is logged where a human can watch it.** An unreviewable loop can't be trusted to run unattended.
16. **Baseline conduct is the [Clanker Constitution](references/clanker-constitution.md).** Honor the request, act with judgment, finish the job, protect existing work, verify reality, communicate for humans, learn in the right place — in force for the orchestrator and every dispatched subagent. It's the floor under the loop rules, never a way around them.

## Integration with other skills

`boil` orchestrates — it doesn't replace specialist skills:

- **[`superpowers`](https://github.com/obra/superpowers)** — `brainstorming`, `verification-before-completion`, `dispatching-parallel-agents`, `systematic-debugging`, `test-driven-development` are all referenced from inside the loop.
- **[`ralph-wiggum`](https://github.com/obra/ralph-wiggum)** — `boil` does the iteration internally rather than relying on a stop-hook loop, but you can wrap it with `/loop` for unattended runs.
- **[`roborev`](https://roborev.io)** — Step 2d Pass 4 enqueues a `roborev review --agent <different-reviewer>` per iteration when roborev is installed in the repo and a reviewable diff exists, so a second LLM critiques each iteration's code. Claude implementations prefer `--agent codex`; Codex implementations prefer `--agent claude-code`. Findings become next-iteration tickets, never silently dismissed.
- **`gate` + `helm` — the full setup.** Three loops, one chain, none duplicating another:
  - **gate** owns the OUTER loop — *is this project worth finishing, and is it converging?* Maturity ladder L0–L5, evidence rules, todo discipline, portfolio WIP limit. One open ladder criterion is one valid boil goal.
  - **helm** is the CONTROLLER — *what is the measured gap, and is it closing?* It turns the goal into machine-checkable subgoals (test / data / human), steers a boil session at the first open one under hard guardrails (budget, stall, WIP, kill-by), re-measures, and ticks the gate ladder box with a formatted EVIDENCE line once the goal measures MET.
  - **boil** owns the INNER loop — *build one thing until it's proven* — and inside it, the self-correcting loop runs builder → judge → manager per ticket.

  The rules rhyme on purpose: gate says *no checkmark without fresh evidence*, helm says *never edit a sensor to pass a goal*, boil says *never edit the answer key to pass a ticket*. Same principle at three scales — whoever is being measured never owns the ruler.
- **[`claudish-to-english`](https://github.com/gvzdv/claudish-to-english)** — optional plugin that appends a plain-English rewrite of each assistant message using a **local** ollama model, so a long unattended run's summaries and footers read in a second, plainer voice. Fails open, no egress. Its Markdown-file hook is opt-in and must be scoped to `.boil/iterations` in `sibling` mode — never over tickets, loops, stories, rubrics, `goal.md`, or an answer key. See [`references/plain-english-output.md`](references/plain-english-output.md).
- **`/loop` and `/schedule`** — wrap `boil` invocations for hands-off recurring runs.

## Subagent routing

The default routing guidance in [`references/specialty-routing.md`](references/specialty-routing.md) maps specialties (e.g., `frontend`, `backend`, `qa`, `debugger`, `performance`, `database`, `nlp`, `ml`, `mobile`, `blockchain`, `docs`) to the subagent types available in the current client. Codex usually collapses many specialties to `worker` / `explorer`; Claude installs with richer custom agents may use `voltagent-*` routes. The table is copied to `.boil/routing.md` at bootstrap so you can adapt it per project.

If a ticket references a specialty not in the routing table, the orchestrator falls back to the current platform default (`worker` on Codex, `general-purpose` on Claude-style rich-agent installs) and adds a TODO at the bottom of `routing.md`.

## Guardrail scripts

These scripts are the mechanical layer that pushes boil away from "vibe coding"
and toward agentic looped development:

```bash
python3 scripts/boil-loop.py init   --root /path/to/project --ticket T-0001   # freeze the key
python3 scripts/boil-loop.py decide --root /path/to/project --ticket T-0001 --attempt 1
python3 scripts/boil-loop.py status --root /path/to/project
python3 scripts/boil-loop.py audit  --root /path/to/project     # loop-safety gate
python3 scripts/boil-helm-log.py sync --root /path/to/project   # STATUS.md + helm session
python3 scripts/boil-commit-guard.py --root /path/to/project   # no AI trailers in commits
python3 scripts/boil-commit-guard.py --install-hook            # reject them at commit time
python3 scripts/boil-doctor.py --root /path/to/project
python3 scripts/ticket-lint.py --root /path/to/project
python3 scripts/vibe-check.py /path/to/project/.boil/iterations/iter-001/summary.md
bash scripts/boil-verify-iteration.sh iter-001 /path/to/project
bash scripts/boil-run-iteration.sh iter-001 /path/to/project --test-cmd "pytest -q"
python3 scripts/boil-sync-agents.py --root /path/to/project
python3 scripts/boil-dispatch-packet.py T-0001 --root /path/to/project
python3 scripts/boil-debug-mode.py --root /path/to/project --iteration iter-001 --ticket T-0001
python3 scripts/boil-pr-summary.py --root /path/to/project --out /tmp/pr.md
python3 scripts/install-codex-skill.py
python3 -m unittest discover -s tests
```

The minimal fixture in `examples/minimal-loop/` shows the expected state shape
without committing a real `.boil/` workspace to this skill repo.

The repository also ships `.github/workflows/boil-guardrails.yml`, which runs
syntax checks, unit tests, and the minimal fixture guardrails on pushes and PRs.

## PR-first mode

For production repositories, boil works best when iterations land on a branch
and the final handoff is a PR. Use `scripts/boil-pr-summary.py` to turn
`.boil/goal.md`, iteration summaries, verification checkboxes, and diff stats
into a reviewable PR body. This keeps agent work reviewable instead of quietly
mutating `main`.

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

## Attribution

boil integrates third-party tools by reference (it invokes, does not vendor them) — notably
[hound-mcp](https://github.com/dondai1234/master-fetch) as its web-fetch tool and
[lsdf-core](https://github.com/ec1980/lsdf-core) for the codebase index. See `NOTICE.md`.
