#!/usr/bin/env python3
"""boil-review.py — a second LLM reads the code, when the script says so.

Why this is a controller step and not a hook. The stock roborev hooks fired on every
commit and every Nth Stop, and each fix commit spawned a fresh review, which spawned
fixes, which spawned commits — a ratchet with no natural end (11 of 43 commits in one
three-day session). Inside boil the *script* decides three things:

  WHEN   only after a milestone PASS, and only when a deterministic risk score says so:
         high blast-radius tier, a risk path touched, the final milestone, or enough
         unreviewed source lines accumulated. Small diffs accumulate; docs and .boil/
         state never count. A job the post-commit hook already enqueued for HEAD is
         adopted, never duplicated.
  HOW OFTEN  one review round per milestone, one fix round per review. The re-review
         is a verdict on the fix, never a new fix node. Findings that survive it are
         handed to the user — the loop does not grant itself another round.
  WHAT   findings at or above `fix_min_severity` become a DAG node `<M>-fix` whose
         script gate is the parent's frozen check (regression). Everything below is
         deferred with a logged disposition in .boil/log.md and the job is closed —
         never silently dismissed. The reviewer's verdict never replaces a green check.

Usage
  boil-review.py review --milestone M3 [--root .] [--dry-run]   after `boil-check.py run` exits 0
  boil-review.py close  --milestone M3-fix [--root .]           after the fix node passes

Exit codes
  0  nothing to do (skipped, clean, or deferred)   70 REVIEW — must-fix findings: a fix node
  71 PENDING — the review is still running          exists, or remain after the one fix round
  2  usage                                          (the user decides)

Config: the `review` object in milestones.json, carried into checks/frozen.json:
  {"enabled": true, "agent": "codex", "model": "", "every_lines": 150, "fix_min_severity": "high",
   "always_tiers": ["T3", "T4"], "risk_paths": ["**/auth/**", "**/migrations/**"],
   "cost_usd": 0.0, "timeout_s": 900, "reasoning": ""}
Ledger: .boil/checks/reviews.jsonl — one record per decision.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {
    "enabled": True, "agent": "", "model": "", "every_lines": 150, "fix_min_severity": "high",
    "always_tiers": ["T3", "T4"], "risk_paths": [], "cost_usd": 0.0, "timeout_s": 900,
    "reasoning": "",
}
SEVERITY = {"critical": 4, "high": 3, "medium": 2, "low": 1}
NOISE_SUFFIXES = (".md", ".rst", ".txt")
NOISE_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
               "Cargo.lock", "Gemfile.lock", "composer.lock"}
NOISE_DIRS = {".boil", "__pycache__", "node_modules", ".git"}
REVIEWED_EVENTS = ("CLEAN", "DEFERRED", "FIX-NODE", "CLOSED", "OPEN")
FINDING_FIELD = re.compile(r"\*\*(Severity|Location|Problem|Fix)\*\*\s*:\s*(.*)", re.IGNORECASE)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_dir(root: Path) -> Path:
    d = root / ".boil" / "checks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_frozen(root: Path) -> dict:
    p = state_dir(root) / "frozen.json"
    if not p.is_file():
        print("no frozen checks — run boil-check.py compile first", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def save_frozen(root: Path, frozen: dict) -> None:
    (state_dir(root) / "frozen.json").write_text(json.dumps(frozen, indent=1) + "\n", encoding="utf-8")


def cfg_of(frozen: dict) -> dict:
    c = dict(DEFAULTS)
    c.update(frozen.get("review") or {})
    return c


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def events(root: Path) -> list[dict]:
    return _jsonl(state_dir(root) / "reviews.jsonl")


def record(root: Path, rec: dict) -> dict:
    rec = {"ts": now(), **rec}
    with (state_dir(root) / "reviews.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def passed(root: Path) -> set[str]:
    return {a["milestone"] for a in _jsonl(state_dir(root) / "attempts.jsonl") if a.get("result") == "PASS"}


def spent(root: Path) -> float:
    return sum(float(a.get("spent_usd", 0) or 0) for a in _jsonl(state_dir(root) / "attempts.jsonl")) + \
        sum(float(e.get("spent_usd", 0) or 0) for e in events(root))


# ------------------------------------------------------------------ git
def git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def is_noise(rel: str) -> bool:
    p = Path(rel)
    return (any(part in NOISE_DIRS for part in p.parts) or p.suffix in NOISE_SUFFIXES
            or p.name in NOISE_NAMES)


def _numstat(text: str | None) -> tuple[int, list[str]]:
    lines, files = 0, []
    for ln in (text or "").splitlines():
        parts = ln.split("\t")
        if len(parts) != 3:
            continue
        add, dele, path = parts
        if is_noise(path):
            continue
        files.append(path)
        lines += (int(add) if add.isdigit() else 0) + (int(dele) if dele.isdigit() else 0)
    return lines, files


def reviewable(root: Path, base: str | None, head: str | None) -> tuple[int, list[str], bool]:
    """Source lines changed since `base`: commits base..HEAD, plus the dirty tree, plus
    untracked files. Docs, lockfiles and .boil/ state are never reviewable lines."""
    lines, files = 0, []
    if base and head and base != head:
        n, f = _numstat(git(root, "diff", "--numstat", f"{base}..{head}"))
        lines += n
        files += f
    n, f = _numstat(git(root, "diff", "--numstat", "HEAD"))
    dirty = n > 0 or bool(f)
    lines += n
    files += f
    for rel in (git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines():
        if not rel or is_noise(rel):
            continue
        try:
            n = sum(1 for _ in (root / rel).open("rb"))
        except OSError:
            n = 0
        files.append(rel)
        lines += n
        dirty = True
    return lines, sorted(set(files)), dirty


def last_reviewed_head(root: Path, frozen: dict) -> str | None:
    for e in reversed(events(root)):
        if e.get("event") in REVIEWED_EVENTS and e.get("head"):
            return e["head"]
    if frozen.get("base_sha"):
        return frozen["base_sha"]
    roots = (git(root, "rev-list", "--max-parents=0", "HEAD") or "").split()
    return roots[0] if roots else None


# ------------------------------------------------------------------ decide
def decide(cfg: dict, node: dict, frozen: dict, done: set[str], lines: int, files: list[str],
           prior: list[dict]) -> tuple[bool, str]:
    """The gate. Pure: no I/O, so the policy is testable and explainable."""
    mid = node["id"]
    if not cfg.get("enabled", True):
        return False, "review disabled in milestones.json"
    if node.get("baseline") == "already-green":
        return False, f"{mid} is an already_green regression guard — nothing new to read"
    if node.get("kind") == "review":
        return False, f"{mid} is a fix node — use `close`"
    if any(e.get("milestone") == mid and e.get("event") in REVIEWED_EVENTS for e in prior):
        return False, f"review round for {mid} already spent (one per milestone)"
    if lines == 0:
        return False, "no reviewable diff since the last review"
    if node.get("tier") in cfg.get("always_tiers", []):
        return True, f"tier {node['tier']} is always reviewed ({lines} lines)"
    for pat in cfg.get("risk_paths", []):
        hit = next((f for f in files if fnmatch.fnmatch(f, pat)), None)
        if hit:
            return True, f"risk path {hit} matches {pat} ({lines} lines)"
    must = [m["id"] for m in frozen["milestones"] if m.get("must_have", True) and m.get("kind") != "review"]
    if all(m in done or m == mid for m in must):
        return True, f"final milestone — the whole accumulated diff ({lines} lines)"
    every = int(cfg.get("every_lines", 150) or 0)
    if every <= 0 or lines >= every:
        return True, f"{lines} unreviewed lines >= {every}"
    return False, f"{lines} unreviewed lines < {every} — accumulating"


# ------------------------------------------------------------------ roborev
def roborev_bin() -> str | None:
    return os.environ.get("BOIL_ROBOREV") or shutil.which("roborev")


def rb(root: Path, *args: str, timeout: int = 120) -> tuple[int, str]:
    exe = roborev_bin()
    if not exe:
        return 127, ""
    try:
        r = subprocess.run([exe, *args], text=True, capture_output=True, cwd=str(root), timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as exc:
        return 126, str(exc)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _json_payload(out: str):
    """roborev pretty-prints JSON over many lines and may prefix a warning line;
    parse from the first bracket."""
    start = min((i for i in (out.find("["), out.find("{")) if i >= 0), default=-1)
    if start < 0:
        return None
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError:
        return None


def list_jobs(root: Path) -> list[dict]:
    rc, out = rb(root, "list", "--json", "--limit", "30")
    if rc != 0:
        return []
    jobs = _json_payload(out) or []
    if not isinstance(jobs, list):
        jobs = []
    return sorted((j for j in jobs if j.get("job_type", "review") in ("review", "range")),
                  key=lambda j: j.get("id", 0))


def covers(job: dict, head: str) -> bool:
    """roborev v0.65 records a single-commit job as `<sha>` and a --since range job as
    `<base>..<head>` (job_type "range"); either one whose end is HEAD covers our diff."""
    ref = job.get("git_ref") or ""
    return head in ref.split("..") or ref.split("..")[-1].startswith(head[:12]) or head.startswith(ref.split("..")[-1] or "-")


def jobs_for_head(root: Path, head: str) -> list[dict]:
    return [j for j in list_jobs(root) if covers(j, head)]


def show_job(root: Path, jid: int) -> dict | None:
    rc, out = rb(root, "show", "--job", "--json", str(jid))
    if rc != 0:
        return None
    job = _json_payload(out)
    return job if isinstance(job, dict) else None


def wait_done(root: Path, head: str, jid: int, timeout: int) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = next((j for j in jobs_for_head(root, head) if j.get("id") == jid), None)
        if job and job.get("status") == "done":
            return job
        if job and job.get("status") in ("failed", "skipped"):
            return None
        time.sleep(5)
    return None


def run_review(root: Path, cfg: dict, base: str | None, head: str, dirty: bool) -> int | str | None:
    """Enqueue and wait. Returns the job id, "timeout", or None when nothing is reviewable."""
    args = ["review", "--wait", "--quiet"]
    if base and base != head:
        args += ["--since", base]
    elif dirty:
        args += ["--dirty"]
    else:
        return None
    if cfg.get("agent"):
        args += ["--agent", cfg["agent"]]
    if cfg.get("model"):
        args += ["--model", cfg["model"]]
    if cfg.get("reasoning"):
        args += ["--reasoning", cfg["reasoning"]]
    before = max((j.get("id", 0) for j in list_jobs(root)), default=0)
    rc, _ = rb(root, *args, timeout=int(cfg.get("timeout_s", 900)))
    if rc == 124:
        return "timeout"
    # The job we just paid for: newest id above the snapshot, preferring one that names HEAD.
    new = [j for j in list_jobs(root) if j.get("id", 0) > before]
    mine = [j for j in new if covers(j, head)] or new
    return mine[-1]["id"] if mine else None


def parse_findings(output: str) -> list[dict]:
    if "## Review Findings" not in output:
        return []
    body = output.split("## Review Findings", 1)[1].split("## Summary", 1)[0]
    found = []
    for block in re.split(r"\n\s*---\s*\n", body):
        f: dict = {}
        for m in FINDING_FIELD.finditer(block):
            f[m.group(1).lower()] = m.group(2).strip()
        if f.get("problem") or f.get("severity"):
            f["severity"] = (f.get("severity") or "Medium").split()[0].strip("*:").capitalize()
            found.append({k: f.get(k, "") for k in ("severity", "location", "problem", "fix")})
    return found


def is_clean(job: dict) -> bool:
    out = (job.get("output") or "").strip()
    return bool(job.get("verdict_bool")) or out.startswith("No issues found")


def split(findings: list[dict], min_sev: str) -> tuple[list[dict], list[dict]]:
    floor = SEVERITY.get((min_sev or "high").lower(), 3)
    must = [f for f in findings if SEVERITY.get(f["severity"].lower(), 2) >= floor]
    rest = [f for f in findings if f not in must]
    return must, rest


def close_job(root: Path, jid: int, comment: str) -> None:
    rb(root, "comment", "--job", str(jid), comment)
    rb(root, "close", str(jid))


def log_deferred(root: Path, mid: str, jid: int, deferred: list[dict]) -> None:
    if not deferred:
        return
    p = root / ".boil" / "log.md"
    body = [f"\n## Deferred review findings — {mid} (roborev job {jid}, {now()[:10]})\n"]
    body += [f"- [{f['severity']}] {f['location']} — {f['problem']} (fix: {f['fix']})" for f in deferred]
    body.append("")
    with p.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(body))


def insert_fix_node(frozen: dict, parent: dict, jid: int, findings: list[dict], head: str) -> dict:
    fid = f"{parent['id']}-fix"
    node = {
        "id": fid, "title": f"address {len(findings)} review finding(s) on {parent['id']} (roborev job {jid})",
        "check": parent["check"], "protect": list(parent.get("protect", [])), "after": [],
        "kind": "review", "tier": parent.get("tier", "T1"),
        "proxy_gap": "the frozen check guards regression only; the findings are re-reviewed once by a second model",
        "must_have": True, "hash": parent["hash"], "baseline": "review-fix", "frozen_at": now(),
        "review": {"job": jid, "head": head, "round": 1, "findings": findings},
    }
    ms = frozen["milestones"]
    idx = next(i for i, m in enumerate(ms) if m["id"] == parent["id"])
    ms.insert(idx + 1, node)
    for m in ms:
        if m["id"] != fid and parent["id"] in m.get("after", []) and fid not in m["after"]:
            m["after"].append(fid)
    return node


# ------------------------------------------------------------------ commands
def cmd_review(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    node = next((m for m in frozen["milestones"] if m["id"] == a.milestone), None)
    if not node:
        print(f"unknown milestone {a.milestone}", file=sys.stderr)
        return 2
    done = passed(root)
    if node["id"] not in done:
        print(f"{node['id']} has not passed — a review follows a PASS", file=sys.stderr)
        return 2
    cfg = cfg_of(frozen)
    prior = events(root)
    head = (git(root, "rev-parse", "HEAD") or "").strip() or None
    if not head:
        rec = record(root, {"milestone": node["id"], "event": "SKIP", "reason": "not a git repository"})
        print(f"SKIP {node['id']}: {rec['reason']}")
        return 0
    base = last_reviewed_head(root, frozen)
    lines, files, dirty = reviewable(root, base, head)
    go, reason = decide(cfg, node, frozen, done, lines, files, prior)
    if go and not roborev_bin():
        go, reason = False, "roborev not installed (not on PATH; set BOIL_ROBOREV to override)"
    if go and cfg.get("cost_usd") and frozen.get("budget_usd") and \
            spent(root) + float(cfg["cost_usd"]) > float(frozen["budget_usd"]):
        go, reason = False, f"budget: ${spent(root):.2f} + review ${cfg['cost_usd']:.2f} > ${frozen['budget_usd']:.2f}"
    if a.dry_run:
        print(json.dumps({"milestone": node["id"], "go": go, "reason": reason, "lines": lines,
                          "files": files, "base": base, "head": head, "dirty": dirty}))
        return 0
    if not go:
        record(root, {"milestone": node["id"], "event": "SKIP", "reason": reason, "lines": lines})
        print(f"SKIP {node['id']}: {reason}")
        return 0
    if not prior:
        rb(root, "snooze", "-d", "8h")   # boil owns review cadence now; quiet the agent-hook nag
    adopted = jobs_for_head(root, head)
    jid: int | str | None
    if adopted:
        job = adopted[-1]
        jid = job["id"]
        if job.get("status") != "done" and not wait_done(root, head, jid, int(cfg["timeout_s"])):
            record(root, {"milestone": node["id"], "event": "PENDING", "reason": reason, "job": jid, "lines": lines})
            print(f"PENDING {node['id']}: adopted roborev job {jid} is still {job.get('status')}")
            return 71
    else:
        jid = run_review(root, cfg, base, head, dirty)
        if jid == "timeout":
            record(root, {"milestone": node["id"], "event": "PENDING", "reason": reason, "lines": lines})
            print(f"PENDING {node['id']}: review did not finish within {cfg['timeout_s']}s — re-run `review` later")
            return 71
        if jid is None:
            record(root, {"milestone": node["id"], "event": "SKIP", "reason": "roborev returned no job", "lines": lines})
            print(f"SKIP {node['id']}: roborev returned no job")
            return 0
    job = show_job(root, int(jid)) or {}
    findings = [] if is_clean(job) else parse_findings(job.get("output") or "")
    must, deferred = split(findings, cfg["fix_min_severity"])
    cost = float(cfg.get("cost_usd") or 0)
    base_rec = {"milestone": node["id"], "reason": reason, "job": int(jid), "head": head, "base": base,
                "lines": lines, "adopted": bool(adopted), "dirty_uncommitted": dirty and base != head,
                "spent_usd": cost}
    if not findings:
        close_job(root, int(jid), f"boil: clean review at milestone {node['id']}")
        record(root, {**base_rec, "event": "CLEAN", "deferred": []})
        print(f"CLEAN {node['id']}: roborev job {jid} — no findings ({reason})")
        return 0
    log_deferred(root, node["id"], int(jid), deferred)
    if not must:
        close_job(root, int(jid), f"boil: {len(deferred)} finding(s) below {cfg['fix_min_severity']} deferred to .boil/log.md")
        record(root, {**base_rec, "event": "DEFERRED", "deferred": deferred})
        print(f"DEFERRED {node['id']}: roborev job {jid} — {len(deferred)} finding(s) below "
              f"{cfg['fix_min_severity']} logged to .boil/log.md, job closed")
        return 0
    fix = insert_fix_node(frozen, node, int(jid), must, head)
    save_frozen(root, frozen)
    record(root, {**base_rec, "event": "FIX-NODE", "node": fix["id"], "findings": must, "deferred": deferred})
    print(f"REVIEW {node['id']}: roborev job {jid} — {len(must)} must-fix finding(s) -> node {fix['id']}; "
          f"{len(deferred)} deferred")
    for f in must:
        print(f"  [{f['severity']}] {f['location']} — {f['problem']}")
    return 70


def cmd_close(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    node = next((m for m in frozen["milestones"] if m["id"] == a.milestone), None)
    if not node or node.get("kind") != "review" or not node.get("review"):
        print(f"{a.milestone} is not a fix node created by `review`", file=sys.stderr)
        return 2
    if node["id"] not in passed(root):
        print(f"{node['id']} has not passed its check yet — the regression gate comes first", file=sys.stderr)
        return 2
    cfg = cfg_of(frozen)
    rv = node["review"]
    head = (git(root, "rev-parse", "HEAD") or "").strip() or None
    base = rv.get("head")
    _, _, dirty = reviewable(root, base, head)
    remaining: list[dict] = list(rv.get("findings", []))
    jid = None
    if head and (head != base or dirty):
        jid = run_review(root, cfg, base, head, dirty)
        if jid == "timeout":
            record(root, {"milestone": node["id"], "event": "PENDING", "reason": "re-review timed out"})
            print(f"PENDING {node['id']}: re-review did not finish — re-run `close` later")
            return 71
        job = show_job(root, int(jid)) if jid else {}
        findings = [] if is_clean(job or {}) else parse_findings((job or {}).get("output") or "")
        remaining, deferred = split(findings, cfg["fix_min_severity"])
        log_deferred(root, node["id"], int(jid), deferred) if jid else None
    cost = float(cfg.get("cost_usd") or 0)
    if not remaining:
        if jid:
            close_job(root, int(jid), f"boil: fix round for {rv['job']} verified clean")
        close_job(root, int(rv["job"]), f"boil: addressed by {node['id']}, re-review job {jid}")
        record(root, {"milestone": node["id"], "event": "CLOSED", "job": rv["job"], "rereview": jid,
                      "head": head, "spent_usd": cost})
        print(f"CLOSED {node['id']}: roborev job {rv['job']} addressed; re-review {jid} clean")
        return 0
    record(root, {"milestone": node["id"], "event": "OPEN", "job": rv["job"], "rereview": jid, "head": head,
                  "findings": remaining, "spent_usd": cost})
    print(f"OPEN {node['id']}: {len(remaining)} finding(s) remain after the one fix round — the user decides "
          f"(roborev job {rv['job']}, re-review {jid})")
    for f in remaining:
        print(f"  [{f['severity']}] {f['location']} — {f['problem']}")
    return 70


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review", help="after a milestone PASS: decide, review once, route findings")
    r.add_argument("--root", default=".")
    r.add_argument("--milestone", required=True)
    r.add_argument("--dry-run", action="store_true", help="print the decision, call nothing")
    r.set_defaults(fn=cmd_review)
    c = sub.add_parser("close", help="after a fix node PASS: re-review once, close or hand over")
    c.add_argument("--root", default=".")
    c.add_argument("--milestone", required=True)
    c.set_defaults(fn=cmd_close)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
