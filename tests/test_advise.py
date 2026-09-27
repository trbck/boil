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



GOAL = """# Goal: tune the entry filter

advisor_domains: decisions

- [ ] Pick an entry filter within 20 variants
"""
Q = "Stop tuning or keep searching?"
GOOD = "ANSWER: Stop and commit to the current best | RULES: ATLB-01-R9 | WHY: goal caps search at 20 variants"


def load_advise():
    import importlib.util
    spec = importlib.util.spec_from_file_location("boil_advise", ADVISE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DecideRecordCase(CorpusCase):
    def setUp(self):
        super().setUp()
        self.proj = self.tmp / "proj"
        (self.proj / ".boil").mkdir(parents=True)
        (self.proj / ".boil" / "goal.md").write_text(GOAL)

    def record(self, verdict, question=Q, *extra):
        return run("record", "--project", str(self.proj), "--question", question,
                   "--verdict", verdict, "--no-log", *extra, env=self.env)

    def decisions(self):
        p = self.proj / ".boil" / "decisions.md"
        return p.read_text() if p.exists() else ""


class DecideTest(DecideRecordCase):
    def decide(self, question, env=None):
        return run("decide", "--project", str(self.proj), "--question", question, env=env or self.env)

    def test_packet_has_question_goal_rules_and_format(self):
        p = self.decide("when to stop searching")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("when to stop searching", p.stdout)
        self.assertIn("Pick an entry filter", p.stdout)
        self.assertIn("ATLB-01-R", p.stdout)
        self.assertIn("ANSWER:", p.stdout)
        self.assertIn("ASK-HUMAN:", p.stdout)

    def test_retired_rules_absent_from_packet(self):
        run("retire", "ATLB-01-R9", "--reason", "x", env=self.env)
        p = self.decide("never reconsider an option you passed on")
        self.assertNotIn("ATLB-01-R9", p.stdout)

    def test_unknown_domain_falls_back(self):
        (self.proj / ".boil" / "goal.md").write_text(GOAL.replace("decisions", "astrology"))
        p = self.decide("when to stop searching")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("astrology", p.stderr)
        self.assertIn("ATLB-01-R", p.stdout)

    def test_advisor_missing_exits_3(self):
        p = self.decide("q", env=dict(self.env, BOIL_ADVISOR_ROOT=str(self.tmp / "nope")))
        self.assertEqual(p.returncode, 3)


class RecordTest(DecideRecordCase):
    def assertRejected(self, verdict, prefix, question=Q):
        p = self.record(verdict, question)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertTrue(p.stderr.startswith(prefix), p.stderr)
        self.assertEqual(self.decisions(), "")

    def test_accepts_and_logs(self):
        p = self.record(GOOD)
        self.assertEqual(p.returncode, 0, p.stderr)
        text = self.decisions()
        self.assertIn("## D-0001", text)
        self.assertIn("rules: ATLB-01-R9", text)
        self.assertIn("veto: –", text)
        self.assertEqual(self.record(GOOD, "another question").returncode, 0)
        self.assertIn("## D-0002", self.decisions())

    def test_ask_human(self):
        self.assertRejected("ASK-HUMAN: no rule fits", "ask-human:")

    def test_malformed(self):
        self.assertRejected("just do it", "malformed:")

    def test_chapter_citation_rejected(self):
        self.assertRejected("ANSWER: stop | RULES: ATLB-01 | WHY: w", "no-rule:")

    def test_unknown_id(self):
        self.assertRejected("ANSWER: stop | RULES: ATLB-01-R999 | WHY: w", "unknown:")

    def test_retired_after_decide_rejected(self):
        run("retire", "ATLB-01-R9", "--reason", "x", env=self.env)
        self.assertRejected(GOOD, "retired:")

    def test_conflict(self):
        # conflicts.md T1: ATLB-01-R9 (Ch.1 row) vs ATLB-02-R13 (Ch.2 row)
        self.assertRejected("ANSWER: stop | RULES: ATLB-01-R9, ATLB-02-R13 | WHY: w", "conflict:")

    def test_same_row_is_not_conflict(self):
        p = self.record("ANSWER: stop | RULES: ATLB-01-R3, ATLB-01-R9 | WHY: w")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_hedged(self):
        self.assertRejected("ANSWER: it depends | RULES: ATLB-01-R9 | WHY: w", "hedged:")

    def test_advisor_missing_rejects(self):
        env = dict(self.env, BOIL_ADVISOR_ROOT=str(self.tmp / "nope"))
        p = run("record", "--project", str(self.proj), "--question", Q, "--verdict", GOOD,
                "--no-log", env=env)
        self.assertEqual(p.returncode, 3)

    def test_multiline_question_roundtrips(self):
        q = "line one\nline two | with: colons"
        self.assertEqual(self.record(GOOD, q).returncode, 0)
        entries = load_advise().parse_decisions(self.decisions())
        self.assertEqual(entries[0]["question"], q)
        self.assertEqual(entries[0]["rules"], ["ATLB-01-R9"])


TICKET = """---
id: T-0041
title: pick filter
type: human-action
status: blocked
priority: P0
human_action:
  required: true
  kind: decision
  reason: "stall"
  safe_summary: "Stop tuning or keep searching?"
---
body
"""


class SweepTest(DecideRecordCase):
    def setUp(self):
        super().setUp()
        (self.proj / ".boil" / "tickets").mkdir()
        self.tpath = self.proj / ".boil" / "tickets" / "T-0041-pick-filter.md"
        self.tpath.write_text(TICKET)
        self.dpath = self.proj / ".boil" / "decisions.md"

    def sweep(self):
        return run("sweep", "--project", str(self.proj), env=self.env)

    def test_accept_unblocks_ticket_and_veto_reblocks(self):
        self.assertEqual(self.record(GOOD, Q, "--ticket", "T-0041").returncode, 0)
        t = self.tpath.read_text()
        self.assertIn("status: open", t)
        self.assertIn("  required: false", t)
        self.assertIn("  advised: D-0001", t)
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto: wrong domain"))
        p = self.sweep()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1 reopened", p.stdout)
        t = self.tpath.read_text()
        self.assertIn("status: blocked", t)
        self.assertIn("  required: true", t)
        self.assertIn("veto: wrong domain (swept)", self.dpath.read_text())
        # the same question with the same rules can no longer auto-decide
        p = self.record(GOOD, Q)
        self.assertEqual(p.returncode, 3)
        self.assertTrue(p.stderr.startswith("vetoed:"), p.stderr)

    def test_sweep_idempotent(self):
        self.record(GOOD, Q, "--ticket", "T-0041")
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto: no"))
        self.sweep()
        before = (self.tpath.read_text(), self.dpath.read_text())
        p = self.sweep()
        self.assertIn("0 reopened", p.stdout)
        self.assertEqual(before, (self.tpath.read_text(), self.dpath.read_text()))

    def test_boil_now_runs_the_sweep(self):
        self.record(GOOD, Q, "--ticket", "T-0041")
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto: no"))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-now.py"), "--root", str(self.proj)],
                       capture_output=True, text=True, env=self.env)
        self.assertIn("status: blocked", self.tpath.read_text())
        self.assertIn("veto: no (swept)", self.dpath.read_text())

    def now(self):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "boil-now.py"), "--root", str(self.proj)],
                              capture_output=True, text=True, env=self.env).stdout

    def lint(self):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "ticket-lint.py"), str(self.tpath)],
                              capture_output=True, text=True)

    def test_advised_ticket_is_not_blocked_on_you_and_lints(self):
        self.assertIn("T-0041", self.now().split("## Blocked on you")[1] if "## Blocked on you" in self.now() else "")
        self.record(GOOD, Q, "--ticket", "T-0041")
        self.assertNotIn("## Blocked on you", self.now())
        lint = self.lint()
        self.assertNotIn("human-required", lint.stdout + lint.stderr)
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto: no"))
        self.assertIn("## Blocked on you", self.now())       # the sweep inside boil-now reopened it
        self.assertNotIn("human-required", (lambda l: l.stdout + l.stderr)(self.lint()))

    def test_no_decisions_file(self):
        p = self.sweep()
        self.assertEqual(p.returncode, 0)
        self.assertIn("0 reopened", p.stdout)

    def test_malformed_entry_skipped_not_rewritten(self):
        self.dpath.write_text("## D-0001 · garbage\nnot a field\n")
        p = self.sweep()
        self.assertEqual(p.returncode, 0)
        self.assertIn("skipped", p.stderr)
        self.assertEqual(self.dpath.read_text(), "## D-0001 · garbage\nnot a field\n")


BRAKE_TICKET = TICKET.replace("  kind: decision\n", "").replace('reason: "stall"', 'reason: "budget spent"')


class ReviewFixTest(DecideRecordCase):
    """Findings from the whole-branch review, each reproduced first."""
    def setUp(self):
        super().setUp()
        self.tdir = self.proj / ".boil" / "tickets"
        self.tdir.mkdir()
        self.dpath = self.proj / ".boil" / "decisions.md"

    def ticket(self, name, text):
        p = self.tdir / name
        p.write_text(text)
        return p

    def test_brake_ticket_cannot_be_advised(self):
        t = self.ticket("T-0001-budget.md", BRAKE_TICKET.replace("T-0041", "T-0001"))
        p = self.record(GOOD, Q, "--ticket", "T-0001")
        self.assertEqual(p.returncode, 3, p.stdout)
        self.assertTrue(p.stderr.startswith("not-advisable:"), p.stderr)
        self.assertIn("status: blocked", t.read_text())
        self.assertEqual(self.decisions(), "")

    def test_missing_ticket_is_rejected_before_logging(self):
        p = self.record(GOOD, Q, "--ticket", "T-0077")
        self.assertEqual(p.returncode, 3)
        self.assertEqual(self.decisions(), "")

    def test_ticket_prefix_never_matches_another_ticket(self):
        other = self.ticket("T-10-other.md", TICKET.replace("T-0041", "T-10"))
        self.assertEqual(self.record(GOOD, Q, "--ticket", "T-1").returncode, 3)
        self.assertIn("status: blocked", other.read_text())

    def test_flip_touches_only_frontmatter_and_human_action(self):
        text = TICKET.replace("priority: P0\n", "priority: P0\nreview:\n  required: true\n").replace(
            "body\n", "body\nstatus: this line is prose\n  required: prose too\n")
        t = self.ticket("T-0041-pick.md", text)
        self.assertEqual(self.record(GOOD, Q, "--ticket", "T-0041").returncode, 0)
        out = t.read_text()
        self.assertIn("review:\n  required: true", out)
        self.assertIn("status: this line is prose\n  required: prose too", out)
        self.assertIn("human_action:\n  advised: D-0001\n  required: false", out)
        self.assertIn("\nstatus: open\n", out)

    def test_decide_accepts_ticket_flag(self):
        p = run("decide", "--project", str(self.proj), "--question", "when to stop searching",
                "--ticket", "T-0041", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--ticket T-0041", p.stdout)

    def test_veto_without_space_sweeps_only_its_entry(self):
        self.record(GOOD, "first")
        self.record(GOOD, "second")
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto:wrong call", 1))
        run("sweep", "--project", str(self.proj), env=self.env)
        entries = load_advise().parse_decisions(self.dpath.read_text())
        self.assertTrue(entries[0]["swept"])
        self.assertFalse(entries[1]["vetoed"], entries[1]["veto"])

    def test_every_line_break_character_is_escaped(self):
        q = "a\rb c\x0cd\x85e\\nf"
        self.assertEqual(self.record(GOOD, q).returncode, 0)
        self.record(GOOD, "next")
        entries = load_advise().parse_decisions(self.dpath.read_text())
        self.assertEqual([e["id"] for e in entries], ["D-0001", "D-0002"])
        self.assertEqual(entries[0]["question"], q)

    def test_bad_ticket_id_rejected(self):
        self.assertEqual(self.record(GOOD, Q, "--ticket", "T 9").returncode, 3)
        self.assertEqual(self.decisions(), "")

    def test_mixed_chapter_and_rule_citation_rejected(self):
        p = self.record("ANSWER: stop | RULES: ATLB-01, ATLB-01-R3 | WHY: w")
        self.assertEqual(p.returncode, 3)
        self.assertTrue(p.stderr.startswith("no-rule:"), p.stderr)

    def test_veto_blocks_the_question_whatever_rules_are_cited(self):
        self.ticket("T-0041-pick.md", TICKET)
        self.record(GOOD, Q, "--ticket", "T-0041")
        self.dpath.write_text(self.dpath.read_text().replace("veto: –", "veto: no"))
        run("sweep", "--project", str(self.proj), env=self.env)
        wider = "ANSWER: stop | RULES: ATLB-01-R9, ATLB-01-R3 | WHY: w"
        self.assertTrue(self.record(wider, Q).stderr.startswith("vetoed:"))
        self.assertTrue(self.record(wider, "reworded", "--ticket", "T-0041").stderr.startswith("vetoed:"))

if __name__ == "__main__":
    unittest.main()
