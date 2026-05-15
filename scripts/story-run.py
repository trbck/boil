#!/usr/bin/env python3
"""
story-run.py — minimal v0 runner for boil stories.

Reads a story file at .boil/stories/STORY-NNN.md, parses frontmatter +
YAML code-blocks per `references/stories.md`, replays the assertions
across four lanes (functional / quant / UX-mechanical / UX-rubric),
updates the story's frontmatter + the MATRIX.md index.

v0 scope:
  - Functional/HTTP   : implemented (uses urllib; no extra deps).
  - Functional/SQL    : stub — returns exit 2 (infra error) with a clear
                        "implement adapters/functional.sh" message.
  - Functional/redis  : stub — same.
  - Quant/gate        : invokes .boil/stories/adapters/quant.sh if present;
                        otherwise stub (exit 2).
  - UX/dom            : stub — requires Playwright; emit clear message.
  - UX/css_property   : stub — same.
  - UX/screenshot_diff: stub — same.
  - UX/rubric         : stub — judge dispatch isn't wired from a script,
                        it requires the orchestrating LLM. Emit a
                        machine-readable "needs orchestrator" line so
                        boil's Pass 0 can pick up the rubric work.

Exit codes:
  0  all lanes pass
  1  one or more assertions failed
  2  infra error (parse failure, missing adapter, network unreachable)

Usage:
  story-run.py STORY-001
  story-run.py --all                 # every story in .boil/stories/
  story-run.py STORY-001 --json      # machine-readable output only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "story-run: ERROR — pyyaml not installed. "
        "pip install pyyaml (or apt install python3-yaml).",
        file=sys.stderr,
    )
    sys.exit(2)


# --------------------------------------------------------------------------
# Parse — story frontmatter + assertion code-blocks
# --------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)


@dataclass
class Story:
    path: Path
    meta: dict[str, Any]
    body: str
    functional: list[dict[str, Any]] = field(default_factory=list)
    quant: list[dict[str, Any]] = field(default_factory=list)
    ux: list[dict[str, Any]] = field(default_factory=list)


def load_story(path: Path) -> Story:
    text = path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML frontmatter")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    blocks = _YAML_BLOCK_RE.findall(body)
    story = Story(path=path, meta=meta, body=body)
    for block in blocks:
        parsed = yaml.safe_load(block)
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            kind = item.get("kind", "")
            if kind in {"http", "redis_xadd", "sql"}:
                story.functional.append(item)
            elif kind in {"gate", "latency"}:
                story.quant.append(item)
            elif kind in {"dom", "css_property", "screenshot_diff", "rubric"}:
                story.ux.append(item)
    return story


# --------------------------------------------------------------------------
# Lane runners
# --------------------------------------------------------------------------


@dataclass
class AssertResult:
    name: str
    kind: str
    status: str           # "pass" | "fail" | "skip" | "error"
    details: str = ""


def _expand_env(s: str) -> str:
    """Substitute ${VAR} from the environment. Missing var = empty string."""
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), s)


def run_http(spec: dict[str, Any]) -> AssertResult:
    name = spec.get("name", "http")
    url = _expand_env(spec.get("url", ""))
    if not url:
        return AssertResult(name, "http", "error", "missing url")
    expect = spec.get("expect", {})
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as e:
        return AssertResult(name, "http", "error", f"{type(e).__name__}: {e}")

    expected_status = expect.get("status", 200)
    if status != expected_status:
        return AssertResult(
            name, "http", "fail",
            f"status={status} expected={expected_status}",
        )
    needles = expect.get("body_contains", [])
    if isinstance(needles, str):
        needles = [needles]
    for needle in needles:
        if needle not in body:
            return AssertResult(
                name, "http", "fail",
                f"body missing {needle!r}",
            )
    return AssertResult(name, "http", "pass",
                        f"{status} ok, {len(needles)} needles matched")


def run_adapter_stub(spec: dict[str, Any], lane: str, repo_root: Path) -> AssertResult:
    """Try project's adapter; if missing, return a clear infra-error."""
    name = spec.get("name", lane)
    kind = spec.get("kind", lane)
    adapter = repo_root / ".boil" / "stories" / "adapters" / f"{lane}.sh"
    if not adapter.exists():
        return AssertResult(
            name, kind, "error",
            f"{lane} adapter required for kind={kind} but "
            f".boil/stories/adapters/{lane}.sh is missing — "
            f"see references/stories.md § Adapters",
        )
    try:
        proc = subprocess.run(
            ["bash", str(adapter)],
            input=json.dumps(spec).encode(),
            capture_output=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return AssertResult(name, kind, "error", "adapter timeout >120s")
    if proc.returncode == 2:
        return AssertResult(name, kind, "error",
                            f"adapter infra-error: {proc.stderr.decode().strip()[:200]}")
    try:
        result = json.loads(proc.stdout.decode())
    except json.JSONDecodeError:
        return AssertResult(name, kind, "error",
                            "adapter stdout not JSON")
    return AssertResult(
        name, kind,
        result.get("status", "error"),
        result.get("details", ""),
    )


def run_rubric_marker(spec: dict[str, Any]) -> AssertResult:
    """v0: rubric judge dispatch needs the orchestrating LLM, not a CLI.
    Emit a structured marker that boil's Pass 0 can pick up."""
    name = spec.get("name", "rubric")
    rubric_id = spec.get("rubric_id", "")
    return AssertResult(
        name, "rubric", "skip",
        f"rubric:{rubric_id} requires orchestrator dispatch — "
        f"see references/rubrics.md § How the judge is dispatched. "
        f"This v0 runner cannot self-evaluate; boil Pass 0 will route "
        f"the judge during the iteration.",
    )


def run_story(story: Story, repo_root: Path) -> tuple[list[AssertResult], str]:
    """Run all four lanes. Return (results, overall_status)."""
    results: list[AssertResult] = []

    # Functional
    for spec in story.functional:
        kind = spec.get("kind", "")
        if kind == "http":
            results.append(run_http(spec))
        elif kind in {"sql", "redis_xadd"}:
            results.append(run_adapter_stub(spec, "functional", repo_root))
        else:
            results.append(AssertResult(spec.get("name", kind), kind, "error",
                                        f"unknown functional kind={kind}"))

    # Quant
    for spec in story.quant:
        results.append(run_adapter_stub(spec, "quant", repo_root))

    # UX
    for spec in story.ux:
        kind = spec.get("kind", "")
        if kind == "rubric":
            results.append(run_rubric_marker(spec))
        else:
            results.append(run_adapter_stub(spec, "ux", repo_root))

    has_fail = any(r.status == "fail" for r in results)
    has_err = any(r.status == "error" for r in results)
    if has_fail:
        overall = "fail"
    elif has_err:
        overall = "error"
    else:
        overall = "pass"   # 'skip' (rubric-needs-orchestrator) is non-blocking from CLI
    return results, overall


# --------------------------------------------------------------------------
# Frontmatter writeback + MATRIX
# --------------------------------------------------------------------------


def update_story_frontmatter(story: Story, results: list[AssertResult],
                             overall: str, sha: str) -> None:
    meta = dict(story.meta)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if overall == "pass":
        meta["last_green_sha"] = sha
        meta["last_green_at"] = now
        meta["last_red_reason"] = ""
        meta["last_red_lane"] = ""
    else:
        first_bad = next((r for r in results
                          if r.status in {"fail", "error"}), None)
        if first_bad is not None:
            lane = {
                "http": "functional", "sql": "functional",
                "redis_xadd": "functional",
                "gate": "quant", "latency": "quant",
                "dom": "ux", "css_property": "ux",
                "screenshot_diff": "ux", "rubric": "ux",
            }.get(first_bad.kind, "?")
            meta["last_red_reason"] = (
                f"{first_bad.kind}/{first_bad.name}: {first_bad.details}"
            )
            meta["last_red_lane"] = lane
    new_fm = yaml.safe_dump(meta, sort_keys=False).rstrip()
    story.path.write_text(f"---\n{new_fm}\n---\n{story.body}")


def regenerate_matrix(stories_dir: Path) -> None:
    rows = []
    for p in sorted(stories_dir.glob("STORY-*.md")):
        try:
            s = load_story(p)
        except Exception as e:
            rows.append((p.stem, f"(parse error: {e})", "", "", "error", str(e)))
            continue
        m = s.meta
        title = m.get("title", "")
        sha = m.get("last_green_sha", "") or "(never)"
        when = m.get("last_green_at", "") or "(never)"
        red = m.get("last_red_reason", "") or "—"
        if m.get("last_green_at"):
            try:
                green_dt = dt.datetime.fromisoformat(
                    m["last_green_at"].replace("Z", "+00:00")
                )
                age_days = (dt.datetime.now(dt.timezone.utc) - green_dt).days
                if age_days > 14:
                    status = f"⚠ rotted ({age_days}d)"
                elif red == "—":
                    status = "✓ green"
                else:
                    status = "✗ red"
            except Exception:
                status = "?"
        else:
            status = "✗ red" if red != "—" else "(never run)"
        rows.append((p.stem, title, sha, when, status, red))

    out = [
        "# Stories matrix — auto-generated by scripts/story-run.py",
        "",
        f"Last regenerated: "
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "| ID | Title | Last green SHA | Last green at | Status | Last red reason |",
        "|----|-------|----------------|---------------|--------|------------------|",
    ]
    for sid, title, sha, when, status, red in rows:
        out.append(f"| {sid} | {title} | {sha} | {when} | {status} | {red} |")
    (stories_dir / "MATRIX.md").write_text("\n".join(out) + "\n")


def current_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "(not-a-git-repo)"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("story", nargs="?", help="STORY-NNN or path; --all for every story")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output only")
    ap.add_argument("--stories-dir", default=".boil/stories",
                    help="default .boil/stories")
    args = ap.parse_args(argv)

    repo_root = Path.cwd()
    stories_dir = repo_root / args.stories_dir
    if not stories_dir.exists():
        print(f"story-run: {stories_dir} does not exist", file=sys.stderr)
        return 2

    if args.all:
        paths = sorted(stories_dir.glob("STORY-*.md"))
    elif args.story:
        if args.story.startswith("STORY-"):
            paths = [stories_dir / f"{args.story}.md"]
        else:
            paths = [Path(args.story)]
    else:
        ap.print_help()
        return 2

    sha = current_sha(repo_root)
    all_results: dict[str, list[AssertResult]] = {}
    worst_exit = 0
    for p in paths:
        if not p.exists():
            print(f"story-run: {p} missing", file=sys.stderr)
            worst_exit = max(worst_exit, 2)
            continue
        try:
            story = load_story(p)
        except Exception as e:
            print(f"story-run: {p} parse error: {e}", file=sys.stderr)
            worst_exit = max(worst_exit, 2)
            continue
        results, overall = run_story(story, repo_root)
        all_results[story.meta.get("id", p.stem)] = results
        update_story_frontmatter(story, results, overall, sha)
        if overall == "fail":
            worst_exit = max(worst_exit, 1)
        elif overall == "error":
            worst_exit = max(worst_exit, 2)

    regenerate_matrix(stories_dir)

    if args.json:
        print(json.dumps({
            sid: [r.__dict__ for r in rs] for sid, rs in all_results.items()
        }, indent=2))
    else:
        for sid, rs in all_results.items():
            print(f"\n=== {sid} ===")
            for r in rs:
                tag = {"pass": "✓", "fail": "✗", "skip": "○",
                       "error": "‼"}.get(r.status, "?")
                print(f"  {tag} [{r.kind}] {r.name}: {r.details}")
        print(f"\nstories: {len(all_results)} run, exit={worst_exit}")
    return worst_exit


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
