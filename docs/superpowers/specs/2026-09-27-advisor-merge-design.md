# Design: merge `advisor` into `boil`; the advisor answers cited decisions

Date: 2026-09-27 · Branch: `advisor-merge` (off `main`) · Status: awaiting user review

## Intent

The user asked for three things:

1. **Merge.** advisor (the book-rule corpus and its scripts) lives inside boil, with the same API.
2. **Decide.** When boil would ask the user something unclear, the advisor answers from its rules
   and the project goal.
3. **Knowledge in helm.** The rule library shows up in the helm dashboard. A human adds knowledge
   there and retires rules there.

Success means:

- `boil advise lookup …` behaves exactly like `lookup.py …` does today.
- A `kind: decision` blocker that a cited, non-conflicting, non-retired rule covers gets decided
  and logged instead of reaching the user.
- Every other blocker reaches the user as it does today.
- The user can veto any logged decision, and retire any rule, from helm.

Stated limit: the corpus covers two domains, **decision-making** (203 rules) and **trading**
(595). Most software questions will find no rule that fits and will still escalate. That is the
intended behaviour, not a gap to paper over.

## Decisions taken with the user (2026-09-26/27)

| # | Fork | Choice |
|---|------|--------|
| 1 | What "merge" means | Physical merge into the boil repo; the advisor repo goes read-only, as gate did |
| 2 | Advisor authority | Decide only when a rule is cited, otherwise ask; every decision is logged and vetoable |
| 3 | Helm knowledge scope | Browse all rules; add notes; retire any rule, with tombstones |
| 4 | Entry point outside a loop | `boil advise`, one skill, advisor's triggers move into boil; the advisor symlink is removed |
| 5 | How a decision is made | The script retrieves, the running agent judges, the script verifies (no second model call) |

## A. Merge layout

- **Source:** `origin/skill-review-fixes` of `git@github.com:trbck/advisor.git`. It holds 4 fixes
  that `main` lacks.
  - `~/src/advisor`, the live skill symlink target, is on `main`, 4 commits behind, and has
    uncommitted edits to `SKILL.md` and `generated/trading/ROUTER.md`.
  - Before the merge, those two diffs are shown to the user, who decides whether to keep them.
    Neither clone is modified or deleted.
- **Method:** a subtree merge (`git merge -s ours --no-commit --allow-unrelated-histories` plus
  `git read-tree --prefix=advisor/`). This keeps advisor's 19 commits of history.
- **Result:** `boil/advisor/{scripts,domains,generated,inbox,references,templates,tests,FORMAT.md,docs}`.
  - Relative paths inside `advisor/` do not change.
  - `ka_common.py` resolves its root from its own location (`ROOT = dirname(dirname(__file__))`), so the scripts run unchanged. Plan
    step A2 verifies this.
- **Dropped:**
  - `advisor/SKILL.md`: it is generated, and its content moves to `references/advisor.md` (see C).
  - `advisor/bin/advisor-sync`: it only maintained the symlink.
  - `advisor/README.md`: shrinks to a pointer section in boil's README.
- **Tests:** boil's test run collects `advisor/tests/`. `advisor/tests/rule-ids.baseline` remains
  the rule-ID contract.
- **Cutover (last step, after the user signs off):**
  - Remove the `~/.claude/skills/advisor` symlink.
  - Push a pointer README to the advisor repo and archive it on GitHub.

## B. Decide and record

### Which questions are advisable

| Escalation | Advisable? |
|---|---|
| human-action ticket with `kind: decision` (a product or design judgment) | yes |
| `ESCALATE-STALL`: two requirements contradict each other | yes |
| human-action ticket for a credential, access, hardware, or account | **no** |
| `ESCALATE-BUDGET`, `-INFRA`, `-LIMIT`, `-VISIBILITY`, `ABORT-TAMPER`, CAP, REVIEW 70 | **no**: the brakes stay human-only |

`kind:` is a new optional field on human-action tickets. When it is absent, the ticket is not
advisable.

### Flow

```
boil advise decide --question "<q>" [--project .]
  → reads .boil/goal.md, plus the optional `advisor_domains: trading, decisions` line
  → lookup.py --search over those domains (all domains if the line is absent)
  → drops retired IDs; prints the question, the goal excerpt (≤40 lines), and the top 8 rules
     with their scores
agent writes ONE of:
  ANSWER: <choice> | RULES: <ID>[, <ID>…] | WHY: <one line tying rule to goal>
  ASK-HUMAN: <reason>
boil advise record --question "<q>" --verdict "<that line>" [--ticket T] [--project .]
  exit 0 → accepted, appended to .boil/decisions.md, helm event `boil.advised`
  exit 3 → rejected (reason printed); caller proceeds with normal escalation
```

`record` rejects the verdict when any of these hold:

- the verdict is `ASK-HUMAN`
- it cites no rule ID
- a cited ID does not exist (`check_citations.py`)
- a cited ID is retired
- two cited IDs appear together in their domain's `conflicts.md`
- the answer is empty or hedged (`depends`, `either`, `unclear`, as a whole word)
- this question and rule were vetoed before (see Veto)

### `.boil/decisions.md`

This file is append-only. Each entry looks like:

```
## D-0007 · 2026-09-27T14:02Z · ticket T-041
question: Stop tuning the entry filter or keep searching?
answer: Stop; commit to the current best after the 37% look phase.
rules: ATLB-01-R3, ATLB-01-R9
why: goal.md caps search at 20 variants; R3's threshold is already past.
veto: –
```

### Veto

- The user sets `veto: <reason>` in the file, or uses the helm button (see D).
- On its next run, `boil advise sweep` (called from `boil-now.py`) reopens each vetoed entry's
  ticket as a normal human-action ticket.
- It then adds a `(question-hash, rule-ids)` entry to `.boil/advisor-vetoes.json`, and `record`
  rejects that pair from then on.

### Hook points

- `boil-loop.py escalate` calls `decide`/`record` for `ESCALATE-STALL` before it writes
  `escalation.md`.
- `SKILL.md` gets one line: "Before filing a `kind: decision` human-action ticket, run
  `boil advise decide`; file the ticket only if `record` exits 3."

## C. Entry point and router

- **Description:** boil's frontmatter `description` gains one sentence with advisor's topic
  triggers. That sentence is generated by `advisor/scripts/build_index.py` from each domain's
  `domain.json`, the same way advisor's own description was.
  - A test asserts that the sentence in `SKILL.md` equals the generated one.
- **`build_index.py`** now renders `references/advisor.md` instead of `SKILL.md`. It uses the
  existing template, minus the frontmatter, and adds the description sentence.
- **Router:** a new row, `references/advisor.md` | "the user asks a knowledge or what-do-the-books-say
  question, or `boil advise` runs".
- **`scripts/boil-advise.py`:**

| Subcommand | Does |
|---|---|
| `lookup …` | forwards all arguments to `advisor/scripts/lookup.py` |
| `check …` | forwards to `check_citations.py` |
| `ingest …` / `build …` | forward to `ingest.py` / `build_index.py` |
| `decide`, `record`, `sweep` | section B |
| `retire ID --reason R` / `unretire ID` | section D |

  `lookup`, `check`, `ingest` and `build` need no `.boil/` directory.
- **Line budget:** `SKILL.md` is 358 lines on `main` and must end at ≤350 after these additions.
  Lines that repeat a reference are replaced with a pointer to it. The plan lists them.

## D. Helm

helm already has `advisor.py`, an advisor content-management tab (commit `aef4abd`), and
`knowledge.py`. This spec only adds to them.

A second session is actively editing helm (uncommitted cockpit/engine/runner changes as of
2026-09-27 00:45). The helm changes below are made in a helm worktree and merged only after that
work has landed.

- **Repoint:** the default `advisor.ROOT` changes from `~/src/advisor` to
  `~/workspace/boil/advisor`. `HELM_ADVISOR_ROOT` still overrides it.
- **Retire:** `advisor.retire(id, reason)` and `advisor.unretire(id)` shell out to
  `boil advise retire|unretire`.
  - Storage: `advisor/domains/<d>/retired.json`, as
    `{"<ID>": {"reason": "...", "date": "...", "by": "helm"}}`.
  - `lookup.py` hides retired IDs unless given `--include-retired`.
  - `check_citations.py` still resolves a retired ID but prints `RETIRED` and exits 1 under
    `--strict`.
  - UI: each rule row gets a Retire button with a required reason. A "Retired" filter shows
    retired rules, each with an Unretire button.
- **Decisions panel** in the project detail view:
  - `GET /api/project/<p>/decisions` returns the parsed `decisions.md`.
  - `POST /api/project/<p>/decision/<D-id>/veto {reason}` writes the `veto:` line. The next
    `sweep` does the rest.
  - Rule IDs render as chips that open the existing rule view.

## Error handling

- **advisor missing or broken.** `decide` exits 3 with the message `advisor unavailable`, and
  escalation proceeds. The advisor can never block an escalation.
- **Malformed `decisions.md`.** `sweep` and helm skip unparseable entries and report their line
  numbers; they never rewrite the file.
- **Retire races.** `retired.json` is written atomically (temp file plus `os.replace`).

## Testing

- **boil `tests/test_advise.py`** (fixture corpus, fixture goal):
  - a cited decision is accepted and logged
  - an unknown ID is rejected
  - a retired ID is rejected
  - a conflicting pair is rejected
  - a hedged answer is rejected
  - a vetoed pair is rejected
  - a budget or tamper escalation never reaches the advisor
  - with the advisor missing, the result is exit 3
  - `lookup` passthrough output is byte-identical to calling `lookup.py` directly
- **`advisor/tests/`** keeps passing in place.
- The description-sync test.
- A new test asserts `SKILL.md` is ≤350 lines. None exists today: the limit was a plan target, not enforced.
- **helm:**
  - `test_advisor.py` covers the retire/unretire round trip and path confinement
  - `test_decisions.py` covers the list, a veto, a bad ID (404), and a malformed entry being
    skipped

## Out of scope

- A second-model judge for decisions. This can be added later if the veto rate shows the agent's
  own judgment is not enough.
- New knowledge domains.
- Hard deletion of book content.
- Changes to helm's per-project `knowledge.py` distillation.
