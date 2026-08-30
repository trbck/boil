"""The boil side of the boil<->helm contract. Skipped when helm is not checked out next door.

Files, not imports: boil writes, helm reads. This test writes with boil's real scripts and reads
with helm's real parsers (`cockpit.shell_session`, `cockpit.parse_now`, `cockpit.verify_summary`),
so a change on either side that breaks the other fails here — the class of failure that let
helm v2 silently stop receiving boil's status.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELM = Path(os.environ.get("HELM_DIR") or Path.home() / "workspace" / "helm")
CHECK = ROOT / "scripts" / "boil-check.py"
LOG = ROOT / "scripts" / "boil-helm-log.py"


def helm_cockpit():
    if not (HELM / "cockpit.py").is_file():
        return None
    sys.path.insert(0, str(HELM))
    import cockpit  # noqa: E402
    return cockpit


@unittest.skipUnless((HELM / "cockpit.py").is_file(), "helm not checked out")
class HelmContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cockpit = helm_cockpit()
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.fake_helm = t / "helm"
        self.fake_helm.mkdir()
        (self.fake_helm / "server.py").write_text("# fake v2\n")
        self.proj = t / "proj"
        (self.proj / ".boil").mkdir(parents=True)
        (self.proj / "src").mkdir()
        (self.proj / "tests").mkdir()
        (self.proj / "tests" / "t.py").write_text("x = 1\n")
        (self.proj / ".boil" / "goal.md").write_text(
            "# Goal\n\n**One-line:** a thing\n\n## Success checklist\n- [ ] the marker exists\n\n"
            "## Requirements understanding\n| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |\n"
            "|---|---|---|---|---|\n| a | b | c | 95 | none |\n\n## How the user will see this works\nls\n")
        (self.proj / ".boil" / "milestones.json").write_text(json.dumps({"budget_usd": 1.0, "review": {"enabled": False},
            "milestones": [{"id": "M1", "title": "the marker exists", "check": "test -f marker.txt", "protect": ["tests"]}]}))
        for cmd in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"], ["add", "-A"], ["commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", str(self.proj), *cmd], check=True, capture_output=True)
        self.env = dict(os.environ, HELM_DIR=str(self.fake_helm), BOIL_DIR=str(ROOT))
        self.env.pop("BOIL_NO_HELM", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def boil(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CHECK), *args, "--root", str(self.proj)], text=True,
                              capture_output=True, env=self.env)

    def test_a_controller_iteration_lands_on_the_cockpit(self) -> None:
        self.assertEqual(self.boil("compile", "--spec", str(self.proj / ".boil" / "milestones.json")).returncode, 0)
        self.assertEqual(self.boil("prepare", "--allow-unguarded").returncode, 0)
        (self.proj / "marker.txt").write_text("x")
        r = self.boil("score", "--milestone", "M1", "--no-review", "--spent-usd", "0.10")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.cockpit.shell_session("proj", self.fake_helm / "runs")
        self.assertIsNotNone(s, "helm's cockpit could not read the session boil wrote")
        self.assertTrue(s["live"])
        self.assertEqual(s["ticket"], "M1")
        self.assertIn("PASS", s["message"])
        os.environ["BOIL_DIR"] = str(ROOT)
        now = self.cockpit.now_summary(self.proj)
        self.assertEqual(now["green"], 1)
        self.assertIn("1/1 green", now["measured"])
        v = self.cockpit.verify_summary(self.proj)
        self.assertIsNotNone(v)
        self.assertEqual(v["verdict"], "MET")

    def test_helm_can_read_boils_version(self) -> None:
        r = subprocess.run([sys.executable, str(CHECK), "--version"], text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout.strip(), r"^boil-check \d+\.\d+\.\d+$")
        self.assertTrue(self.cockpit.boil_version_ok(ROOT), "helm's MIN_BOIL_VERSION is above this checkout")


if __name__ == "__main__":
    unittest.main()
