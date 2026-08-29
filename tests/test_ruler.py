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


if __name__ == "__main__":
    unittest.main()
