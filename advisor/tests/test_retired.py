"""Retired rules: tombstones that hide a rule from retrieval but keep its ID resolvable."""
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ADV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULE = "ATLB-01-R9"
QUERY = "never reconsider an option you passed on"


class RetiredTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "advisor")
        shutil.copytree(ADV, self.root, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "tests"))
        with open(os.path.join(self.root, "domains", "decisions", "retired.json"), "w") as f:
            json.dump({RULE: {"reason": "test", "date": "2026-09-27", "by": "test"}}, f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_script(self, *args, inp=None):
        return subprocess.run([sys.executable, *args], cwd=self.root, capture_output=True,
                              text=True, input=inp)

    def test_search_hides_retired(self):
        out = self.run_script("scripts/lookup.py", "--domain", "decisions", "--search", QUERY).stdout
        self.assertNotIn(RULE, out)

    def test_include_retired_shows_it(self):
        out = self.run_script("scripts/lookup.py", "--domain", "decisions", "--include-retired",
                              "--search", QUERY).stdout
        self.assertIn(RULE, out)

    def test_rule_lookup_still_resolves_and_marks(self):
        p = self.run_script("scripts/lookup.py", "--rule", RULE)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("RETIRED", p.stdout)

    def test_check_citations_flags_retired(self):
        p = self.run_script("scripts/check_citations.py", "--json", inp="per %s we stop" % RULE)
        self.assertIn(RULE, json.loads(p.stdout)["retired"])
        self.assertEqual(p.returncode, 0)
        strict = self.run_script("scripts/check_citations.py", "--strict", inp="per %s we stop" % RULE)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("RETIRED", strict.stdout)

    def test_save_retired_is_atomic_and_roundtrips(self):
        sys.path.insert(0, os.path.join(self.root, "scripts"))
        try:
            sys.modules.pop("ka_common", None)
            ka_common = importlib.import_module("ka_common")
            ka_common.save_retired("decisions", {"ATLB-01-R3": {"reason": "x", "date": "d", "by": "t"}})
            self.assertIn("ATLB-01-R3", ka_common.load_retired("decisions"))
            self.assertFalse([f for f in os.listdir(os.path.join(self.root, "domains", "decisions"))
                              if f.endswith(".tmp")])
        finally:
            sys.path.pop(0)
            sys.modules.pop("ka_common", None)


if __name__ == "__main__":
    unittest.main()
