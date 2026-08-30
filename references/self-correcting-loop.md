# The Self-Correcting Loop — builder / judge / manager

> **Load when:** you are running a **tier T3** ticket in a legacy ticket project (`references/legacy-ticket-loop.md`). Under the controller, a T3 *milestone* runs through the same `prepare` / `score` as every other tier: the frozen check is the answer key, the script is the judge, and the **manager role is dropped** — `score`'s exit code decides revise / finish / escalate, and `boil-review.py` is the cross-model review. See `references/effort-tiers.md`.

A `boil` ticket used to be a one-shot: dispatch a specialist, read its report, believe it or don't. This file defines the layer that replaces "believe it or don't" with a bounded, evidence-backed correction cycle.

Three roles, one ticket:

| Role | Job | Sees | Never sees |
|---|---|---|---|
| **builder** | Makes the attempt. | The ticket, goal/memory slices, the codebase, the *reference* of the answer key. | The judge's verdicts from other attempts, the manager's rationale. |
| **judge** | Checks the attempt against the answer key. Nothing else. | The answer key, the artifacts it names, the diff, the demo. | The builder's chat, the builder's self-report, prior judge runs on this ticket. |
| **manager** | Decides: revise, finish, or escalate to a human. | Everything — every attempt, every verdict, the budget, the clock. | — |

**The judge is the important part.** A judge with no answer key outside the builder's own reasoning is not a judge; it is the same model agreeing with itself in a different font. Every other rule in this file exists to protect that one property.

---

## The answer key (read this before anything else)

The answer key is the external ground truth the judge measures against. It is the difference between a correction loop and a hall of mirrors.

### The three kinds

| kind | What it is | Ground truth is | Judge's job |
|---|---|---|---|
| `suite` | A test selector or command. | The exit code + captured stdout of running it. | Run it (or read the captured run), quote the result line, compare to `expect`. |
| `document` | A source document — spec, API reference, upstream issue, RFC, schema, data file. | The document's own text. | Quote the specific lines the implementation must satisfy, then show where the artifact does or doesn't satisfy them. |
| `checklist` | A written rubric (`references/rubrics.md` shape) authored before the build. | The fixed `eval_steps`. | Execute every step in order, cite evidence per step, apply `pass_rule`. |
| `none` | No external key exists. | — | **No loop.** The ticket runs as a plain one-shot and may not close a goal checkbox. Requires a written `reason`. |

Anything that isn't one of those three is the builder grading itself. There is no fourth kind.

### The key contract on the ticket

```yaml
answer_key:
  kind: suite                       # suite | document | checklist | none
  ref: "tests/e2e/filter.spec.ts::refetches on date change"
  expect: pass                      # suite only: pass | fail | <exact stdout substring>
  authored_by: orchestrator         # orchestrator | user | upstream | <specialty> — NEVER the builder
  frozen_at: 2026-08-03T10:00:00Z   # before the first build attempt starts
  frozen_sha: a4b5c6d               # git sha (or content hash) of the key at freeze time
  protected: true                   # the builder may not edit the key's file(s)
  reason: ""                        # required only when kind: none
```

### The four freeze rules

1. **Authored elsewhere.** `authored_by` may never be the builder's specialty for this ticket. The orchestrator, the user, or an upstream source writes the key. A builder that writes its own key writes its own grade.
2. **Frozen first.** `frozen_at` must precede the first build attempt's start time, and `frozen_sha` must be the key's content hash at that moment. A key that appears after the attempt is a post-hoc justification.
3. **Protected during the loop.** The key's files are read-only to the builder — same principle as helm's `protected_paths`. If the key's hash changes mid-loop, the loop **aborts and escalates** as a tamper event. It does not "re-freeze and continue."
4. **Weakening is tampering.** Deleting a case, adding `skip`/`xfail`, loosening a threshold, or narrowing a selector all count as edits, even if the file's line count grows. The manager compares hashes, not intentions.

### Writing the key first

Write the judge's checklist **before** the ticket is dispatched — ideally before you know how you'd implement it. A key written after you've seen the implementation is shaped by the implementation. Practically, this means the orchestrator fills `answer_key` during Phase 1 (the answer-key map) or at ticket-creation time, never during Step 2c.

If you cannot state the key, you do not yet understand the ticket. That is useful information — file a `brainstorm` or `research` ticket instead of dispatching a builder at a fuzzy target.

---

## Adopting this — start narrow

Do not turn the whole loop on across a whole project on day one.

1. **Pick one narrow task you already repeat.** "Add an endpoint with tests." "Fix a failing story." "Port a component to the new design token set." Something you have done at least three times, where you already know what "right" looks like.
2. **Write that task's judge checklist first**, by hand, before automating anything. If writing it is hard, the loop would have been guessing.
3. **Run it with the retry limit at 1** for the first few tickets, so a bad key surfaces as a fast escalation instead of three expensive revisions.
4. **Raise the limit to 3 only after the key has caught a real error** — one the builder reported as done. Until then you have a loop with an unvalidated ruler.
5. **Then run the red-team suite** (below) before you let it run unattended.

---

## Loop state on disk

```
.boil/loops/
└── T-0042/
    ├── loop.json               # the manager's state machine — authoritative
    ├── attempt-1/
    │   ├── build.md            # builder's return report (verbatim)
    │   ├── judge.md            # judge's verdict + evidence trace
    │   └── manager.json        # the decision + why
    ├── attempt-2/
    │   └── …
    └── escalation.md           # written only when the loop escalates — the human packet
```

`loop.json` shape:

```json
{
  "ticket": "T-0042",
  "status": "running | accepted | escalated | aborted",
  "answer_key": { "kind": "suite", "ref": "…", "frozen_sha": "a4b5c6d", "frozen_at": "…" },
  "max_revisions": 3,
  "attempts": [
    {"n": 1, "started_at": "…", "verdict": "FAIL", "failure_signature": "suite:tests/x::test_y:AssertionError",
     "decision": "REVISE", "reason": "new failure signature, attempt 1 of 3", "cost_usd": 0.0}
  ],
  "budget": {"usd_cap": 0.0, "usd_spent": 0.0, "wall_clock_cap_min": 0},
  "escalated_to_ticket": ""
}
```

Everything in `loop.json` is written by `scripts/boil-loop.py`. Agents never hand-edit it — an agent editing the manager's state machine is the same failure class as a builder editing the key.

---

## The handoffs

Four handoffs. Each one has a **format**, a **trigger**, and a **failure path**. If any of those three is missing, the handoff will eventually deadlock or silently drop work.

| # | Handoff | Format | Trigger | Failure path |
|---|---|---|---|---|
| 1 | orchestrator → builder | Dispatch packet (`references/ticket-system.md`) + the key's `ref` (never the key's contents when `kind: checklist`) | Ticket picked in Step 2a and `loop.json` initialized | Builder can't start → `status: blocked` + `working_on` + return; manager records ABORT-BLOCKED, no attempt consumed |
| 2 | builder → judge | `build.md` — the ticket return contract, verbatim | Builder returns; orchestrator has verified the diff is real (`git diff --stat`) | Report missing required sections → manager returns it once as MALFORMED; a second malformed report consumes an attempt |
| 3 | judge → manager | `judge.md` — evidence trace + verdict + `failure_signature` | Judge writes its file | Verdict with no key evidence cited → **INVALID**, judge re-runs once, no attempt consumed; second INVALID escalates as an infra fault |
| 4 | manager → next role | `manager.json` — decision + reason (+ defect brief on REVISE) | Judge verdict recorded | Decision unreachable (budget/tamper/limit) → ESCALATE, write `escalation.md`, convert ticket to `human-action` |

### Handoff 1 — the build packet

Standard dispatch packet, plus this block:

```markdown
## Answer key (you are measured against this — you may NOT edit it)
- kind: suite
- ref: tests/e2e/filter.spec.ts::refetches on date change
- These files are READ-ONLY for you: tests/e2e/filter.spec.ts
- Making the key pass by editing, skipping, xfailing, or narrowing it ends this
  ticket as a tamper abort. Change the real code.
- You will not see the judge's verdict. Do not write to .boil/loops/.
```

When `kind: checklist`, give the builder the criterion sentence but **not** the `eval_steps`. Handing over the steps turns them into a spec to game rather than a measure to satisfy. When `kind: document`, give the builder the document — it's the source of truth for both sides.

### Handoff 2 — the build report

The existing ticket return contract (`references/ticket-system.md` § Return), written to `attempt-N/build.md`. Required sections: Changed files, Proof / tests, Confidence gate, New ticket proposals filed, Blockers, Demo notes, Acceptance criteria.

The manager checks one thing mechanically before passing it on: **the builder did not touch the key.** `git diff --stat` against the key's paths must be empty, and the key's hash must equal `frozen_sha`. If not — tamper abort, no revision offered.

### Handoff 3 — the judge verdict

`attempt-N/judge.md`:

```markdown
# Judge — T-0042 — attempt N

**Answer key:** <kind> — <ref>  (frozen_sha: <sha>)
**Key integrity:** VERIFIED (hash matches frozen_sha) | TAMPERED
**Criterion:** <what passing means, in one sentence, taken from the key>

## Evidence trace

### Check 1: <what the key demands>
**Action:** <what the judge ran / read>
**Observation:** <what came back — quote it>
**Evidence:** <command + output line | file:line from the document | artifact path>
**Result:** PASS | FAIL | INDETERMINATE

### Check 2: …

## Verdict
**Decision:** PASS | FAIL | INDETERMINATE | INVALID
**Failure signature:** <normalized one-liner — see below; empty on PASS>
**Reason (one sentence):** <the load-bearing finding>

## If FAIL — the defect, not the fix
<one sentence naming what is wrong, in the artifact's terms. Do NOT prescribe an
implementation — that is the builder's job and a prescribed fix biases the next attempt.>
```

Rules the judge operates under:

- **Cite the key or return INVALID.** Every PASS check must quote something from the key's execution or text. "Looks correct" is INVALID, not PASS.
- **Never run the builder's own claim as evidence.** The builder's `47 passed` line is hearsay; the judge re-runs the selector itself, or reads the captured run the orchestrator produced.
- **INDETERMINATE is a first-class answer.** Missing artifact, unreadable screenshot, key that won't execute → INDETERMINATE. Guessing is worse than admitting you can't see it.
- **Different model family than the builder where the runtime allows it.** Same-family judge is the shared-blind-spot risk; see the red-team scenario below. Record which family judged in `manager.json`.

**Failure signature** is a normalized string used for stall detection — `<kind>:<ref>:<error class>:<first distinguishing detail>`, e.g. `suite:tests/x.py::test_y:AssertionError:expected 3 got 5`. Two identical signatures in a row mean the revisions are not converging, and that is worth more than one more attempt.

### Handoff 4 — the manager decision

```json
{"attempt": 2, "verdict": "FAIL", "decision": "REVISE",
 "reason": "new failure signature; attempt 2 of 3",
 "defect_brief": "<the judge's one-sentence defect, verbatim>",
 "judge_family": "codex", "builder_family": "claude", "cost_usd": 0.0}
```

On REVISE, the builder is re-dispatched with the **defect brief only** — not the judge's full trace, and never the judge's prescribed fix. It gets what is wrong, not how the grader would fix it.

---

## The manager's decision table

Evaluated top to bottom; the first matching row wins.

| Condition | Decision | Effect |
|---|---|---|
| Key hash ≠ `frozen_sha`, or key file in the builder's diff | **ABORT-TAMPER** | Revert the key, write `escalation.md`, escalate. No further attempts. |
| Budget cap (usd or wall-clock) exceeded | **ESCALATE-BUDGET** | Stop. The packet says how much was spent on what. |
| Verdict INVALID, first occurrence | **RERUN-JUDGE** | Re-dispatch the judge. Attempt counter unchanged. |
| Verdict INVALID, second occurrence | **ESCALATE-INFRA** | The judge layer is broken; a human must look at the key. |
| Verdict INDETERMINATE, < 2 consecutive | **REVISE-VISIBILITY** | File a `demo-prep` ticket. Attempt counter unchanged. |
| Verdict INDETERMINATE, 2 consecutive | **ESCALATE-VISIBILITY** | You cannot see the work; more attempts won't change that. |
| Verdict PASS, key evidence cited | **ACCEPT** | Close the ticket, fill `proof`, allow the goal checkbox to move. |
| Verdict FAIL, attempt == `max_revisions` | **ESCALATE-LIMIT** | Hard stop. Full history to a human. |
| Verdict FAIL, same `failure_signature` as previous attempt | **ESCALATE-STALL** | Two identical failures = not converging. Stop early; don't burn attempt 3. |
| Verdict FAIL, attempt < `max_revisions` | **REVISE** | Re-dispatch the builder with the defect brief. |

**`max_revisions` is 3 and it is a hard limit.** Three failed revisions stop the loop and send the full history to a human. Not "usually three." The manager does not get to decide the task is nearly there.

Two brakes fire *before* the limit and both are deliberate: ESCALATE-STALL (same failure twice) and ESCALATE-BUDGET. An honest early stop is cheaper than a third attempt at a wall.

---

## Escalation — the human packet

`escalation.md` is what a human reads. It must be complete enough that they never open `loop.json`.

```markdown
# Escalation — T-0042 — <ESCALATE-LIMIT | -STALL | -BUDGET | -INFRA | -VISIBILITY | ABORT-TAMPER>

**Ticket:** T-0042 — <title>
**Goal checkbox:** <the goal.md line this was closing>
**Answer key:** <kind> — <ref> (frozen <when>, authored by <who>)
**Attempts:** 3 of 3   **Spent:** $X.XX / NN min
**Why it stopped:** <one sentence — the decision-table row that fired>

## What the human has to decide
<one sentence: the actual question. "Is the key right?" / "Is this task possible
as specified?" / "Which of two conflicting requirements wins?">

## Attempt history
### Attempt 1 — FAIL — <failure_signature>
- Built: <changed files, one line>
- Judge found: <the defect sentence>
- Manager: REVISE — <reason>
### Attempt 2 — …
### Attempt 3 — …

## What stayed constant
<the failure that survived every attempt — usually the real finding>

## Artifacts
- Diff: <sha range or file list>
- Judge traces: .boil/loops/T-0042/attempt-*/judge.md
- Full build reports: .boil/loops/T-0042/attempt-*/build.md
```

Then, mechanically:

1. Ticket becomes `type: human-action`, `status: blocked`, `priority: P0`, `working_on: "blocked on user decision: <safe summary>"`.
2. `human_action.safe_summary` = the "What the human has to decide" sentence. Secret-free — same rules as every other human-action ticket.
3. Susi bridge sync + Pushover, if the local bridge exists (SKILL.md Step 2d.5).
4. The escalation becomes the **first `Next:` item** in the iteration report block, phrased as an imperative.
5. The goal checkbox stays unchecked. An escalated loop is not a closed loop.

An escalation is a successful outcome of the system. The loop caught something it could not resolve and stopped cleanly with a complete record. That is the whole point — it is not a failure to be papered over with a fourth attempt.

---

## Red-team it before you trust it

Do not run this unattended until it has survived all four. Each is a real test with an expected observable behavior — `tests/test_selfcorrect.py` covers the harness half; the model half you run once by hand on a scratch ticket.

### 1. The unsolvable task

Give it a ticket that cannot be satisfied as written — a key demanding two contradictory things, or a feature requiring an unavailable dependency.

**Expected:** three FAIL verdicts (or an earlier ESCALATE-STALL), then `escalation.md` naming the contradiction, ticket converted to `human-action`, goal checkbox untouched.
**Failure to look for:** the loop "succeeds" on attempt 3 by reinterpreting the ticket, or the manager grants a fourth attempt.

### 2. The confidently wrong answer

Have the builder return `confidence: 100` on all three axes, a report full of green claims, and code that does not actually satisfy the key.

**Expected:** judge FAILs on re-executed key evidence. The builder's confidence block is not an input to the manager's decision at all.
**Failure to look for:** ACCEPT because the report looked thorough. If confidence scores can move the verdict, the judge is decorative.

### 3. The shared model blind spot

Run builder and judge on the same model family against a task where that family has a known systematic error (a deprecated API it still emits, an idiom it consistently mis-uses).

**Expected:** the `suite`/`document` key catches it regardless of family, because it isn't a model opinion. If only a `checklist` key exists, the same-family judge will likely miss it — which is exactly why `manager.json` records both families and why a different-family judge is preferred.
**Failure to look for:** a PASS whose evidence is the judge's own reasoning rather than a quote from the key. That verdict should have been INVALID.

### 4. The most expensive possible run

Price the worst case before you fund it:

```
worst case = max_revisions × (1 build + 2 judges) + manager overhead
           = 3 builds + 6 judges + 3 manager decisions
```

Two judges per attempt, not one: an attempt can absorb exactly one INVALID or INDETERMINATE re-run before the loop escalates as an infra/visibility fault. That is the ceiling — a third judge run on the same attempt is unreachable.

Run one ticket deliberately to that ceiling with the budget cap set just above it.

**Expected:** the run stops at the cap with ESCALATE-BUDGET, and `escalation.md` reports the spend. The cost of a hopeless ticket is bounded and known.
**Failure to look for:** unbounded builder retries inside a single attempt, or a judge re-run loop that never consumes the attempt counter.

If the system catches real errors and stops cleanly on all four, you can run it without watching every step.

---

## Status logging — helm

Every state transition emits a status event, so the loop is watchable in real time and reviewable afterwards:

```bash
python3 <boil-skill-repo>/scripts/boil-helm-log.py emit --root <project> \
  --kind boil.judge.verdict --ticket T-0042 --attempt 2 \
  --status FAIL --detail "suite:tests/x::test_y:AssertionError"
```

That writes `.boil/status.jsonl` and re-renders `.boil/STATUS.md` always, and additionally pushes the session snapshot into helm when helm is present. See `references/helm-status.md` for the event kinds, the session object, and how it renders on the helm dashboard.

The events the loop must emit, at minimum:

| Transition | kind | status |
|---|---|---|
| `loop.json` created | `boil.loop.init` | the key kind + ref |
| Builder dispatched | `boil.build.start` | attempt number |
| Build report recorded | `boil.build.done` | changed-file count |
| Judge dispatched | `boil.judge.start` | attempt number |
| Verdict recorded | `boil.judge.verdict` | PASS/FAIL/INDETERMINATE/INVALID + signature |
| Manager decided | `boil.manager.decision` | the decision + reason |
| Loop ended | `boil.loop.accept` / `boil.loop.escalate` | terminal reason |

---

## How this relates to the layers you already have

- **`proof_strategy`** says *what shape* of proof a ticket needs. The **answer key** says *which specific external artifact* is the ruler and pins its hash. Every behavior ticket has both; they are not alternatives.
- **Rubrics** (`references/rubrics.md`) are the `checklist` answer-key kind. A rubric attached to a ticket is that ticket's key; a rubric attached to a goal checkbox stays where it is, evaluated at iteration level in Step 2d Pass 3. Same file format, two scopes.
- **Stories** (`references/stories.md`) are the user-experience contract and are usually the best `suite` key for user-perceivable work — the runner already produces a re-executable green/red.
- **Pass 2 (adversarial re-test)** attacks from an angle nobody specified in advance. The judge checks the angle that *was* specified in advance. Keep both: the key catches "didn't do what was asked", Pass 2 catches "did what was asked and broke something else."
- **Pass 4 (roborev cross-LLM review)** reviews the code as code. The judge measures behavior against the key. A clean roborev pass is not a substitute for a green key, and vice versa.
- **helm** (`references/helm-status.md`) is the controller above all of this: it owns the goal's setpoint and the outer measure→steer→re-measure cycle, and it is where these events are watched. The answer key is to a ticket what a helm criterion contract is to a goal — the same principle at a smaller scale, which is why the tamper rules read the same.
