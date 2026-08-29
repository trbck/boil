# boil

A Codex/Claude Code skill that builds one thing until it is proven — inside a project that is
actually converging. It owns three scopes: the **portfolio** (should I be in this project at
all?), the **ladder** (is this project converging?), and the **run loop** (is this one thing
built and verified?). Every iteration ends with a **user-visible demo**.

> The outer two scopes used to be a separate skill, `gate`. It was merged in on 2026-08-28,
> because a separate skill has to be invoked voluntarily — and measurably was not. See
> [MERGE-PLAN.md](MERGE-PLAN.md) for the evidence and the design.

## What it does

You say something like:

```
boil the /api/orders endpoint until POST returns 201 with a real order_id
```

`boil` then:

1. **Reads one file.** `boil-now.py` derives `.boil/NOW.md` — ~40 lines covering project
   status, ladder position, goal progress, the brakes, and the actionable tickets. Its exit
   code is the instruction: 0 continue, 2 restrict to cheap work, 3 stop and ask. A parked
   project refuses work before a line is written.
2. **Crystallizes the goal** — and keeps it small. **A goal is one ladder criterion, not a
   project:** max 7 checkboxes, max 2500 bytes, and it must state how you will see it works.
   This is linted, because goal size predicts failure better than anything else measured
   (see below).
3. **Loops.** Each iteration picks ready tickets, dispatches them at **the tier their blast
   radius earns**, verifies with the project's real commands, re-tests from an angle the
   implementer did not use, and produces a 30-second demo.
4. **Reports once.** One block: what changed, goal progress, the real proof output, the demo,
   the next actions — and the same result appended to `.boil/log.md` as a ladder `EVIDENCE:`
   line. Written once, used twice.
5. **Stops itself.** Three brakes are binding and hand the decision to you rather than
   pressing on: **stall** (three iterations with no checkbox moving), **WIP** (more than 5
   actionable tickets), and **budget** (the goal's cap is spent).
6. **Terminates honestly.** `boil-doctor.py --final` refuses to write a `FINAL.md` unless
   every checkbox is green *and* carries a fresh evidence line. An unfinished goal produces
   `HANDOFF.md` instead — X of Y done, what is left, why.
7. **Re-measures before it believes.** A goal checkbox tagged `{#id}` is bound to a frozen check;
   `boil-check.py verify --write` runs the check and stamps the evidence itself, `boil-doctor.py
   --final` re-runs every check before a FINAL, and `boil-guard.py` keeps the worker off the
   tests, the protected paths, the frozen ruler, and the human sign-off. Data counts as evidence
   too: `boil-assert-db.py` turns a query plus an assertion into a check command.

## The controller (verifier-first, since 2026-08-29)

The loop's decisions are made by a script, not by the model. Per milestone the LLM is
called twice — once to **draft** an acceptance check, once to **attempt** the milestone —
and `scripts/boil-check.py` does the rest:

```bash
python3 scripts/boil-check.py compile --root P --spec P/.boil/milestones.json  # validate → freeze
python3 scripts/boil-check.py next    --root P                                 # first failing node
python3 scripts/boil-check.py run     --root P --milestone M3 --rerun          # 0 PASS · 10 RETRY · 20 STALL · 30 CAP · 40 BUDGET · 50 TAMPER
python3 scripts/boil-check.py split   --root P --milestone M3 --spec '[...]'   # 2-4 sub-checks, once
python3 scripts/boil-check.py audit   --root P --diff attempt.diff             # skip markers, protected-path writes, monkey-patching
python3 scripts/boil-check.py status  --root P                                 # one line, zero LLM tokens
python3 scripts/boil-review.py review --root P --milestone M3                  # after PASS: script decides if a 2nd model reads the diff
python3 scripts/boil-review.py close  --root P --milestone M3-fix              # one re-review; clean closes, else the user decides
```

Rules the script enforces, each with a test: a check that already passes is **not
falsifiable** and is never frozen; the check and its protected files are hashed together
and any drift is **TAMPER**; the implementer **never runs the check** — the controller
runs it once and returns one counterexample line; an identical failure twice is a
**STALL**; four attempts is the **CAP**; passed milestones are never re-run. The
evidence, per rule, is in `_research/boil-convergence/PLAN.md`.

## Effort tiers

Ceremony is chosen by blast radius, not by habit:

| Tier | What runs | Use for |
|---|---|---|
| **T1** direct *(default)* | the orchestrator edits, runs the test, shows the diff | config, copy, docs, deps, small covered refactors |
| **T2** delegated | one builder subagent + independent orchestrator verification | needs isolation, or parallelisable |
| **T3** adversarial | frozen answer key + builder + isolated judge in a different model family + deterministic manager + cross-LLM review | money, auth, data loss, production — or anything that already failed twice |

`tier:` is a required ticket field; `ticket-lint.py` warns when a T1/T2 ticket mentions
payment, auth, migrations or production. Most tickets are T1.

## Why the limits exist

Measured across the 15 projects carrying `.boil/` state on 2026-08-28:

| Project | Iterations | Tickets | goal.md | Checkboxes green |
|---|---:|---:|---:|---|
| susi | 13 | 71 | **976 B** | **7/7** |
| strategies | 21 | 107 | 5.6 KB | 8/8 |
| ttengine | **65** | **205** | 4.6 KB | **2/7** |
| fomo2 | 11 | 100 | **8.3 KB** | **0/7** |
| trtools2 *(archived)* | **69** | **308** | 6.5 KB | **0/13** |

Throughput was never the problem — ttengine closed 156 tickets, trtools2 closed 173.
Convergence was. Passes that file tickets rather than fix them make the pool a generator
(156 done / 40 open; 173 done / 104 open), and nothing stopped either run: `escalation.md`
existed **zero** times across 86 loop directories. Rules that live only in prose do not
execute. Every limit above is therefore a script with a test.

## The self-correcting loop (tier T3)

Every **T3** ticket runs a bounded correction cycle with three roles:

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

It also triggers on the outer-loop work absorbed from `gate`:

- "gate this project" / "audit this project" / "review the portfolio"
- "what should I work on?" / "init project governance"
- **any session started in a project that contains a `.boil/` directory**

Explicit invocation: `/boil <goal> till <condition>`, or the subcommands
`/boil init | status | audit | review | migrate`.

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
├── templates/                        charter, ladder, log, scorecard, CLAUDE.md snippet
├── examples/governance/              filled charter + ladder showing evidence discipline
├── references/
│   ├── clanker-constitution.md      Baseline conduct layer — the Clanker Constitution
│   │                                 verbatim (CC BY 4.0) + mapping to boil's hard rules
│   ├── outer-loop.md                 Charter, maturity ladder L0-L5, evidence rules,
│   │                                 the ticket-pool WIP rules, the three brakes,
│   │                                 portfolio + audit protocol (absorbed from gate)
│   ├── effort-tiers.md               T1/T2/T3: which ceremony a ticket pays and why
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
    ├── boil-now.py                   the session-start read; derives .boil/NOW.md
    ├── boil-brakes.py                tick per iteration; check stall / WIP / budget
    ├── boil-portfolio.py             regenerates PORTFOLIO.md; --check for CI/cron
    ├── boil-migrate.py               folds a legacy .gate/ into .boil/
    ├── boil_common.py                shared frontmatter/checkbox parsing helpers
    ├── boil-doctor.py                validates a `.boil/` workspace; --final is the
    │                                 termination gate (no FINAL.md without evidence)
    ├── ticket-lint.py                lints ticket schema, tier, goal size, answer keys,
    │                                 blockers, secrets
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

The skill treats the session as a small software firm that knows what it costs. It reads the board once (`NOW.md`), then each iteration picks ready tickets and gives each one only as much process as its blast radius earns: most are handled directly, some go to a specialist subagent, and the expensive minority — money, auth, data loss, production — get the full adversarial protocol with a frozen answer key and an independent judge. It verifies with the project's real commands, re-tests from an angle the implementer did not use, and produces a demo you can check in 30 seconds. When agents find work outside their ticket they file proposals; anything past the WIP limit goes to the icebox unrouted. The loop stops when the checklist is green **and evidenced**, when you say stop, or when a brake fires — three iterations without a checkbox moving, a pool that outran the consumer, or a spent budget. A fired brake hands you the decision; it does not grant itself another attempt.

## Hard rules

Eight, each mechanically checkable. Everything else lives in the reference that owns it —
that is what keeps `SKILL.md` at ~15 KB instead of 65 KB.

1. **One read at session start.** `boil-now.py`. Exit 3 means stop and ask.
2. **A goal is one ladder criterion** — max 7 checkboxes, max 2500 B, a demo target required. Enforced by `ticket-lint.py`.
3. **No claim without fresh output in the same message.** Run it, paste the line, then claim. Never from memory.
4. **Always re-test from an angle the implementer did not.**
5. **No iteration without a demo.** If you can't demo it, you can't claim it.
6. **Tier by blast radius; raise it after two failures, never lower it.** Lowering a tier to get past a failure is the same move as editing the answer key.
7. **The brakes are binding.** Three flat iterations, more than 5 actionable tickets, or a spent budget stop the loop and hand the decision to the user. The manager never grants itself another attempt.
8. **Protect the user's work.** Never reset, stash, overwrite, or amend without explicit authorization. Never merge a PR without it — a plan, a green key, or an accepted loop is not merge authority. Never add AI attribution trailers or commit as an AI identity.

Baseline conduct is the [Clanker Constitution](references/clanker-constitution.md) — honor
the request, act with judgment, finish the job, protect existing work, verify reality,
communicate for humans, learn in the right place. It is a floor and never an excuse:
"scale process to the task" governs which *tier* a ticket pays, not whether the clarity
gate, the demo, or a T3 answer key applies.

The rules that used to be numbered 9-25 have not been deleted — they moved into the
reference that owns them (`self-correcting-loop.md` for the answer key, retry limit and
tamper rules; `stories.md` for story coverage; `outer-loop.md` for evidence and the
portfolio), and are loaded when their trigger fires.

## Integration with other skills

`boil` orchestrates — it doesn't replace specialist skills:

- **[`superpowers`](https://github.com/obra/superpowers)** — `brainstorming`, `verification-before-completion`, `dispatching-parallel-agents`, `systematic-debugging`, `test-driven-development` are all referenced from inside the loop.
- **[`ralph-wiggum`](https://github.com/obra/ralph-wiggum)** — `boil` does the iteration internally rather than relying on a stop-hook loop, but you can wrap it with `/loop` for unattended runs.
- **[`roborev`](https://roborev.io)** — `scripts/boil-review.py` runs it *milestone-wise, on the script's decision*, not per commit: after a milestone PASS it fires only for a T3/T4 tier, a `risk_paths` hit, the final milestone, or `every_lines` accumulated unreviewed source lines; it adopts a job the post-commit hook already enqueued for HEAD; one review round + one fix round per milestone, never a ratchet. Must-fix findings become a `<M>-fix` DAG node gated by the parent's frozen check; the rest are deferred into `.boil/log.md` with the job closed — never silently dismissed. Claude implementations set `"agent": "codex"`; Codex implementations `"agent": "claude-code"`.
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
# the loop's own gates
python3 scripts/boil-now.py     --root /path/to/project --write   # THE session-start read
python3 scripts/boil-brakes.py  tick  --root /path/to/project --iteration iter-001 --spent-usd 0.80
python3 scripts/boil-brakes.py  check --root /path/to/project     # 0 continue / 2 restrict / 3 stop
python3 scripts/boil-doctor.py  --final --root /path/to/project --write   # termination gate
python3 scripts/boil-portfolio.py --root ~/workspace --check      # exits 1 on rule violations
python3 scripts/boil-migrate.py --root /path/to/project --apply   # fold a legacy .gate/ in

# T3 machinery
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

The minimal fixture in `examples/minimal-loop/` shows the expected state shape across
all three scopes — charter/ladder/log, goal/tickets/proof-map, and the brake state
(`budget.json`, `progress.jsonl`, `icebox.md`) — without committing a real `.boil/`
workspace to this skill repo. Its README shows what each part demonstrates and how to
make each gate fail on purpose.

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
