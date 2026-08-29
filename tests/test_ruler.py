"""Tests for the ruler additions: boil-assert-db, boil-check verify, boil-guard,
doctor/now enforcement. Every script is exercised the way boil runs it — as a
subprocess — never imported."""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASSERT_DB = SCRIPTS / "boil-assert-db.py"
CHECK = SCRIPTS / "boil-check.py"
GUARD = SCRIPTS / "boil-guard.py"
DOCTOR = SCRIPTS / "boil-doctor.py"
NOW = SCRIPTS / "boil-now.py"
LINT = SCRIPTS / "ticket-lint.py"
TODAY = dt.date.today().isoformat()   # human evidence in fixtures is dated today, so it never goes stale


def run(script: Path, *args: str, cwd: Path | None = None, stdin: str | None = None
        ) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], text=True,
                          capture_output=True, cwd=cwd, input=stdin)


class AssertDbTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "runs.sqlite"
        con = sqlite3.connect(self.db)
        con.execute("create table runs (strategy text, sharpe real, created_at int)")
        con.executemany("insert into runs values (?, ?, ?)",
                        [("x", 0.62, 1), ("x", 0.91, 2), ("y", 1.4, 3)])
        con.commit()
        con.close()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def q(self, query: str, expr: str, db: Path | None = None, *extra: str):
        return run(ASSERT_DB, "--db", str(db or self.db), "--query", query, "--assert", expr, *extra)

    def test_pass_when_assertion_holds_on_first_row(self) -> None:
        r = self.q("select sharpe from runs where strategy='x' order by created_at desc limit 1",
                   "sharpe >= 0.8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS sharpe=0.91", r.stdout)

    def test_fail_when_assertion_does_not_hold(self) -> None:
        r = self.q("select sharpe from runs where strategy='x' order by created_at asc limit 1",
                   "sharpe >= 0.8")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL sharpe=0.62", r.stdout)

    def test_no_rows_is_a_fail_not_an_error(self) -> None:
        r = self.q("select sharpe from runs where strategy='nope'", "sharpe >= 0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no rows", r.stdout)

    def test_missing_db_is_an_error(self) -> None:
        r = self.q("select 1 as n", "n == 1", db=Path(self.tmp.name) / "missing.sqlite")
        self.assertEqual(r.returncode, 2)
        self.assertIn("missing db", r.stdout)

    def test_query_error_is_an_error(self) -> None:
        r = self.q("select nope from runs", "nope == 1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("query failed", r.stdout)

    def test_escape_attempt_in_assertion_is_an_error(self) -> None:
        r = self.q("select 1 as n", "().__class__.__base__.__subclasses__()")
        self.assertEqual(r.returncode, 2)
        self.assertIn("assert failed to eval", r.stdout)

    def test_unknown_column_name_is_an_error(self) -> None:
        r = self.q("select 1 as n", "m == 1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown name", r.stdout)

    def test_safe_builtins_and_arith_work(self) -> None:
        r = self.q("select count(*) as n, max(sharpe) as top from runs",
                   "n == 3 and round(top, 1) == 1.4 and abs(-1) == 1 and (n > 2 if top > 1 else False)")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_engine_can_be_forced(self) -> None:
        r = self.q("select 1 as n", "n == 1", None, "--engine", "sqlite")
        self.assertEqual(r.returncode, 0, r.stdout)


class RulerWorkspace:
    """A throwaway project with a frozen milestone set. M_PASS passes, M_FAIL fails."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".boil").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_guard.py").write_text("def test_ok():\n    assert True\n")
        (self.root / "src").mkdir()
        self.goal = self.root / ".boil" / "goal.md"
        self.goal.write_text(
            "# Goal\n\n**One-line:** fixture\n\n## Success checklist\n"
            "- [ ] the marker file exists {#M_PASS}\n"
            "- [ ] the second marker exists {#M_FAIL}\n"
            "- [ ] an untagged manual box\n"
            f"- [x] operator approved — EVIDENCE: reviewed | {TODAY} | human\n"
            "\n## Requirements understanding\n\n| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |\n|---|---|---|---|---|\n| a | b | c | 99 | none |\n"
            "\n## How the user will see this works\nrun verify\n")
        spec = {"budget_usd": 0, "cap": 4, "stall": 2, "determinism_runs": 1, "milestones": [
            {"id": "M_PASS", "title": "marker", "check": "test -f out.txt", "kind": "artifact",
             "protect": ["tests/test_guard.py"]},
            {"id": "M_FAIL", "title": "second marker", "check": "test -f never.txt", "kind": "artifact"},
        ]}
        (self.root / ".boil" / "milestones.json").write_text(json.dumps(spec))
        r = run(CHECK, "compile", "--root", str(self.root), "--spec",
                str(self.root / ".boil" / "milestones.json"))
        assert r.returncode == 0, r.stdout + r.stderr

    def make_pass(self) -> None:
        (self.root / "out.txt").write_text("x")

    def verify(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(CHECK, "verify", "--root", str(self.root), *extra)

    def close(self) -> None:
        self.tmp.cleanup()


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = RulerWorkspace()

    def tearDown(self) -> None:
        self.ws.close()

    def test_all_red_reports_gap_with_exit_1(self) -> None:
        r = self.ws.verify("--json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["verdict"], "GAP")
        self.assertEqual((out["green"], out["total"]), (0, 2))
        by = {x["milestone"]: x for x in out["results"]}
        self.assertEqual(by["M_PASS"]["result"], "FAIL")
        self.assertTrue(by["M_PASS"]["counterexample"])

    def test_partial_green_is_still_gap(self) -> None:
        self.ws.make_pass()
        r = self.ws.verify("--json")
        self.assertEqual(r.returncode, 1)
        out = json.loads(r.stdout)
        self.assertEqual((out["green"], out["total"]), (1, 2))

    def test_verify_records_no_attempt(self) -> None:
        self.ws.verify()
        self.assertFalse((self.ws.root / ".boil" / "checks" / "attempts.jsonl").exists())

    def test_tamper_is_exit_50(self) -> None:
        (self.ws.root / "tests" / "test_guard.py").write_text("def test_ok():\n    assert 1\n")
        r = self.ws.verify("--json")
        self.assertEqual(r.returncode, 50, r.stdout)
        self.assertEqual(json.loads(r.stdout)["verdict"], "TAMPER")

    def test_write_stamps_evidence_only_on_passing_tagged_boxes(self) -> None:
        self.ws.make_pass()
        r = self.ws.verify("--write")
        self.assertEqual(r.returncode, 1, r.stdout)
        lines = self.ws.goal.read_text().splitlines()
        passed = next(ln for ln in lines if "{#M_PASS}" in ln)
        failed = next(ln for ln in lines if "{#M_FAIL}" in ln)
        manual = next(ln for ln in lines if "untagged manual" in ln)
        human = next(ln for ln in lines if "| human" in ln)
        self.assertTrue(passed.startswith("- [x]"), passed)
        self.assertIn("EVIDENCE: `test -f out.txt` -> exit 0 |", passed)
        self.assertIn("| auto {#M_PASS}", passed)
        self.assertTrue(failed.startswith("- [ ]"), failed)
        self.assertNotIn("EVIDENCE", failed)
        self.assertTrue(manual.startswith("- [ ]"))
        self.assertEqual(human, f"- [x] operator approved — EVIDENCE: reviewed | {TODAY} | human")

    def test_write_is_idempotent_and_refreshes_the_date(self) -> None:
        self.ws.make_pass()
        self.ws.verify("--write")
        first = self.ws.goal.read_text()
        self.ws.verify("--write")
        self.assertEqual(first, self.ws.goal.read_text())
        self.assertEqual(first.count("EVIDENCE: `test -f out.txt`"), 1)

    def test_write_never_unticks(self) -> None:
        self.ws.make_pass()
        self.ws.verify("--write")
        (self.ws.root / "out.txt").unlink()
        r = self.ws.verify("--write", "--json")
        self.assertEqual(json.loads(r.stdout)["green"], 0)
        passed = next(ln for ln in self.ws.goal.read_text().splitlines() if "{#M_PASS}" in ln)
        self.assertTrue(passed.startswith("- [x]"), "verify --write must never un-tick a box")

    def test_all_green_is_met_exit_0(self) -> None:
        self.ws.make_pass()
        (self.ws.root / "never.txt").write_text("x")
        r = self.ws.verify("--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["verdict"], "MET")


if __name__ == "__main__":
    unittest.main()
