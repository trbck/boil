#!/usr/bin/env bash
# The roborev Stop hook, owned by boil.
#
# WHY IT LIVES HERE. It used to sit alone in ~/.claude/hooks/roborev-milestone.sh while
# boil-review.py, three directories away, claimed to own review cadence. Two owners, one
# decision: the hook could not see boil's reviewer state and boil could not see the hook's
# cadence. When roborev's `review_agent` drifted to `codex` while `review_model` still held
# the Ollama tag `glm-5.3:cloud`, nothing on either side noticed that the pair was
# impossible, and every review 400'd for a day. One owner now: this file ships with the
# skill, and ~/.claude/settings.json points at it.
#
# WHAT IT DOES, in order:
#   1. Resolve the reviewer. `boil-reviewer.py apply` writes today's (agent, model) pair
#      into roborev's global config as a pair. codex is the primary; when codex is rate
#      limited the pair becomes claude-code + glm-5.3:cloud (Ollama Cloud) and a cooldown
#      starts; when the cooldown lapses a real smoke-test probe decides whether codex is
#      back. Cheap: the probe is throttled and only runs when a cooldown has expired.
#   2. Fire roborev only on a declared milestone. No automatic triggering: the stock hooks
#      fired on every Bash call and every 5th Stop, each fix commit spawned a fresh review,
#      and one three-day session produced 11 of 43 commits that way, with nobody deciding
#      it should.
#
#   Declare a milestone:  touch ~/.claude/.roborev-milestone
#   Cancel one:           rm -f ~/.claude/.roborev-milestone
#   Review right now:     roborev fix --list        (never needed the hook)
#   Who is reviewing:     boil-reviewer.py status
#
# Restore the pre-milestone behaviour from ~/.claude/settings.json.pre-milestone.
set -uo pipefail

MARKER="${ROBOREV_MILESTONE_MARKER:-$HOME/.claude/.roborev-milestone}"
# Same resolution order as the Python side: an explicit override, then PATH, then the
# usual install location. Hard-coding one path meant a roborev installed anywhere else
# looked exactly like no roborev at all.
ROBOREV="${BOIL_ROBOREV:-$(command -v roborev 2>/dev/null || echo "$HOME/.local/bin/roborev")}"
REVIEWER="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/boil-reviewer.py"

# The payload must be consumed either way: a hook that leaves stdin unread can block the
# writer.
payload="$(cat 2>/dev/null || true)"

if [ ! -e "$MARKER" ]; then
  exit 0   # no milestone declared: silence, and no subprocess cost
fi

# Nothing to run: keep the marker so the milestone is still reviewed once roborev is back.
# Only an attempt consumes it.
if [ ! -x "$ROBOREV" ]; then
  exit 0
fi

# Consume the marker before the attempt. If roborev is slow or the review fails, the next
# Stop must not fire a second review for the same milestone.
rm -f "$MARKER"

# The project this Stop belongs to. $PWD is the last resort: the marker is machine-wide,
# so on a box with several boil projects it is the harness's own project directory that
# says which one declared the milestone.
ROOT="${CLAUDE_PROJECT_DIR:-${BOIL_ROOT:-$PWD}}"

# Keep the reviewer honest before spending a review on it. `apply` is all-or-nothing, so a
# failure leaves roborev's config exactly as it was and the review can still go ahead —
# but it is said out loud rather than swallowed.
if [ -f "$REVIEWER" ]; then
  if ! apply_err="$(python3 "$REVIEWER" apply --root "$ROOT" 2>&1 >/dev/null)"; then
    printf 'roborev milestone hook: reviewer apply failed, roborev config unchanged\n%s\n' \
      "${apply_err:0:300}" >&2
  fi
fi

# Thresholds forced to 1 so this single invocation reviews whatever is open, rather than
# waiting for the counters the automatic mode uses.
# A wedged roborev must not hold the harness's Stop hook open forever.
err="$(printf '%s' "$payload" | timeout "${BOIL_ROBOREV_TIMEOUT:-120}" "$ROBOREV" agent-hook run \
  --agent claude \
  --source=roborev-milestone \
  --turn-threshold 1 \
  --commit-threshold 1 \
  --failed-review-threshold 1 2>&1 >/dev/null)"
rc=$?

if [ "$rc" -ne 0 ]; then
  # A failed attempt must not look like a completed one. The marker goes back so the
  # milestone is still reviewed on the next Stop, and the reason is said out loud —
  # a silently swallowed milestone is exactly the cadence loss this hook exists to
  # prevent.
  touch "$MARKER"
  printf 'roborev milestone hook: %s exited %s; milestone marker restored\n%s\n' \
    "$ROBOREV" "$rc" "${err:0:500}" >&2
fi
exit 0
