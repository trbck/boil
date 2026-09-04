"""Unit tests for scripts/research_status.py.

Two real fixtures document the schema (captured from the installed hyperresearch
CLI on 2026-09-04, not invented):
  tests/fixtures/hr-run-status.json  - `hyperresearch run status <tag> --json` stdout
  tests/fixtures/run.json            - the raw manifest that CLI reads

Run with: python3 -m unittest tests.test_research_status -v   (from repo root)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
sys.path.insert(0, SCRIPTS)

import research_status as RS  # noqa: E402


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


class NormalizeTest(unittest.TestCase):
    """The raw manifest lacks `resume`/`escalations`; normalize() must compute
    the same `resume` the real CLI reports for the identical manifest state."""

    def test_computes_resume_matching_the_real_cli_output_for_the_same_manifest(self):
        raw = load_fixture("run.json")
        cli_data = load_fixture("hr-run-status.json")["data"]
        normalized = RS.normalize(raw)
        self.assertEqual(normalized["resume"], cli_data["resume"])

    def test_leaves_an_existing_resume_block_untouched(self):
        cli_data = load_fixture("hr-run-status.json")["data"]
        normalized = RS.normalize(dict(cli_data))
        self.assertEqual(normalized["resume"], cli_data["resume"])

    def test_all_steps_done_yields_no_next_step(self):
        data = {
            "profile_steps": ["1", "2"],
            "steps": {"1": {"status": "done"}, "2": {"status": "done"}},
        }
        normalized = RS.normalize(data)
        self.assertIsNone(normalized["resume"]["next_step"])
        self.assertEqual(normalized["resume"]["done_steps"], ["1", "2"])
        self.assertEqual(normalized["resume"]["remaining_steps"], [])


class FormatStatusLineTest(unittest.TestCase):
    def test_renders_the_documented_shape_from_the_real_fixture(self):
        data = load_fixture("hr-run-status.json")["data"]
        line = RS.format_status_line(data, "probe-tag-a1b2c3")
        self.assertIn("run probe-tag-a1b2c3", line)
        self.assertIn("light", line)
        self.assertIn("step 2 (1/5 done)", line)
        self.assertIn("running", line)
        self.assertIn("0 sources", line)
        self.assertIn("$0.00", line)
        self.assertIn("elapsed", line)

    def test_surfaces_possibly_stalled(self):
        data = load_fixture("hr-run-status.json")["data"]
        data = dict(data)
        data["possibly_stalled"] = True
        line = RS.format_status_line(data, "t")
        self.assertIn("STALLED", line)

    def test_surfaces_blocked_on(self):
        data = load_fixture("hr-run-status.json")["data"]
        data = dict(data)
        data["blocked_on"] = "needs-human-review"
        line = RS.format_status_line(data, "t")
        self.assertIn("blocked: needs-human-review", line)

    def test_all_done_omits_a_next_step_number(self):
        data = {
            "vault_tag": "done-tag", "profile": "light", "status": "done",
            "profile_steps": ["1", "2"],
            "steps": {"1": {"status": "done"}, "2": {"status": "done"}},
            "spend": {"sources_fetched": 5, "estimated_usd": 1.23},
            "started_at": "2026-09-04T18:00:00+00:00",
            "updated_at": "2026-09-04T18:10:00+00:00",
        }
        line = RS.format_status_line(data, "done-tag")
        self.assertIn("(2/2 done)", line)
        self.assertNotIn("step None", line)


class ElapsedTest(unittest.TestCase):
    def test_sub_minute_shown_in_seconds(self):
        elapsed = RS.format_elapsed(
            "2026-09-04T18:31:25.344009+00:00", "2026-09-04T18:31:36.837908+00:00")
        self.assertEqual(elapsed, "11s")

    def test_minutes(self):
        elapsed = RS.format_elapsed(
            "2026-09-04T18:00:00+00:00", "2026-09-04T18:14:00+00:00")
        self.assertEqual(elapsed, "14 min")

    def test_missing_updated_at_returns_none_rather_than_raising(self):
        self.assertIsNone(RS.format_elapsed("2026-09-04T18:00:00+00:00", None))

    def test_garbage_input_returns_none_rather_than_raising(self):
        self.assertIsNone(RS.format_elapsed("not-a-date", "also-not-a-date"))


class LoadStatusTest(unittest.TestCase):
    def test_falls_back_to_the_manifest_file_when_the_cli_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "research", "runs", "fixture-tag")
            os.makedirs(run_dir)
            with open(os.path.join(FIXTURES, "run.json"), encoding="utf-8") as fh:
                manifest = fh.read()
            with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
                fh.write(manifest)
            data, err = RS.load_status("fixture-tag", tmp, cli_path="/no/such/hyperresearch-binary")
            self.assertIsNone(err)
            self.assertEqual(data["vault_tag"], "probe-tag-a1b2c3")

    def test_reports_a_clear_message_when_no_manifest_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, err = RS.load_status("missing-tag", tmp, cli_path="/no/such/hyperresearch-binary")
            self.assertIsNone(data)
            self.assertIn("no run manifest at", err)
            self.assertIn("missing-tag", err)


class MainCliTest(unittest.TestCase):
    def test_prints_a_status_line_for_a_fixture_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "research", "runs", "fixture-tag")
            os.makedirs(run_dir)
            with open(os.path.join(FIXTURES, "run.json"), encoding="utf-8") as fh:
                manifest = fh.read()
            with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
                fh.write(manifest)
            env = dict(os.environ)
            env["PATH"] = "/no/such/dir"  # force the file fallback, no hyperresearch on PATH
            proc = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "research_status.py"),
                 "fixture-tag", "--research-root", tmp],
                capture_output=True, text=True, cwd=ROOT, env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("run probe-tag-a1b2c3", proc.stdout)
            self.assertIn("step 2 (1/5 done)", proc.stdout)

    def test_exits_non_zero_with_clear_message_for_missing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["PATH"] = "/no/such/dir"
            proc = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "research_status.py"),
                 "nope", "--research-root", tmp],
                capture_output=True, text=True, cwd=ROOT, env=env,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("no run manifest at", proc.stdout)


if __name__ == "__main__":
    unittest.main()
