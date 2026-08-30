#!/usr/bin/env python3
"""bench/run.py — the convergence bench, and boil's end-to-end test.

Drives the whole driver protocol over seeded mini-repos in `bench/projects/<name>/`:

    compile → prepare → <implementer> → score (→ split on STALL, close on a fix node) → doctor --final

Two implementers:

  scripted   applies `patches/<milestone>/<attempt>/` overlays (a directory tree copied onto
             the project) — deterministic, seconds, runs in CI. Each project's `expect.json`
             names the exit codes that must fire, so every controller verdict (PASS, RETRY on a
             real counterexample, STALL → split, CAP, TAMPER, audit, review fix node) is proven
             on real code on every push.
  llm        dispatches ONE `claude -p` per attempt with the packet as its whole prompt, the
             guard wired, and records cost. Run by hand: it produces the numbers that say
             whether boil is effective — first-attempt pass rate, attempts per milestone,
             $ per green box — the instrument PLAN §6 asks for.

Usage
  python3 bench/run.py --implementer scripted [--only NAME] [--json] [--keep]
  python3 bench/run.py --implementer llm [--only NAME] [--model M] [--out bench/results/<date>.json]
  python3 bench/run.py --list

Project layout
  project/            the repo as the implementer first sees it
  boil/goal.md        the goal (boxes are bound to milestones at compile)
  boil/milestones.json
  patches/<M>/<n>/    scripted attempt n on milestone M (exact n; absent = an attempt that changed nothing)
  splits/<M>.json     the child spec `split` gets when M stalls
  roborev-scenario.json   when present, a fake `roborev` is put on PATH with this scenario
  expect.json         {"events": [[milestone, attempt, exit], ["split", M, exit], ["close", M, exit]],
                       "final": <doctor --final exit>}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
PROJECTS = HERE / "projects"
FAKE_ROBOREV = HERE / "fake-roborev" / "roborev"
MAX_ITERATIONS = 40


def sh(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env, timeout=timeout)


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def script(name: str) -> str:
    return str(SCRIPTS / name)


def copy_tree(src: Path, dst: Path) -> list[str]:
    """Copy every file under src onto dst; returns the relative paths written."""
    written = []
    for f in sorted(src.rglob("*")):
        if f.is_file():
            rel = f.relative_to(src)
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            # copy, not copy2: a preserved mtime plus an equal size lets Python reuse a stale
            # .pyc, and the "correct" overlay never runs. Bump the mtime past any cached one.
            shutil.copy(f, dst / rel)
            os.utime(dst / rel, None)
            written.append(str(rel))
    return written


def overlay_for(project: Path, mid: str, attempt: int) -> Path | None:
    base = project / "patches" / mid
    if not base.is_dir():
        return None
    ov = base / str(attempt)
    return ov if ov.is_dir() else None       # exact attempt only: no overlay = an attempt that changed nothing


# ------------------------------------------------------------------ implementers
def scripted_attempt(project: Path, work: Path, mid: str, attempt: int, packet: str) -> dict:
    ov = overlay_for(project, mid, attempt)
    if not ov:
        return {"overlay": None, "files": [], "cost": 0.0}
    files = copy_tree(ov, work)
    # Overlays land within the same second and may keep a file's size; Python's pyc check
    # (mtime in whole seconds + size) would then run the previous attempt's bytecode.
    for cache in work.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    return {"overlay": str(ov.relative_to(project)), "files": files, "cost": 0.0}


def llm_attempt(project: Path, work: Path, mid: str, attempt: int, packet: str, model: str | None) -> dict:
    """ONE headless implementer whose entire prompt is the packet. The guard is wired into
    the work tree's .claude/settings.json so the ruler is architecturally off-limits."""
    prompt = (work / packet).read_text(encoding="utf-8")
    # The guard hook is the fence, not the permission mode: the implementer may run its own
    # code and scratch tests; boil-guard.py denies writes to and runs of the ruler.
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
           "--allowedTools", "Bash", "Edit", "Write", "MultiEdit", "Read", "Glob", "Grep",
           "--settings", str(work / ".claude" / "settings.json")]
    if model:
        cmd += ["--model", model]
    r = sh(cmd, work, timeout=3600)
    cost, text = 0.0, r.stdout
    try:
        data = json.loads(r.stdout)
        cost = float(data.get("total_cost_usd", 0) or 0)
        text = data.get("result", "")
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"overlay": None, "files": [], "cost": cost, "rc": r.returncode, "summary": text[-400:]}


# ------------------------------------------------------------------ one project
def run_project(project: Path, implementer: str, model: str | None, keep: bool) -> dict:
    name = project.name
    tmp = Path(tempfile.mkdtemp(prefix=f"boil-bench-{name}-"))
    work = tmp / "work"
    shutil.copytree(project / "project", work)
    shutil.copytree(project / "boil", work / ".boil")
    git(work, "init", "-q")
    git(work, "config", "user.email", "bench@boil")
    git(work, "config", "user.name", "boil bench")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "seed")

    env = dict(os.environ)
    scenario = project / "roborev-scenario.json"
    if scenario.is_file():
        fake_dir = tmp / "fake"
        fake_dir.mkdir()
        shutil.copy2(scenario, fake_dir / "scenario.json")
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        shutil.copy2(FAKE_ROBOREV, bin_dir / "roborev")
        (bin_dir / "roborev").chmod((bin_dir / "roborev").stat().st_mode | stat.S_IEXEC)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_ROBOREV_DIR"] = str(fake_dir)
        env.pop("BOIL_ROBOREV", None)
    else:
        env["PATH"] = "/nonexistent" + os.pathsep + env.get("PATH", "")   # no accidental real reviews
        env["BOIL_ROBOREV"] = ""
    if implementer == "llm":
        settings = sh([sys.executable, script("boil-guard.py"), "--settings-json", "--root", str(work)], work)
        (work / ".claude").mkdir(exist_ok=True)
        (work / ".claude" / "settings.json").write_text(settings.stdout)

    def check(*args: str) -> subprocess.CompletedProcess[str]:
        return sh([sys.executable, script("boil-check.py"), *args, "--root", str(work)], work, env)

    result = {"project": name, "implementer": implementer, "events": [], "attempts": {}, "spend_usd": 0.0,
              "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "workdir": str(work)}
    t0 = time.time()
    r = check("compile", "--spec", str(work / ".boil" / "milestones.json"))
    result["compile"] = {"exit": r.returncode, "out": r.stdout.strip()[-600:]}
    if r.returncode != 0:
        result.update({"final": None, "green": 0, "total": 0, "seconds": round(time.time() - t0, 1),
                       "ledger": [], "first_pass_failed": [], "status": ""})
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
        return result

    for _ in range(MAX_ITERATIONS):
        pr = check("prepare", *([] if implementer == "llm" else ["--allow-unguarded"]))
        if pr.returncode != 0:
            result["events"].append(["prepare", pr.returncode])   # 40 = BUDGET before dispatch
            break
        out = json.loads(pr.stdout.strip().splitlines()[-1])
        if out.get("done"):
            break
        mid, attempt = out["milestone"], out["attempt"]
        if not out.get("dispatch", True):
            att = {"overlay": None, "files": [], "cost": 0.0, "dispatch": False}
        elif implementer == "scripted":
            att = scripted_attempt(project, work, mid, attempt, out["packet"])
        else:
            att = llm_attempt(project, work, mid, attempt, out["packet"], model)
        result["spend_usd"] += att["cost"]
        sc = check("score", "--milestone", mid, "--spent-usd", str(att["cost"]))
        code = sc.returncode
        result["events"].append([mid, attempt, code])
        result["attempts"][mid] = attempt
        result.setdefault("log", []).append({"milestone": mid, "attempt": attempt, "exit": code,
                                             "attempt_info": att, "score": sc.stdout.strip()[-800:]})
        if code == 0 and mid.endswith("-fix"):
            cl = sh([sys.executable, script("boil-review.py"), "close", "--milestone", mid, "--root", str(work)],
                    work, env)
            result["events"].append(["close", mid, cl.returncode])
            if cl.returncode == 70:
                break
        elif code == 20:
            split = project / "splits" / f"{mid}.json"
            if not split.is_file():
                break
            sp = check("split", "--milestone", mid, "--spec", split.read_text())
            result["events"].append(["split", mid, sp.returncode])
            result.setdefault("log", []).append({"split": mid, "exit": sp.returncode,
                                                 "out": (sp.stdout + sp.stderr).strip()[-600:]})
            if sp.returncode != 0:
                break
        elif code in (30, 40, 50):
            break
        elif code == 71:
            break
        # a driver commits landed work; the next prepare measures its diff from here
        git(work, "add", "-A")
        subprocess.run(["git", "-C", str(work), "commit", "-qm", f"{mid} attempt {attempt}"], capture_output=True)

    fin = sh([sys.executable, script("boil-doctor.py"), "--final", "--root", str(work)], work, env)
    result["final"] = fin.returncode
    st = check("status")
    result["status"] = st.stdout.strip()
    ledger_path = work / ".boil" / "checks" / "attempts.jsonl"
    result["ledger"] = [json.loads(ln) for ln in ledger_path.read_text().splitlines() if ln.strip()] \
        if ledger_path.is_file() else []
    # the same computation a real project gets from `boil-check.py report`
    rep = json.loads(check("report", "--json").stdout.strip().splitlines()[-1])
    for key in ("green", "total", "first_pass_rate", "first_pass_failed", "usd_per_green_box", "compile", "review"):
        result[key] = rep[key]
    result["report"] = rep
    result["seconds"] = round(time.time() - t0, 1)
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
        result.pop("workdir", None)
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--implementer", choices=["scripted", "llm"], default="scripted")
    ap.add_argument("--only", help="run one project")
    ap.add_argument("--model", help="llm mode: model for claude -p")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    ap.add_argument("--out", help="write the result JSON here (llm mode defaults to bench/results/<date>.json)")
    ap.add_argument("--keep", action="store_true", help="keep the work trees")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    names = sorted(p.name for p in PROJECTS.iterdir() if p.is_dir())
    if a.list:
        for n in names:
            exp = PROJECTS / n / "expect.json"
            print(f"{n:14s} {'expect.json' if exp.is_file() else '(no expectation)'}")
        return 0
    if a.only:
        names = [a.only]
    results = {}
    failures = 0
    for n in names:
        res = run_project(PROJECTS / n, a.implementer, a.model, a.keep)
        results[n] = res
        exp_path = PROJECTS / n / "expect.json"
        if a.implementer == "scripted" and exp_path.is_file():
            exp = json.loads(exp_path.read_text())
            ok = res["events"] == exp["events"] and res["final"] == exp["final"]
            res["as_expected"] = ok
            failures += 0 if ok else 1
        if not a.json:
            print(f"{n:14s} {res['green']}/{res['total']} green | events {res['events']} | final {res['final']}"
                  f" | ${res['spend_usd']:.2f} | {res['seconds']}s"
                  + ("" if res.get("as_expected", True) else "  <-- NOT AS EXPECTED"))
    doc = {"implementer": a.implementer, "model": a.model,
           "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "projects": results}
    out = a.out
    if not out and a.implementer == "llm":
        out = str(HERE / "results" / f"{dt.date.today().isoformat()}-{a.model or 'default'}.json")
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(doc, indent=1) + "\n")
        if not a.json:
            print(f"results -> {out}")
    if a.json:
        print(json.dumps(doc))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
