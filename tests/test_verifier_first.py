"""Tests for the verifier-first controller (`scripts/boil-check.py`).

Each rule the controller enforces exists because the research run behind it
(`_research/boil-convergence/PLAN.md`) found the prose rule does not execute:
a check must be validated before it is frozen, the implementer never runs the
check, one counterexample flows back, an identical failure twice is a stall,
caps and budgets are pre-call gates, and a drifted check or harness is tamper.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "boil-check.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECK), *args], text=True,
                          capture_output=True, cwd=cwd)


class Workspace:
    """A throwaway project with a .boil/ dir and a milestone spec."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".boil").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_guard.py").write_text("def test_ok():\n    assert True\n")

    def spec(self, milestones: list[dict], **top) -> Path:
        body = {"budget_usd": 5.0, "cap": 4, "stall": 2, "milestones": milestones}
        body.update(top)
        p = self.root / ".boil" / "milestones.json"
        p.write_text(json.dumps(body))
        return p

    def compile(self, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
        return run("compile", "--root", str(self.root), "--spec",
                   str(self.root / ".boil" / "milestones.json"), *(extra or []))

    def frozen(self) -> dict:
        return json.loads((self.root / ".boil" / "checks" / "frozen.json").read_text())

    def attempts(self) -> list[dict]:
        p = self.root / ".boil" / "checks" / "attempts.jsonl"
        if not p.is_file():
            return []
        return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]

    def close(self) -> None:
        self.tmp.cleanup()


FAILING = {"id": "M1", "title": "artifact exists", "check": "test -f out.txt", "kind": "artifact"}
PASSING = {"id": "M0", "title": "readme exists", "check": "test -d tests", "kind": "artifact"}


class CompileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Workspace()

    def tearDown(self) -> None:
        self.ws.close()

    def test_a_check_that_already_passes_is_rejected_as_unfalsifiable(self) -> None:
        self.ws.spec([PASSING])
        r = self.ws.compile()
        self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
        self.assertIn("not falsifiable", r.stdout)
        self.assertEqual(self.ws.frozen()["milestones"], [])

    def test_a_failing_check_is_frozen_with_a_hash(self) -> None:
        self.ws.spec([FAILING])
        r = self.ws.compile()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = self.ws.frozen()["milestones"][0]
        self.assertEqual(m["id"], "M1")
        self.assertTrue(m["hash"])

    def test_an_already_green_regression_guard_is_allowed(self) -> None:
        guard = dict(PASSING, already_green=True, protect=["tests/test_guard.py"])
        self.ws.spec([guard])
        r = self.ws.compile()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ws.frozen()["milestones"][0]["baseline"], "already-green")

    def test_a_check_whose_gold_command_fails_is_rejected(self) -> None:
        self.ws.spec([dict(FAILING, gold="false")])
        r = self.ws.compile()
        self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
        self.assertIn("gold", r.stdout)

    def test_a_flaky_check_is_rejected(self) -> None:
        # Alternates pass/fail on every invocation via a counter file.
        flaky = ("python3 -c \"import pathlib as p; f=p.Path('.n'); n=int(f.read_text() or 0) "
                 "if f.exists() else 0; f.write_text(str(n+1)); raise SystemExit(n % 2)\"")
        self.ws.spec([{"id": "M2", "title": "flaky", "check": flaky, "kind": "test"}], determinism_runs=3)
        r = self.ws.compile()
        self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
        self.assertIn("deterministic", r.stdout)


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Workspace()
        self.ws.spec([FAILING])
        self.assertEqual(self.ws.compile().returncode, 0)

    def tearDown(self) -> None:
        self.ws.close()

    def run_m1(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run("run", "--root", str(self.ws.root), "--milestone", "M1", *extra)

    def test_a_pass_prints_an_evidence_line(self) -> None:
        (self.ws.root / "out.txt").write_text("x")
        r = self.run_m1("--rerun")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("EVIDENCE:", r.stdout)
        self.assertEqual(self.ws.attempts()[-1]["result"], "PASS")

    def test_a_failure_returns_exactly_one_counterexample_line(self) -> None:
        r = self.run_m1()
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        lines = [ln for ln in r.stdout.splitlines() if ln.strip().startswith("counterexample:")]
        self.assertEqual(len(lines), 1)
        self.assertNotIn("test -f out.txt", "\n".join(lines))  # the check's source never flows back

    def test_the_same_failure_twice_is_a_stall(self) -> None:
        self.run_m1()
        r = self.run_m1()
        self.assertEqual(r.returncode, 20, r.stdout + r.stderr)
        self.assertEqual(self.ws.attempts()[-1]["result"], "STALL")

    def test_the_attempt_ceiling_hands_to_the_user(self) -> None:
        # Vary the failure so the stall rule does not fire first.
        for i in range(3):
            (self.ws.root / ".boil" / "checks" / "frozen.json").write_text(
                json.dumps(self.ws.frozen()))
            self.run_m1("--note", f"variant-{i}")
        r = self.run_m1("--note", "variant-3")
        self.assertEqual(r.returncode, 30, r.stdout + r.stderr)

    def test_editing_a_protected_file_is_tamper(self) -> None:
        self.ws.spec([dict(FAILING, protect=["tests/test_guard.py"])])
        self.assertEqual(self.ws.compile().returncode, 0)
        (self.ws.root / "tests" / "test_guard.py").write_text("def test_ok():\n    assert 1\n")
        r = self.run_m1()
        self.assertEqual(r.returncode, 50, r.stdout + r.stderr)
        self.assertEqual(self.ws.attempts()[-1]["result"], "TAMPER")

    def test_an_exhausted_budget_stops_before_running_the_check(self) -> None:
        r = self.run_m1("--spent-usd", "6.0")
        self.assertEqual(r.returncode, 40, r.stdout + r.stderr)
        self.assertEqual(self.ws.attempts()[-1]["result"], "BUDGET")


class GraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Workspace()
        self.ws.spec([
            FAILING,
            {"id": "M2", "title": "second", "check": "test -f two.txt", "after": ["M1"]},
            {"id": "M3", "title": "third", "check": "test -f three.txt", "after": ["M2"]},
        ])
        self.assertEqual(self.ws.compile().returncode, 0)

    def tearDown(self) -> None:
        self.ws.close()

    def next_id(self) -> str:
        r = run("next", "--root", str(self.ws.root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)["milestone"]

    def test_next_respects_dependencies_and_skips_passed_nodes(self) -> None:
        self.assertEqual(self.next_id(), "M1")
        (self.ws.root / "out.txt").write_text("x")
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        self.assertEqual(self.next_id(), "M2")

    def test_split_adds_children_and_next_returns_the_first_child(self) -> None:
        r = run("split", "--root", str(self.ws.root), "--milestone", "M1", "--spec",
                json.dumps([{"id": "M1a", "title": "a", "check": "test -f a.txt"},
                            {"id": "M1b", "title": "b", "check": "test -f b.txt"}]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.next_id(), "M1a")
        ids = [m["id"] for m in self.ws.frozen()["milestones"]]
        self.assertIn("M1a", ids)
        self.assertIn("M1b", ids)

    def test_split_is_allowed_once_per_milestone(self) -> None:
        spec = json.dumps([{"id": "M1a", "title": "a", "check": "test -f a.txt"}])
        self.assertEqual(run("split", "--root", str(self.ws.root), "--milestone", "M1",
                             "--spec", spec).returncode, 0)
        r = run("split", "--root", str(self.ws.root), "--milestone", "M1", "--spec", spec)
        self.assertNotEqual(r.returncode, 0)


class AuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Workspace()
        self.ws.spec([dict(FAILING, protect=["tests"])])
        self.assertEqual(self.ws.compile().returncode, 0)

    def tearDown(self) -> None:
        self.ws.close()

    def test_a_skip_marker_in_the_diff_is_flagged(self) -> None:
        diff = self.ws.root / "d.diff"
        diff.write_text("+++ b/src/x.py\n+@pytest.mark.skip\n+def test_x(): pass\n")
        r = run("audit", "--root", str(self.ws.root), "--diff", str(diff))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("skip", r.stdout)

    def test_a_new_file_under_a_protected_path_is_flagged(self) -> None:
        diff = self.ws.root / "d.diff"
        diff.write_text("+++ b/tests/conftest.py\n+def pytest_runtest_makereport(): pass\n")
        r = run("audit", "--root", str(self.ws.root), "--diff", str(diff))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("tests/conftest.py", r.stdout)

    def test_a_clean_diff_passes(self) -> None:
        diff = self.ws.root / "d.diff"
        diff.write_text("+++ b/src/x.py\n+def add(a, b):\n+    return a + b\n")
        r = run("audit", "--root", str(self.ws.root), "--diff", str(diff))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class StatusTest(unittest.TestCase):
    def test_status_is_one_machine_line(self) -> None:
        ws = Workspace()
        try:
            ws.spec([FAILING])
            self.assertEqual(ws.compile().returncode, 0)
            r = run("status", "--root", str(ws.root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            self.assertIn("0/1 green", lines[0])
            self.assertIn("$", lines[0])
        finally:
            ws.close()


if __name__ == "__main__":
    unittest.main()


BRAKES = ROOT / "scripts" / "boil-brakes.py"
LINT = ROOT / "scripts" / "ticket-lint.py"
PACKET = ROOT / "scripts" / "boil-dispatch-packet.py"


def runpy(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)


class BrakesIntegrationTest(unittest.TestCase):
    """In verifier-first mode the controller's last verdict per milestone is a brake."""

    def setUp(self) -> None:
        self.ws = Workspace()
        (self.ws.root / ".boil" / "goal.md").write_text(
            "# Goal\n\n## Success checklist\n- [ ] artifact exists\n\n## How the user will see this works\nls out.txt\n")
        self.ws.spec([FAILING])
        self.assertEqual(self.ws.compile().returncode, 0)

    def tearDown(self) -> None:
        self.ws.close()

    def test_an_unresolved_stall_stops_the_loop(self) -> None:
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        self.assertEqual(self.ws.attempts()[-1]["result"], "STALL")
        r = runpy(BRAKES, "check", "--root", str(self.ws.root), "--json")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("milestone", [f["brake"] for f in json.loads(r.stdout)["findings"]])

    def test_a_later_pass_clears_the_milestone_brake(self) -> None:
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        (self.ws.root / "out.txt").write_text("x")
        run("run", "--root", str(self.ws.root), "--milestone", "M1")
        r = runpy(BRAKES, "check", "--root", str(self.ws.root), "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


DONE_TICKET = """---
id: T-0001
title: do the thing
type: feature
specialty: general
status: done
priority: P1
proof_strategy: verification-only
tier: T1
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
working_on: "done"
answer_key:
  kind: none
  reason: verifier-first milestone M1 carries the frozen check
---

## Context
closed by milestone M1
"""


class LintIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Workspace()
        (self.ws.root / ".boil" / "goal.md").write_text(
            "# Goal\n\n## Success checklist\n- [ ] artifact exists\n\n## How the user will see this works\nls out.txt\n")
        (self.ws.root / ".boil" / "tickets").mkdir()

    def tearDown(self) -> None:
        self.ws.close()

    def codes(self, r: subprocess.CompletedProcess[str]) -> list[str]:
        return [i["code"] for i in json.loads(r.stdout)["issues"]]

    def test_drafted_but_unfrozen_checks_are_an_error(self) -> None:
        self.ws.spec([FAILING])  # milestones.json exists, frozen.json does not
        r = runpy(LINT, "--root", str(self.ws.root), "--json")
        self.assertIn("checks-not-frozen", self.codes(r))

    def test_a_frozen_milestone_without_a_proxy_gap_warns(self) -> None:
        self.ws.spec([FAILING])
        self.assertEqual(self.ws.compile().returncode, 0)
        r = runpy(LINT, "--root", str(self.ws.root), "--json")
        self.assertIn("milestone-no-proxy-gap", self.codes(r))
        self.assertNotIn("checks-not-frozen", self.codes(r))

    def test_in_verifier_first_mode_a_done_ticket_needs_no_confidence_block(self) -> None:
        self.ws.spec([dict(FAILING, proxy_gap="file existence, not content")])
        self.assertEqual(self.ws.compile().returncode, 0)
        (self.ws.root / ".boil" / "tickets" / "T-0001.md").write_text(DONE_TICKET)
        r = runpy(LINT, "--root", str(self.ws.root), "--json")
        self.assertNotIn("missing-confidence", self.codes(r), r.stdout)


class DispatchPacketTest(unittest.TestCase):
    def test_a_milestone_packet_carries_the_counterexample_but_never_the_check(self) -> None:
        ws = Workspace()
        try:
            (ws.root / ".boil" / "goal.md").write_text("# Goal\n**One-line:** ship it\n")
            ws.spec([dict(FAILING, proxy_gap="existence only")])
            self.assertEqual(ws.compile().returncode, 0)
            run("run", "--root", str(ws.root), "--milestone", "M1")  # one failure -> counterexample
            r = runpy(PACKET, "--root", str(ws.root), "--milestone", "M1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            packet = (ws.root / ".boil" / "dispatch" / "M1.md").read_text()
            self.assertIn("artifact exists", packet)
            self.assertIn("counterexample", packet.lower())
            self.assertIn("do not modify", packet.lower())
            self.assertNotIn("test -f out.txt", packet)
            self.assertNotIn("Confidence gate", packet)
        finally:
            ws.close()


class CompileEnvironmentTest(unittest.TestCase):
    """A check that cannot even run is not falsifiable — it is broken. Found by dogfooding:
    `python3 -m pytest` failed with "No module named pytest" and was frozen as falsifiable."""

    def test_a_check_that_fails_for_an_environment_reason_is_rejected(self) -> None:
        ws = Workspace()
        try:
            ws.spec([{"id": "M9", "title": "needs a missing tool", "check": "python3 -m no_such_module_xyz", "kind": "test"}])
            r = ws.compile()
            self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
            self.assertIn("cannot run", r.stdout)
            self.assertEqual(ws.frozen()["milestones"], [])
        finally:
            ws.close()

    def test_a_missing_command_is_rejected(self) -> None:
        ws = Workspace()
        try:
            ws.spec([{"id": "M9", "title": "missing binary", "check": "no-such-binary-xyz --version", "kind": "test"}])
            r = ws.compile()
            self.assertEqual(r.returncode, 60, r.stdout + r.stderr)
            self.assertIn("cannot run", r.stdout)
        finally:
            ws.close()


class LintTicketsOptionalTest(unittest.TestCase):
    def test_in_verifier_first_mode_a_missing_tickets_dir_is_not_an_error(self) -> None:
        ws = Workspace()
        try:
            (ws.root / ".boil" / "goal.md").write_text(
                "# Goal\n\n## Success checklist\n- [ ] artifact exists\n\n## How the user will see this works\nls out.txt\n")
            ws.spec([dict(FAILING, proxy_gap="existence only")])
            self.assertEqual(ws.compile().returncode, 0)
            r = runpy(LINT, "--root", str(ws.root), "--json")
            codes = [i["code"] for i in json.loads(r.stdout)["issues"]]
            self.assertNotIn("missing-tickets-dir", codes)
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            ws.close()


class ProtectedPathHashTest(unittest.TestCase):
    """Found by dogfooding: `protect: ["tests"]` hashed tests/__pycache__ written by the
    check itself, so the next run was TAMPER. Caches and build artefacts are not the ruler."""

    def test_bytecode_caches_under_a_protected_dir_do_not_trip_tamper(self) -> None:
        ws = Workspace()
        try:
            (ws.root / "tests" / "conftest_free.py").write_text("x = 1\n")
            check = "python3 -c \"import sys; sys.path.insert(0,'tests'); import conftest_free; raise SystemExit(1)\""
            ws.spec([{"id": "M1", "title": "imports a protected module", "check": check, "protect": ["tests"]}])
            self.assertEqual(ws.compile().returncode, 0)
            (ws.root / "tests" / "__pycache__").mkdir(exist_ok=True)
            (ws.root / "tests" / "__pycache__" / "junk.cpython-311.pyc").write_bytes(b"\x00cache")
            (ws.root / ".pytest_cache").mkdir(exist_ok=True)
            r = run("run", "--root", str(ws.root), "--milestone", "M1")
            self.assertEqual(r.returncode, 10, r.stdout + r.stderr)  # a real failure, not TAMPER
        finally:
            ws.close()


class RecompileArchivesAttemptsTest(unittest.TestCase):
    def test_recompiling_a_changed_check_archives_its_old_attempts(self) -> None:
        ws = Workspace()
        try:
            ws.spec([FAILING])
            self.assertEqual(ws.compile().returncode, 0)
            run("run", "--root", str(ws.root), "--milestone", "M1")
            self.assertEqual(len(ws.attempts()), 1)
            ws.spec([dict(FAILING, check="test -f out2.txt")])  # re-authored check
            self.assertEqual(ws.compile().returncode, 0)
            self.assertEqual(ws.attempts(), [])  # ledger starts clean for the new ruler
            archived = list((ws.root / ".boil" / "checks").glob("attempts-*.jsonl"))
            self.assertEqual(len(archived), 1)
        finally:
            ws.close()


class RejectionHintTest(unittest.TestCase):
    """Found by dogfooding: a milestone implemented before its check was frozen is
    rejected as not falsifiable, and the message gave the driver no way forward."""

    def test_green_rejection_names_the_already_green_escape_hatch(self):
        ws = Workspace()
        try:
            ws.spec([PASSING])
            r = ws.compile()
            self.assertEqual(r.returncode, 60)
            self.assertIn("already_green", r.stdout)
        finally:
            ws.close()


class RecompileKeepsUnchangedPassesTest(unittest.TestCase):
    """Found by dogfooding: re-freezing after one check changed archived the whole
    ledger, so a milestone whose ruler had not moved lost its PASS and was re-queued."""

    def test_a_passed_milestone_with_an_unchanged_check_stays_passed(self):
        ws = Workspace()
        try:
            guard = {"id": "G", "title": "guard", "check": "test -f tests/test_guard.py",
                     "already_green": True, "tier": "T1"}
            ws.spec([guard, FAILING])
            self.assertEqual(ws.compile().returncode, 0)
            self.assertEqual(run("run", "--root", str(ws.root), "--milestone", "G").returncode, 0)
            changed = dict(FAILING, check="test -f out2.txt")
            ws.spec([guard, changed])
            self.assertEqual(ws.compile().returncode, 0)
            ids = {a["milestone"] for a in ws.attempts()}
            self.assertIn("G", ids)
            self.assertNotIn(FAILING["id"], ids)
            nxt = json.loads(run("next", "--root", str(ws.root)).stdout)
            self.assertEqual(nxt["milestone"], FAILING["id"])
        finally:
            ws.close()
