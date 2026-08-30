"""The helm bridge under the controller.

helm's cockpit shows a shell session from `runs/sessions/<project>.json` — a file that, until
now, only got written when the LLM remembered to call the `helm_status` MCP tool. Under the
controller the script owns the iteration, so the script reports it: `prepare` and `score`
emit status events, and every emit upserts the dashboard's session file in the schema
`helm_mcp.py` writes. The snapshot and STATUS.md know milestones, not only tickets.
Everything here runs against a fake HELM_DIR — a test must never write into the operator's helm.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "scripts" / "boil-helm-log.py"
CHECK = ROOT / "scripts" / "boil-check.py"


def fake_helm(tmp: Path) -> Path:
    hd = tmp / "helm"
    hd.mkdir()
    (hd / "helm.py").write_text("# fake\n")
    return hd


def run(script: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, env=env)


class EmitUpsertsDashboardSessionTest(unittest.TestCase):
    def test_emit_writes_the_shell_session_file_the_cockpit_reads(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            hd = fake_helm(tmp)
            proj = tmp / "proj"
            (proj / ".boil").mkdir(parents=True)
            (proj / ".boil" / "goal.md").write_text("# Goal\n**One-line:** a thing\n\n- [ ] box one\n")
            env = dict(os.environ, HELM_DIR=str(hd))
            env.pop("BOIL_NO_HELM", None)
            r = run(LOG, "emit", "--root", str(proj), "--kind", "boil.score", "--ticket", "M1",
                    "--attempt", "2", "--status", "PASS", "--detail", "EVIDENCE: `test -f x` -> exit 0", env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            sp = hd / "runs" / "sessions" / "proj.json"
            self.assertTrue(sp.is_file(), "the dashboard's session file was not written")
            s = json.loads(sp.read_text())
            self.assertEqual(s["project"], "proj")
            self.assertEqual(s["path"], str(proj))
            self.assertEqual(s["ticket"], "M1")
            self.assertIn("PASS", s["message"])
            self.assertIn("M1", s["message"])
            self.assertTrue(s["phase"])
            dt.datetime.strptime(s["updated"], "%Y-%m-%dT%H:%M:%S.%fZ")      # the cockpit's exact format
            self.assertEqual(s["events"][-1]["kind"], "boil.score")
            lines = (hd / "runs" / "sessions" / "proj.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(lines[-1])["project"], "proj")
            # the operator's own MCP fields are never clobbered by a boil emit
            s["demo"] = "kept"; s["blocked"] = "kept"
            sp.write_text(json.dumps(s))
            run(LOG, "emit", "--root", str(proj), "--kind", "boil.prepare", "--ticket", "M2", "--status", "dispatch", env=env)
            s2 = json.loads(sp.read_text())
            self.assertEqual(s2["demo"], "kept")
            self.assertEqual(s2["blocked"], "kept")
            self.assertEqual(s2["ticket"], "M2")

    def test_boil_no_helm_keeps_everything_local(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            hd = fake_helm(tmp)
            proj = tmp / "proj"
            (proj / ".boil").mkdir(parents=True)
            (proj / ".boil" / "goal.md").write_text("# Goal\n**One-line:** a thing\n")
            env = dict(os.environ, HELM_DIR=str(hd), BOIL_NO_HELM="1")
            r = run(LOG, "emit", "--root", str(proj), "--kind", "boil.score", "--status", "PASS", env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse((hd / "runs").exists())
            self.assertTrue((proj / ".boil" / "status.jsonl").is_file())


class MilestoneAwareSnapshotTest(unittest.TestCase):
    def test_snapshot_and_status_md_carry_milestones(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t)
            checks = proj / ".boil" / "checks"
            checks.mkdir(parents=True)
            (proj / ".boil" / "goal.md").write_text("# Goal\n**One-line:** a thing\n\n- [ ] box one {#M1}\n- [ ] box two {#M2}\n")
            (checks / "frozen.json").write_text(json.dumps({"budget_usd": 5, "cap": 4, "stall": 2, "milestones": [
                {"id": "M1", "title": "one", "check": "test -f a", "tier": "T1", "after": [], "hash": "x", "must_have": True},
                {"id": "M2", "title": "two", "check": "test -f b", "tier": "T2", "after": ["M1"], "hash": "y", "must_have": True}]}))
            (checks / "attempts.jsonl").write_text(
                json.dumps({"ts": "t", "milestone": "M1", "attempt": 1, "result": "FAIL", "counterexample": "AssertionError: 1 != 2", "spent_usd": 0.5}) + "\n"
                + json.dumps({"ts": "t", "milestone": "M1", "attempt": 2, "result": "FAIL", "counterexample": "AssertionError: 1 != 3", "spent_usd": 0.5}) + "\n")
            (checks / "iteration.json").write_text(json.dumps({"milestone": "M1", "attempt": 3, "head": "abc", "packet": ".boil/dispatch/M1.md"}))
            env = dict(os.environ, BOIL_NO_HELM="1")
            r = run(LOG, "session", "--root", str(proj), "--json", env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            snap = json.loads(r.stdout)
            ms = {m["id"]: m for m in snap["milestones"]}
            self.assertEqual(ms["M1"]["attempts"], 2)
            self.assertEqual(ms["M1"]["result"], "FAIL")
            self.assertIn("1 != 3", ms["M1"]["counterexample"])
            self.assertEqual(ms["M2"]["result"], "-")
            self.assertEqual(snap["status"], "running")               # an unscored iteration is in flight
            self.assertEqual(snap["iteration"], "M1#3")
            self.assertEqual(snap["counts"]["milestones_green"], 0)
            self.assertEqual(snap["counts"]["milestones"], 2)
            r = run(LOG, "session", "--root", str(proj), env=env)
            self.assertIn("| M1 |", r.stdout)
            self.assertIn("Milestones", r.stdout)


class ControllerEmitsStatusTest(unittest.TestCase):
    def test_prepare_and_score_report_to_helm_without_an_mcp_call(self) -> None:
        sys.path.insert(0, str(ROOT / "tests"))
        from test_iteration import Project  # noqa: E402  — the W1 fixture
        p = Project()
        try:
            with tempfile.TemporaryDirectory() as t:
                hd = fake_helm(Path(t))
                env = dict(os.environ, HELM_DIR=str(hd))
                env.pop("BOIL_NO_HELM", None)
                self.assertEqual(run(CHECK, "compile", "--root", str(p.root), "--spec",
                                     str(p.spec()), env=env).returncode, 0)
                self.assertEqual(run(CHECK, "prepare", "--root", str(p.root), env=env).returncode, 0)
                (p.root / "one.txt").write_text("x")
                r = run(CHECK, "score", "--root", str(p.root), "--milestone", "M1", "--no-review", env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                kinds = [json.loads(ln)["kind"] for ln in (p.root / ".boil" / "status.jsonl").read_text().splitlines()]
                self.assertIn("boil.prepare", kinds)
                self.assertIn("boil.score", kinds)
                s = json.loads((hd / "runs" / "sessions" / f"{p.root.name}.json").read_text())
                self.assertEqual(s["ticket"], "M1")
                self.assertIn("PASS", s["message"])
                self.assertEqual(s["iteration"], "M1#1")
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()


class HelmDirDetectionTest(unittest.TestCase):
    """Found live: helm v2 has no helm.py (server.py + helm_mcp.py), so the bridge silently
    skipped the real helm since its restart."""

    def test_a_v2_helm_checkout_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            hd = tmp / "helm"
            hd.mkdir()
            (hd / "server.py").write_text("# v2\n")
            (hd / "helm_mcp.py").write_text("# v2\n")
            proj = tmp / "proj"
            (proj / ".boil").mkdir(parents=True)
            (proj / ".boil" / "goal.md").write_text("# Goal\n**One-line:** a thing\n")
            env = dict(os.environ, HELM_DIR=str(hd))
            env.pop("BOIL_NO_HELM", None)
            r = run(LOG, "emit", "--root", str(proj), "--kind", "boil.score", "--status", "PASS", "--json", env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((hd / "runs" / "sessions" / "proj.json").is_file())
            self.assertIn('"session": "written"', r.stdout)
