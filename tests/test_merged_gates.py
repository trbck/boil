"""Tests for the merged outer/inner loop gates.

These cover the mechanisms added when gate was folded into boil: the three
convergence brakes, the goal-size lint, the tier field, the termination gate,
and migration. Every one of them exists because the equivalent prose rule in
SKILL.md provably never fired — so each needs a test proving the script does.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

GOAL = """# Goal
**One-line:** Ship the thing.

## Success checklist
- [ ] The endpoint returns 201.
- [ ] The list view renders.

## How the user will see this works
Run `curl -XPOST localhost:8000/orders`.
"""

TICKET = """---
id: T-0001
title: {title}
type: {ttype}
specialty: general
status: {status}
priority: P1
proof_strategy: verification-only
tier: {tier}
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
answer_key:
  kind: document
  ref: ACCEPTANCE.md
  authored_by: orchestrator
  frozen_at: 2026-06-10T09:31:00Z
  frozen_sha: ""
  protected: true
working_on: ""
---

## Context
{body}
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class Workspace:
    """A throwaway project root with `.boil/` state."""

    def __init__(self, stack: unittest.TestCase, goal: str = GOAL) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        stack.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.boil = self.root / ".boil"
        (self.boil / "tickets").mkdir(parents=True)
        (self.boil / "goal.md").write_text(goal, encoding="utf-8")

    def ticket(self, name: str = "T-0001.md", *, title: str = "Do the thing",
               ttype: str = "test", status: str = "open", tier: str = "T1",
               body: str = "Nothing risky.") -> None:
        (self.boil / "tickets" / name).write_text(
            TICKET.format(title=title, ttype=ttype, status=status, tier=tier, body=body),
            encoding="utf-8")

    def green(self, n: int) -> None:
        """Tick the first n checkboxes, with evidence."""
        lines = (self.boil / "goal.md").read_text(encoding="utf-8").splitlines()
        done = 0
        for i, ln in enumerate(lines):
            if ln.startswith("- [ ]") and done < n:
                lines[i] = ln.replace("- [ ]", "- [x]", 1) + \
                    " EVIDENCE: `pytest -q` -> 4 passed | 2026-08-28 | auto"
                done += 1
        (self.boil / "goal.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def brakes(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(str(SCRIPTS / "boil-brakes.py"), *args, "--root", str(self.root))

    def tick(self, iteration: str, spent: float | None = None) -> None:
        args = ["tick", "--iteration", iteration]
        if spent is not None:
            args += ["--spent-usd", str(spent)]
        self.brakes(*args)

    def lint(self) -> subprocess.CompletedProcess[str]:
        return run(str(SCRIPTS / "ticket-lint.py"), "--root", str(self.root), "--json")


class StallBrakeTest(unittest.TestCase):
    def test_three_flat_iterations_stop_the_loop(self) -> None:
        w = Workspace(self)
        for i in range(1, 4):
            w.tick(f"iter-00{i}")
        proc = w.brakes("check")
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("not converging", proc.stdout)

    def test_two_flat_iterations_do_not(self) -> None:
        w = Workspace(self)
        for i in range(1, 3):
            w.tick(f"iter-00{i}")
        self.assertEqual(w.brakes("check").returncode, 0)

    def test_progress_resets_the_counter(self) -> None:
        w = Workspace(self)
        w.tick("iter-001")
        w.tick("iter-002")
        w.green(1)
        w.tick("iter-003")
        self.assertEqual(w.brakes("check").returncode, 0)

    def test_a_finished_goal_is_completion_not_a_stall(self) -> None:
        """All boxes green for three iterations means done, not stuck."""
        w = Workspace(self)
        w.green(2)
        for i in range(1, 4):
            w.tick(f"iter-00{i}")
        self.assertEqual(w.brakes("check").returncode, 0)

    def test_backfilled_records_do_not_count_as_flat(self) -> None:
        """boil-migrate seeds green=null: an iteration happened, unknown outcome."""
        w = Workspace(self)
        (w.boil / "progress.jsonl").write_text(
            "".join(json.dumps({"iteration": f"iter-00{i}", "green": None,
                                "total": 2, "backfilled": True}) + "\n" for i in range(1, 5)),
            encoding="utf-8")
        self.assertEqual(w.brakes("check").returncode, 0)


class WipBrakeTest(unittest.TestCase):
    def test_over_the_limit_restricts(self) -> None:
        w = Workspace(self)
        for i in range(1, 7):
            w.ticket(f"T-000{i}.md")
        proc = w.brakes("check", "--wip", "5")
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("WIP limit", proc.stdout)

    def test_blocked_tickets_do_not_count_against_wip(self) -> None:
        w = Workspace(self)
        for i in range(1, 7):
            w.ticket(f"T-000{i}.md", status="blocked")
        self.assertEqual(w.brakes("check", "--wip", "5").returncode, 0)


class BudgetBrakeTest(unittest.TestCase):
    def test_sixty_percent_restricts(self) -> None:
        w = Workspace(self)
        (w.boil / "budget.json").write_text(json.dumps({"goal_usd": 10}), encoding="utf-8")
        w.tick("iter-001", spent=7.0)
        proc = w.brakes("check", "--stall", "99")
        self.assertEqual(proc.returncode, 2, proc.stdout)

    def test_spent_budget_stops(self) -> None:
        w = Workspace(self)
        (w.boil / "budget.json").write_text(json.dumps({"goal_usd": 10}), encoding="utf-8")
        w.tick("iter-001", spent=11.0)
        proc = w.brakes("check", "--stall", "99")
        self.assertEqual(proc.returncode, 3, proc.stdout)

    def test_spend_accumulates_across_ticks(self) -> None:
        w = Workspace(self)
        (w.boil / "budget.json").write_text(json.dumps({"goal_usd": 10}), encoding="utf-8")
        w.tick("iter-001", spent=3.0)
        w.tick("iter-002", spent=3.0)
        spent = json.loads((w.boil / "budget.json").read_text())["spent_usd"]
        self.assertAlmostEqual(spent, 6.0)


class GoalLintTest(unittest.TestCase):
    def _codes(self, w: Workspace) -> set[str]:
        return {i["code"] for i in json.loads(w.lint().stdout)["issues"]}

    def test_a_goal_with_too_many_checkboxes_is_rejected(self) -> None:
        boxes = "\n".join(f"- [ ] thing {i}" for i in range(9))
        w = Workspace(self, goal=f"# Goal\n\n## Success checklist\n{boxes}\n\n"
                                 "## How the user will see this works\nRun it.\n")
        self.assertIn("goal-too-many-boxes", self._codes(w))

    def test_a_project_sized_goal_is_rejected(self) -> None:
        filler = "\n".join(f"Context line {i} explaining more scope." for i in range(120))
        w = Workspace(self, goal=GOAL + "\n## Notes\n" + filler)
        self.assertIn("goal-too-large", self._codes(w))

    def test_a_goal_with_no_demo_target_is_rejected(self) -> None:
        w = Workspace(self, goal="# Goal\n\n## Success checklist\n- [ ] It works.\n")
        self.assertIn("goal-no-demo-target", self._codes(w))

    def test_a_feature_sized_goal_passes(self) -> None:
        w = Workspace(self)
        w.ticket()
        self.assertEqual(w.lint().returncode, 0, w.lint().stdout)


class TierLintTest(unittest.TestCase):
    def _codes(self, w: Workspace) -> set[str]:
        return {i["code"] for i in json.loads(w.lint().stdout)["issues"]}

    def test_tier_is_required(self) -> None:
        w = Workspace(self)
        w.ticket()
        path = w.boil / "tickets" / "T-0001.md"
        path.write_text(path.read_text().replace("tier: T1\n", ""), encoding="utf-8")
        self.assertIn("missing-field", self._codes(w))

    def test_an_invalid_tier_is_rejected(self) -> None:
        w = Workspace(self)
        w.ticket(tier="T9")
        self.assertIn("bad-tier", self._codes(w))

    def test_high_blast_radius_work_at_a_low_tier_warns(self) -> None:
        w = Workspace(self)
        w.ticket(title="Add Stripe billing webhook", tier="T1")
        self.assertIn("tier-underscoped", self._codes(w))

    def test_the_warning_does_not_fire_on_substrings(self) -> None:
        """`auth` must not match `authored_by` in every ticket's answer key."""
        w = Workspace(self)
        w.ticket(title="Tidy the changelog", tier="T1")
        self.assertNotIn("tier-underscoped", self._codes(w))


class AnswerKeyByTierTest(unittest.TestCase):
    """The answer-key contract binds at T3, not on every behavior ticket.

    Before the merge, `ticket-lint` demanded an externally-authored, frozen,
    hash-protected key for every bug/feature/test/refactor/perf ticket — which
    forced the full adversarial protocol onto one-line fixes. That is what made
    the loop pay T3 everywhere. These tests pin the tier-aware boundary.
    """

    NO_KEY = """---
id: T-0001
title: {title}
type: feature
specialty: backend
status: open
priority: P1
proof_strategy: red-green
tier: {tier}
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
answer_key:
  kind: none
  reason: "proof is the project's own suite"
working_on: ""
---

## Context
{title}
"""

    def _codes(self, tier: str, title: str = "Add a list filter") -> set[str]:
        w = Workspace(self)
        (w.boil / "tickets" / "T-0001.md").write_text(
            self.NO_KEY.format(tier=tier, title=title), encoding="utf-8")
        return {i["code"] for i in json.loads(w.lint().stdout)["issues"]}

    def test_a_t1_feature_needs_no_frozen_answer_key(self) -> None:
        self.assertNotIn("answer-key-none-behavior", self._codes("T1"))

    def test_a_t2_feature_needs_no_frozen_answer_key(self) -> None:
        self.assertNotIn("answer-key-none-behavior", self._codes("T2"))

    def test_a_t3_feature_still_requires_external_ground_truth(self) -> None:
        self.assertIn("answer-key-none-behavior", self._codes("T3"))

    def test_a_missing_tier_is_treated_as_adversarial(self) -> None:
        """A ticket must not dodge the key requirement by omitting the field."""
        w = Workspace(self)
        text = self.NO_KEY.format(tier="T1", title="Add a list filter").replace("tier: T1\n", "")
        (w.boil / "tickets" / "T-0001.md").write_text(text, encoding="utf-8")
        codes = {i["code"] for i in json.loads(w.lint().stdout)["issues"]}
        self.assertIn("answer-key-none-behavior", codes)
        self.assertIn("missing-field", codes)

    def test_a_t1_ticket_still_needs_a_reason_for_kind_none(self) -> None:
        w = Workspace(self)
        text = self.NO_KEY.format(tier="T1", title="Add a list filter")
        text = text.replace('  reason: "proof is the project\'s own suite"\n', "")
        (w.boil / "tickets" / "T-0001.md").write_text(text, encoding="utf-8")
        codes = {i["code"] for i in json.loads(w.lint().stdout)["issues"]}
        self.assertIn("answer-key-none-reason", codes)


class TerminationGateTest(unittest.TestCase):
    def _final(self, w: Workspace, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(str(SCRIPTS / "boil-doctor.py"), "--root", str(w.root), "--final", *extra)

    def test_an_unfinished_goal_cannot_be_declared_final(self) -> None:
        w = Workspace(self)
        w.green(1)
        proc = self._final(w)
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("still open", proc.stdout)

    def test_a_green_but_unevidenced_goal_cannot_be_declared_final(self) -> None:
        w = Workspace(self)
        text = (w.boil / "goal.md").read_text().replace("- [ ]", "- [x]")
        (w.boil / "goal.md").write_text(text, encoding="utf-8")
        proc = self._final(w)
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("EVIDENCE", proc.stdout)

    def test_a_green_evidenced_goal_passes(self) -> None:
        w = Workspace(self)
        w.green(2)
        proc = self._final(w)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_refusal_writes_a_handoff_not_a_final(self) -> None:
        w = Workspace(self)
        w.green(1)
        self._final(w, "--write")
        handoff = w.boil / "HANDOFF.md"
        self.assertTrue(handoff.is_file())
        self.assertIn("not done", handoff.read_text())
        self.assertFalse((w.boil / "FINAL.md").exists())


class MigrateTest(unittest.TestCase):
    def _migrate(self, w: Workspace, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(str(SCRIPTS / "boil-migrate.py"), "--root", str(w.root), *extra)

    def test_dry_run_writes_nothing(self) -> None:
        w = Workspace(self)
        (w.root / ".gate").mkdir()
        (w.root / ".gate" / "charter.md").write_text("---\nstatus: active\n---\n", encoding="utf-8")
        self._migrate(w)
        self.assertFalse((w.boil / "charter.md").exists())

    def test_apply_folds_gate_into_boil(self) -> None:
        w = Workspace(self)
        (w.root / ".gate").mkdir()
        (w.root / ".gate" / "charter.md").write_text("---\nstatus: active\n---\n", encoding="utf-8")
        (w.root / ".gate" / "ladder.md").write_text("- [ ] L1 thing\n", encoding="utf-8")
        self._migrate(w, "--apply")
        self.assertTrue((w.boil / "charter.md").is_file())
        self.assertTrue((w.boil / "ladder.md").is_file())
        self.assertTrue((w.boil / "icebox.md").is_file())
        self.assertTrue((w.boil / "budget.json").is_file())
        self.assertTrue((w.root / ".gate").is_dir(), "migration is non-destructive by default")

    def test_existing_boil_files_are_never_overwritten(self) -> None:
        w = Workspace(self)
        (w.boil / "charter.md").write_text("MINE\n", encoding="utf-8")
        (w.root / ".gate").mkdir()
        (w.root / ".gate" / "charter.md").write_text("THEIRS\n", encoding="utf-8")
        self._migrate(w, "--apply")
        self.assertEqual((w.boil / "charter.md").read_text(), "MINE\n")


class VibeCheckFormatTest(unittest.TestCase):
    """The Step 2e report block must pass the progress-theater detector.

    The merged skill replaced four report surfaces with one block that labels its
    next actions `**Next:**`. The old `\\bNext:\\b` pattern could not match that —
    the trailing word boundary needs a word character after the colon, and bold
    puts an asterisk there — so a correct report was flagged as missing next steps.
    """

    def _check(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "summary.md"
            path.write_text(text, encoding="utf-8")
            return run(str(SCRIPTS / "vibe-check.py"), str(path))

    NEW_FORMAT = """## Iteration 3 — the orders endpoint creates a real row

**Changed:** `api/orders.py`, `tests/api/test_orders.py`
**Goal:** 2/4 checkboxes — "POST returns 201" turned green
**Proof:** `pytest tests/api -q` -> 12 passed in 1.8s
**Demo (30s):** run `curl -XPOST localhost:8000/api/orders`
**Next:** wire the list view refetch (T-0012)
"""

    HEADING_FORMAT = """## Iteration 1

Implemented the thing.

**Tests:** 4 passed
**Demo:** open http://localhost:3000

## Suggested next steps
1. do the next thing
"""

    def test_the_merged_report_block_passes(self) -> None:
        proc = self._check(self.NEW_FORMAT)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_the_older_heading_form_still_passes(self) -> None:
        proc = self._check(self.HEADING_FORMAT)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_progress_theater_is_still_caught(self) -> None:
        proc = self._check("## Iteration 2\n\nImplemented the feature. It should work now.\n")
        self.assertEqual(proc.returncode, 1)
        for code in ("missing-tests", "missing-demo", "missing-next", "speculative-language"):
            self.assertIn(code, proc.stdout)


class NowTest(unittest.TestCase):
    def _now(self, w: Workspace) -> subprocess.CompletedProcess[str]:
        return run(str(SCRIPTS / "boil-now.py"), "--root", str(w.root))

    def test_now_stays_orientation_sized(self) -> None:
        w = Workspace(self)
        for i in range(1, 9):
            w.ticket(f"T-000{i}.md", title="A fairly long ticket title " * 4)
        out = self._now(w).stdout
        self.assertLess(len(out.splitlines()), 45, "NOW.md must stay a ~40-line read")

    def test_a_parked_project_refuses_work(self) -> None:
        w = Workspace(self)
        (w.boil / "charter.md").write_text(
            "---\nstatus: parked\nreentry: when the API ships\n---\n", encoding="utf-8")
        proc = self._now(w)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("PARKED", proc.stdout)

    def test_a_fired_brake_surfaces_at_session_start(self) -> None:
        w = Workspace(self)
        for i in range(1, 4):
            w.tick(f"iter-00{i}")
        proc = self._now(w)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("STOP", proc.stdout)


if __name__ == "__main__":
    unittest.main()


class ClaudeSessionTrailerTest(unittest.TestCase):
    """Found live on streammachine: `Claude-Session:` lines survived the strip and the guard.
    Any AI session/attribution trailer is attribution."""

    def test_claude_session_trailer_is_flagged(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bcg", Path(__file__).resolve().parents[1] / "scripts" / "boil-commit-guard.py")
        bcg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bcg)
        self.assertTrue(bcg.AI_PATTERN.search("Claude-Session: https://claude.ai/code/session_01X"))
        self.assertTrue(bcg.AI_PATTERN.search("Codex-Session: https://chatgpt.com/codex/x"))
        self.assertFalse(bcg.AI_PATTERN.search("uses the claude-ollama wrapper for reviews"))
