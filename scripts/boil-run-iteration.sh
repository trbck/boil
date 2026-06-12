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

if [[ -d "$PROJECT_ROOT/.boil/stories" ]]; then
  python3 "$SCRIPT_DIR/story-run.py" --all --stories-dir "$PROJECT_ROOT/.boil/stories" --iteration "$ITERATION"
fi

for cmd in "${TEST_CMDS[@]}"; do
  (cd "$PROJECT_ROOT" && bash -lc "$cmd")
done

if [[ -d "$PROJECT_ROOT/.boil/iterations/$ITERATION" ]]; then
  bash "$SCRIPT_DIR/boil-verify-iteration.sh" "$ITERATION" "$PROJECT_ROOT"
fi

echo "boil-run-iteration: gates complete for $ITERATION"
