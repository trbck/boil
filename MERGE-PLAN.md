# Plan: merge `gate` into `boil` as one token-aware skill

Status: steps 2-7 built and tested on branch `merge-gate` (2026-08-28). Steps 1 and 8 pending — see §9.

---

## 1. What the evidence actually says

Measured across the 15 projects in `~/workspace` that carry `.boil/` state.

| Project | Iters | Tickets | goal.md size | Checkboxes green |
|---|---|---|---|---|
| susi | 13 | 71 | **976 B** | **7/7** |
| MAF | 12 | 64 | — | 5/5 |
| strategies | 21 | 107 | 5.6 KB | 8/8 |
| oddstrading | 6 | 18 | 5.9 KB | 0/9 (honest negative — goal was falsification) |
| ttengine | **65** | **205** | 4.6 KB | **2/7**, still L1 in PORTFOLIO |
| fomo2 | 11 | 100 | **8.3 KB** | **0/7** |
| _archive/trtools2 | **69** | **308** | 6.5 KB | **0/13**, archived |

Three facts fall out:

1. **The inner loop works when the goal is small.** susi's goal.md is 976 bytes: 7 observable
   checkboxes, one demo target, explicit out-of-scope. It went 7/7. It is the best spec in the
   workspace and it is already ours — v2's goal template should just be that file.
2. **The inner loop cannot rescue a project-sized goal.** ttengine burned 65 iterations and 205
   tickets and is still at L1 with 2/7. trtools2 burned 69 iterations and 308 tickets, reached
   0/13, and got archived. Neither run was lazy — they were *productive*: 156 and 173 tickets
   closed respectively. Throughput was never the problem. Convergence was.
3. **The layer that fixes convergence exists and is not being run.** Only 4 of 15 boil projects
   have `.gate/`. `PORTFOLIO.md` was last generated 2026-07-23 and has been sitting on
   "WIP limit breached: 4 active" for five weeks. gate is correct and unused, because it is a
   separate skill that must be voluntarily invoked. Voluntary governance is not governance.

Supporting detail:

- **The ticket pool is a generator, not just a queue.** Passes 2/3/4 are specified to *file*
  tickets rather than fix ("Do not try to fix roborev findings in the same iteration"). Result:
  ttengine 156 done / 40 still open; trtools2 173 done / 104 open. Each iteration nets more work
  than it removes. trtools2's schema also disintegrated under load — 21 distinct `status:` values
  including `done-interesting-tail-fragile`.
- **The brakes never fired.** 60 loop dirs in ttengine, 26 in fomo2, and `escalation.md` exists
  **zero** times anywhere. Across 65 iterations nothing ever hit the 3-revision limit. Either the
  machinery wasn't run as written, or its terminal states are unreachable in practice. A rule that
  lives only as prose in a 65 KB file does not execute.
- **Resident context cost.** `SKILL.md` is 65 KB (~16k tokens) loaded on every trigger, plus 12
  reference files totalling ~160 KB it instructs you to read, plus 26 hard rules to re-honour each
  turn. Across 17 edits since May, every commit added a mechanism; none removed one.
- **Reporting is written seven times.** Per iteration: `demo.md`, machine summary, human narrative,
  suggested-next-steps, orientation footer, `STATUS.md`, iteration summary — all restating the same
  state.

**Diagnosis:** boil is a verification framework with a build loop attached. It has no cost governor
and no outer-loop stop. gate is the missing stop, and it is optional. The fix is not more rigor —
it is *placing* the rigor.

---

## 2. Target: one skill, three scopes

Keep the name `boil` (installed everywhere, the verb is right); gate is absorbed, not bolted on.

| Scope | Question | Cadence | Artifact |
|---|---|---|---|
| **Portfolio** | should I be in this project at all? | session start, automatic | `~/workspace/PORTFOLIO.md` |
| **Ladder** | is the project converging? | end of every iteration, automatic | `.boil/ladder.md`, `.boil/log.md` |
| **Run** | is this one thing built and proven? | the loop | `.boil/goal.md`, tickets, demo |

One state directory. `.gate/` merges into `.boil/`:

```
.boil/
  charter.md   # gate: why, north star, kill criteria, non-goals
  ladder.md    # gate: L0–L5 evidence-gated criteria
  log.md       # gate: append-only, one EVIDENCE line per iteration
  NOW.md       # GENERATED: the only file read at session start (~40 lines)
  goal.md      # boil: ONE ladder criterion, ≤7 checkboxes, ≤1500 B
  tickets/     # boil: max 5 open, rest in icebox.md
  budget.json  # NEW: enforced ceiling
```

The seam that makes the merge clean: **boil's demo proof and gate's EVIDENCE line become the same
artifact.** One green iteration emits one line that simultaneously closes a boil checkbox and ticks
a gate ladder box. Today that hand-off is manual prose; that is why it never happens.

---

## 3. The nine changes

**C1 — Cut resident context ~4x.** `SKILL.md` to ≤350 lines (~5k tokens): the loop, the stop
conditions, a router table. Everything else moves behind an explicit trigger — *"read
`references/rubrics.md` only when a checkbox has a rubric attached."* 26 hard rules compress to the
8 a script can check; the rest demote into the reference that owns them.

**C2 — Effort tiers, chosen by blast radius.** Today every ticket pays the full ceremony: packet →
builder → judge → manager → 5 verification passes → demo → 3 report surfaces. ~6 model calls
minimum, for a config tweak and a payment flow alike.

| Tier | What runs | When |
|---|---|---|
| **T1 direct** (default) | orchestrator edits, runs the test, shows the diff | most tickets |
| **T2 delegated** | one builder subagent + orchestrator verification | needs isolation or parallelism |
| **T3 adversarial** | builder + independent judge + frozen answer key + cross-LLM review | money / auth / data-loss / irreversible, or after two T2 failures |

Tier is a required ticket field. The ladder criterion or the user can force T3. This is the single
biggest token line-item: today everything is T3.

**C3 — Enforced budget.** `budget.json` sets per-iteration and per-goal ceilings.
`boil-loop.py decide` already takes `--cost-usd`; wire it to a real stop. At 60%: drop to T1-only,
stop filing new tickets. At 100%: stop, report spend against checkboxes closed, ask.

**C4 — WIP limit on the ticket pool.** Max 5 open tickets (gate's NOW rule, applied one scale
down). Proposals beyond that go to `icebox.md` and are not routed. Fixes the generator problem
directly: the queue can no longer outrun the consumer.

**C5 — The convergence brake, moved inside.** gate's stall rule — 3 sessions with no gate delta —
runs automatically at the end of every boil iteration. **Three consecutive iterations with no
checkbox moving = the loop exits** and asks: split the criterion, re-scope, or park. Computed by
script from the iteration records, so it cannot be vibed past. This is the rule that would have
stopped trtools2 at iteration 10 instead of 69.

**C6 — Goal size limit, enforced by lint.** Goal = exactly one ladder criterion, ≤7 checkboxes,
every checkbox observable as a command or URL, and a demo target required. `ticket-lint.py`
errors above that. Larger intent belongs on the ladder, not in the goal.

*Built as:* error above **2500 bytes**, warning above 1800, rather than the 1500 B written
here originally. 1500 B did not leave room for the `## Requirements understanding` table that
`boil-doctor.py` already requires, so a compliant goal could not have been written. 2500 B is
still far below every failure measured (4.6-8.3 KB) and above susi's 976 B success.

**C7 — Report once.** One demo block in chat (what changed / the one command or URL / which
checkbox moved) + one appended EVIDENCE line in `log.md`. Delete the narrative, the
suggested-next-steps block, and the mandatory footer as *separate* surfaces — fold their content
into the single demo block. Seven surfaces to two.

**C8 — Termination is a script.** `boil-doctor.py --final` refuses to write `FINAL.md` unless every
checkbox carries fresh evidence. With checkboxes open, the only writable artifact is `HANDOFF.md`:
X of Y done, what is left, why. (Today's FINALs are honest — but nothing *makes* them honest.)

**C9 — Portfolio check at session start, automatic.** Read `NOW.md`; if the project is `parked`,
say so and stop before any work. If WIP > 3, surface it first. No `/gate review` to remember.

---

## 4. What gets removed or demoted

Nothing in boil is wrong; there is simply too much of it resident at once.

- **Demoted to tier-gated references** (loaded only when their trigger fires): stories, rubrics,
  roborev cross-LLM review, self-correcting builder/judge/manager, helm status logging, L-SDF,
  hound, Susi bridge, plain-English output.
- **Compressed in place:** the Clanker Constitution summary (7 lines in SKILL.md → 1 line + a
  pointer), the 26 hard rules (→ 8 checkable + the rest in references).
- **Deleted as separate surfaces:** the human narrative block, the suggested-next-steps block, the
  mandatory `----------` footer — content folded into the one demo block.

---

## 5. Migration

15 projects carry `.boil/` state; 4 also carry `.gate/`.

1. `boil migrate --root <project>` — fold `.gate/` into `.boil/`, generate `NOW.md`, preserve
   history, emit a one-screen honest scorecard. Dry-run by default.
2. **Migrate only the 3 that will be active.** The other 12 stay as-is; they are archives.
3. **First real use is a decision, not a build:** run the portfolio review across all 15 and park
   or kill down to 3 active. "Not reaching the goal on respective projects" is partly a statement
   that 15 loops are open at once.

---

## 6. How we know it worked

The merged skill logs cost per closed checkbox. Claims to verify after 3 goals, not before:

| Metric | Today | Target |
|---|---|---|
| Resident context on trigger | ~16k tokens | ~5k |
| Model calls per average ticket | ~6 | ~1.5 |
| Report surfaces per iteration | 7 | 2 |
| Iterations per closed checkbox | ttengine 32.5 | ≤5 |
| Projects with a stale outer loop | 11 of 15 | 0 (it is automatic) |

Estimated 60–75% fewer tokens per closed checkbox. That is a projection from the call-count and
context math above, not a measurement — the instrumentation exists so it becomes checkable.

---

## 7. Decisions taken (2026-08-28)

1. **Name: keep `boil`.** gate is absorbed; the `gate` repo becomes read-only/archived. No reinstall,
   no AGENTS.md churn.
2. **Cut depth: demote everything behind triggers.** Nothing is deleted. Stories, rubrics, roborev,
   the self-correcting loop, helm, L-SDF, hound, Susi bridge, and plain-English output all survive as
   references loaded only when their trigger fires. Reversible.
3. **Migration: the 3 active projects only.** The other 12 stay untouched as archives.

### Build order — status

| # | Step | Why first |
|---|---|---|
| # | Step | Status |
|---|---|---|
| 1 | Portfolio park/kill pass across the 15 → pick 3 active | **pending** — needs the user's decision (§9) |
| 2 | `SKILL.md` to ≤350 lines + router table; mechanisms behind triggers | **done** — 661 → 326 lines, 65 KB → 15 KB |
| 3 | Effort tiers T1/T2/T3 + required `tier:` field | **done** — `references/effort-tiers.md`, lint-enforced |
| 4 | Brakes: stall, WIP, budget | **done** — `boil-brakes.py`, 11 tests |
| 5 | Fold `.gate/` into `.boil/`; unify demo proof and EVIDENCE line | **done** — `boil-migrate.py`, `--final` requires the EVIDENCE line |
| 6 | `goal.md` size lint | **done** — `ticket-lint.py lint_goal` |
| 7 | `boil-doctor.py --final` gate + `HANDOFF.md` | **done** — 4 tests |
| 8 | Migrate the 3 active projects | **pending** — after step 1 names them |

Steps 2–7 landed on branch `merge-gate`: 71 tests green (43 pre-existing + 28 new), full CI
sequence green locally.

### What was built beyond the plan

- **`boil-now.py`** — the single session-start read, deriving `NOW.md` (~31 lines on a real
  project) from charter + ladder + goal + tickets + brakes + log. The plan assumed NOW.md
  would exist; this is its generator, and its exit code carries the instruction (0/2/3).
- **A portfolio reality check.** `status: active` is a claim; commit activity is evidence.
  `boil-portfolio.py` compares them and adds three health flags the gate version lacked:
  `UNAUDITED` (busy repo, no ladder delta — ttengine: 297 commits, 53 days), `DECLARED-DEAD`
  (active, 0 commits), `UNGOVERNED` (busy repo, `.boil/`, no charter — helm and strategies).
- **Backfill.** `boil-migrate.py` seeds `progress.jsonl` from existing `iterations/` so the
  stall brake is not blind on a project that has already run 65 iterations. Backfilled
  records carry `green: null` and never count as flat.

## 9. Open decisions (step 1)

The portfolio, regenerated with the reality check, says real WIP is **6**, not the declared 4:

| Project | Status | Commits 30d | Ladder delta | Flag |
|---|---|---:|---|---|
| ttengine | active | 297 | 53 days | UNAUDITED |
| fomo2 | active | 111 | 44 days | UNAUDITED |
| strategies | *(none)* | 61 | — | UNGOVERNED |
| helm | *(none)* | 48 | — | UNGOVERNED |
| sb_wtools | active | 2 | 50 days | ZOMBIE |
| oddstrading | active | 0 | 36 days | DECLARED-DEAD |

Needed from the user: which **3** are active. The evidence suggests ttengine, fomo2, and one
of strategies/helm; sb_wtools and oddstrading are parks on their own numbers.

---

## 8. Objections, answered

**"You are removing the verification that made boil trustworthy."** T3 keeps all of it — the frozen
answer key, the independent judge, the cross-LLM review — gated to where a mistake is expensive. And
universal T3 is what produced zero escalations across 60 loops. Ceremony everywhere is not rigor
anywhere.

**"Merging two skills makes the skill bigger."** The merged `SKILL.md` is smaller than boil's alone,
because ~60% of the current file is mechanism description that belongs in a reference. gate's whole
spec is 12 KB and most of it becomes scripts.

**"The stall brake will stop legitimate hard work."** It stops and *asks*; it does not kill. Cost of
a false stop: one prompt. Cost of no stop: trtools2 — 69 iterations, 308 tickets, 0/13, archived.
