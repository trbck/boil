#!/usr/bin/env bash
# Verify a boil iteration directory has proof, demo, and non-vague next steps.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: boil-verify-iteration.sh iter-NNN [project-root]" >&2
  exit 2
fi

ITERATION="$1"
PROJECT_ROOT="${2:-$PWD}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ITER_DIR="$PROJECT_ROOT/.boil/iterations/$ITERATION"

if [[ ! -d "$ITER_DIR" ]]; then
  echo "boil-verify: missing iteration dir: $ITER_DIR" >&2
  exit 2
fi

SUMMARY="$ITER_DIR/summary.md"
DEMO="$ITER_DIR/demo.md"
VERIFY_LOG="$ITER_DIR/verify.log"
RETEST_LOG="$ITER_DIR/retest.log"

missing=0
for path in "$SUMMARY" "$DEMO"; do
  if [[ ! -f "$path" ]]; then
    echo "boil-verify: missing required file: $path" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  exit 2
fi

python3 "$SCRIPT_DIR/vibe-check.py" "$SUMMARY"

if [[ ! -s "$VERIFY_LOG" ]]; then
  echo "boil-verify: warning: verify.log is missing or empty" >&2
fi
if [[ ! -s "$RETEST_LOG" ]]; then
  echo "boil-verify: warning: retest.log is missing or empty" >&2
fi

echo "boil-verify: ok for $ITERATION"
