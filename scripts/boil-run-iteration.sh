#!/usr/bin/env bash
# Run boil's mechanical gates for one iteration.

set -euo pipefail

ITERATION="${1:-}"
PROJECT_ROOT="${2:-$PWD}"
if [[ -z "$ITERATION" ]]; then
  echo "usage: boil-run-iteration.sh iter-NNN [project-root] [--test-cmd CMD ...]" >&2
  exit 2
fi
shift || true
if [[ $# -gt 0 && "$1" != --* ]]; then
  shift || true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_CMDS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --test-cmd)
      TEST_CMDS+=("$2")
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

python3 "$SCRIPT_DIR/boil-doctor.py" --root "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/ticket-lint.py" --root "$PROJECT_ROOT"

# Verifier-first project: the controller owns the iteration (prepare / score). This script
# is then the periodic re-measure — every frozen check re-run, the brakes, NOW.md — and
# nothing from the legacy ticket loop below runs.
if [[ -f "$PROJECT_ROOT/.boil/checks/frozen.json" ]]; then
  python3 "$SCRIPT_DIR/boil-check.py" verify --root "$PROJECT_ROOT" || true
  BRAKES_EXIT=0
  python3 "$SCRIPT_DIR/boil-brakes.py" check --root "$PROJECT_ROOT" || BRAKES_EXIT=$?
  python3 "$SCRIPT_DIR/boil-now.py" --root "$PROJECT_ROOT" --write >/dev/null || true
  python3 "$SCRIPT_DIR/boil-helm-log.py" emit --root "$PROJECT_ROOT" \
    --kind boil.iteration.gates --status ok --detail "$ITERATION" || true
  exit "$BRAKES_EXIT"
fi

python3 "$SCRIPT_DIR/boil-loop.py" audit --root "$PROJECT_ROOT"

if [[ -d "$PROJECT_ROOT/.boil/stories" ]]; then
  python3 "$SCRIPT_DIR/story-run.py" --all --stories-dir "$PROJECT_ROOT/.boil/stories" --iteration "$ITERATION"
fi

for cmd in "${TEST_CMDS[@]}"; do
  (cd "$PROJECT_ROOT" && bash -lc "$cmd")
done

if [[ -d "$PROJECT_ROOT/.boil/iterations/$ITERATION" ]]; then
  bash "$SCRIPT_DIR/boil-verify-iteration.sh" "$ITERATION" "$PROJECT_ROOT"
fi

# Record this iteration's progress, then evaluate the convergence brakes. The tick is
# what makes the stall brake able to fire at all, so it runs even when a brake then
# stops the loop. `check` exits 2 (restrict) or 3 (stop); neither is a gate failure —
# it is the loop being told to change what it does next, which the caller reports.
python3 "$SCRIPT_DIR/boil-brakes.py" tick --root "$PROJECT_ROOT" --iteration "$ITERATION"
BRAKES_EXIT=0
python3 "$SCRIPT_DIR/boil-brakes.py" check --root "$PROJECT_ROOT" || BRAKES_EXIT=$?
python3 "$SCRIPT_DIR/boil-now.py" --root "$PROJECT_ROOT" --write >/dev/null || true

# Refresh the operator's status view (and helm's, when helm is installed). Never fatal:
# a status-logging failure must not fail an iteration that otherwise passed its gates.
python3 "$SCRIPT_DIR/boil-helm-log.py" emit --root "$PROJECT_ROOT" \
  --kind boil.iteration.gates --status ok --detail "$ITERATION" || true

case "$BRAKES_EXIT" in
  2) echo "boil-run-iteration: gates complete for $ITERATION — BRAKES: RESTRICT (T1 work only, file no new tickets)" ;;
  3) echo "boil-run-iteration: gates complete for $ITERATION — BRAKES: STOP (put the decision to the user)" ;;
  *) echo "boil-run-iteration: gates complete for $ITERATION" ;;
esac
