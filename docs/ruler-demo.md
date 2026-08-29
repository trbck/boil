# Ruler end-to-end demo

This proves the ruler works on a scratch project with real captured output: a
data check goes GAP, `boil-doctor.py --final` refuses to declare done, the
guard blocks an edit to the sensor's protected path, a real data change flips
the check to MET with a stamped evidence line, and `--final` then reports OK.
All commands below were run against the `ruler` branch's
`scripts/boil-assert-db.py`, `boil-check.py`, `boil-guard.py`, and
`boil-doctor.py`, on a fresh scratch project — output is verbatim, not
paraphrased.

## Setup

```
$ cd /tmp/rulerdemo-scratch && rm -rf rulerdemo && mkdir rulerdemo && cd rulerdemo && git init -q && mkdir -p .boil tests
$ python3 - <<'EOF'
import sqlite3
con = sqlite3.connect("runs.sqlite"); con.execute("create table runs(sharpe real)"); con.execute("insert into runs values (0.62)"); con.commit()
EOF
```

`.boil/goal.md`:

```
# Goal

**One-line:** the latest run clears the Sharpe floor.

## Success checklist
- [ ] latest run has sharpe >= 0.8 {#sharpe_floor}

## Requirements understanding

| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---:|---|
| floor | a data check | verify exit 0 | 99 | none |

## How the user will see this works
`boil-check.py verify --root .`
```

`.boil/milestones.json` (S = the `ruler` worktree's `scripts/` dir):

```
{"determinism_runs": 1, "milestones": [{"id": "sharpe_floor", "title": "floor", "kind": "metric",
  "check": "python3 $S/boil-assert-db.py --db runs.sqlite --query 'select sharpe from runs order by rowid desc limit 1' --assert 'sharpe >= 0.8'",
  "protect": ["tests"]}]}
```

## Compile

```
$ python3 $S/boil-check.py compile --root . --spec .boil/milestones.json
FROZEN sharpe_floor hash=5c07e7e78ab2f8d3 baseline=falsifiable
1 frozen, 0 rejected -> .../rulerdemo-task7/.boil/checks/frozen.json
compile exit 0
```

## Step 1: verify before the fix — data check goes GAP

```
$ python3 $S/boil-check.py verify --root .
FAIL   sharpe_floor  FAIL sharpe=0.62 | assert sharpe >= 0.8
GAP: 0/1 must-have milestones green
verify exit 1
```

## Step 2: doctor --final refuses to declare done

```
$ python3 $S/boil-doctor.py --final --root . ; echo "doctor exit $?"
FINAL REFUSED — this goal may not be declared done:
  - 1 of 1 checkboxes are still open
  - milestone sharpe_floor is FAIL now (FAIL sharpe=0.62 | assert sharpe >= 0.8) — re-measured, not remembered

Re-run with --write to produce HANDOFF.md instead.
doctor exit 3
```

## Step 3: guard blocks a sensor edit

The check's `protect` list includes `tests`. Simulating a Write hook call
against a file under `tests/`:

```
$ echo '{"tool_name":"Write","tool_input":{"file_path":".../tests/t.py","content":"x"}}' | python3 $S/boil-guard.py --root .
boil guard: refusing to edit tests — it is part of the ruler this goal is measured by. A check may not be made to pass by editing the sensor. Make the real code change instead.
exit=2
```

The worker cannot make the check pass by editing the protected test path —
only a real code/data change is accepted.

## Step 4: real data change → MET, evidence stamped

```
$ sqlite3 runs.sqlite "insert into runs values (0.91)"
$ python3 $S/boil-check.py verify --root . --write
PASS   sharpe_floor
MET: 1/1 must-have milestones green | 1 box(es) stamped
verify --write exit 0

$ grep sharpe_floor .boil/goal.md
- [x] latest run has sharpe >= 0.8 — EVIDENCE: `python3 .../boil-assert-db.py --db runs.sqlite --query 'select sharpe from runs order by rowid desc limit 1' --assert 'sharpe >= 0.8'` -> exit 0 | 2026-08-29 | auto {#sharpe_floor}
```

## Step 5: doctor --final now reports OK

```
$ python3 $S/boil-doctor.py --final --root . ; echo "doctor exit $?"
FINAL OK: every checkbox is green and carries an EVIDENCE line.
The evidence lines are paste-ready for the gate ladder.
doctor exit 0
```

## Commit guard and branch log

```
$ python3 scripts/boil-commit-guard.py
OK: no AI attribution in commits (-50)
guard exit 0

$ git log --oneline verifier-first..ruler
c583475 ruler: document {#id} binding, verify, the data sensor and the guard
16658b4 ruler: lint the {#id} binding between goal boxes and frozen milestones
a6196f2 ruler: doctor refuses instead of crashing on an unparseable human-evidence date or malformed verify output (round 1 review findings)
7a7b905 ruler: doctor --final re-verifies frozen checks and expires stale human evidence; NOW shows the measurement
08280da ruler: close symlink and path-qualified-binary bypasses in boil-guard (round 2 review findings)
d13bef5 ruler: fix boil-guard write-op detection (round 1 review findings)
93af206 ruler: add boil-guard, the PreToolUse hook that keeps the worker off the ruler
f4f425c ruler: boil-check verify re-measures every frozen check and stamps evidence on {#id}-tagged boxes
29e2a98 ruler: add boil-assert-db, the data sensor (query + whitelisted assertion, exit code is the verdict)
```
