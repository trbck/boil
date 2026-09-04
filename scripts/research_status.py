#!/usr/bin/env python3
"""One line of progress for a hyperresearch run.

    python3 scripts/research_status.py <vault_tag> [--research-root ~/.advisor-research] [--json]

Prefers the installed `hyperresearch` CLI (`hyperresearch run status <tag> --json`,
run with cwd = the research root) since it is the canonical source of truth and
already computes resume/escalations. Falls back to reading
`<research-root>/research/runs/<tag>/run.json` directly -- and computing the same
`resume` block itself -- only if the CLI binary is missing or exits non-zero.

The schema (manifest_version, vault_tag, profile, profile_steps, status,
started_at, updated_at, budget_usd, blocked_on, steps, chapters, spend, resume,
possibly_stalled, escalations) is documented, not guessed: it was captured from
the real CLI on this machine and both a `run status --json` sample and the raw
`run.json` it reads live in tests/fixtures/.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def manifest_path(research_root, tag):
    return os.path.join(os.path.expanduser(research_root), "research", "runs", tag, "run.json")


def cli_status(tag, research_root, cli_path="hyperresearch"):
    """Try `<cli_path> run status <tag> --json`. Returns the `data` dict, or None."""
    try:
        proc = subprocess.run(
            [cli_path, "run", "status", tag, "--json"],
            cwd=os.path.expanduser(research_root),
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        parsed = json.loads(proc.stdout)
    except ValueError:
        return None
    if not parsed.get("ok"):
        return None
    return parsed.get("data")


def load_status(tag, research_root, cli_path="hyperresearch"):
    """Returns (data, error). Exactly one is None."""
    data = cli_status(tag, research_root, cli_path=cli_path)
    if data is not None:
        return data, None
    path = manifest_path(research_root, tag)
    if not os.path.exists(path):
        return None, "no run manifest at %s" % path
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, "could not read run manifest at %s: %s" % (path, exc)
    return data, None


def normalize(data):
    """Ensure `resume` is present, computing it from profile_steps/steps if not.

    The raw run.json the CLI reads does not carry `resume` or `escalations` --
    those are the CLI's own computation. Reproduced here so the file-fallback
    path renders the same status line the CLI would have.
    """
    data = dict(data)
    if not data.get("resume"):
        profile_steps = data.get("profile_steps") or []
        steps = data.get("steps") or {}
        done = [s for s in profile_steps if (steps.get(s) or {}).get("status") == "done"]
        remaining = [s for s in profile_steps if s not in done]
        data["resume"] = {
            "next_step": remaining[0] if remaining else None,
            "done_steps": done,
            "remaining_steps": remaining,
            "chapters_pending": [],
        }
    data.setdefault("spend", {})
    data.setdefault("escalations", {})
    return data


def format_elapsed(started_at, updated_at):
    if not started_at or not updated_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(updated_at)
        seconds = (end - start).total_seconds()
    except (TypeError, ValueError):
        return None
    seconds = max(0, seconds)
    if seconds < 60:
        return "%ds" % int(round(seconds))
    return "%d min" % int(round(seconds / 60))


def format_status_line(data, tag):
    data = normalize(data)
    resume = data["resume"]
    total = len(data.get("profile_steps") or [])
    done_n = len(resume.get("done_steps") or [])
    next_step = resume.get("next_step")
    step_part = ("step %s (%d/%d done)" % (next_step, done_n, total) if next_step
                 else "(%d/%d done)" % (done_n, total))

    spend = data.get("spend") or {}
    sources = spend.get("sources_fetched", 0)
    cost = spend.get("estimated_usd") or 0.0

    parts = [
        "run %s" % (data.get("vault_tag") or tag),
        data.get("profile") or "?",
        step_part,
        data.get("status") or "unknown",
        "%s sources" % sources,
        "$%.2f" % cost,
    ]
    elapsed = format_elapsed(data.get("started_at"), data.get("updated_at"))
    if elapsed:
        parts.append("%s elapsed" % elapsed)

    line = " · ".join(parts)
    if data.get("possibly_stalled"):
        line += " · STALLED"
    if data.get("blocked_on"):
        line += " · blocked: %s" % data["blocked_on"]
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag", help="vault tag of the hyperresearch run")
    ap.add_argument("--research-root", default="~/.advisor-research",
                    help="root that holds research/runs/<tag>/ (default: ~/.advisor-research)")
    ap.add_argument("--json", action="store_true", help="print the normalized manifest as JSON")
    args = ap.parse_args(argv)

    data, err = load_status(args.tag, args.research_root)
    if err:
        print(err)
        return 1

    data = normalize(data)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_status_line(data, args.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
