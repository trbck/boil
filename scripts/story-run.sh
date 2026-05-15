#!/usr/bin/env bash
# story-run.sh — thin wrapper around story-run.py so callers can use the
# same invocation shape as references/stories.md documents.
#
# Usage:
#   bash scripts/story-run.sh STORY-001
#   bash scripts/story-run.sh --all
#
# When boil is installed at ~/.claude/skills/boil and the project's PATH
# doesn't include that scripts dir, projects can either:
#   1. symlink it:  ln -s ~/.claude/skills/boil/scripts/story-run.sh \
#                          .boil/scripts/story-run.sh
#   2. invoke it directly:
#        bash ~/.claude/skills/boil/scripts/story-run.sh STORY-001

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/story-run.py" "$@"
