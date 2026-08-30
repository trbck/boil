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
if cmd == "review":
    out = sc.get("review_outputs", []).pop(0) if sc.get("review_outputs") else sc.get("review_output", "No issues found.\nSummary: ok")
    jid = max([j["id"] for j in sc.get("jobs", [])] + [100]) + 1
    # real roborev (v0.65): a --since range job records git_ref as "<base>..<head>" and
    # job_type "range"; a single-commit job records the sha and job_type "review".
    if "--since" in sys.argv:
        ref, jt = sys.argv[sys.argv.index("--since") + 1] + ".." + head(sys.argv), "range"
    else:
        ref, jt = head(sys.argv), "review"
    sc.setdefault("jobs", []).append({"id": jid, "git_ref": ref, "branch": "main", "job_type": jt,
                                      "status": "done", "agent": "fake", "closed": False,
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
        env.pop("BOIL_ROBOREV", None)
        return env

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


if __name__ == "__main__":
    unittest.main()


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
