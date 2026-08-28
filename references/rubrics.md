# Semantic Rubrics — LLM-as-Judge for `boil`

> **Load when:** a goal checkbox that moved this iteration has a rubric attached, inline or in `.boil/rubrics/`. Deterministic criteria (exit codes, latency, schema checks) never need one — direct verification covers them.

Vibe-checking a demo is not verification. When a goal contains a semantic criterion ("the agent honored the user's constraint across turns", "the dashboard is actually readable", "the refactor preserved behavior") string-match and exit codes will tell you nothing. This file defines the rubric layer: how to encode semantic acceptance as code, and how to dispatch a context-isolated judge to evaluate it.

This is the `boil` adaptation of G-Eval / LLM-as-Judge with forced evidence traces. The rubric is the deterministic part. The judge is the non-deterministic engine that executes it.

---

## When to use rubrics (and when NOT to)

**Use a rubric when** the goal checklist item is semantic — pass/fail depends on intent, behavior over time, subjective quality, or anything you can't reduce to an exit code:

- "Chatbot maintains the refund-method constraint from turn 1 across the rest of the conversation."
- "The dashboard's loading state is obvious to a first-time user."
- "The refactor preserved the public API contract."
- "Error messages tell the user what to do next, not just what went wrong."

**Skip the rubric when** the criterion is deterministic — a command's exit code is the truth:

- "`pnpm test` exits 0."
- "p95 latency on `/api/orders` is under 200ms over a 1k-request run."
- "Lighthouse a11y score ≥ 95 on `/admin`."
- "The migration completes without errors against a fresh DB."

Deterministic checks stay in Step 2d Pass 1. Rubrics live in Pass 3 (new — see below). If a checklist item has both a deterministic and a semantic side, write it as two checklist items and rubric only the semantic half.

### Rubrics at two scales

A rubric is a **written checklist**, which makes it one of the three valid answer-key kinds in `references/self-correcting-loop.md`. The same file format serves two scopes:

| Scope | Attached to | Evaluated at | Consequence of FAIL |
|---|---|---|---|
| **Ticket** (`answer_key.kind: checklist`) | one ticket, frozen before its first build attempt | Step 2c.5, once per attempt | the manager's decision table — REVISE, or escalate at the retry limit |
| **Goal** (this file's original scope) | one `goal.md` checkbox | Step 2d Pass 3, once per iteration | the checkbox stays unchecked; one ticket per failed rubric |

Nothing below changes for goal-scope rubrics. When a rubric is used as a *ticket's* answer key, three extra rules apply, and they exist to keep the judge external:

1. **It is frozen and hashed** before the builder is dispatched (`boil-loop.py init`), and it is read-only for the duration.
2. **The builder gets the `criterion` sentence, never the `eval_steps`.** Handing over the steps turns a measure into a spec to game.
3. **A verdict that cites no evidence from the rubric's artifacts is INVALID, not PASS** — the manager downgrades it automatically and re-runs the judge.

A `suite` key (a real test) is stronger than a `checklist` key whenever one is available, because it doesn't share the judge's priors — see the shared-blind-spot scenario in the red-team suite. Reach for a `checklist` key when the criterion genuinely cannot be reduced to an exit code, not when writing the test is inconvenient.

---

## Rubric anatomy

A rubric is structured data attached to one `goal.md` checklist item. Every rubric has the same five fields:

```yaml
id: R-001                        # stable, used in judge output filenames
checkbox: <verbatim goal checklist item this rubric backs>
criterion: <one-sentence semantic question the judge will answer>
eval_steps:                      # ordered, deterministic instructions to the judge
  - <step 1 — what to extract>
  - <step 2 — what to verify>
  - <step 3 — what to compare>
  - <step 4 — scoring rule>
artifacts_required:              # what the judge needs to see (paths relative to .boil/)
  - iterations/iter-NNN/demo.md
  - iterations/iter-NNN/artifacts/<file>
  - <any other concrete artifact, e.g. a transcript, a diff file, a screenshot>
pass_rule: <exact pass/fail logic, e.g. "score == 1" or "all 4 steps return PASS">
```

The `eval_steps` field is the most important. Specificity is the whole point — vague steps ("decide if the output is good") collapse back into vibe-checking. The judge's job is to *execute* the steps, not interpret them.

### Two ways to store rubrics

**Inline in `goal.md`** — preferred when there are ≤5 rubrics and they fit comfortably under each checklist item. Extends the state-files template like so:

```markdown
## Success checklist

- [ ] Agent maintains refund-method constraint across all turns of a session.
  ```yaml
  rubric:
    id: R-001
    criterion: "Agent never offers store credit if the user declined it in turn 1."
    eval_steps:
      - "Extract the user's stated refund constraint from turn 1 of the transcript."
      - "Scan every subsequent agent message for offers of store credit / wallet balance / gift card."
      - "Verify the final resolution names a payment method consistent with turn 1's constraint."
      - "Score 1 if all checks pass, 0 if any agent message violates the constraint."
    artifacts_required:
      - iterations/iter-NNN/artifacts/transcript.json
    pass_rule: "score == 1"
  ```

- [ ] <next checklist item>
```

**Separate file in `.boil/rubrics/R-NNN.md`** — preferred when the rubric is long, references a lot of artifacts, or is shared across multiple checklist items. The checklist item just carries `rubric: R-001` and the file holds the rest.

Pick one style per project and stick with it.

---

## The judge subagent

The judge is dispatched at Step 2d Pass 3 (after direct verification and adversarial re-test). It is **context-isolated by design** — this is what prevents the "graded their own homework" failure mode.

### What the judge receives

Only:
1. The rubric (the full YAML block above).
2. The `artifacts_required` files, read fresh.
3. The iteration's `demo.md`.
4. The diff range for the iteration (`git diff <prev-iter-sha>..HEAD --stat` and any specific files the rubric points at).

### What the judge does NOT receive

- The implementation chat history.
- The ticket the implementer worked on.
- The implementer's self-report or summary.
- Any prior judge runs for the same rubric (each judge run is independent — a flaky pass last iteration shouldn't bias this one).

### What the judge must produce

A markdown file at `.boil/iterations/iter-NNN/judges/R-NNN.md` with this exact shape:

```markdown
# Judge — R-001 — iter-NNN

**Criterion:** <copied from rubric>
**Pass rule:** <copied from rubric>

## Evidence trace

### Step 1: <step text from rubric>
**Action:** <what the judge actually did>
**Observation:** <what it found>
**Result:** PASS | FAIL | INDETERMINATE
**Evidence:** <quote, file:line, or artifact reference>

### Step 2: <step text>
...

## Verdict
**Score:** <number or PASS/FAIL>
**Decision:** PASS | FAIL | INDETERMINATE
**Reason (one sentence):** <the load-bearing finding from the trace>

## If FAIL — actionable next step
<exactly one sentence the orchestrator can copy as a ticket title>
```

The evidence trace is non-negotiable. A judge that returns only a verdict — even if it's "correct" — is unusable, because the orchestrator can't tell *which step* failed, can't file a precise ticket, and can't audit drift over iterations. **Treat the trace as the real output; the verdict is a derived summary.** The trace should contain actions, observations, and cited evidence, not hidden chain-of-thought.

### Dispatch prompt template

```
You are the judge for rubric R-NNN. Your only job is to execute the eval_steps below and return the verdict file at .boil/iterations/iter-NNN/judges/R-NNN.md.

You have not seen the implementation. You do not need to know how the work was built. You evaluate ONLY what is in the artifacts.

# Rubric
<paste the full rubric YAML>

# Artifacts (read these before doing anything else)
<list the absolute paths from artifacts_required>

# Diff for this iteration
<paste the output of `git diff <prev-sha>..HEAD --stat` and any per-file diffs the rubric points at>

# Demo report
<paste the contents of .boil/iterations/iter-NNN/demo.md>

# Output requirements
Write your verdict to .boil/iterations/iter-NNN/judges/R-NNN.md using the exact template in references/rubrics.md ("What the judge must produce"). Every eval_step must appear as its own section with Action, Observation, Result, and Evidence. The Verdict section is derived from those step results — if the pass_rule says "score == 1" and any step is FAIL, the verdict is FAIL. Do not skip steps. Do not collapse steps. If an artifact is missing, mark the relevant step INDETERMINATE and explain in Observation.

Return: the absolute path of the file you wrote, plus a one-line verdict summary.
```

Route the judge with `specialty: judge` (see `references/specialty-routing.md`).

---

## Orchestrator workflow — Step 2d Pass 3

After Pass 1 (direct verification) and Pass 2 (adversarial re-test from a different angle), the orchestrator runs Pass 3 — semantic judgment — IF the iteration touched any goal checkbox that has a rubric attached.

1. **Identify in-scope rubrics.** For each goal checkbox the iteration claims to have moved or closed, gather its rubric (inline block or `.boil/rubrics/R-NNN.md`).
2. **Skip rubrics nothing touched.** If no artifacts in `artifacts_required` changed this iteration and the rubric isn't a re-check rubric (see "Standing rubrics" below), skip — it would only be re-confirming prior work.
3. **Dispatch all judges in parallel.** One Agent call per rubric, all in a single message, using the prompt template above. They are pure functions of artifacts → verdict — no shared state, safe to parallelize.
4. **Collect verdicts.** Read each `judges/R-NNN.md`. Tally PASS / FAIL / INDETERMINATE.
5. **Act on the results:**
   - **All PASS** → mark the corresponding goal checkboxes green in `goal.md`. Proceed to demo summary.
   - **Any FAIL** → leave the checkboxes unchecked. File one ticket per failed rubric using the "actionable next step" sentence verbatim as the ticket title. Tag the ticket with the specialty the failure points at (a refund-flow rubric failure → `backend` or whatever owns the flow). Continue the loop.
   - **Any INDETERMINATE** → the artifact set is broken or missing. File a `demo-prep` ticket, not an implementation ticket — the work might be done, you just couldn't see it.
6. **Cite verdicts in `summary.md`.** Add a line: `Rubrics evaluated: R-001 PASS, R-002 FAIL → T-00XX, R-003 SKIPPED (no touched artifacts).` The user should see the judge outcomes alongside the test counts.

### Termination implication

Phase 3 termination criterion 1 now reads:
> Every checkbox in `goal.md` is checked, AND the most recent direct + adversarial verification both pass, AND **every rubric attached to a checked checkbox has a current PASS verdict in this iteration or the most recent iteration that touched its artifacts**, AND the user accepted the most recent demo.

The judge replaces the orchestrator's eyeball check of semantic criteria. It does not replace user acceptance — the user is still the final authority on the demo.

---

## Standing rubrics (regression catches)

Some rubrics shouldn't only run when their artifacts change — they're invariants. ("The agent's tone is never condescending." "Error messages always include a next-step.") Mark these with `standing: true` in the rubric YAML; they run every iteration regardless of which files changed. Keep the standing set small — every standing rubric multiplies judge cost per loop.

---

## Authoring rubrics — practical guidance

**Write eval_steps as instructions, not questions.** Bad: "Was the constraint honored?" Good: "Extract the constraint from turn 1. Scan turns 2-N. Report violations with line refs."

**Force the judge to cite evidence.** Every step's Result must be backed by Evidence — a quote, a `file:line`, an artifact path. A trace with no evidence is a vibe-check wearing a uniform.

**Keep steps independent where possible.** A step that depends on the previous step's interpretation is fragile. Steps that each extract or check one specific thing are robust.

**Use INDETERMINATE liberally.** A judge that guesses when it can't see the artifact is worse than one that flags the gap. INDETERMINATE → `demo-prep` ticket → fix the visibility → re-judge cleanly.

**Re-author when a rubric flaps.** If a rubric flips PASS/FAIL between iterations on artifacts that didn't meaningfully change, the rubric is the problem, not the implementation. Tighten the eval_steps until the judgment is stable.

**Cap rubrics per goal at ~5.** More than that and you're writing a test suite, not a goal contract — push the surplus down into actual tests the deterministic Pass 1 can run.

---

## Common rubric patterns

**State retention** — "Across N turns, the agent never violates constraint X established in turn M." Extract → scan → check → score.

**Behavioral preservation** — "After the refactor, behavior B still holds." Run B against pre-diff version, run B against post-diff version, compare outputs, score on equivalence.

**UX intent** — "A first-time user can complete task T without external help." Walk through the artifact (screenshot, recording, transcript) as if seeing it cold; flag every place help would be needed; score on count.

**Contract preservation** — "The public API's response shape for endpoint E is unchanged for inputs I1..In." Compare schemas, not just status codes.

**Tone / safety** — "No agent message is condescending / dismissive / unsafe." Scan every agent message; classify; score on count of violations.

Patterns are starting points — adapt the eval_steps to the actual artifact you have.

---

## Gotchas

- **The judge is an LLM. It can be wrong.** Treat its FAIL verdicts as strong signals, not gospel. If a judge fails a rubric the user clearly considers passed, fix the rubric or push back in the trace — don't loop forever on a bad rubric.
- **Don't route the judge through the implementer's specialty.** A frontend dev judging frontend work is the bias the article warns about. The `judge` specialty maps to a generalist or research-style agent precisely because it shouldn't share priors with the implementer.
- **Judges cost real tokens.** Every rubric × every iteration that touches it = one subagent dispatch. Budget by skipping irrelevant rubrics aggressively (step 2 above).
- **Don't let rubrics replace user acceptance.** The judge passing is necessary, not sufficient. The user accepting the demo is still the final gate in Phase 3.
- **Version your rubrics with the goal.** If the user refines `goal.md`, audit the rubrics — a refined goal often invalidates an old rubric's eval_steps. Stale rubrics are worse than no rubrics.
