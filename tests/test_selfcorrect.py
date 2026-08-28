"""Red-team suite for the self-correcting loop.

`references/self-correcting-loop.md` says not to trust the loop unattended until it
survives four scenarios: an unsolvable task, a confidently wrong answer, a shared model
blind spot, and the most expensive possible run. The model half of each has to be run by
hand on a scratch ticket; the HARNESS half is deterministic and lives here.

These tests are adversarial on purpose. Each one drives boil-loop.py toward the outcome a
naive implementation would produce (a fourth attempt, a PASS on a confident report, a
green verdict with no evidence, an unbounded spend) and asserts it does not happen.

Every subprocess call passes --no-log: a test must never write into the operator's real
helm stores.

Run: python3 -m unittest tests.test_selfcorrect
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "scripts" / "boil-loop.py"
LINT = ROOT / "scripts" / "ticket-lint.py"

# 0 = ACCEPT/REVISE, 2 = usage error, 3 = terminal (any ESCALATE-*, ABORT-TAMPER)
EXIT_OK, EXIT_USAGE, EXIT_TERMINAL = 0, 2, 3

TICKET = """---
id: T-0001
title: {title}
type: {ttype}
specialty: frontend
status: in-progress
priority: P1
proof_strategy: red-green
tier: T3
opened_by: orchestrator
opened_at: 2026-08-03T09:00:00Z
blocked_by: []
answer_key:
{key}
working_on: "implementing"
---

## Context
Red-team fixture.
"""

DEFAULT_KEY = """  kind: suite
  ref: "tests/test_key.py::test_behavior"
  expect: pass
  authored_by: orchestrator
  frozen_at: 2026-08-03T10:00:00Z
  frozen_sha: ""
  protected: true"""

JUDGE_FAIL = """# Judge — T-0001 — attempt {n}

**Key integrity:** VERIFIED
## Evidence trace
### Check 1: the selector passes
**Action:** ran the frozen selector
**Observation:** it failed
**Evidence:** `E   AssertionError: expected 3 got 5`
**Result:** FAIL

## Verdict
**Decision:** FAIL
**Failure signature:** {sig}
**Reason (one sentence):** {reason}
"""

JUDGE_PASS_NO_EVIDENCE = """# Judge — T-0001 — attempt {n}

**Key integrity:** VERIFIED
## Verdict
**Decision:** PASS
**Failure signature:**
**Reason (one sentence):** the implementation looks correct and the report is thorough.
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class LoopHarness:
    """A throwaway project with one armed loop."""

    def __init__(self, stack: unittest.TestCase, *, ttype: str = "bug",
                 key: str = DEFAULT_KEY, title: str = "Red-team ticket",
                 init: bool = True, **init_flags: str):
        td = tempfile.TemporaryDirectory()
        stack.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root / ".boil" / "tickets").mkdir(parents=True)
        (self.root / "tests").mkdir()
        self.key_file = self.root / "tests" / "test_key.py"
        self.key_file.write_text("def test_behavior():\n    assert compute() == 3\n", encoding="utf-8")
        self.ticket = self.root / ".boil" / "tickets" / "T-0001.md"
        self.ticket.write_text(TICKET.format(title=title, ttype=ttype, key=key), encoding="utf-8")
        self.init_result = None
        if init:
            flags: list[str] = []
            for k, v in init_flags.items():
                flags += [f"--{k.replace('_', '-')}", str(v)]
            self.init_result = self.loop("init", *flags)

    def loop(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(str(LOOP), args[0], "--root", str(self.root), "--ticket", "T-0001",
                   "--no-log", *args[1:])

    def attempt(self, n: int, judge_text: str, *, cost: str = "0",
                changed: tuple[str, ...] = ("src/app.ts",)) -> subprocess.CompletedProcess[str]:
        """One full builder → judge → manager cycle; returns the `decide` result."""
        build_flags: list[str] = []
        for path in changed:
            build_flags += ["--changed-file", path]
        self.loop("record-build", "--attempt", str(n), "--builder-family", "claude", *build_flags)
        jf = self.root / f"judge-{n}.md"
        jf.write_text(judge_text, encoding="utf-8")
        self.loop("record-judge", "--attempt", str(n), "--file", str(jf), "--judge-family", "codex")
        return self.loop("decide", "--attempt", str(n), "--cost-usd", cost, "--json")

    def state(self) -> dict:
        return json.loads((self.root / ".boil" / "loops" / "T-0001" / "loop.json")
                          .read_text(encoding="utf-8"))

    def decision(self, proc: subprocess.CompletedProcess[str]) -> str:
        return json.loads(proc.stdout)["decision"]


class UnsolvableTaskTest(unittest.TestCase):
    """Scenario 1 — a ticket that cannot be satisfied as written.

    Expected: three failures escalate with a full history, the goal checkbox is untouched,
    and there is no fourth attempt. The failure to look for is a loop that quietly grants
    another try, or 'succeeds' by reinterpreting the ticket."""

    def test_three_distinct_failures_escalate_at_the_limit(self) -> None:
        h = LoopHarness(self)
        first = h.attempt(1, JUDGE_FAIL.format(n=1, sig="suite:key:AssertionError:got 5",
                                               reason="returns 5, the key demands 3"))
        self.assertEqual(first.returncode, EXIT_OK)
        self.assertEqual(h.decision(first), "REVISE")

        second = h.attempt(2, JUDGE_FAIL.format(n=2, sig="suite:key:TypeError:None",
                                                reason="returns None after the refactor"))
        self.assertEqual(h.decision(second), "REVISE")

        third = h.attempt(3, JUDGE_FAIL.format(n=3, sig="suite:key:AssertionError:got 4",
                                               reason="returns 4, still not 3"))
        self.assertEqual(h.decision(third), "ESCALATE-LIMIT")
        self.assertEqual(third.returncode, EXIT_TERMINAL,
                         "a terminal decision must exit 3 so a driving script can branch on it")
        self.assertEqual(h.state()["status"], "escalated")

    def test_no_fourth_attempt_is_ever_offered(self) -> None:
        h = LoopHarness(self)
        for n, sig in enumerate(("a", "b", "c"), start=1):
            h.attempt(n, JUDGE_FAIL.format(n=n, sig=f"suite:key:E{sig}", reason=f"failure {sig}"))
        fourth = h.attempt(4, JUDGE_FAIL.format(n=4, sig="suite:key:Ed", reason="failure d"))
        self.assertEqual(h.decision(fourth), "ESCALATE-LIMIT",
                         "attempt 4 must still escalate — the limit is not a soft suggestion")

    def test_escalation_packet_carries_the_whole_history(self) -> None:
        h = LoopHarness(self)
        reasons = ["returns 5, the key demands 3", "returns None after the refactor",
                   "returns 4, still not 3"]
        for n, reason in enumerate(reasons, start=1):
            h.attempt(n, JUDGE_FAIL.format(n=n, sig=f"suite:key:sig{n}", reason=reason))
        proc = h.loop("escalate", "--convert-ticket")
        self.assertEqual(proc.returncode, EXIT_TERMINAL, proc.stdout + proc.stderr)

        packet = (h.root / ".boil" / "loops" / "T-0001" / "escalation.md").read_text(encoding="utf-8")
        for n, reason in enumerate(reasons, start=1):
            self.assertIn(f"Attempt {n}", packet)
            self.assertIn(reason, packet, "every judge's finding must survive into the packet")
        self.assertIn("What the human has to decide", packet)
        self.assertIn("ESCALATE-LIMIT", packet)

        ticket = h.ticket.read_text(encoding="utf-8")
        self.assertIn("type: human-action", ticket)
        self.assertIn("status: blocked", ticket)
        self.assertIn("priority: P0", ticket)
        self.assertIn("required: true", ticket)

    def test_stall_brake_stops_before_burning_the_last_attempt(self) -> None:
        """Two identical failure signatures mean the revisions are not converging.
        Stopping early is cheaper than a third attempt at the same wall."""
        h = LoopHarness(self)
        sig = "suite:key:AssertionError:expected 3 got 5"
        h.attempt(1, JUDGE_FAIL.format(n=1, sig=sig, reason="off by two"))
        second = h.attempt(2, JUDGE_FAIL.format(n=2, sig=sig, reason="off by two"))
        self.assertEqual(h.decision(second), "ESCALATE-STALL")
        self.assertEqual(second.returncode, EXIT_TERMINAL)


class ConfidentlyWrongTest(unittest.TestCase):
    """Scenario 2 — the builder returns 100/100 confidence and green claims over work
    that does not satisfy the key.

    Expected: the judge's verdict decides, and the builder's confidence is not an input.
    The failure to look for is an ACCEPT because the report looked thorough."""

    CONFIDENT_REPORT = """### Changed files
- src/app.ts — implemented the feature

### Proof / tests
- Final proof: `pytest` → 47 passed in 2.3s
- Status: green

### Confidence gate
- Requirements understood: 100 — crystal clear
- Implementation matches: 100 — exactly as specified
- Verification working: 100 — full suite green
- Remaining uncertainty: none
"""

    def test_a_confident_report_does_not_move_the_verdict(self) -> None:
        h = LoopHarness(self)
        report = h.root / "build.md"
        report.write_text(self.CONFIDENT_REPORT, encoding="utf-8")
        h.loop("record-build", "--attempt", "1", "--report", str(report),
               "--changed-file", "src/app.ts", "--builder-family", "claude")
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_FAIL.format(n=1, sig="suite:key:AssertionError:got 5",
                                        reason="the frozen selector still fails on HEAD"),
                      encoding="utf-8")
        h.loop("record-judge", "--attempt", "1", "--file", str(jf))
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "REVISE",
                         "a 100/100 self-report must not override a FAIL against the key")

        stored = (h.root / ".boil" / "loops" / "T-0001" / "attempt-1" / "build.md").read_text()
        self.assertIn("Requirements understood: 100", stored,
                      "the report is kept for the human packet — it is just not evidence")

    def test_builder_cannot_pass_by_weakening_the_key(self) -> None:
        """The most attractive shortcut for a stuck builder: edit the ruler."""
        h = LoopHarness(self)
        h.key_file.write_text("def test_behavior():\n    pass  # TODO\n", encoding="utf-8")
        h.loop("record-build", "--attempt", "1", "--changed-file", "tests/test_key.py")
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_FAIL.format(n=1, sig="x", reason="y").replace(
            "**Decision:** FAIL", "**Decision:** PASS"), encoding="utf-8")
        h.loop("record-judge", "--attempt", "1", "--file", str(jf))
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "ABORT-TAMPER",
                         "a tampered key aborts even when the judge said PASS")
        self.assertEqual(proc.returncode, EXIT_TERMINAL)
        self.assertEqual(h.state()["status"], "aborted")

    def test_deleting_the_key_is_tampering_too(self) -> None:
        h = LoopHarness(self)
        h.key_file.unlink()
        h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
        h.loop("record-judge", "--attempt", "1", "--verdict", "PASS")
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "ABORT-TAMPER")

    def test_audit_catches_a_key_that_moved_after_the_ticket_closed(self) -> None:
        """The slow version of the same cheat: pass honestly, then change the ruler."""
        h = LoopHarness(self)
        h.attempt(1, JUDGE_FAIL.format(n=1, sig="", reason="ok").replace(
            "**Decision:** FAIL", "**Decision:** PASS"))
        ticket = h.ticket.read_text(encoding="utf-8").replace("status: in-progress", "status: done")
        h.ticket.write_text(ticket, encoding="utf-8")
        clean = run(str(LOOP), "audit", "--root", str(h.root), "--no-log")
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

        h.key_file.write_text("def test_behavior():\n    pass\n", encoding="utf-8")
        drifted = run(str(LOOP), "audit", "--root", str(h.root), "--no-log", "--json")
        self.assertEqual(drifted.returncode, 1)
        self.assertIn("key-drift", drifted.stdout)


class SharedBlindSpotTest(unittest.TestCase):
    """Scenario 3 — builder and judge share a systematic error.

    The structural defenses are: a verdict with no cited key evidence is not a PASS, the
    key must be authored outside the builder, and both model families are recorded so a
    same-family pair is visible rather than buried."""

    def test_pass_without_cited_evidence_is_downgraded_to_invalid(self) -> None:
        h = LoopHarness(self)
        h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_PASS_NO_EVIDENCE.format(n=1), encoding="utf-8")
        h.loop("record-judge", "--attempt", "1", "--file", str(jf))
        self.assertEqual(h.state()["attempts"][0]["verdict"], "INVALID",
                         "a PASS whose only evidence is the judge's own opinion is not a PASS")
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "RERUN-JUDGE")
        self.assertEqual(proc.returncode, EXIT_OK, "a re-run is not a terminal state")

    def test_a_judge_that_stays_unusable_escalates_as_infra(self) -> None:
        h = LoopHarness(self)
        h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_PASS_NO_EVIDENCE.format(n=1), encoding="utf-8")
        for _ in range(2):
            h.loop("record-judge", "--attempt", "1", "--file", str(jf))
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "ESCALATE-INFRA",
                         "two unusable verdicts mean the key or the judge route is broken")

    def test_rerun_judge_does_not_consume_a_builder_attempt(self) -> None:
        h = LoopHarness(self)
        h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_PASS_NO_EVIDENCE.format(n=1), encoding="utf-8")
        h.loop("record-judge", "--attempt", "1", "--file", str(jf))
        h.loop("decide", "--attempt", "1")
        # the judge comes back with a real trace this time
        good = h.root / "judge2.md"
        good.write_text(JUDGE_FAIL.format(n=1, sig="suite:key:E1", reason="off by two"),
                        encoding="utf-8")
        h.loop("record-judge", "--attempt", "1", "--file", str(good))
        proc = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(proc), "REVISE")
        self.assertIn("attempt 1 of 3", json.loads(proc.stdout)["reason"],
                      "the re-run must not have burned an attempt")

    def test_both_model_families_are_recorded_for_every_attempt(self) -> None:
        h = LoopHarness(self)
        h.attempt(1, JUDGE_FAIL.format(n=1, sig="suite:key:E1", reason="off by two"))
        att = h.state()["attempts"][0]
        self.assertEqual(att["builder_family"], "claude")
        self.assertEqual(att["judge_family"], "codex")
        manager = json.loads((h.root / ".boil" / "loops" / "T-0001" / "attempt-1" /
                              "manager.json").read_text(encoding="utf-8"))
        self.assertEqual(manager["builder_family"], "claude")
        self.assertEqual(manager["judge_family"], "codex")

    def test_a_self_authored_key_is_refused_at_arming_time(self) -> None:
        """If the builder's own specialty wrote the key, there is no external ruler."""
        key = DEFAULT_KEY.replace("authored_by: orchestrator", "authored_by: frontend")
        h = LoopHarness(self, key=key, init=False)
        proc = h.loop("init")
        self.assertEqual(proc.returncode, EXIT_USAGE)
        self.assertIn("builder's own specialty", proc.stderr)
        self.assertFalse((h.root / ".boil" / "loops" / "T-0001" / "loop.json").exists())

    def test_lint_rejects_a_behavior_ticket_with_no_key(self) -> None:
        h = LoopHarness(self, key='  kind: none\n  reason: "felt obvious"', init=False)
        proc = run(str(LINT), "--root", str(h.root), "--no-goal", "--json")
        self.assertEqual(proc.returncode, 1)
        codes = {i["code"] for i in json.loads(proc.stdout)["issues"]}
        self.assertIn("answer-key-none-behavior", codes)

    def test_lint_allows_kind_none_on_a_docs_ticket_with_a_reason(self) -> None:
        h = LoopHarness(self, ttype="docs",
                        key='  kind: none\n  reason: "prose only; no external ground truth"',
                        init=False)
        proc = run(str(LINT), "--root", str(h.root), "--no-goal", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_a_key_that_cannot_be_read_cannot_be_frozen(self) -> None:
        key = DEFAULT_KEY.replace('ref: "tests/test_key.py::test_behavior"',
                                  'ref: "tests/does_not_exist.py::test_x"')
        h = LoopHarness(self, key=key, init=False)
        proc = h.loop("init")
        self.assertEqual(proc.returncode, EXIT_USAGE)
        self.assertIn("unreadable", proc.stderr)


class MostExpensiveRunTest(unittest.TestCase):
    """Scenario 4 — price the worst case before funding it.

    worst case = max_revisions × (1 build + 2 judges) + manager overhead
               = 3 builds + 6 judges + 3 decisions.
    Two judges per attempt because an attempt absorbs exactly one INVALID/INDETERMINATE
    re-run before escalating. The failure to look for is an unbounded spend, or a judge
    re-run loop that never consumes the attempt counter and so never terminates."""

    def test_budget_cap_stops_the_run_and_reports_the_spend(self) -> None:
        h = LoopHarness(self, budget_usd="1.00")
        first = h.attempt(1, JUDGE_FAIL.format(n=1, sig="suite:key:E1", reason="off by two"),
                          cost="0.60")
        self.assertEqual(h.decision(first), "REVISE")
        second = h.attempt(2, JUDGE_FAIL.format(n=2, sig="suite:key:E2", reason="now off by one"),
                           cost="0.60")
        self.assertEqual(h.decision(second), "ESCALATE-BUDGET")
        self.assertEqual(second.returncode, EXIT_TERMINAL)
        self.assertAlmostEqual(h.state()["budget"]["usd_spent"], 1.20, places=4)

        h.loop("escalate")
        packet = (h.root / ".boil" / "loops" / "T-0001" / "escalation.md").read_text(encoding="utf-8")
        self.assertIn("$1.20", packet, "the human packet must say what the failure cost")

    def test_budget_beats_a_pass_verdict(self) -> None:
        """Cost control is checked above the verdict: an over-cap run stops even on green."""
        h = LoopHarness(self, budget_usd="0.10")
        proc = h.attempt(1, JUDGE_FAIL.format(n=1, sig="", reason="fine").replace(
            "**Decision:** FAIL", "**Decision:** PASS"), cost="5.00")
        self.assertEqual(h.decision(proc), "ESCALATE-BUDGET")

    def test_worst_case_attempt_count_is_bounded_by_max_revisions(self) -> None:
        for limit in (1, 2, 3):
            with self.subTest(max_revisions=limit):
                h = LoopHarness(self, max_revisions=str(limit))
                self.assertEqual(h.state()["max_revisions"], limit)
                decisions = [
                    h.decision(h.attempt(n, JUDGE_FAIL.format(
                        n=n, sig=f"suite:key:E{n}", reason=f"failure {n}")))
                    for n in range(1, limit + 1)
                ]
                self.assertEqual(decisions[-1], "ESCALATE-LIMIT")
                self.assertEqual(decisions[:-1], ["REVISE"] * (limit - 1))

    def test_judge_reruns_are_capped_at_one_per_attempt(self) -> None:
        """The ceiling that makes the worst case computable: a judge re-run loop that
        never consumed the attempt counter would be unbounded spend with no terminal state."""
        h = LoopHarness(self)
        jf = h.root / "judge.md"
        jf.write_text(JUDGE_PASS_NO_EVIDENCE.format(n=1), encoding="utf-8")
        decisions = []
        for _ in range(5):
            h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
            h.loop("record-judge", "--attempt", "1", "--file", str(jf))
            proc = h.loop("decide", "--attempt", "1", "--json")
            decisions.append(h.decision(proc))
        self.assertEqual(decisions[0], "RERUN-JUDGE")
        self.assertTrue(all(d == "ESCALATE-INFRA" for d in decisions[1:]),
                        f"only ONE re-run per attempt is allowed, got {decisions}")

    def test_indeterminate_gets_one_retry_then_stops(self) -> None:
        """A judge that cannot see the artifact is bounded too — two blind verdicts and
        the loop stops instead of paying for a third look at nothing."""
        h = LoopHarness(self)
        h.loop("record-build", "--attempt", "1", "--changed-file", "src/app.ts")
        h.loop("record-judge", "--attempt", "1", "--verdict", "INDETERMINATE",
               "--defect", "the screenshot artifact is missing")
        first = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(first), "REVISE-VISIBILITY")
        self.assertEqual(first.returncode, EXIT_OK)

        h.loop("record-judge", "--attempt", "1", "--verdict", "INDETERMINATE",
               "--defect", "still missing")
        second = h.loop("decide", "--attempt", "1", "--json")
        self.assertEqual(h.decision(second), "ESCALATE-VISIBILITY")
        self.assertEqual(second.returncode, EXIT_TERMINAL)


class AuditGateTest(unittest.TestCase):
    """The iteration gate: a ticket may not claim done on an unproven loop."""

    def test_done_behavior_ticket_without_a_loop_fails_the_audit(self) -> None:
        h = LoopHarness(self, init=False)
        h.ticket.write_text(h.ticket.read_text(encoding="utf-8")
                            .replace("status: in-progress", "status: done"), encoding="utf-8")
        proc = run(str(LOOP), "audit", "--root", str(h.root), "--no-log", "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no-loop", proc.stdout)

    def test_done_ticket_on_an_escalated_loop_fails_the_audit(self) -> None:
        h = LoopHarness(self)
        sig = "suite:key:AssertionError:same"
        h.attempt(1, JUDGE_FAIL.format(n=1, sig=sig, reason="off by two"))
        h.attempt(2, JUDGE_FAIL.format(n=2, sig=sig, reason="off by two"))
        h.loop("escalate", "--convert-ticket")
        # an operator "fixes" the board by marking it done anyway
        h.ticket.write_text(h.ticket.read_text(encoding="utf-8")
                            .replace("status: blocked", "status: done")
                            .replace("type: human-action", "type: bug"), encoding="utf-8")
        proc = run(str(LOOP), "audit", "--root", str(h.root), "--no-log", "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unaccepted-loop", proc.stdout)

    def test_terminal_loop_without_an_escalation_packet_fails_the_audit(self) -> None:
        h = LoopHarness(self)
        sig = "suite:key:AssertionError:same"
        h.attempt(1, JUDGE_FAIL.format(n=1, sig=sig, reason="off by two"))
        h.attempt(2, JUDGE_FAIL.format(n=2, sig=sig, reason="off by two"))
        proc = run(str(LOOP), "audit", "--root", str(h.root), "--no-log", "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing-escalation", proc.stdout,
                      "a stopped loop with no human packet is an invisible dead end")

    def test_accepted_loop_passes_the_audit(self) -> None:
        h = LoopHarness(self)
        h.attempt(1, JUDGE_FAIL.format(n=1, sig="", reason="all checks pass")
                  .replace("**Decision:** FAIL", "**Decision:** PASS"))
        h.ticket.write_text(h.ticket.read_text(encoding="utf-8")
                            .replace("status: in-progress", "status: done"), encoding="utf-8")
        proc = run(str(LOOP), "audit", "--root", str(h.root), "--no-log")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class StatusLoggingTest(unittest.TestCase):
    """The status log is what makes an unattended run reviewable."""

    def test_snapshot_carries_tickets_decisions_and_judge_reasoning(self) -> None:
        h = LoopHarness(self)
        h.attempt(1, JUDGE_FAIL.format(n=1, sig="suite:key:E1",
                                       reason="the refetch fires with a stale range"))
        (h.root / ".boil" / "goal.md").write_text(
            "# Goal\n\n**One-line:** chart refetches\n\n- [x] one\n- [ ] two\n", encoding="utf-8")
        proc = run(str(ROOT / "scripts" / "boil-helm-log.py"), "session",
                   "--root", str(h.root), "--no-helm", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snap = json.loads(proc.stdout)

        self.assertEqual(snap["goal"], "chart refetches")
        self.assertEqual(snap["goal_progress"], {"green": 1, "total": 2})
        ticket = snap["tickets"][0]
        self.assertEqual(ticket["id"], "T-0001")
        self.assertEqual(ticket["answer_key"]["kind"], "suite")
        self.assertEqual(ticket["loop"]["last_decision"], "REVISE")
        self.assertEqual(ticket["loop"]["defect"], "the refetch fires with a stale range")
        self.assertIn("Evidence", ticket["loop"]["trail"][0]["judge_excerpt"],
                      "the dashboard must be able to show the reasoning, not just the verdict")
        self.assertTrue(snap["decisions"], "manager decisions must be in the snapshot")

    def test_emit_writes_local_files_and_never_needs_helm(self) -> None:
        h = LoopHarness(self)
        proc = run(str(ROOT / "scripts" / "boil-helm-log.py"), "emit", "--root", str(h.root),
                   "--kind", "boil.judge.verdict", "--ticket", "T-0001", "--attempt", "1",
                   "--status", "FAIL", "--detail", "suite:key:E1", "--no-helm")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        line = json.loads((h.root / ".boil" / "status.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line["kind"], "boil.judge.verdict")
        self.assertEqual(line["status"], "FAIL")
        self.assertIn("boil status", (h.root / ".boil" / "STATUS.md").read_text(encoding="utf-8"))

    def test_helm_push_targets_the_helm_dir_and_is_isolatable(self) -> None:
        """Proves the bridge writes where helm reads — against a fake HELM_DIR, so a test
        run can never touch the operator's real event log."""
        import os
        h = LoopHarness(self)
        fake = h.root / "fake-helm"
        (fake).mkdir()
        (fake / "helm.py").write_text("# fake\n", encoding="utf-8")
        env = dict(os.environ, HELM_DIR=str(fake))
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "boil-helm-log.py"), "emit",
             "--root", str(h.root), "--kind", "boil.loop.escalate", "--ticket", "T-0001",
             "--status", "ESCALATE-LIMIT", "--detail", "three revisions failed"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)

        sessions = list((fake / "runs" / "boil").glob("*.json"))
        self.assertEqual(len(sessions), 1, "the session object must land in helm's store")
        session = json.loads(sessions[0].read_text(encoding="utf-8"))
        self.assertEqual(session["tickets"][0]["id"], "T-0001")

        events = list((fake / "runs" / "events").glob("*.jsonl"))
        self.assertEqual(len(events), 1)
        rec = json.loads(events[0].read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(rec["kind"], "boil.loop.escalate")
        self.assertTrue(rec["kind"].startswith("boil."),
                        "the kind must stay in the boil.* namespace so `helm events --kind boil` finds it")
        self.assertEqual(rec["session"], session["session_id"])


if __name__ == "__main__":
    unittest.main()
