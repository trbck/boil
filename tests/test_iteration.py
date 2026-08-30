"""W1 — one iteration is two commands: `boil-check.py prepare` and `boil-check.py score`.

Why: the driver used to run seven commands in order from memory and paste the EVIDENCE
line by hand. Every step was tokens and a place to deviate — the author broke the order
twice on a four-milestone toy. Now `prepare` hands out the packet and `score` owns every
write that follows an attempt: audit, verdict, the goal box's tick, spend, the tick record,
the status line. No EVIDENCE line is ever LLM-written. Goal boxes are bound to milestones at
compile time — an unbound must-have is not frozen.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "boil-check.py"
NOW = ROOT / "scripts" / "boil-now.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)


GOAL = """# Goal

**One-line:** two files exist

## Success checklist
- [ ] the first marker exists
- [ ] the second marker exists
- [ ] an operator-only box

## Requirements understanding
| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---|---|
| a | b | c | 99 | none |

## How the user will see this works
ls *.txt
"""


class Project:
    def __init__(self, goal: str = GOAL, milestones: list[dict] | None = None, git: bool = True,
                 wire_guard: bool = True) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".boil").mkdir()
        if wire_guard:
            (self.root / ".claude").mkdir()
            (self.root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
                {"matcher": "Write|Edit|MultiEdit|Bash",
                 "hooks": [{"type": "command", "command": f"python3 {ROOT / 'scripts' / 'boil-guard.py'} --root {self.root}"}]}]}}))
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_guard.py").write_text("def test_ok():\n    assert True\n")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("x = 1\n")
        (self.root / ".boil" / "goal.md").write_text(goal)
        (self.root / ".boil" / "budget.json").write_text(json.dumps({"goal_usd": 5.0, "spent_usd": 0.0}))
        if git:
            for cmd in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                        ["add", "-A"], ["commit", "-qm", "init"]):
                subprocess.run(["git", "-C", str(self.root), *cmd], check=True, capture_output=True)
        self.milestones = milestones if milestones is not None else [
            {"id": "M1", "title": "first marker", "box": "the first marker exists",
             "check": "test -f one.txt", "kind": "artifact", "protect": ["tests"], "proxy_gap": "existence"},
            {"id": "M2", "title": "second marker", "box": "the second marker exists",
             "check": "test -f two.txt", "kind": "artifact", "after": ["M1"], "proxy_gap": "existence"},
        ]

    def spec(self, **top) -> Path:
        body = {"budget_usd": 5.0, "cap": 4, "stall": 2, "determinism_runs": 1,
                "review": {"enabled": False}, "milestones": self.milestones}
        body.update(top)
        p = self.root / ".boil" / "milestones.json"
        p.write_text(json.dumps(body))
        return p

    def compile(self) -> subprocess.CompletedProcess[str]:
        return run(CHECK, "compile", "--root", str(self.root), "--spec", str(self.spec()))

    def check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(CHECK, *args, "--root", str(self.root))

    def goal(self) -> str:
        return (self.root / ".boil" / "goal.md").read_text()

    def attempts(self) -> list[dict]:
        p = self.root / ".boil" / "checks" / "attempts.jsonl"
        return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.is_file() else []

    def close(self) -> None:
        self.tmp.cleanup()


class CompileBindsBoxesTest(unittest.TestCase):
    def test_compile_stamps_the_milestone_tag_onto_its_goal_box(self) -> None:
        p = Project()
        try:
            r = p.compile()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("- [ ] the first marker exists {#M1}", p.goal())
            self.assertIn("- [ ] the second marker exists {#M2}", p.goal())
            self.assertIn("- [ ] an operator-only box\n", p.goal())          # untouched
        finally:
            p.close()

    def test_a_title_that_equals_the_box_text_binds_without_a_box_field(self) -> None:
        p = Project(milestones=[{"id": "M1", "title": "the first marker exists", "check": "test -f one.txt",
                                 "kind": "artifact"}])
        try:
            self.assertEqual(p.compile().returncode, 0)
            self.assertIn("- [ ] the first marker exists {#M1}", p.goal())
        finally:
            p.close()

    def test_an_unbound_must_have_is_rejected_when_the_goal_has_boxes(self) -> None:
        p = Project(milestones=[{"id": "M9", "title": "something else", "check": "test -f nine.txt",
                                 "kind": "artifact"}])
        try:
            r = p.compile()
            self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
            self.assertIn("unbound", r.stdout)
            self.assertNotIn("{#M9}", p.goal())
        finally:
            p.close()

    def test_a_nice_to_have_needs_no_box(self) -> None:
        p = Project(milestones=[{"id": "M1", "title": "the first marker exists", "check": "test -f one.txt"},
                                {"id": "N1", "title": "bonus", "check": "test -f bonus.txt", "must_have": False}])
        try:
            self.assertEqual(p.compile().returncode, 0)
        finally:
            p.close()

    def test_a_goal_without_boxes_does_not_enforce_binding(self) -> None:
        p = Project(goal="# Goal\n**One-line:** x\n", milestones=[{"id": "M1", "title": "t", "check": "test -f a"}])
        try:
            self.assertEqual(p.compile().returncode, 0)
        finally:
            p.close()

    def test_compile_is_idempotent_on_tags(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            once = p.goal()
            self.assertEqual(p.compile().returncode, 0)
            self.assertEqual(p.goal(), once)
        finally:
            p.close()


class PrepareTest(unittest.TestCase):
    def test_prepare_hands_out_the_packet_and_records_the_iteration(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["milestone"], "M1")
            self.assertEqual(out["attempt"], 1)
            self.assertTrue((p.root / out["packet"]).is_file())
            self.assertIn("guard", out)
            it = json.loads((p.root / ".boil" / "checks" / "iteration.json").read_text())
            self.assertEqual(it["milestone"], "M1")
            self.assertTrue(it["head"])
        finally:
            p.close()

    def test_prepare_dry_run_writes_nothing(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare", "--dry-run")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["milestone"], "M1")
            self.assertFalse((p.root / ".boil" / "checks" / "iteration.json").exists())
            self.assertFalse((p.root / ".boil" / "dispatch").exists())
        finally:
            p.close()

    def test_prepare_on_a_finished_goal_says_done(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            for name in ("one.txt", "two.txt"):
                (p.root / name).write_text("x")
                self.assertEqual(p.check("prepare").returncode, 0)
                self.assertEqual(p.check("score", "--milestone", json.loads(p.check("prepare").stdout)["milestone"],
                                         "--no-review").returncode, 0)
            r = p.check("prepare")
            self.assertEqual(r.returncode, 0)
            self.assertTrue(json.loads(r.stdout)["done"])
        finally:
            p.close()


class ScoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.p = Project()
        self.assertEqual(self.p.compile().returncode, 0)

    def tearDown(self) -> None:
        self.p.close()

    def score(self, mid: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.p.check("score", "--milestone", mid, "--no-review", *extra)

    def test_a_pass_ticks_the_bound_box_with_evidence_and_owns_the_spend(self) -> None:
        self.assertEqual(self.p.check("prepare").returncode, 0)
        (self.p.root / "one.txt").write_text("x")
        r = self.score("M1", "--spent-usd", "0.40")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        goal = self.p.goal()
        self.assertRegex(goal, r"- \[x\] the first marker exists — EVIDENCE: `test -f one\.txt` -> exit 0 \| \d{4}-\d{2}-\d{2} \| auto \{#M1\}")
        self.assertIn("- [ ] the second marker exists {#M2}", goal)
        last = self.p.attempts()[-1]
        self.assertEqual(last["result"], "PASS")
        self.assertEqual(last["check"], "test -f one.txt")
        self.assertIn("EVIDENCE:", last["evidence"])
        self.assertIn("milestones 1/2 green", r.stdout.strip().splitlines()[-1])
        budget = json.loads((self.p.root / ".boil" / "budget.json").read_text())
        self.assertAlmostEqual(budget["spent_usd"], 0.40)
        progress = (self.p.root / ".boil" / "progress.jsonl").read_text()
        self.assertIn('"iteration": "M1#1"', progress)

    def test_a_failure_returns_the_counterexample_and_a_repeat_stalls(self) -> None:
        self.assertEqual(self.p.check("prepare").returncode, 0)
        r = self.score("M1")
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        self.assertIn("counterexample", r.stdout)
        self.assertIn("- [ ] the first marker exists {#M1}", self.p.goal())
        self.assertEqual(self.p.check("prepare").returncode, 0)
        r = self.score("M1")
        self.assertEqual(r.returncode, 20, r.stdout + r.stderr)

    def test_an_audit_finding_scores_the_attempt_as_a_failure_even_if_the_check_passes(self) -> None:
        self.assertEqual(self.p.check("prepare").returncode, 0)
        (self.p.root / "one.txt").write_text("x")
        (self.p.root / "src" / "app.py").write_text("import pytest\n@pytest.mark.skip\ndef test_x(): pass\n")
        r = self.score("M1")
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        self.assertIn("audit", r.stdout.lower())
        self.assertEqual(self.p.attempts()[-1]["result"], "FAIL")
        self.assertIn("- [ ] the first marker exists {#M1}", self.p.goal())

    def test_score_refuses_a_milestone_that_was_not_prepared(self) -> None:
        r = self.score("M2")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("prepare", r.stdout + r.stderr)

    def test_score_runs_the_reviewer_after_a_pass_unless_told_not_to(self) -> None:
        self.assertEqual(self.p.check("prepare").returncode, 0)
        (self.p.root / "one.txt").write_text("x")
        r = self.p.check("score", "--milestone", "M1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        events = (self.p.root / ".boil" / "checks" / "reviews.jsonl").read_text()
        self.assertIn('"milestone": "M1"', events)


class NowNextTest(unittest.TestCase):
    def test_now_names_the_next_milestone_and_the_two_commands(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = run(NOW, "--root", str(p.root), "--write")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            now = (p.root / ".boil" / "NOW.md").read_text()
            self.assertIn("M1", now.split("**Next:**")[1])
            self.assertIn("prepare", now.split("**Next:**")[1])
            self.assertIn("score", now.split("**Next:**")[1])
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()


class CompileIsAtomicTest(unittest.TestCase):
    """Found on the sample: a compile that rejected every milestone (new binding rule) wrote
    an empty frozen.json, destroying the previous freeze and its carry-forward records."""

    def test_a_compile_with_a_rejection_leaves_the_previous_freeze_untouched(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)
            before = (p.root / ".boil" / "checks" / "frozen.json").read_text()
            p.milestones.append({"id": "M9", "title": "nowhere", "check": "test -f nine.txt"})
            r = p.compile()
            self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
            self.assertEqual((p.root / ".boil" / "checks" / "frozen.json").read_text(), before)
            self.assertIn("nothing frozen", r.stdout)
        finally:
            p.close()


class PrepareGuardTest(unittest.TestCase):
    """W2: no packet without the guard. The packet's 'you cannot run the check' was prose;
    prepare makes it a precondition."""

    def test_prepare_refuses_without_a_wired_guard(self) -> None:
        p = Project(wire_guard=False)
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--wire-guard", r.stdout + r.stderr)
            self.assertFalse((p.root / ".boil" / "dispatch").exists())
        finally:
            p.close()

    def test_wire_guard_merges_the_hook_and_prepare_proceeds(self) -> None:
        p = Project(wire_guard=False)
        try:
            (p.root / ".claude").mkdir()
            (p.root / ".claude" / "settings.json").write_text(json.dumps(
                {"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo other"}]}]}}))
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare", "--wire-guard")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1])["guard"], "wired")
            settings = json.loads((p.root / ".claude" / "settings.json").read_text())
            self.assertEqual(settings["permissions"], {"allow": ["Bash(ls)"]})              # untouched
            cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]]
            self.assertIn("echo other", cmds)
            self.assertTrue(any("boil-guard.py" in c for c in cmds))
            self.assertEqual(p.check("prepare", "--wire-guard").returncode, 0)             # idempotent
            settings2 = json.loads((p.root / ".claude" / "settings.json").read_text())
            self.assertEqual(settings, settings2)
        finally:
            p.close()

    def test_allow_unguarded_is_an_explicit_choice_that_is_warned(self) -> None:
        p = Project(wire_guard=False)
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare", "--allow-unguarded")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("prose only", r.stderr)
        finally:
            p.close()


class ReportTest(unittest.TestCase):
    """W4: one page per goal, computed from the ledgers — the same numbers the bench records."""

    def _drive(self, p: Project) -> None:
        self.assertEqual(p.compile().returncode, 0)
        self.assertEqual(p.check("prepare").returncode, 0)
        self.assertEqual(p.check("score", "--milestone", "M1", "--no-review", "--spent-usd", "0.30").returncode, 10)
        (p.root / "one.txt").write_text("x")
        self.assertEqual(p.check("prepare").returncode, 0)
        self.assertEqual(p.check("score", "--milestone", "M1", "--no-review", "--spent-usd", "0.20").returncode, 0)
        (p.root / "two.txt").write_text("x")
        self.assertEqual(p.check("prepare").returncode, 0)
        self.assertEqual(p.check("score", "--milestone", "M2", "--no-review", "--spent-usd", "0.10").returncode, 0)

    def test_report_json_carries_the_effectiveness_numbers(self) -> None:
        p = Project()
        try:
            self._drive(p)
            r = p.check("report", "--json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            d = json.loads(r.stdout)
            self.assertEqual(d["green"], 2)
            self.assertEqual(d["total"], 2)
            self.assertEqual(d["attempts"], {"M1": 2, "M2": 1})
            self.assertEqual(d["first_pass_rate"], 0.5)
            self.assertAlmostEqual(d["spend_usd"], 0.60)
            self.assertAlmostEqual(d["usd_per_green_box"], 0.30)
            self.assertEqual(d["first_pass_failed"], ["M1"])
            self.assertEqual(d["compile"]["rejected"], 0)
            self.assertIn("review", d)
        finally:
            p.close()

    def test_report_markdown_is_one_page_with_a_milestone_table(self) -> None:
        p = Project()
        try:
            self._drive(p)
            r = p.check("report")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("| M1 |", r.stdout)
            self.assertIn("first-attempt pass rate", r.stdout)
            self.assertIn("$ per green box", r.stdout)
        finally:
            p.close()

    def test_compile_rejections_are_counted(self) -> None:
        p = Project(milestones=[{"id": "M1", "title": "the first marker exists", "check": "test -f one.txt"},
                                {"id": "M9", "title": "nowhere", "check": "test -f nine.txt"}])
        try:
            self.assertEqual(p.compile().returncode, 60)
            p.milestones.pop()
            self.assertEqual(p.compile().returncode, 0)
            d = json.loads(p.check("report", "--json").stdout)
            self.assertEqual(d["compile"]["rejected"], 1)
            self.assertEqual(d["compile"]["runs"], 2)
        finally:
            p.close()


class PrepareEconomicsTest(unittest.TestCase):
    """From the first real bench run (2026-08-30): an already_green guard cost a $1.03
    implementer call, and a $1.57 attempt was refused scoring because it crossed the budget.
    Money is committed at dispatch, so the gates that save it live in `prepare`."""

    def test_an_already_green_guard_is_scored_without_a_dispatch(self) -> None:
        p = Project(milestones=[
            {"id": "G", "title": "the first marker exists", "check": "test -d src", "already_green": True},
            {"id": "M2", "title": "the second marker exists", "check": "test -f two.txt", "after": ["G"]}])
        try:
            self.assertEqual(p.compile().returncode, 0)
            r = p.check("prepare")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(out["milestone"], "G")
            self.assertFalse(out["dispatch"])
            self.assertIn("already_green", out["reason"])
            self.assertFalse((p.root / ".boil" / "dispatch").exists())
            self.assertEqual(p.check("score", "--milestone", "G", "--no-review").returncode, 0)
            out2 = json.loads(p.check("prepare").stdout.strip().splitlines()[-1])
            self.assertEqual(out2["milestone"], "M2")
            self.assertTrue(out2["dispatch"])
        finally:
            p.close()

    def test_a_paid_attempt_is_always_scored_and_the_next_prepare_refuses_on_budget(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)               # budget 5.0
            self.assertEqual(p.check("prepare").returncode, 0)
            (p.root / "one.txt").write_text("x")
            r = p.check("score", "--milestone", "M1", "--no-review", "--spent-usd", "6.00")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)   # the check ran, the box is ticked
            self.assertIn("- [x] the first marker exists", p.goal())
            self.assertIn("BUDGET", r.stdout)                          # and the overrun is said
            r = p.check("prepare")
            self.assertEqual(r.returncode, 40, r.stdout + r.stderr)
            self.assertIn("BUDGET", r.stdout)
            self.assertFalse((p.root / ".boil" / "dispatch" / "M2.md").exists())
        finally:
            p.close()

    def test_prepare_projects_the_next_attempt_from_the_running_average(self) -> None:
        p = Project()
        try:
            self.assertEqual(p.compile().returncode, 0)               # budget 5.0
            self.assertEqual(p.check("prepare").returncode, 0)
            (p.root / "one.txt").write_text("x")
            self.assertEqual(p.check("score", "--milestone", "M1", "--no-review", "--spent-usd", "3.00").returncode, 0)
            r = p.check("prepare")                                     # 3.00 spent + ~3.00 expected > 5.00
            self.assertEqual(r.returncode, 40, r.stdout + r.stderr)
            self.assertIn("expected", r.stdout)
        finally:
            p.close()
