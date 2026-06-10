# Minimal boil loop fixture

This fixture shows the minimum state shape for an agentic boil loop.

It uses `boil-state/` instead of `.boil/` because the skill repo ignores
`.boil/` workspaces globally. To try it manually:

```bash
tmp="$(mktemp -d)"
cp -R examples/minimal-loop/project/. "$tmp/"
cp -R examples/minimal-loop/boil-state "$tmp/.boil"
python3 scripts/boil-doctor.py --root "$tmp"
python3 scripts/ticket-lint.py --root "$tmp"
bash scripts/boil-verify-iteration.sh iter-001 "$tmp"
```
