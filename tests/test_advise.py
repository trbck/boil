"""boil advise: the advisor as a boil subcommand, and the decide/record contract.

Every test works on a private copy of the corpus (BOIL_ADVISOR_ROOT), so retiring a rule
never touches the real one, and every record passes --no-log so nothing reaches helm.

Run: python3 -m unittest tests.test_advise
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADVISE = ROOT / "scripts" / "boil-advise.py"
ADVISOR = ROOT / "advisor"


def run(*args, env=None, cwd=None, inp=None):
    return subprocess.run([sys.executable, str(ADVISE), *args], capture_output=True, text=True,
                          env=env, cwd=cwd, input=inp)


class CorpusCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.adv = self.tmp / "advisor"
        shutil.copytree(ADVISOR, self.adv,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "tests"))
        self.env = dict(os.environ, BOIL_ADVISOR_ROOT=str(self.adv))

    def tearDown(self):
        shutil.rmtree(self.tmp)


class PassthroughTest(CorpusCase):
    def test_lookup_is_byte_identical(self):
        args = ["--domain", "decisions", "--search", "when to stop searching"]
        direct = subprocess.run([sys.executable, str(self.adv / "scripts" / "lookup.py"), *args],
                                capture_output=True, text=True)
        via = run("lookup", *args, env=self.env)
        self.assertEqual(via.returncode, direct.returncode)
        self.assertEqual(via.stdout, direct.stdout)

    def test_lookup_needs_no_boil_dir(self):
        p = run("lookup", "--list", "domains", env=self.env, cwd=str(self.tmp))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("decisions", p.stdout)

    def test_exit_status_forwarded(self):
        p = run("lookup", "--rule", "NOPE-99-R1", env=self.env)
        self.assertNotEqual(p.returncode, 0)


class RetireTest(CorpusCase):
    def retired(self):
        return json.loads((self.adv / "domains" / "decisions" / "retired.json").read_text())

    def test_retire_then_unretire(self):
        p = run("retire", "ATLB-01-R9", "--reason", "superseded", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.retired()["ATLB-01-R9"]["reason"], "superseded")
        self.assertEqual(run("unretire", "ATLB-01-R9", env=self.env).returncode, 0)
        self.assertNotIn("ATLB-01-R9", self.retired())

    def test_retire_keeps_other_tombstones(self):
        run("retire", "ATLB-01-R9", "--reason", "a", env=self.env)
        run("retire", "atlb-01-r3", "--reason", "b", env=self.env)
        self.assertEqual(sorted(self.retired()), ["ATLB-01-R3", "ATLB-01-R9"])
        self.assertNotIn("domain", self.retired()["ATLB-01-R9"])

    def test_retire_unknown_id_fails(self):
        self.assertEqual(run("retire", "ATLB-99-R99", "--reason", "x", env=self.env).returncode, 2)

    def test_unretire_not_retired_fails(self):
        self.assertEqual(run("unretire", "ATLB-01-R9", env=self.env).returncode, 2)

    def test_retire_requires_reason(self):
        self.assertNotEqual(run("retire", "ATLB-01-R9", env=self.env).returncode, 0)


if __name__ == "__main__":
    unittest.main()
