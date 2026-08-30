"""W3 — the convergence bench is also the end-to-end test.

`bench/run.py --implementer scripted` drives the whole driver protocol — compile → prepare →
attempt → score (→ split / close) → doctor --final — over seeded mini-repos whose attempts are
overlays applied per (milestone, attempt). Each project's `expect.json` names the exit codes
that must fire, so every controller verdict is exercised on real code, in CI, in seconds:
PASS, RETRY via a real counterexample, STALL → split, CAP, TAMPER, the audit finding, and the
reviewer's fix node. The same runner with `--implementer llm` produces the effectiveness
numbers (first-pass rate, $ per green box) — the instrument PLAN §6 needs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "bench" / "run.py"
PROJECTS = ROOT / "bench" / "projects"


def bench(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(RUN), *args], text=True, capture_output=True)


class BenchTest(unittest.TestCase):
    def _run(self, name: str) -> dict:
        r = bench("--implementer", "scripted", "--only", name, "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        result = json.loads(r.stdout)["projects"][name]
        expect = json.loads((PROJECTS / name / "expect.json").read_text())
        self.assertEqual(result["events"], expect["events"], json.dumps(result, indent=1))
        self.assertEqual(result["final"], expect["final"])
        return result

    def test_wordfreq_retries_on_a_real_counterexample_then_finishes(self) -> None:
        r = self._run("wordfreq")
        self.assertEqual(r["green"], r["total"])
        self.assertIn("M2", r["first_pass_failed"])
        self.assertEqual(r["attempts"]["M2"], 2)

    def test_stall_split_stalls_on_an_identical_failure_and_recovers_through_a_split(self) -> None:
        r = self._run("stall-split")
        self.assertEqual(r["green"], r["total"])

    def test_cap_stops_after_four_attempts_and_flags_the_audit_finding(self) -> None:
        r = self._run("cap")
        self.assertLess(r["green"], r["total"])
        self.assertTrue(any("audit" in (a.get("counterexample") or "").lower() for a in r["ledger"]))

    def test_tamper_aborts_when_the_implementer_edits_the_ruler(self) -> None:
        self._run("tamper")

    def test_review_findings_become_a_fix_node_that_is_closed_after_one_round(self) -> None:
        r = self._run("review")
        self.assertEqual(r["green"], r["total"])

    def test_every_project_has_an_expectation_and_the_runner_lists_them(self) -> None:
        names = sorted(p.name for p in PROJECTS.iterdir() if p.is_dir())
        self.assertEqual(names, ["cap", "review", "stall-split", "tamper", "wordfreq"])
        r = bench("--list")
        self.assertEqual(r.returncode, 0)
        for n in names:
            self.assertIn(n, r.stdout)


if __name__ == "__main__":
    unittest.main()
