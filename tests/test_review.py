"""Tests for the milestone-wise roborev integration (`scripts/boil-review.py`).

Why a controller step and not a hook: the stock roborev hooks fired on every commit and
every Nth Stop, and each fix commit spawned a fresh review — a ratchet that produced 11 of
43 commits in one session. Inside boil the script decides *when* a second LLM reads the
code (on a milestone PASS, by a deterministic risk score), *how many times* (one review
round + one fix round per milestone, never more), and *what happens to findings* (must-fix
ones become a DAG node gated by the parent's frozen check; the rest are deferred with a
logged disposition — never silently dismissed).

`roborev` is replaced on PATH by a scripted fake that records every call.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "scripts" / "boil-review.py"
CHECK = ROOT / "scripts" / "boil-check.py"
PACKET = ROOT / "scripts" / "boil-dispatch-packet.py"
BRAKES = ROOT / "scripts" / "boil-brakes.py"

FAKE_ROBOREV = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
D = os.environ["FAKE_ROBOREV_DIR"]
S = os.path.join(D, "scenario.json")
sc = json.load(open(S))
with open(os.path.join(D, "calls.log"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
def save(): json.dump(sc, open(S, "w"))
def head(args):
    repo = "."
    if "--repo" in args: repo = args[args.index("--repo") + 1]
    return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], text=True, capture_output=True).stdout.strip()
if cmd == "status":
    print("Daemon: running"); sys.exit(0)
if cmd == "list":
    print(json.dumps(sc.get("jobs", []) or None, indent=2)); sys.exit(0)   # real CLI pretty-prints
if cmd == "config":
    # roborev keeps review_agent and review_model as independent globals; a bare --agent
    # inherits whatever review_model holds. The fake models that inheritance faithfully.
    cfg = sc.setdefault("config", {})
    if sys.argv[2] == "get":
        print(cfg.get(sys.argv[3], "")); sys.exit(0)
    if sys.argv[2] == "set":
        args = [a for a in sys.argv[3:] if not a.startswith("--")]
        if args[0] in sc.get("config_set_fails", []):
            print("refused to set %s" % args[0], file=sys.stderr); sys.exit(1)
        cfg[args[0]] = args[1] if len(args) > 1 else ""
        save(); sys.exit(0)
    sys.exit(0)
if cmd == "check-agents":
    ag = sys.argv[sys.argv.index("--agent") + 1] if "--agent" in sys.argv else "codex"
    if ag in sc.get("down_agents", []):
        print("  x %s   %s ... FAILED (%s)" % (ag, ag, sc.get("down_error", "usage limit reached")))
        print("0 passed, 1 failed, 0 skipped"); sys.exit(1)
    print("  ? %s   %s ... OK (2 bytes)" % (ag, ag))
    print("1 passed, 0 failed, 0 skipped"); sys.exit(0)
if cmd == "review":
    agent = sys.argv[sys.argv.index("--agent") + 1] if "--agent" in sys.argv else ""
    jid = max([j["id"] for j in sc.get("jobs", [])] + [100]) + 1
    # The production failure of 2026-09-04: no --model, so the global leaks in, and codex
    # rejects an Ollama tag with a 400.
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else sc.get("config", {}).get("review_model", "")
    if agent == "codex" and ":" in model:
        ref = sys.argv[sys.argv.index("--since") + 1] + ".." + head(sys.argv) if "--since" in sys.argv else head(sys.argv)
        err = "The '%s' model is not supported when using Codex with a ChatGPT account." % model
        sc.setdefault("jobs", []).append({"id": jid, "git_ref": ref, "branch": "main",
                                          "job_type": "range" if "--since" in sys.argv else "review",
                                          "status": "failed", "agent": agent, "model": model,
                                          "closed": False, "error": err})
        save(); print(err, file=sys.stderr); sys.exit(1)
    if agent in sc.get("refuse_agents", []):
        # roborev refusing before it enqueues anything: no job is ever created, so its own
        # stderr is the only evidence of why.
        print(sc.get("refuse_error", "error: rate limit reached"), file=sys.stderr); sys.exit(1)
    if agent in sc.get("down_agents", []):
        # A failed job has no review; the error only ever shows up in `list`.
        ref = sys.argv[sys.argv.index("--since") + 1] + ".." + head(sys.argv) if "--since" in sys.argv else head(sys.argv)
        sc.setdefault("jobs", []).append({"id": jid, "git_ref": ref, "branch": "main",
                                          "job_type": "range" if "--since" in sys.argv else "review",
                                          "status": "failed", "agent": agent, "closed": False,
                                          "error": sc.get("down_error", "usage limit reached")})
        save(); print(sc.get("down_error", "usage limit reached"), file=sys.stderr); sys.exit(1)
    out = sc.get("review_outputs", []).pop(0) if sc.get("review_outputs") else sc.get("review_output", "No issues found.\nSummary: ok")
    # real roborev (v0.65): a --since range job records git_ref as "<base>..<head>" and
    # job_type "range"; a single-commit job records the sha and job_type "review".
    if "--since" in sys.argv:
        ref, jt = sys.argv[sys.argv.index("--since") + 1] + ".." + head(sys.argv), "range"
    else:
        ref, jt = head(sys.argv), "review"
    sc.setdefault("jobs", []).append({"id": jid, "git_ref": ref, "branch": "main", "job_type": jt,
                                      "status": "done", "agent": agent or "fake", "closed": False,
                                      "verdict": "P" if out.startswith("No issues") else "F"})
    sc.setdefault("shows", {})[str(jid)] = {"job_id": jid, "output": out, "closed": False,
                                            "verdict_bool": 1 if out.startswith("No issues") else 0}
    save(); print(out); sys.exit(0)
if cmd == "show":
    jid = [a for a in sys.argv[2:] if a.isdigit()][0]
    print(json.dumps(sc["shows"][jid], indent=2)); sys.exit(0)
if cmd == "close":
    jid = [a for a in sys.argv[2:] if a.isdigit()][0]
    sc["shows"][jid]["closed"] = True; save(); sys.exit(0)
sys.exit(0)
'''

FINDINGS_HIGH = """## Review Findings

- **Severity**: High
- **Location**: wordfreq/cli.py:12
- **Problem**: `count_words` reads the whole file into memory; a large input will OOM.
- **Fix**: stream line by line.

---

- **Severity**: Low
- **Location**: wordfreq/cli.py:3
- **Problem**: unused import `os`.
- **Fix**: remove it.

## Summary
Adds counting.
"""

FINDINGS_LOW = """## Review Findings

- **Severity**: Low
- **Location**: wordfreq/cli.py:3
- **Problem**: unused import `os`.
- **Fix**: remove it.

## Summary
Adds counting.
"""

CLEAN = "No issues found.\n\nSummary: fine."


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True).stdout


class Project:
    """A git repo with a frozen two-milestone DAG (M1 -> M2 -> M3), a fake roborev, and a ledger."""

    def __init__(self, review: dict | None = None, tiers: dict | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "proj"
        self.root.mkdir()
        (self.root / ".boil").mkdir()
        (self.root / ".boil" / "goal.md").write_text("# Goal\n**One-line:** a thing\n")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "t.py").write_text("x = 1\n")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('hi')\n")
        self.fake = Path(self.tmp.name) / "bin"
        self.fake.mkdir()
        rb = self.fake / "roborev"
        rb.write_text(FAKE_ROBOREV)
        rb.chmod(rb.stat().st_mode | stat.S_IEXEC)
        self.fake_dir = Path(self.tmp.name) / "fake"
        self.fake_dir.mkdir()
        self.scenario({})
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@t")
        git(self.root, "config", "user.name", "t")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")
        tiers = tiers or {}
        ms = []
        for i, mid in enumerate(("M1", "M2", "M3")):
            ms.append({"id": mid, "title": f"milestone {mid}", "check": f"test -f done-{mid}.txt",
                       "protect": ["tests"], "after": [f"M{i}"] if i else [], "tier": tiers.get(mid, "T1"),
                       "proxy_gap": "x"})
        spec = {"budget_usd": 10.0, "milestones": ms}
        if review is not None:
            spec["review"] = review
        (self.root / ".boil" / "milestones.json").write_text(json.dumps(spec))
        r = self.check("compile", "--spec", str(self.root / ".boil" / "milestones.json"))
        assert r.returncode == 0, r.stdout + r.stderr

    def scenario(self, sc: dict) -> None:
        (self.fake_dir / "scenario.json").write_text(json.dumps(sc))

    def env(self, missing: bool = False) -> dict:
        env = dict(os.environ)
        env["PATH"] = ("/nonexistent" if missing else str(self.fake)) + os.pathsep + "/usr/bin:/bin"
        env["FAKE_ROBOREV_DIR"] = str(self.fake_dir)
        env["BOIL_NO_HELM"] = "1"
        # The reviewer cooldown is machine-wide in production; per-project here so a test
        # can neither read nor write the developer's real fallback state.
        env["BOIL_REVIEWER_STATE"] = str(self.fake_dir / "reviewer.json")
        env.pop("BOIL_ROBOREV", None)
        for k in ("BOIL_REVIEW_AGENT", "BOIL_REVIEW_MODEL",
                  "BOIL_REVIEW_BACKUP_AGENT", "BOIL_REVIEW_BACKUP_MODEL"):
            env.pop(k, None)
        return env

    def reviewer_state(self) -> dict:
        p = self.fake_dir / "reviewer.json"
        return json.loads(p.read_text()) if p.is_file() else {}

    def calls(self) -> list[list[str]]:
        p = self.fake_dir / "calls.log"
        return [json.loads(ln) for ln in p.read_text().splitlines()] if p.is_file() else []

    def _run(self, script: Path, *args: str, missing: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(script), *args, "--root", str(self.root)], text=True,
                              capture_output=True, env=self.env(missing), cwd=str(self.root))

    def check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._run(CHECK, *args)

    def review(self, *args: str, missing: bool = False) -> subprocess.CompletedProcess[str]:
        return self._run(REVIEW, *args, missing=missing)

    def land(self, mid: str, lines: int = 5, commit: bool = True) -> None:
        """Implement a milestone: touch its artifact, add `lines` source lines, pass the check."""
        (self.root / f"done-{mid}.txt").write_text("x")
        with (self.root / "src" / "app.py").open("a") as f:
            f.write("".join(f"v_{mid}_{i} = {i}\n" for i in range(lines)))
        if commit:
            git(self.root, "add", "-A")
            git(self.root, "commit", "-qm", f"land {mid}")
        r = self.check("run", "--milestone", mid)
        assert r.returncode == 0, r.stdout + r.stderr

    def frozen(self) -> dict:
        return json.loads((self.root / ".boil" / "checks" / "frozen.json").read_text())

    def events(self) -> list[dict]:
        p = self.root / ".boil" / "checks" / "reviews.jsonl"
        return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.is_file() else []

    def close(self) -> None:
        self.tmp.cleanup()


class DecideTest(unittest.TestCase):
    """The gate: when does a milestone PASS earn a second-LLM review?"""

    def test_roborev_missing_is_a_silent_skip(self) -> None:
        p = Project()
        try:
            p.land("M1", lines=500)
            r = p.review("review", "--milestone", "M1", missing=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "SKIP")
            self.assertIn("roborev", p.events()[-1]["reason"])
        finally:
            p.close()

    def test_a_small_diff_accumulates_instead_of_firing(self) -> None:
        p = Project(review={"every_lines": 100})
        try:
            p.land("M1", lines=10)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ev = p.events()[-1]
            self.assertEqual(ev["event"], "SKIP")
            self.assertIn("unreviewed", ev["reason"])
            self.assertFalse(any(c[0] == "review" for c in p.calls()))
        finally:
            p.close()

    def test_accumulated_lines_across_milestones_fire_once(self) -> None:
        p = Project(review={"every_lines": 100})
        try:
            p.land("M1", lines=60)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            p.land("M2", lines=60)
            r = p.review("review", "--milestone", "M2")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "CLEAN")
            reviews = [c for c in p.calls() if c[0] == "review"]
            self.assertEqual(len(reviews), 1)
            self.assertIn("--since", reviews[0])
        finally:
            p.close()

    def test_the_final_milestone_always_gets_a_review(self) -> None:
        p = Project(review={"every_lines": 1000})
        try:
            p.land("M1", lines=2)
            p.land("M2", lines=2)
            p.land("M3", lines=2)
            r = p.review("review", "--milestone", "M3")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "CLEAN")
            self.assertIn("final", p.events()[-1]["reason"])
        finally:
            p.close()

    def test_a_high_blast_radius_tier_always_gets_a_review(self) -> None:
        p = Project(review={"every_lines": 1000}, tiers={"M1": "T3"})
        try:
            p.land("M1", lines=2)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "CLEAN")
            self.assertIn("T3", p.events()[-1]["reason"])
        finally:
            p.close()

    def test_docs_and_boil_state_do_not_count_as_reviewable_lines(self) -> None:
        p = Project(review={"every_lines": 50})
        try:
            (p.root / "NOTES.md").write_text("\n".join(["line"] * 400) + "\n")
            (p.root / ".boil" / "log.md").write_text("\n".join(["line"] * 400) + "\n")
            p.land("M1", lines=1)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "SKIP")
        finally:
            p.close()

    def test_a_regression_guard_is_never_reviewed(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            spec = json.loads((p.root / ".boil" / "milestones.json").read_text())
            spec["milestones"][0]["already_green"] = True
            spec["milestones"][0]["check"] = "test -d src"
            (p.root / ".boil" / "milestones.json").write_text(json.dumps(spec))
            self.assertEqual(p.check("compile", "--spec", str(p.root / ".boil" / "milestones.json")).returncode, 0)
            self.assertEqual(p.check("run", "--milestone", "M1").returncode, 0)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "SKIP")
            self.assertIn("already_green", p.events()[-1]["reason"])
        finally:
            p.close()

    def test_one_review_round_per_milestone(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(p.events()[-1]["event"], "SKIP")
            self.assertIn("round", p.events()[-1]["reason"])
            self.assertEqual(len([c for c in p.calls() if c[0] == "review"]), 1)
        finally:
            p.close()


class FindingsTest(unittest.TestCase):
    """What happens to what the reviewer says."""

    def test_must_fix_findings_become_a_dag_node_gated_by_the_parent_check(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": FINDINGS_HIGH})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 70, r.stdout + r.stderr)
            ids = [m["id"] for m in p.frozen()["milestones"]]
            self.assertEqual(ids, ["M1", "M1-fix", "M2", "M3"])
            fix = p.frozen()["milestones"][1]
            self.assertEqual(fix["check"], "test -f done-M1.txt")
            self.assertEqual(fix["kind"], "review")
            self.assertEqual(len(fix["review"]["findings"]), 1)          # the High one only
            self.assertEqual(fix["review"]["findings"][0]["severity"], "High")
            m2 = p.frozen()["milestones"][2]
            self.assertIn("M1-fix", m2["after"])                          # dependants wait for the fix
            nxt = json.loads(p.check("next").stdout)
            self.assertEqual(nxt["milestone"], "M1-fix")
            self.assertEqual(p.events()[-1]["event"], "FIX-NODE")
            self.assertEqual(len(p.events()[-1]["deferred"]), 1)          # the Low one, logged not lost
        finally:
            p.close()

    def test_the_fix_packet_carries_the_findings_not_the_check(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": FINDINGS_HIGH})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 70)
            r = subprocess.run([sys.executable, str(PACKET), "--milestone", "M1-fix", "--root", str(p.root)],
                               text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            text = (p.root / ".boil" / "dispatch" / "M1-fix.md").read_text()
            self.assertIn("OOM", text)
            self.assertIn("wordfreq/cli.py:12", text)
            self.assertNotIn("done-M1.txt", text)
        finally:
            p.close()

    def test_only_low_findings_are_deferred_and_the_job_closed(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": FINDINGS_LOW})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual([m["id"] for m in p.frozen()["milestones"]], ["M1", "M2", "M3"])
            self.assertEqual(p.events()[-1]["event"], "DEFERRED")
            self.assertTrue(any(c[0] == "close" for c in p.calls()))
            self.assertIn("unused import", (p.root / ".boil" / "log.md").read_text())
        finally:
            p.close()

    def test_a_clean_review_is_closed(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": CLEAN})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            self.assertEqual(p.events()[-1]["event"], "CLEAN")
            self.assertTrue(any(c[0] == "close" for c in p.calls()))
        finally:
            p.close()

    def test_an_existing_job_for_head_is_adopted_not_duplicated(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            head = git(p.root, "rev-parse", "HEAD").strip()
            p.scenario({"jobs": [{"id": 500, "git_ref": head, "branch": "main", "job_type": "review",
                                  "status": "done", "agent": "codex"}],
                        "shows": {"500": {"job_id": 500, "output": CLEAN, "closed": False, "verdict_bool": 1}}})
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(any(c[0] == "review" for c in p.calls()))
            self.assertEqual(p.events()[-1]["job"], 500)
            self.assertEqual(p.events()[-1]["event"], "CLEAN")
        finally:
            p.close()


class FixRoundTest(unittest.TestCase):
    """One fix round. The re-review is a verdict on the fix, never a new fix node."""

    def _with_fix_node(self, p: Project) -> None:
        p.scenario({"review_output": FINDINGS_HIGH})
        p.land("M1", lines=5)
        self.assertEqual(p.review("review", "--milestone", "M1").returncode, 70)

    def test_close_after_a_clean_re_review_closes_both_jobs(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            self._with_fix_node(p)
            sc = json.loads((p.fake_dir / "scenario.json").read_text())
            sc["review_output"] = CLEAN
            p.scenario(sc)
            p.land("M1-fix", lines=3)
            r = p.review("close", "--milestone", "M1-fix")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "CLOSED")
            closes = [c for c in p.calls() if c[0] == "close"]
            self.assertEqual(len(closes), 2)
        finally:
            p.close()

    def test_findings_remaining_after_the_fix_round_stop_the_loop_for_the_user(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            self._with_fix_node(p)
            p.land("M1-fix", lines=3)                                     # still FINDINGS_HIGH on re-review
            r = p.review("close", "--milestone", "M1-fix")
            self.assertEqual(r.returncode, 70, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "OPEN")
            self.assertEqual([m["id"] for m in p.frozen()["milestones"]], ["M1", "M1-fix", "M2", "M3"])
            b = subprocess.run([sys.executable, str(BRAKES), "check", "--root", str(p.root)],
                               text=True, capture_output=True)
            self.assertIn("STOP", b.stdout + b.stderr)
            self.assertIn("review", (b.stdout + b.stderr).lower())
        finally:
            p.close()

    def test_close_on_a_node_without_a_review_is_a_usage_error(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            self.assertEqual(p.review("close", "--milestone", "M1").returncode, 2)
        finally:
            p.close()


class StatusTest(unittest.TestCase):
    def test_status_line_names_an_open_review(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": FINDINGS_HIGH})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 70)
            p.land("M1-fix", lines=3)
            self.assertEqual(p.review("close", "--milestone", "M1-fix").returncode, 70)
            s = p.check("status").stdout
            self.assertIn("review", s)
            self.assertIn("OPEN", s)
        finally:
            p.close()


class RecompileKeepsBaseShaTest(unittest.TestCase):
    """Found on the sample: a recompile reset `base_sha` to the new HEAD, which would hide
    every unreviewed line landed since the first freeze from the accumulator."""

    def test_base_sha_survives_a_recompile_after_commits(self) -> None:
        p = Project(review={"every_lines": 100})
        try:
            first = p.frozen()["base_sha"]
            self.assertEqual(first, git(p.root, "rev-parse", "HEAD").strip())
            p.land("M1", lines=10)
            r = p.check("compile", "--spec", str(p.root / ".boil" / "milestones.json"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.frozen()["base_sha"], first)
        finally:
            p.close()


class ReviewModelPassthroughTest(unittest.TestCase):
    """A reviewer is an agent AND a model: with Codex out of quota the review runs as
    claude-code driven by an Ollama cloud model, which roborev selects by --model."""

    def test_agent_and_model_are_passed_to_roborev(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": "kimi-k3:cloud"})
        try:
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            call = next(c for c in p.calls() if c[0] == "review")
            self.assertIn("--agent", call); self.assertEqual(call[call.index("--agent") + 1], "claude-code")
            self.assertIn("--model", call); self.assertEqual(call[call.index("--model") + 1], "kimi-k3:cloud")
        finally:
            p.close()


class ReviewerPairTest(unittest.TestCase):
    """The reviewer is a *pair*. On 2026-09-04 roborev's `review_agent` said codex while its
    `review_model` still held the Ollama tag `glm-5.3:cloud` left over from the Ollama era,
    so every review died on `The 'glm-5.3:cloud' model is not supported when using Codex
    with a ChatGPT account.` — six milestones in a row, silently, because a failed review
    just means no second opinion arrives. These tests hold the pair together."""

    def test_an_ollama_tag_is_never_handed_to_codex(self) -> None:
        """The reported bug, at the point where it can still be caught."""
        p = Project(review={"every_lines": 0, "agent": "codex", "model": "glm-5.3:cloud"})
        try:
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            call = next(c for c in p.calls() if c[0] == "review")
            self.assertEqual(call[call.index("--agent") + 1], "codex")
            self.assertNotIn("--model", call)   # dropped, not forwarded into a 400
        finally:
            p.close()

    def test_codex_is_named_explicitly_so_roborevs_own_default_cannot_leak_in(self) -> None:
        """Passing a bare --agent is what let roborev fill the model itself."""
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            call = next(c for c in p.calls() if c[0] == "review")
            self.assertEqual(call[call.index("--agent") + 1], "codex")
        finally:
            p.close()

    def test_a_codex_quota_wall_falls_back_to_ollama_within_the_same_round(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"],
                        "down_error": "stream error: 429 you have reached your usage limit"})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            agents = [c[c.index("--agent") + 1] for c in p.calls() if c[0] == "review"]
            self.assertEqual(agents, ["codex", "claude-code"])
            backup = next(c for c in p.calls() if c[0] == "review" and "claude-code" in c)
            self.assertEqual(backup[backup.index("--model") + 1], "glm-5.3:cloud")
            ev = p.events()[-1]
            self.assertEqual(ev["event"], "CLEAN")          # the milestone still got reviewed
            self.assertEqual(ev["reviewer"], "claude-code")
            self.assertEqual(p.reviewer_state()["active"], "backup")
        finally:
            p.close()

    def test_the_cooldown_keeps_later_reviews_on_the_backup(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            n_before = len([c for c in p.calls() if c[0] == "review"])
            p.land("M2", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M2").returncode, 0)
            later = [c[c.index("--agent") + 1] for c in p.calls() if c[0] == "review"][n_before:]
            self.assertEqual(later, ["claude-code"])        # codex is not retried during cooldown
        finally:
            p.close()

    def test_the_loop_returns_to_codex_only_after_a_probe_says_codex_answers(self) -> None:
        """The cooldown is a lower bound; availability is what actually decides."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            st = p.reviewer_state()
            st["cooldown_until"] = "2000-01-01T00:00:00Z"    # the timer has run out
            st.pop("last_probe", None)
            (p.fake_dir / "reviewer.json").write_text(json.dumps(st))

            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M2", lines=5)
            p.review("review", "--milestone", "M2")
            self.assertEqual(p.reviewer_state()["active"], "backup")   # probe failed: stay put
            self.assertTrue(any(c[0] == "check-agents" for c in p.calls()))

            st = p.reviewer_state()
            st["cooldown_until"] = "2000-01-01T00:00:00Z"
            st.pop("last_probe", None)
            (p.fake_dir / "reviewer.json").write_text(json.dumps(st))
            p.scenario({})                                   # codex is back
            p.land("M3", lines=5)
            r = p.review("review", "--milestone", "M3")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.reviewer_state()["active"], "primary")
            self.assertEqual(p.events()[-1]["reviewer"], "codex")
        finally:
            p.close()


class ReviewerClassifyTest(unittest.TestCase):
    """A 400 for an impossible agent/model pair is a configuration bug. Reading it as a
    quota hit would route around it forever and hide the thing that needs fixing."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "boil_reviewer_uT", ROOT / "scripts" / "boil-reviewer.py")
        self.rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rv)

    def test_the_reported_400_is_not_a_quota_hit(self) -> None:
        self.assertEqual(self.rv.classify(
            "The 'glm-5.3:cloud' model is not supported when using Codex with a ChatGPT account."),
            "incompatible")

    def test_usage_and_rate_limits_are_quota_hits(self) -> None:
        for text in ("you (trbck) have reached your session usage limit",
                     "status 429 Too Many Requests", "rate_limit_error", "resource_exhausted"):
            self.assertEqual(self.rv.classify(text), "quota", text)

    def test_an_ordinary_crash_is_neither(self) -> None:
        self.assertEqual(self.rv.classify("exit status 1: segmentation fault"), "fail")

    def test_the_cooldown_ladder_lengthens_with_each_strike(self) -> None:
        s = {"active": "primary", "strikes": 0, "history": []}
        mins = []
        for _ in range(6):
            self.rv.start_cooldown(s, "429")
            mins.append(s["history"][-1]["cooldown_min"])
        self.assertEqual(mins, [15, 30, 60, 120, 240, 240])

    def test_only_claude_code_may_carry_an_ollama_tag(self) -> None:
        self.assertEqual(self.rv.repair({"agent": "codex", "model": "glm-5.3:cloud"})["model"], "")
        self.assertEqual(self.rv.repair({"agent": "claude-code", "model": "glm-5.3:cloud"})["model"],
                         "glm-5.3:cloud")
        self.assertEqual(self.rv.repair({"agent": "codex", "model": "gpt-5.1-codex"})["model"],
                         "gpt-5.1-codex")


class ReviewerFailureIsNeverGreenTest(unittest.TestCase):
    """A reviewer that never ran produces an empty finding list, and an empty finding list
    reads as CLEAN. That path turns a dead reviewer into a green milestone, which is worse
    than no review at all — the loop would believe a second model had blessed the code."""

    def test_a_dead_reviewer_is_a_skip_not_a_clean(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex", "claude-code"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ev = p.events()[-1]
            self.assertEqual(ev["event"], "SKIP")
            self.assertIn("failed", ev["reason"])
            self.assertEqual([t["outcome"] for t in ev["attempts"]], ["quota", "quota"])
        finally:
            p.close()

    def test_an_impossible_pair_stops_instead_of_hiding_behind_the_backup(self) -> None:
        """A 400 for an agent/model pair is a configuration bug. A green backup review would
        bury it, and the bug would outlive everyone who could remember setting it."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_model": "glm-5.3:cloud"}, "seal": False})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            ev = p.events()[-1]
            # The leak is sealed before the call, so the review succeeds on codex.
            self.assertEqual(ev["event"], "CLEAN", r.stdout + r.stderr)
            self.assertEqual(ev["reviewer"], "codex")
            sets = [c for c in p.calls() if c[:2] == ["config", "set"]]
            self.assertTrue(sets, "the incompatible global model should have been cleared")
            self.assertIn("review_model", sets[0])
        finally:
            p.close()

    def test_a_global_model_the_agent_can_run_is_left_alone(self) -> None:
        """The seal is narrow: it repairs an impossible default, not the user's choices."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_model": "gpt-5.1-codex"}})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            self.assertFalse([c for c in p.calls() if c[:2] == ["config", "set"]])
        finally:
            p.close()

    def test_a_fix_node_is_not_closed_on_a_review_that_never_ran(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"review_output": FINDINGS_HIGH})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 70)
            fix = next(m for m in p.frozen()["milestones"] if m["id"].endswith("-fix"))
            (p.root / "src" / "app.py").open("a").write("fixed = 1\n")
            (p.root / f"done-{fix['id']}.txt").write_text("x")
            git(p.root, "add", "-A")
            git(p.root, "commit", "-qm", "fix")
            p.check("run", "--milestone", fix["id"])
            p.scenario({"down_agents": ["codex", "claude-code"], "down_error": "429 usage limit",
                        "jobs": [], "shows": {}})
            r = p.review("close", "--milestone", fix["id"])
            self.assertEqual(r.returncode, 71, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "PENDING")
            self.assertNotIn("CLOSED", r.stdout)
        finally:
            p.close()


class FallbackReachesEveryPathTest(unittest.TestCase):
    """Three ways a reviewer can die without the fallback ever being consulted."""

    def test_an_adopted_job_that_died_does_not_stand_in_for_a_review(self) -> None:
        """The daemon's post-commit hook may already have enqueued a job for this HEAD. If
        that job failed, adopting it means the milestone waits forever on a reviewer that
        is already dead, and the backup is never asked."""
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            head = git(p.root, "rev-parse", "HEAD").strip()
            p.scenario({"jobs": [{"id": 90, "git_ref": head, "branch": "main", "job_type": "review",
                                  "status": "failed", "agent": "codex", "closed": False,
                                  "error": "stream error: 429 usage limit reached"}]})
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ev = p.events()[-1]
            self.assertEqual(ev["event"], "CLEAN")
            self.assertEqual(ev["reviewer"], "claude-code")     # the backup did the work
            self.assertEqual(p.reviewer_state()["limited"], {"agent": "codex", "model": ""})
        finally:
            p.close()

    def test_a_refusal_before_the_job_exists_still_reaches_the_backup(self) -> None:
        """roborev can refuse at the CLI, before enqueuing. No job means no error field,
        so the CLI's own output is the only evidence there is."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"refuse_agents": ["codex"],
                        "refuse_error": "error: 429 Too Many Requests"})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            agents = [c[c.index("--agent") + 1] for c in p.calls() if c[0] == "review"]
            self.assertEqual(agents, ["codex", "claude-code"])
            self.assertEqual(p.events()[-1]["reviewer"], "claude-code")
        finally:
            p.close()

    def test_a_codex_wall_does_not_push_an_unrelated_reviewer_onto_its_backup(self) -> None:
        """The state file is machine-wide. A codex quota says nothing about a project that
        reviews with something else, and forcing it onto a backup would be a fallback
        nobody asked for."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            self.assertEqual(p.reviewer_state()["active"], "backup")

            env = p.env()
            env["BOIL_REVIEW_AGENT"] = "gemini"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"),
                                "resolve", "--root", str(p.root), "--json"],
                               text=True, capture_output=True, env=env, cwd=str(p.root))
            self.assertEqual(json.loads(r.stdout)["agent"], "gemini", r.stdout + r.stderr)
            self.assertEqual(json.loads(r.stdout)["using"], "primary")
        finally:
            p.close()

    def test_a_green_review_elsewhere_does_not_shorten_the_limited_agents_ladder(self) -> None:
        """The strike count is the cooldown ladder for whichever agent hit the wall. A
        success by an unrelated reviewer says nothing about that wall."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            strikes = p.reviewer_state()["strikes"]
            self.assertGreaterEqual(strikes, 1)

            env = p.env()
            env["BOIL_REVIEW_AGENT"] = "gemini"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"),
                            "report", "--root", str(p.root), "--agent", "gemini",
                            "--outcome", "ok"], text=True, capture_output=True, env=env, cwd=str(p.root))
            after = p.reviewer_state()
            self.assertEqual(after["strikes"], strikes)
            self.assertEqual(after["limited"], {"agent": "codex", "model": ""})
        finally:
            p.close()

    def test_a_backup_on_the_same_agent_but_a_different_model_is_still_tried(self) -> None:
        """A project whose primary is claude-code has a backup that is also claude-code,
        on the Ollama tag. Deduplicating by agent alone would call that already tried and
        skip the only reviewer left."""
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": "",
                            "backup_agent": "claude-code", "backup_model": "glm-5.3:cloud"})
        try:
            p.scenario({"down_agents": ["claude-code"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            models = [(c[c.index("--model") + 1] if "--model" in c else "")
                      for c in p.calls() if c[0] == "review"]
            self.assertEqual(models, ["", "glm-5.3:cloud"], r.stdout + r.stderr)
        finally:
            p.close()


class DriftIsVisibleTest(unittest.TestCase):
    """The 2026-09-04 drift lived in roborev's own global config, not in `.boil`. A check
    that only validates boil's view would have passed the whole time it was broken."""

    def _reviewer(self, p: "Project", *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"), *args,
                               "--root", str(p.root)], text=True, capture_output=True,
                              env=env or p.env(), cwd=str(p.root))

    def test_status_reports_an_incompatible_roborev_global_pair(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "glm-5.3:cloud"}})
            out = self._reviewer(p, "status").stdout
            self.assertIn("roborev global config pairs", out)
            self.assertIn("glm-5.3:cloud", out)
        finally:
            p.close()

    def test_a_healthy_global_pair_is_silent(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            self.assertNotIn("roborev global config pairs", self._reviewer(p, "status").stdout)
        finally:
            p.close()

    def test_apply_repairs_the_global_pair(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "glm-5.3:cloud"}})
            self._reviewer(p, "apply")
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_agent"], "codex")
            self.assertEqual(cfg["review_model"], "")
        finally:
            p.close()

    def test_an_explicit_failed_probe_advances_the_ladder(self) -> None:
        """Otherwise `cooldown_until` stays in the past and every later resolve probes
        again immediately — the backoff would never actually happen."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            before = p.reviewer_state()
            self.assertEqual(before["limited"], {"agent": "codex", "model": ""})
            r = self._reviewer(p, "probe", "--force")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            after = p.reviewer_state()
            self.assertEqual(after["strikes"], before["strikes"] + 1)
            self.assertGreater(after["cooldown_until"], before["cooldown_until"])
        finally:
            p.close()

    def test_the_fast_tier_pair_drifts_on_its_own_and_is_checked_too(self) -> None:
        """`apply` writes both pairs, so the fast one can go bad by itself and break every
        review that asks for fast reasoning."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "",
                                   "review_agent_fast": "codex",
                                   "review_model_fast": "kimi-k3:cloud"}})
            out = self._reviewer(p, "status").stdout
            self.assertIn("review_model_fast", out)
            self.assertIn("kimi-k3:cloud", out)
        finally:
            p.close()

    def test_a_runnable_global_default_is_the_users_choice_and_is_left_alone(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "gpt-5.1-codex"}})
            self.assertNotIn("roborev global config pairs", self._reviewer(p, "status").stdout)
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_model"], "gpt-5.1-codex")
        finally:
            p.close()

    def test_the_fast_tier_is_judged_against_its_own_agent(self) -> None:
        """`review_agent_fast: claude-code` legitimately carries an Ollama tag. Judging
        that model against the *primary* agent would clear the very configuration the
        seal promises to leave alone."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "",
                                   "review_agent_fast": "claude-code",
                                   "review_model_fast": "glm-5.3:cloud"}})
            p.land("M1", lines=5)
            self.assertEqual(p.review("review", "--milestone", "M1").returncode, 0)
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_model_fast"], "glm-5.3:cloud")
        finally:
            p.close()

    def test_apply_leaves_a_deliberately_different_fast_reviewer_alone(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "",
                                   "review_agent_fast": "claude-code",
                                   "review_model_fast": "kimi-k3:cloud"}})
            self._reviewer(p, "apply")
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_agent_fast"], "claude-code")
            self.assertEqual(cfg["review_model_fast"], "kimi-k3:cloud")
            self.assertEqual(cfg["review_agent"], "codex")
        finally:
            p.close()

    def test_apply_still_repairs_a_fast_tier_that_is_itself_impossible(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "",
                                   "review_agent_fast": "codex",
                                   "review_model_fast": "glm-5.3:cloud"}})
            self._reviewer(p, "apply")
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_model_fast"], "")
        finally:
            p.close()


class ClassifyBreadthTest(unittest.TestCase):
    """`incompatible` refuses the fallback and tells the user to fix their config. It has
    to mean an impossible agent/model pair and nothing else."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "boil_reviewer_uT2", ROOT / "scripts" / "boil-reviewer.py")
        self.rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rv)

    def test_an_ordinary_400_is_not_a_configuration_bug(self) -> None:
        for text in ('{"type":"invalid_request_error","message":"maximum context length exceeded"}',
                     '{"type":"invalid_request_error","message":"tool call arguments were malformed"}'):
            self.assertEqual(self.rv.classify(text), "fail", text)

    def test_the_model_mismatch_signatures_still_read_as_incompatible(self) -> None:
        for text in ("The 'glm-5.3:cloud' model is not supported when using Codex with a ChatGPT account.",
                     "unknown model: foo", "no such model: bar", "model_not_found"):
            self.assertEqual(self.rv.classify(text), "incompatible", text)


class ResolverOutageTest(unittest.TestCase):
    """The resolver failing to load must not be the quietest possible failure. Before this
    was handled, a syntax error in boil-reviewer.py disabled every review on the machine
    and each milestone read as an ordinary skip — the exact shape of the bug that started
    all of this."""

    def _broken(self, p: "Project") -> Path:
        """A scripts/ copy whose resolver raises at import."""
        d = Path(p.tmp.name) / "brokenscripts"
        d.mkdir(exist_ok=True)
        for name in ("boil-review.py", "boil_common.py"):
            (d / name).write_text((ROOT / "scripts" / name).read_text())
        (d / "boil-reviewer.py").write_text("raise RuntimeError('deliberately broken')\n")
        return d / "boil-review.py"

    def test_a_broken_resolver_is_announced_and_still_gets_the_code_reviewed(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.land("M1", lines=5)
            r = subprocess.run([sys.executable, str(self._broken(p)), "review",
                                "--milestone", "M1", "--root", str(p.root)],
                               text=True, capture_output=True, env=p.env(), cwd=str(p.root))
            self.assertIn("failed to load", r.stderr)
            self.assertIn("RuntimeError", r.stderr)
            # No --agent at all: roborev's own default reviewer runs, which beats silence.
            call = next(c for c in p.calls() if c[0] == "review")
            self.assertNotIn("--agent", call)
            self.assertEqual(p.events()[-1]["event"], "CLEAN", r.stdout + r.stderr)
        finally:
            p.close()

    def test_apply_never_writes_the_backup_into_review_agent(self) -> None:
        """roborev's own quota fallback is keyed on `review_agent` being the primary.
        Writing the backup there during a cooldown leaves the daemon with nothing to
        return to, so every path that does not go through boil stays on the backup until
        a person notices."""
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"down_agents": ["codex"], "down_error": "429 usage limit"})
            p.land("M1", lines=5)
            p.review("review", "--milestone", "M1")
            self.assertEqual(p.reviewer_state()["active"], "backup")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"), "apply",
                            "--root", str(p.root)], text=True, capture_output=True,
                           env=p.env(), cwd=str(p.root))
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_agent"], "codex")
            # Nothing to clear, so nothing is written: an unset global stays unset.
            self.assertEqual(cfg.get("review_model", ""), "")
            self.assertEqual(cfg["review_backup_agent"], "claude-code")
            self.assertEqual(cfg["review_backup_model"], "glm-5.3:cloud")
        finally:
            p.close()


class ApplyIsAllOrNothingTest(unittest.TestCase):
    """`apply` writes roborev's global reviewer policy. A half-written pair is the exact
    drift this whole change exists to prevent, so it must not be a state apply can leave
    behind — and an empty boil-level model must not wipe a global one that works."""

    def _apply(self, p: "Project") -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"),
                               "apply", "--root", str(p.root)],
                              text=True, capture_output=True, env=p.env(), cwd=str(p.root))

    def test_a_runnable_global_model_survives_an_empty_boil_preference(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "gpt-5.1-codex"}})
            self._apply(p)
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_model"], "gpt-5.1-codex")
        finally:
            p.close()

    def test_an_impossible_global_model_is_still_cleared(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": "glm-5.3:cloud"}})
            self._apply(p)
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_model"], "")
        finally:
            p.close()

    def test_a_failure_partway_through_leaves_the_config_as_it_was(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "gemini", "review_model": "",
                                   "review_backup_agent": "gemini"},
                        "config_set_fails": ["review_backup_agent"]})
            r = self._apply(p)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("rolled back", r.stderr)
            cfg = json.loads((p.fake_dir / "scenario.json").read_text())["config"]
            self.assertEqual(cfg["review_agent"], "gemini")   # put back, not left as codex
        finally:
            p.close()


# At the very bottom on purpose. This guard used to sit mid-file, so `python
# tests/test_review.py` executed and exited before the classes below it were even defined
# — a safety net that looked present and never ran, which is precisely the failure mode
# these tests exist to catch.
if __name__ == "__main__":
    unittest.main()


class IncompatiblePairStopsTest(unittest.TestCase):
    """The no-fallback stop for an impossible pair, exercised directly. A green backup
    review would bury the configuration bug, and the bug would then outlive everyone who
    could remember setting it."""

    def test_an_impossible_pair_is_not_routed_around(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "codex", "model": ""})
        try:
            # The seal cannot help here: roborev reports the 400 without a global to clear.
            p.scenario({"down_agents": ["codex"],
                        "down_error": "The 'x:y' model is not supported when using Codex "
                                      "with a ChatGPT account."})
            p.land("M1", lines=5)
            r = p.review("review", "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            agents = [c[c.index("--agent") + 1] for c in p.calls() if c[0] == "review"]
            self.assertEqual(agents, ["codex"])        # the backup was never asked
            ev = p.events()[-1]
            self.assertEqual(ev["event"], "SKIP")
            self.assertEqual([t["outcome"] for t in ev["attempts"]], ["incompatible"])
            self.assertNotEqual(p.reviewer_state().get("active"), "backup")
            self.assertIn("impossible pair", r.stderr)
        finally:
            p.close()

    def test_a_ledger_failure_does_not_cost_the_caller_its_review(self) -> None:
        """The ledger entry matters more than the cooldown bookkeeping: losing the job id
        means an open roborev job and the same milestone reviewed and billed again."""
        p = Project(review={"every_lines": 0})
        try:
            env = p.env()
            env["BOIL_REVIEWER_STATE"] = "/proc/definitely/not/writable/reviewer.json"
            p.land("M1", lines=5)
            r = subprocess.run([sys.executable, str(REVIEW), "review", "--milestone", "M1",
                                "--root", str(p.root)], text=True, capture_output=True,
                               env=env, cwd=str(p.root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.events()[-1]["event"], "CLEAN", r.stdout + r.stderr)
        finally:
            p.close()


class PolicyDriftNoteTest(unittest.TestCase):
    """A project may legitimately pin a reviewer of its own. What it may not do is keep a
    pin whose *meaning* changed underneath it: ttengine pinned `claude-code` while the
    machine's global model was an Ollama tag, so the pin meant "review on Ollama". Emptying
    that global silently turned the same pin into "review on real Claude" — another
    provider, another bill, nothing in the config touched, and the pair still perfectly
    coherent, so no existing check said a word."""

    def _status(self, p: "Project") -> str:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-reviewer.py"),
                            "status", "--root", str(p.root)],
                           text=True, capture_output=True, env=p.env(), cwd=str(p.root))
        return r.stdout

    def test_a_pin_that_differs_from_the_machine_policy_is_noted(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": ""})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            out = self._status(p)
            self.assertRegex(out, r"(?m)^note\s")
            self.assertIn("claude-code", out)
            self.assertIn("codex", out)
        finally:
            p.close()

    def test_the_note_says_what_a_bare_backup_agent_actually_costs(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": ""})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            self.assertIn("not on Ollama", self._status(p))
        finally:
            p.close()

    def test_a_pin_carrying_its_own_model_is_noted_without_the_ollama_advice(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": "glm-5.3:cloud"})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            out = self._status(p)
            self.assertRegex(out, r"(?m)^note\s")
            self.assertNotIn("not on Ollama", out)
        finally:
            p.close()

    def test_a_project_that_follows_the_policy_is_silent(self) -> None:
        p = Project(review={"every_lines": 0, "agent": "codex", "model": ""})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            self.assertNotRegex(self._status(p), r"(?m)^note\s")
        finally:
            p.close()

    def test_an_unpinned_project_is_silent(self) -> None:
        p = Project(review={"every_lines": 0})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            self.assertNotRegex(self._status(p), r"(?m)^note\s")
        finally:
            p.close()

    def test_the_note_never_fails_the_doctor(self) -> None:
        """It has to pass, or people learn to ignore a red doctor."""
        p = Project(review={"every_lines": 0, "agent": "claude-code", "model": ""})
        try:
            p.scenario({"config": {"review_agent": "codex", "review_model": ""}})
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-doctor.py"),
                                "--root", str(p.root), "--json"],
                               text=True, capture_output=True, env=p.env(), cwd=str(p.root))
            checks = json.loads(r.stdout)["checks"]
            pair = next(c for c in checks if c["code"] == "reviewer-pair")
            self.assertTrue(pair["ok"], pair)
            self.assertIn("pins agent", pair["message"])
        finally:
            p.close()
