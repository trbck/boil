#!/usr/bin/env python3
"""The verifier-first controller: the sensor is the gate, this script is the loop.

An LLM is called for exactly two things per milestone — drafting a check and
attempting the milestone — and decides nothing. This script owns the rest:

  compile  validate every drafted check, then freeze it (hash check + protected files)
  next     the next milestone: first failing node in dependency order
  run      run ONE frozen check; return one minimal counterexample and a decision code
  split    add 2–4 sub-milestones under a stalled node (once per node)
  audit    scan a diff for known gaming signatures (skip markers, protected-path writes, ...)
  status   one machine-generated line: green/total, current attempt, spend
  verify   re-run every frozen check now; --write stamps evidence on {#id}-tagged goal boxes

Rules, each traceable to `_research/boil-convergence/PLAN.md`:
  * validate before freeze — a check that passes on the current state is not
    falsifiable and is rejected; a `gold` command must pass; runs must agree
  * the controller runs the check; the implementer never gets its source or a tool
  * one minimal counterexample flows back, never the suite or the trace
  * stall = identical failure signature twice in a row
  * caps and budget are checked BEFORE the check runs; the LLM never self-terminates
  * check and protected files are hashed together; drift = TAMPER
  * passed milestones are never re-run; retry only the failed node

Exit codes (the driver obeys them and never reasons about them):
  0 PASS   10 RETRY   20 STALL   30 CAP   40 BUDGET   50 TAMPER
  60 NOT-FALSIFIABLE (compile)   1 audit finding   2 usage
  verify: 0 MET  1 GAP  50 TAMPER
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STATE = Path(".boil") / "checks"
DEFAULT_CAP = 4              # 1 fresh + 2 feedback rounds + 1 fresh-context resample
DEFAULT_STALL = 2            # identical failure signature N times in a row
DEFAULT_TIMEOUT = 300        # seconds per check run
DEFAULT_DETERMINISM = 2      # identical outcomes required at compile time
COUNTEREXAMPLE = re.compile(r"(AssertionError|assert |Error:|FAILED|FAIL:|Traceback|expected|got )", re.I)
AUDIT_SIGNATURES = [
    (re.compile(r"^\+.*(pytest\.mark\.(skip|xfail)|@skip\b|@unittest\.skip|\.skip\(|xfail)"), "skip marker"),
    (re.compile(r"^\+.*(monkeypatch|monkey_patch|setattr\((os|sys|time|torch|subprocess)\b)"), "monkey-patching"),
    (re.compile(r"^\+.*(git log|git show|reference[_ ]solution|gold[_ ]patch)"), "git-history / reference access"),
    (re.compile(r"^\+.*(_always_pass|return True  *#.*pass|sys\.exit\(0\)  *#)"), "evaluator stub"),
]

# A goal checkbox binds to a milestone by ending with {#<milestone id>}:
#   - [ ] latest run clears the Sharpe floor {#sharpe_floor}
# `verify --write` stamps evidence only on tagged boxes. Untagged boxes keep manual evidence.
CHECKBOX_TAG = re.compile(r"\{#([A-Za-z0-9_.-]+)\}\s*$")
CHECKBOX_LINE = re.compile(r"^(\s*-\s*)\[( |x|X)\]")
OLD_EVIDENCE = re.compile(r"\s*[—-]*\s*EVIDENCE:.*$")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(*parts: bytes) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
        h.update(b"\0")
    return h.hexdigest()[:16]


def state_dir(root: Path) -> Path:
    d = root / STATE
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_frozen(root: Path) -> dict:
    p = state_dir(root) / "frozen.json"
    if not p.is_file():
        print("no frozen checks — run `compile` first", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def save_frozen(root: Path, frozen: dict) -> None:
    (state_dir(root) / "frozen.json").write_text(json.dumps(frozen, indent=1) + "\n", encoding="utf-8")


IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis",
                "node_modules", ".git", ".tox", ".venv", "dist", "build"}
IGNORED_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp")


def _is_artifact(rel: Path) -> bool:
    return any(part in IGNORED_DIRS for part in rel.parts) or rel.suffix in IGNORED_SUFFIXES


def harness_hash(root: Path, m: dict) -> str:
    """Hash the check command plus every protected source file, as one artifact.
    Tampering only succeeds when scorer and tests are edited together — so both are frozen.
    Build caches the check itself writes (__pycache__, .pytest_cache, *.pyc) are not the ruler."""
    parts = [m["check"].encode()]
    for rel in m.get("protect", []):
        p = root / rel
        files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]
        for f in files:
            frel = f.relative_to(root) if f.is_absolute() else Path(rel)
            if _is_artifact(frel):
                continue
            parts.append(str(frel).encode())
            parts.append(f.read_bytes() if f.is_file() else b"<missing>")
    return sha(*parts)


def run_cmd(root: Path, cmd: str, timeout: int) -> tuple[int, str]:
    """Run a check in a clean subprocess. Its output is captured; the implementer never sees it."""
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")}
    try:
        r = subprocess.run(cmd, shell=True, cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired as e:
        return 124, f"TIMEOUT after {timeout}s\n{e.stdout or ''}\n{e.stderr or ''}"


def counterexample(output: str) -> str:
    """The single most informative failing line — never the whole trace."""
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for ln in lines:
        if COUNTEREXAMPLE.search(ln) and not ln.startswith("File "):
            return ln[:240]
    return (lines[-1] if lines else "check failed with no output")[:240]


def failure_signature(output: str, note: str = "") -> str:
    """Stable hash of the failure, insensitive to timings, addresses and absolute paths.
    `note` lets the driver fold in the attempt's diff hash, so 'same failure, same diff' stalls."""
    norm = re.sub(r"0x[0-9a-f]+|\d+\.\d+s|/[\w./-]+/", "", output)
    tail = "\n".join(ln for ln in norm.splitlines() if ln.strip())[-2000:]
    return sha(tail.encode(), note.encode())


def attempts(root: Path, mid: str | None = None) -> list[dict]:
    p = state_dir(root) / "attempts.jsonl"
    if not p.is_file():
        return []
    out = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [a for a in out if mid is None or a["milestone"] == mid]


def append(root: Path, rec: dict) -> None:
    with (state_dir(root) / "attempts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def passed(root: Path) -> set[str]:
    return {a["milestone"] for a in attempts(root) if a["result"] == "PASS"}


def spent_total(root: Path) -> float:
    reviews = state_dir(root) / "reviews.jsonl"
    review_cost = 0.0
    if reviews.is_file():
        for ln in reviews.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                review_cost += float(json.loads(ln).get("spent_usd", 0) or 0)
            except (json.JSONDecodeError, ValueError):
                continue
    return round(sum(float(a.get("spent_usd", 0) or 0) for a in attempts(root)) + review_cost, 4)


def _head_sha(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def open_review(root: Path) -> str:
    """`review OPEN job N (M)` when boil-review.py handed findings to the user, else ''."""
    reviews = state_dir(root) / "reviews.jsonl"
    if not reviews.is_file():
        return ""
    last: dict[str, dict] = {}
    for ln in reviews.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if e.get("milestone"):
            last[e["milestone"]] = e
    opens = [e for e in last.values() if e.get("event") in ("OPEN", "PENDING")]
    return "; ".join(f"review {e['event']} job {e.get('job', '?')} ({e['milestone']})" for e in opens)


# ---------------------------------------------------------------- compile
ENV_FAILURE = re.compile(r"No module named|command not found|not found\b|No such file or directory: '?(python|pytest|node|npm|uv|cargo|go)\b|Permission denied", re.I)


def environment_failure(rc: int, output: str) -> str:
    """A check that cannot even run is broken, not falsifiable. Exit 127 is the shell's
    'command not found'; a missing interpreter module or binary is the same class."""
    if rc in (126, 127):
        return f"exit {rc} (command not found / not executable)"
    m = ENV_FAILURE.search(output)
    return m.group(0) if m else ""


def validate(root: Path, m: dict, runs: int) -> tuple[dict | None, str]:
    """Return (frozen milestone, '') or (None, reason). The gates, in order:
    can-run, determinism, falsifiability, gold-sanity, then hash."""
    timeout = int(m.get("timeout", DEFAULT_TIMEOUT))
    outcomes = []
    first_out = ""
    for i in range(max(1, runs)):
        rc, out = run_cmd(root, m["check"], timeout)
        if i == 0:
            first_out = out
            env = environment_failure(rc, out) if rc != 0 else ""
            if env:
                return None, f"check cannot run in the verifier environment ({env}) — fix the command, not the code"
        outcomes.append(rc != 0)
    if len(set(outcomes)) > 1:
        return None, f"check is not deterministic across {runs} runs — not frozen"
    fails_now = outcomes[0]
    if not fails_now and not m.get("already_green"):
        return None, ("check passes on the current state — not falsifiable, not frozen "
                      "(tighten the check; if the milestone already landed, set already_green: true "
                      "to freeze it as a regression guard)")
    gold = m.get("gold")
    if gold:
        grc, _ = run_cmd(root, gold, timeout)
        if grc != 0:
            return None, "gold-sanity command failed — the check cannot be trusted to pass on a known-good state"
    fm = {
        "id": m["id"], "title": m.get("title", m["id"]), "check": m["check"],
        "protect": list(m.get("protect", [])), "after": list(m.get("after", [])),
        "kind": m.get("kind", "test"), "tier": m.get("tier", "T1"),
        "proxy_gap": m.get("proxy_gap", ""), "must_have": bool(m.get("must_have", True)),
        "hash": harness_hash(root, m),
        "baseline": "falsifiable" if fails_now else "already-green",
        "counterexample_at_compile": counterexample(first_out) if fails_now else "",
        "frozen_at": now(),
    }
    return fm, ""


def cmd_compile(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    runs = int(spec.get("determinism_runs", a.determinism_runs))
    prev_path = state_dir(root) / "frozen.json"
    prev_records, prev_doc = {}, {}
    if prev_path.is_file():
        try:
            prev_doc = json.loads(prev_path.read_text(encoding="utf-8"))
            prev_records = {m["id"]: m for m in prev_doc.get("milestones", [])}
        except (json.JSONDecodeError, KeyError):
            prev_records, prev_doc = {}, {}
    prev = {mid: r["hash"] for mid, r in prev_records.items()}
    frozen = {"compiled_at": now(), "budget_usd": float(spec.get("budget_usd", 0) or 0),
              "cap": int(spec.get("cap", DEFAULT_CAP)), "stall": int(spec.get("stall", DEFAULT_STALL)),
              "determinism_runs": runs, "milestones": [],
              "review": spec.get("review", {}),
              # the sha the unreviewed-diff accumulator starts from; never moved by a recompile
              "base_sha": prev_doc.get("base_sha") or _head_sha(root)}
    rejected = 0
    for m in spec["milestones"]:
        old = prev_records.get(m["id"])
        if old and old["hash"] == harness_hash(root, m):
            # Falsifiability was proven once for this exact check + harness; the tree may
            # have moved since (the milestone may have landed) but the ruler has not.
            fm = dict(old, title=m.get("title", old.get("title")), after=list(m.get("after", [])),
                      kind=m.get("kind", old.get("kind")), tier=m.get("tier", old.get("tier")),
                      proxy_gap=m.get("proxy_gap", old.get("proxy_gap")),
                      must_have=bool(m.get("must_have", old.get("must_have", True))))
            frozen["milestones"].append(fm)
            print(f"FROZEN {m['id']} hash={fm['hash']} baseline={fm['baseline']} (carried from {fm['frozen_at']})")
            continue
        fm, reason = validate(root, m, runs)
        if fm is None:
            rejected += 1
            print(f"REJECT {m['id']}: {reason}")
            print(f"       {m['check']}")
            continue
        frozen["milestones"].append(fm)
        print(f"FROZEN {m['id']} hash={fm['hash']} baseline={fm['baseline']}")
    # Fix nodes were created by boil-review.py, not by the spec; a recompile keeps them
    # under their parent as long as the parent survived.
    ids = [m["id"] for m in frozen["milestones"]]
    for old in prev_records.values():
        if old.get("kind") == "review" and old["id"] not in ids:
            parent = old["id"].rsplit("-fix", 1)[0]
            if parent in ids:
                frozen["milestones"].insert(ids.index(parent) + 1, old)
                ids.insert(ids.index(parent) + 1, old["id"])
    # A re-authored check is a new ruler: attempts made against the old one do not count
    # toward the cap or the stall, so those records are archived. Attempts against a
    # milestone whose hash did not move — including its PASS — are carried over.
    new = {m["id"]: m["hash"] for m in frozen["milestones"]}
    ledger = state_dir(root) / "attempts.jsonl"
    if prev and ledger.is_file():
        keep, drop = [], []
        for ln in ledger.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            mid = json.loads(ln).get("milestone")
            (keep if mid in new and new[mid] == prev.get(mid) else drop).append(ln)
        if drop:
            archived = ledger.with_name(f"attempts-{now().replace(':', '')}.jsonl")
            archived.write_text("\n".join(drop) + "\n", encoding="utf-8")
            ledger.write_text(("\n".join(keep) + "\n") if keep else "", encoding="utf-8")
            changed = sorted({json.loads(ln)["milestone"] for ln in drop})
            print(f"checks changed for {', '.join(changed)} — their attempts archived to {archived.name}")
    save_frozen(root, frozen)
    print(f"{len(frozen['milestones'])} frozen, {rejected} rejected -> {state_dir(root) / 'frozen.json'}")
    return 60 if rejected else 0


# ------------------------------------------------------------------- next
def topo_next(frozen: dict, done: set[str]) -> dict | None:
    """First node whose dependencies are all green, in spec order. Passed nodes are never re-run."""
    for m in frozen["milestones"]:
        if m["id"] in done:
            continue
        if all(dep in done for dep in m["after"]):
            return m
    return None


def cmd_next(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    m = topo_next(frozen, passed(root))
    if not m:
        print(json.dumps({"milestone": None, "done": True}))
        return 0
    prior = attempts(root, m["id"])
    print(json.dumps({"milestone": m["id"], "title": m["title"], "kind": m["kind"], "tier": m["tier"],
                      "attempt_next": len(prior) + 1, "cap": frozen["cap"],
                      "last_result": prior[-1]["result"] if prior else None,
                      "last_counterexample": (prior[-1].get("counterexample") if prior else "") or ""}))
    return 0


# -------------------------------------------------------------------- run
def cmd_run(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    m = next((x for x in frozen["milestones"] if x["id"] == a.milestone), None)
    if not m:
        print(f"unknown milestone {a.milestone}", file=sys.stderr)
        return 2
    ts = now()
    # Pre-call gates, in this order: tamper, budget, cap. None of them runs the check.
    if harness_hash(root, m) != m["hash"]:
        append(root, {"ts": ts, "milestone": m["id"], "result": "TAMPER", "spent_usd": a.spent_usd})
        print(f"TAMPER {m['id']}: check or protected file changed since freeze — loop aborted, human decides")
        return 50
    if frozen["budget_usd"] and spent_total(root) + a.spent_usd > frozen["budget_usd"]:
        append(root, {"ts": ts, "milestone": m["id"], "result": "BUDGET", "spent_usd": a.spent_usd})
        print(f"BUDGET ${spent_total(root):.2f} > ${frozen['budget_usd']:.2f} — stop, ask the user")
        return 40
    prior = attempts(root, m["id"])
    n = len(prior) + 1
    if n > frozen["cap"]:
        append(root, {"ts": ts, "milestone": m["id"], "attempt": n, "result": "CAP", "spent_usd": a.spent_usd})
        print(f"CAP {m['id']}: {frozen['cap']} attempts used — split the milestone or hand to the user")
        return 30

    rc, out = run_cmd(root, m["check"], DEFAULT_TIMEOUT)
    if rc == 0 and a.rerun:  # a pass must repeat: 84% of pass->fail transitions are flakes
        rc2, out2 = run_cmd(root, m["check"], DEFAULT_TIMEOUT)
        if rc2 != 0:
            rc, out = rc2, "FLAKY: passed once then failed\n" + out2
    if rc == 0:
        append(root, {"ts": ts, "milestone": m["id"], "attempt": n, "result": "PASS", "spent_usd": a.spent_usd})
        print(f"PASS {m['id']} attempt {n} — EVIDENCE: `{m['check']}` -> exit 0 | {ts[:10]} | auto")
        return 0

    sig = failure_signature(out, a.note)
    ce = counterexample(out)
    rec = {"ts": ts, "milestone": m["id"], "attempt": n, "result": "FAIL", "signature": sig,
           "counterexample": ce, "spent_usd": a.spent_usd}
    recent = [x.get("signature") for x in prior if x["result"] in ("FAIL", "STALL")][-(frozen["stall"] - 1):]
    if frozen["stall"] > 1 and len(recent) == frozen["stall"] - 1 and all(s == sig for s in recent):
        rec["result"] = "STALL"
        append(root, rec)
        print(f"STALL {m['id']}: identical failure signature {frozen['stall']}x — split this milestone or ask the user")
        print(f"  counterexample: {ce}")
        return 20
    if n >= frozen["cap"]:
        rec["result"] = "CAP"
        append(root, rec)
        print(f"CAP {m['id']}: {n} attempts — hand to the user (or split); do not attempt {n + 1}")
        print(f"  counterexample: {ce}")
        return 30
    append(root, rec)
    print(f"RETRY {m['id']} attempt {n}/{frozen['cap']} failed (sig {sig})")
    print(f"  counterexample: {ce}")
    print("  next: a fresh implementer call gets ONLY the line above + the milestone spec; it may not run the check")
    return 10


# ------------------------------------------------------------------ split
def cmd_split(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    parent = next((x for x in frozen["milestones"] if x["id"] == a.milestone), None)
    if not parent:
        print(f"unknown milestone {a.milestone}", file=sys.stderr)
        return 2
    if parent.get("split"):
        print(f"{a.milestone} was already split once — a second stall goes to the user, not to another split")
        return 3
    children = json.loads(a.spec)
    if not 1 <= len(children) <= 4:
        print("split takes 1-4 sub-milestones", file=sys.stderr)
        return 2
    frozen_children = []
    for c in children:
        c.setdefault("after", list(parent["after"]))
        c.setdefault("tier", parent["tier"])
        fm, reason = validate(root, c, frozen.get("determinism_runs", DEFAULT_DETERMINISM))
        if fm is None:
            print(f"REJECT {c['id']}: {reason}")
            return 60
        fm["parent"] = parent["id"]
        frozen_children.append(fm)
    idx = frozen["milestones"].index(parent)
    parent["split"] = [c["id"] for c in frozen_children]
    parent["after"] = list(dict.fromkeys(parent["after"] + parent["split"]))  # parent now depends on its children
    frozen["milestones"][idx:idx] = frozen_children
    save_frozen(root, frozen)
    print(f"SPLIT {parent['id']} -> {', '.join(parent['split'])}")
    return 0


# ------------------------------------------------------------------ audit
def cmd_audit(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    protected = sorted({p for m in frozen["milestones"] for p in m.get("protect", [])})
    text = Path(a.diff).read_text(encoding="utf-8", errors="replace")
    findings: list[str] = []
    current = ""
    for ln in text.splitlines():
        if ln.startswith("+++ "):
            current = ln[4:].strip()
            current = current[2:] if current.startswith("b/") else current
            for p in protected:
                if current == p or current.startswith(p.rstrip("/") + "/"):
                    findings.append(f"write under protected path: {current}")
            continue
        for rx, label in AUDIT_SIGNATURES:
            if rx.search(ln):
                findings.append(f"{label} in {current or '?'}: {ln.strip()[:120]}")
    if findings:
        for f in findings:
            print(f"AUDIT {f}")
        return 1
    print("AUDIT clean")
    return 0


# ----------------------------------------------------------------- status
def cmd_status(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    done = passed(root)
    must = [m for m in frozen["milestones"] if m.get("must_have", True)]
    green = sum(1 for m in must if m["id"] in done)
    cur = topo_next(frozen, done)
    if cur:
        at = attempts(root, cur["id"])
        cur_s = f"current {cur['id']} att {len(at)}/{frozen['cap']} last={at[-1]['result'] if at else '-'}"
    else:
        cur_s = "current - (done)"
    budget = f"/${frozen['budget_usd']:.2f}" if frozen["budget_usd"] else ""
    rv = open_review(root)
    print(f"milestones {green}/{len(must)} green | delta {len(must) - green} | {cur_s} | "
          f"spent ${spent_total(root):.2f}{budget}{' | ' + rv if rv else ''} | {now()}")
    return 0


# ----------------------------------------------------------------- verify
def verify_all(root: Path, frozen: dict) -> list[dict]:
    """Re-run every frozen check NOW. No attempt record, no cap, no budget — this is the
    operator's (and the doctor's) re-measurement, not an implementer attempt. A green
    checkbox is re-measured, never remembered."""
    results = []
    for m in frozen["milestones"]:
        rec = {"milestone": m["id"], "must_have": bool(m.get("must_have", True)),
               "check": m["check"], "counterexample": ""}
        if harness_hash(root, m) != m["hash"]:
            rec["result"] = "TAMPER"
        else:
            rc, out = run_cmd(root, m["check"], int(m.get("timeout", DEFAULT_TIMEOUT)))
            rec["result"] = "PASS" if rc == 0 else "FAIL"
            if rc != 0:
                rec["counterexample"] = counterexample(out)
        results.append(rec)
    return results


def verify_verdict(results: list[dict]) -> tuple[str, int, int]:
    """(verdict, green, total) over must_have milestones. TAMPER outranks everything."""
    must = [r for r in results if r["must_have"]]
    green = sum(1 for r in must if r["result"] == "PASS")
    if any(r["result"] == "TAMPER" for r in results):
        return "TAMPER", green, len(must)
    if any(r["result"] != "PASS" for r in must):
        return "GAP", green, len(must)
    return "MET", green, len(must)


def stamp_evidence(goal: Path, results: list[dict], date: str) -> int:
    """Tick + stamp an auto EVIDENCE line on each {#id}-tagged box whose check PASSed.
    Never un-ticks, never touches an untagged box, never touches a `| human` line.
    Returns the number of lines changed."""
    if not goal.is_file():
        return 0
    passed = {r["milestone"]: r for r in results if r["result"] == "PASS"}
    lines = goal.read_text(encoding="utf-8").splitlines()
    changed = 0
    for i, ln in enumerate(lines):
        tag = CHECKBOX_TAG.search(ln)
        if not tag or not CHECKBOX_LINE.match(ln) or re.search(r"\|\s*human\b", ln):
            continue
        mid = tag.group(1)
        if mid not in passed:
            continue
        body = OLD_EVIDENCE.sub("", ln[:tag.start()]).rstrip()
        body = CHECKBOX_LINE.sub(lambda mo: f"{mo.group(1)}[x]", body, count=1)
        new = f"{body} — EVIDENCE: `{passed[mid]['check']}` -> exit 0 | {date} | auto {{#{mid}}}"
        if new != ln:
            lines[i] = new
            changed += 1
    if changed:
        goal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def cmd_verify(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    frozen = load_frozen(root)
    results = verify_all(root, frozen)
    verdict, green, total = verify_verdict(results)
    stamped = 0
    if a.write:
        stamped = stamp_evidence(root / ".boil" / "goal.md", results, now()[:10])
    if a.json:
        print(json.dumps({"results": results, "green": green, "total": total,
                          "verdict": verdict, "stamped": stamped}))
    else:
        for r in results:
            extra = f"  {r['counterexample']}" if r["counterexample"] else ""
            print(f"{r['result']:6s} {r['milestone']}{extra}")
        print(f"{verdict}: {green}/{total} must-have milestones green"
              + (f" | {stamped} box(es) stamped" if a.write else ""))
    return {"MET": 0, "GAP": 1, "TAMPER": 50}[verdict]


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile", help="validate drafted checks, then freeze them")
    c.add_argument("--root", default=".")
    c.add_argument("--spec", required=True, help="milestones JSON drafted by the check-authoring call")
    c.add_argument("--determinism-runs", type=int, default=DEFAULT_DETERMINISM)
    c.set_defaults(fn=cmd_compile)
    n = sub.add_parser("next", help="the next milestone in dependency order")
    n.add_argument("--root", default=".")
    n.set_defaults(fn=cmd_next)
    r = sub.add_parser("run", help="run one frozen check and decide")
    r.add_argument("--root", default=".")
    r.add_argument("--milestone", required=True)
    r.add_argument("--spent-usd", type=float, default=0.0, help="cost of the attempt being scored")
    r.add_argument("--rerun", action="store_true", help="a pass must repeat (flake guard)")
    r.add_argument("--note", default="", help="attempt annotation folded into the failure signature, e.g. the diff hash")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("split", help="add 1-4 sub-milestones under a stalled node (once)")
    s.add_argument("--root", default=".")
    s.add_argument("--milestone", required=True)
    s.add_argument("--spec", required=True, help="JSON list of child milestones")
    s.set_defaults(fn=cmd_split)
    d = sub.add_parser("audit", help="scan a diff for gaming signatures")
    d.add_argument("--root", default=".")
    d.add_argument("--diff", required=True)
    d.set_defaults(fn=cmd_audit)
    t = sub.add_parser("status", help="one machine-generated status line")
    t.add_argument("--root", default=".")
    t.set_defaults(fn=cmd_status)
    v = sub.add_parser("verify", help="re-run EVERY frozen check now (no attempt recorded); --write stamps evidence")
    v.add_argument("--root", default=".")
    v.add_argument("--json", action="store_true")
    v.add_argument("--write", action="store_true", help="tick + stamp EVIDENCE on {#id}-tagged goal boxes that pass")
    v.set_defaults(fn=cmd_verify)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
