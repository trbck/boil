# Status logging — boil sessions in helm

> **Load when:** this session is driven by a helm contract, or you are wiring status logging. Not needed for an ordinary local loop — `boil-now.py` already surfaces state.

A long boil run is opaque: the operator sees a wall of tool calls, then a summary. This file defines the layer that fixes that — a status log written at every state transition, rendered two ways:

- **live** — the helm dashboard shows the running session: which ticket, which attempt, which verdict, what the manager decided and why
- **after the fact** — the same records are on disk, so "what happened in iteration 7 and why did T-0042 escalate?" is answerable without the transcript

boil never *depends* on helm. The project-local files are always written; the helm push is additive and fails silently when helm isn't installed.

---

## What gets written where

| Path | Owner | Purpose |
|---|---|---|
| `<project>/.boil/status.jsonl` | boil | Append-only event log. Canonical. One line per transition. |
| `<project>/.boil/STATUS.md` | boil | Rendered operator overview. Regenerated on every emit. |
| `<project>/.boil/session.json` | boil | This session's identity + full snapshot. |
| `$HELM_DIR/runs/boil/<session_id>.json` | boil writes, helm reads | The session as a helm object — what the dashboard and `helm boil` render. |
| `$HELM_DIR/runs/events/<YYYY-MM>.jsonl` | boil appends, helm reads | The same transitions on helm's chronological event log, as `boil.*` kinds. |

The contract between the two repos is **files, not imports**. boil writes plain JSON to known paths and helm reads it, so either side can be upgraded alone. Both use a single `O_APPEND` write for log lines (the kernel serializes it), so parallel subagents and the orchestrator can all log without a lock.

`HELM_DIR` resolution, in order: the `$HELM_DIR` env var, then `~/workspace/helm`, then `~/wp/helm`. A directory only counts if it contains `helm.py`. `$HELM_EVENTS_DIR` overrides the event-log location, matching helm's own convention.

---

## Commands

```bash
S=<boil-skill-repo>/scripts

# one transition (this also re-renders STATUS.md and pushes the snapshot)
python3 $S/boil-helm-log.py emit --root <project> --kind boil.judge.verdict \
        --ticket T-0042 --attempt 2 --status FAIL --detail "suite:tests/x::test_y:AssertionError"

# rebuild the snapshot from .boil/ state — idempotent, safe to run any time
python3 $S/boil-helm-log.py sync --root <project>

# attach this session to a helm criterion contract, so it lands on that goal's card
python3 $S/boil-helm-log.py link --root <project> --stem <contract stem>

# read it back locally
python3 $S/boil-helm-log.py session --root <project>          # rendered
python3 $S/boil-helm-log.py session --root <project> --json   # machine
```

Add `--no-helm` to keep a run entirely project-local (useful in tests and fixtures — a smoke test must never write into the operator's real helm stores).

`scripts/boil-loop.py` emits its own transitions automatically; pass it `--no-log` to suppress that.

---

## Event kinds

Namespaced `boil.*` so helm's existing prefix filter works unchanged: `helm events --kind boil`.

| kind | Emitted when | `status` carries |
|---|---|---|
| `boil.session.start` | Phase 1 bootstrap completes | the goal one-liner |
| `boil.iteration.start` | Step 2 begins an iteration | `iter-NNN` |
| `boil.dispatch` | A builder batch goes out | ticket ids |
| `boil.loop.init` | An answer key is frozen | the key kind |
| `boil.build.start` / `boil.build.done` | Builder dispatched / returned | attempt number, key integrity |
| `boil.judge.start` / `boil.judge.verdict` | Judge dispatched / verdict recorded | PASS / FAIL / INDETERMINATE / INVALID |
| `boil.manager.decision` | Manager decided | ACCEPT / REVISE / ESCALATE-* / ABORT-TAMPER |
| `boil.loop.accept` / `boil.loop.escalate` | A loop reached a terminal state | the terminal reason |
| `boil.story.replay` | Step 2d Pass 0 ran | green / red per story |
| `boil.demo` | Step 2e produced a demo | the demo path |
| `boil.blocker` | A human-action ticket was filed | the safe summary |
| `boil.iteration.gates` | `boil-run-iteration.sh` finished | ok / failure |

Every line carries `ts`, `kind`, `session`, `project`, and `stem` (empty when the session isn't linked to a helm goal), plus whichever of `ticket`, `attempt`, `status`, `detail` apply.

---

## The session object

`runs/boil/<session_id>.json` — everything the dashboard needs in one read, so rendering never has to walk the project tree:

```jsonc
{
  "session_id": "boil-myproject-20260803-101500",
  "stem": "myproject.filters.G2",        // "" when not linked to a helm goal
  "project": "/home/you/workspace/myproject",
  "project_name": "myproject",
  "goal": "chart refetches on filter change",
  "status": "running | blocked | done | idle",
  "iteration": "iter-003",
  "goal_progress": {"green": 2, "total": 5},
  "checkboxes": [{"done": true, "text": "filter triggers refetch"}],
  "tickets": [{
    "id": "T-0042", "title": "…", "specialty": "frontend", "status": "in-progress",
    "priority": "P1", "working_on": "implementing refetch hook",
    "answer_key": {"kind": "suite", "ref": "tests/…", "authored_by": "orchestrator",
                   "frozen_sha": "a4b5c6d"},
    "loop": {
      "status": "running", "attempts": 2, "max_revisions": 3,
      "last_verdict": "FAIL", "last_decision": "REVISE",
      "defect": "the refetch fires but with a stale date range",
      "failure_signature": "suite:tests/x::test_y:AssertionError",
      "trail": [{"n": 1, "verdict": "FAIL", "decision": "REVISE",
                 "judge_excerpt": "…the judge's evidence trace…",
                 "builder_family": "claude", "judge_family": "codex"}],
      "escalation": "…the human packet, when there is one…"
    }
  }],
  "decisions": [...],   // flattened manager decisions, newest last
  "blockers":  [...],   // human-action tickets + escalated loops, with safe summaries
  "events":    [...],   // the last 60 status events, newest first
  "demo": ".boil/iterations/iter-003/demo.md"
}
```

`judge_excerpt` is the first ~1500 characters of the judge's verdict file. That is deliberate: the dashboard shows the **reasoning**, not just the verdict, because a verdict with no visible evidence trace is exactly what the loop is designed to distrust. `builder_family` and `judge_family` are surfaced so a same-family builder/judge pair — the shared-blind-spot risk — is visible at a glance rather than buried in a JSON file.

Secrets never reach this object: it carries ticket metadata, `working_on` lines, judge traces, and manager reasons. Same rule as every other boil artifact — if it can't be in a ticket, it can't be in the status log. `human_action.safe_summary` is what surfaces for blockers, never the underlying credential or private URL.

---

## Reading it back

From helm:

```sh
helm boil                       # every boil session, live status first
helm boil --show <session_id>   # tickets, answer keys, judge verdicts, manager decisions
helm boil -c <stem>             # only sessions burning down that goal
helm events --kind boil         # the chronological log across all sessions
helm events --kind boil -c <stem> -n 100
```

From the dashboard: a **boil sessions** panel at the top level, and — for a linked session — a `🔥 boil` drawer on the goal's own card next to the journal drawer, showing the live ticket table, each ticket's frozen answer key, the attempt trail with the judge's reasoning, and the manager's decision + reason per attempt.

From the project, with no helm at all: `.boil/STATUS.md` is the same view in markdown, and `.boil/status.jsonl` is greppable.

---

## Where this sits in the chain

helm's existing **journal** (`journals/<stem>.md`) is the prose narrative of a goal across runs — hypotheses, findings, dead ends, reproducibility notes. The boil session object is the *mechanical* state of one session: tickets, verdicts, decisions, counters. They answer different questions and neither replaces the other. A steered boil session should keep writing the journal exactly as `build_boil_prompt` instructs, and the status log rides alongside it.

Rule of thumb: if a returning human would want to read it as a story, it goes in the journal. If the operator wants to know *what is happening right now*, it goes in the status log.
