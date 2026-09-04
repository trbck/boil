"""Unit tests for scripts/research_note.py.

Run with: python3 -m unittest tests.test_research_note -v   (from repo root)
"""
import datetime
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
sys.path.insert(0, SCRIPTS)

import research_note as RN  # noqa: E402
import ka_common as K  # noqa: E402

REPORT_PATH = os.path.join(FIXTURES, "sample-final-report.md")


def read_report():
    with open(REPORT_PATH, encoding="utf-8") as fh:
        return fh.read()


class FindH1Test(unittest.TestCase):
    def test_finds_the_h1_title(self):
        title = RN.find_h1(read_report())
        self.assertEqual(title, "Cross-sectional momentum decay in small-cap equities")

    def test_returns_none_when_no_h1(self):
        self.assertIsNone(RN.find_h1("## just a section\n\nbody text\n"))


class SanitizeScalarTest(unittest.TestCase):
    def test_colon_round_trips_through_parse_frontmatter(self):
        value = "What is alpha: a definition"
        rendered = "question: %s" % RN.sanitize_scalar(value)
        meta, _ = K.parse_frontmatter("---\n%s\n---\nbody\n" % rendered)
        self.assertEqual(meta["question"], value)

    def test_hash_round_trips_through_parse_frontmatter(self):
        value = "what is the #1 driver of decay"
        rendered = "question: %s" % RN.sanitize_scalar(value)
        meta, _ = K.parse_frontmatter("---\n%s\n---\nbody\n" % rendered)
        self.assertEqual(meta["question"], value)

    def test_bracket_wrapped_value_does_not_get_read_back_as_a_list(self):
        value = "[momentum decay]"
        rendered = "question: %s" % RN.sanitize_scalar(value)
        meta, _ = K.parse_frontmatter("---\n%s\n---\nbody\n" % rendered)
        self.assertEqual(meta["question"], value)
        self.assertIsInstance(meta["question"], str)

    def test_empty_value_round_trips_as_empty_string(self):
        rendered = "question: %s" % RN.sanitize_scalar("")
        meta, _ = K.parse_frontmatter("---\n%s\n---\nbody\n" % rendered)
        self.assertEqual(meta.get("question"), "")


class NormalizeFindingsHeadingTest(unittest.TestCase):
    def test_renames_a_recognised_synonym_to_the_canonical_heading(self):
        body = read_report().split("\n", 1)[1]  # drop the H1 line
        new_body, found = RN.normalize_findings_heading(body)
        self.assertTrue(found)
        self.assertIn("## Key findings", new_body)
        self.assertNotIn("## Recommendations", new_body)

    def test_leaves_body_unchanged_and_reports_not_found_when_no_findings_section(self):
        body = "## Method\n\nsome text\n\n## Open questions\n\nmore text\n"
        new_body, found = RN.normalize_findings_heading(body)
        self.assertFalse(found)
        self.assertEqual(new_body, body)


class WouldBeRulesTest(unittest.TestCase):
    def test_extracts_the_three_recommendation_items_as_rules(self):
        body = read_report().split("\n", 1)[1]
        new_body, _ = RN.normalize_findings_heading(body)
        note_id, rules = RN.compute_rules("Cross-sectional momentum decay", new_body)
        self.assertEqual(len(rules), 3)
        self.assertTrue(rules[0].startswith("Use a 6-month formation window"))
        self.assertEqual(note_id, "NOTE-cross-sectional-momentum-decay")

    def test_no_rules_when_no_findings_section(self):
        note_id, rules = RN.compute_rules("t", "## Method\n\ntext\n")
        self.assertEqual(rules, [])


class BuildMetaTest(unittest.TestCase):
    def test_defaults(self):
        meta = RN.build_meta(title="X title", category=None, topics=None,
                              run_tag=None, question=None, domain=None)
        self.assertEqual(meta["category"], "research")
        self.assertEqual(meta["source"], "hyperresearch")
        self.assertEqual(meta["authority"], "derived")
        self.assertEqual(meta["date"], datetime.date.today().isoformat())
        self.assertNotIn("topics", meta)
        self.assertNotIn("run", meta)
        self.assertNotIn("question", meta)

    def test_topics_run_and_question_are_included_when_given(self):
        meta = RN.build_meta(title="X", category="trading", topics="a,b",
                              run_tag="efield-a3f9b7", question="why: this", domain="trading")
        self.assertEqual(meta["topics"], ["a", "b"])
        self.assertEqual(meta["run"], "efield-a3f9b7")
        self.assertEqual(meta["question"], "why: this")
        self.assertEqual(meta["domain"], "trading")
        self.assertEqual(meta["category"], "trading")


class EndToEndDryRunTest(unittest.TestCase):
    """Exercises the CLI end to end against the fixture report."""

    def test_dry_run_prints_frontmatter_and_would_be_rules_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "inbox")
            os.makedirs(out_dir)
            proc = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "research_note.py"),
                 "--report", REPORT_PATH, "--question", "how does momentum decay: small caps",
                 "--out", out_dir, "--dry-run"],
                capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("title: Cross-sectional momentum decay in small-cap equities", proc.stdout)
            self.assertIn("source: hyperresearch", proc.stdout)
            note_id = "NOTE-%s" % K.slug("Cross-sectional momentum decay in small-cap equities", 32)
            self.assertIn("%s-R1" % note_id, proc.stdout)
            self.assertIn("%s-R3" % note_id, proc.stdout)
            self.assertEqual(os.listdir(out_dir), [])

    def test_real_run_writes_a_note_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "inbox")
            os.makedirs(out_dir)
            cmd = [sys.executable, os.path.join(SCRIPTS, "research_note.py"),
                   "--report", REPORT_PATH, "--out", out_dir]
            proc1 = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc1.returncode, 0, proc1.stderr)
            files1 = os.listdir(out_dir)
            self.assertEqual(len(files1), 1)

            proc2 = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc2.returncode, 0, proc2.stderr)
            files2 = sorted(os.listdir(out_dir))
            self.assertEqual(len(files2), 2)
            self.assertTrue(any(f.endswith("-2.md") for f in files2))

            with open(os.path.join(out_dir, files1[0]), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("## Key findings", text)
            self.assertIn("authority: derived", text)

    def test_written_note_frontmatter_round_trips_a_colon_and_hash_bearing_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "inbox")
            os.makedirs(out_dir)
            question = "what is the #1 driver: momentum or cost?"
            proc = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "research_note.py"),
                 "--report", REPORT_PATH, "--question", question, "--out", out_dir],
                capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = os.path.join(out_dir, os.listdir(out_dir)[0])
            with open(written, encoding="utf-8") as fh:
                text = fh.read()
            meta, _ = K.parse_frontmatter(text)
            self.assertEqual(meta["question"], question)


if __name__ == "__main__":
    unittest.main()
