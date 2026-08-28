# Minimal boil loop fixture

The minimum state shape for a boil loop, across all three scopes — outer loop
(`charter.md`, `ladder.md`, `log.md`), run loop (`goal.md`, `tickets/`,
`proof-map.md`), and the brakes (`budget.json`, `progress.jsonl`, `icebox.md`).

It uses `boil-state/` instead of `.boil/` because the skill repo ignores
`.boil/` workspaces globally. To try it manually:

```bash
tmp="$(mktemp -d)"
cp -R examples/minimal-loop/project/. "$tmp/"
cp -R examples/minimal-loop/boil-state "$tmp/.boil"

python3 scripts/boil-now.py     --root "$tmp"            # the session-start read
python3 scripts/boil-doctor.py  --root "$tmp"
python3 scripts/ticket-lint.py  --root "$tmp"            # schema + tier + goal size
python3 scripts/boil-brakes.py  check --root "$tmp"      # stall / WIP / budget
python3 scripts/boil-doctor.py  --final --root "$tmp"    # termination gate
bash    scripts/boil-run-iteration.sh iter-001 "$tmp"    # all gates at once
```

Things the fixture deliberately demonstrates:

- **`goal.md` is 2 checkboxes and under 1 KB**, each carrying an `EVIDENCE:` line —
  which is what lets `--final` pass. Try deleting one evidence line and re-running
  `--final` to see it refuse and offer `HANDOFF.md` instead.
- **The ticket declares `tier: T1`**, so it needs no frozen answer key. Change it to
  `tier: T3` and `ticket-lint.py` will demand external ground truth.
- **The ladder has an open L1 criterion**, so `boil-now.py` names it as the next
  target rather than reporting the project finished.
