#!/usr/bin/env bash
# story-run.sh — thin wrapper around story-run.py so callers can use the
# same invocation shape as references/stories.md documents.
#
# Usage:
#   bash scripts/story-run.sh STORY-001 --iteration iter-003
#   bash scripts/story-run.sh --all --iteration iter-003
#
# When boil is installed outside the project and the project's PATH doesn't
# include that scripts dir, projects can either:
#   1. symlink it:  ln -s ~/.codex/skills/boil/scripts/story-run.sh \
#                          .boil/scripts/story-run.sh
#   2. invoke it directly:
#        bash ~/.codex/skills/boil/scripts/story-run.sh STORY-001 --iteration iter-003

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/story-run.py" "$@"
