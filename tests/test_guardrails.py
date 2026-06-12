from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cmd(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class GuardrailScriptsTest(unittest.TestCase):
    def test_ticket_lint_accepts_valid_human_action_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tickets = root / ".boil" / "tickets"
            tickets.mkdir(parents=True)
            (tickets / "T-0001.md").write_text(
                """---
id: T-0001
title: Provide test API key
type: human-action
specialty: general
status: blocked
priority: P0
proof_strategy: verification-only
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
human_action:
  required: true
  reason: "User needs to add the API key locally."
  safe_summary: "Add the missing API key locally, then ask boil to continue."
  susi_task_id: ""
  susi_sync_status: pending
  pushover_status: pending
working_on: "blocked on user action: add missing API key"
---

## Context
Safe, secret-free blocker.
""",
                encoding="utf-8",
            )
            proc = run_cmd(sys.executable, str(ROOT / "scripts" / "ticket-lint.py"), "--root", str(root), "--json")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(data["ok"])

    def test_ticket_lint_rejects_possible_secret(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tickets = root / ".boil" / "tickets"
            tickets.mkdir(parents=True)
            (tickets / "T-0001.md").write_text(
                """---
id: T-0001
title: Bad ticket
type: bug
specialty: backend
status: open
priority: P1
proof_strategy: red-green
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
working_on: ""
---

api_key = "abcdefghijklmnopqrstuvwx"
""",
                encoding="utf-8",
            )
            proc = run_cmd(sys.executable, str(ROOT / "scripts" / "ticket-lint.py"), "--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("possible-secret", proc.stdout)

    def test_ticket_lint_rejects_done_ticket_without_confidence_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tickets = root / ".boil" / "tickets"
            tickets.mkdir(parents=True)
            (tickets / "T-0001.md").write_text(
                """---
id: T-0001
title: Done without enough proof
type: feature
specialty: backend
status: done
priority: P1
proof_strategy: red-green
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
confidence:
  requirements_understood: 99
  implementation_matches: 80
  verification_working: 99
  evidence: []
  uncertainty:
    - "No adversarial retest yet."
working_on: "done"
---

## Context
This should fail the confidence gate.
""",
                encoding="utf-8",
            )
            proc = run_cmd(sys.executable, str(ROOT / "scripts" / "ticket-lint.py"), "--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("low-confidence", proc.stdout)
            self.assertIn("missing-confidence-evidence", proc.stdout)
            self.assertIn("remaining-uncertainty", proc.stdout)

    def test_vibe_check_flags_summary_without_demo_or_next_steps(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            summary = Path(td) / "summary.md"
            summary.write_text("Implemented the dashboard fix.\n\nTests: should pass.\n", encoding="utf-8")
            proc = run_cmd(sys.executable, str(ROOT / "scripts" / "vibe-check.py"), str(summary), "--json")
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            codes = {item["code"] for item in data["issues"]}
            self.assertIn("missing-demo", codes)
            self.assertIn("missing-next", codes)
            self.assertIn("speculative-language", codes)

    def test_susi_bridge_dry_run_has_normalized_contract(self) -> None:
        bridge = ROOT / ".susi-human-blockers" / "add_blocker.py"
        if not bridge.exists():
            self.skipTest("local ignored Susi bridge is not installed")
        proc = run_cmd(
            sys.executable,
            str(bridge),
            "--project-root",
            "/tmp/example-project",
            "--ticket",
            ".boil/tickets/T-0043.md",
            "--summary",
            "Add the missing API key locally, then ask boil to continue.",
            "--dry-run",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["susi_sync_status"], "dry_run")
        self.assertEqual(data["pushover_status"], "dry_run")
        self.assertIn("payload", data)
        self.assertIn("pushover", data)

    def test_story_run_all_empty_directory_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            stories = Path(td) / "stories"
            stories.mkdir()
            proc = run_cmd(
                sys.executable,
                str(ROOT / "scripts" / "story-run.py"),
                "--all",
                "--stories-dir",
                str(stories),
                "--json",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(json.loads(proc.stdout), {})

    def test_story_run_missing_story_is_infra_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            stories = Path(td) / "stories"
            stories.mkdir()
            proc = run_cmd(
                sys.executable,
                str(ROOT / "scripts" / "story-run.py"),
                "STORY-404",
                "--stories-dir",
                str(stories),
                "--json",
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("missing", proc.stderr)

    def test_doctor_passes_minimal_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            boil = root / ".boil"
            (boil / "tickets").mkdir(parents=True)
            (boil / "goal.md").write_text(
                """# Goal

## Requirements understanding

| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---:|---|
| Test doctor | Validate a minimal workspace | doctor exits 0 | 99 | none |
""",
                encoding="utf-8",
            )
            for name in ("memory.md", "implementation.md", "bugs.md", "routing.md"):
                (boil / name).write_text(f"# {name}\n", encoding="utf-8")
            (boil / "tickets" / "T-0001.md").write_text(
                """---
id: T-0001
title: Add smoke proof
type: test
specialty: verification
status: open
priority: P1
proof_strategy: verification-only
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
working_on: ""
---

## Context
Minimal valid ticket.
""",
                encoding="utf-8",
            )
            proc = run_cmd(
                sys.executable,
                str(ROOT / "scripts" / "boil-doctor.py"),
                "--root",
                str(root),
                "--skill-root",
                str(ROOT),
                "--json",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_sync_agents_and_dispatch_packet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            boil = root / ".boil"
            tickets = boil / "tickets"
            tickets.mkdir(parents=True)
            (boil / "goal.md").write_text("# Goal\n\n## Requirements understanding\n\nAcceptance signal\nConfidence\n", encoding="utf-8")
            (boil / "memory.md").write_text("# Memory\n", encoding="utf-8")
            (tickets / "T-0001.md").write_text(
                """---
id: T-0001
title: Packet ticket
type: test
specialty: verification
status: open
priority: P1
proof_strategy: verification-only
opened_by: orchestrator
opened_at: 2026-06-10T09:30:00Z
blocked_by: []
working_on: ""
---

## Context
Packet test.
""",
                encoding="utf-8",
            )
            sync = run_cmd(sys.executable, str(ROOT / "scripts" / "boil-sync-agents.py"), "--root", str(root), "--skill-root", str(ROOT))
            self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / ".cursor" / "rules" / "boil.mdc").exists())
            packet = run_cmd(sys.executable, str(ROOT / "scripts" / "boil-dispatch-packet.py"), "T-0001", "--root", str(root))
            self.assertEqual(packet.returncode, 0, packet.stdout + packet.stderr)
            self.assertTrue((boil / "dispatch" / "T-0001.md").exists())

    def test_debug_mode_and_pr_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iter_dir = root / ".boil" / "iterations" / "iter-001"
            iter_dir.mkdir(parents=True)
            (root / ".boil" / "goal.md").write_text("# Goal\n\nDemo goal.\n", encoding="utf-8")
            (iter_dir / "summary.md").write_text("# Iteration 1\n\nImplemented.\n", encoding="utf-8")
            debug = run_cmd(
                sys.executable,
                str(ROOT / "scripts" / "boil-debug-mode.py"),
                "--root",
                str(root),
                "--iteration",
                "iter-001",
                "--ticket",
                "T-0001",
                "--failure",
                "test failed",
            )
            self.assertEqual(debug.returncode, 0, debug.stdout + debug.stderr)
            self.assertTrue((root / ".boil" / "debug" / "iter-001" / "T-0001-debug.md").exists())
            pr = run_cmd(sys.executable, str(ROOT / "scripts" / "boil-pr-summary.py"), "--root", str(root))
            self.assertEqual(pr.returncode, 0, pr.stdout + pr.stderr)
            self.assertIn("PR Summary", pr.stdout)

    def test_run_iteration_script_accepts_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "examples" / "minimal-loop" / "project", root, dirs_exist_ok=True)
            shutil.copytree(ROOT / "examples" / "minimal-loop" / "boil-state", root / ".boil")
            proc = run_cmd("bash", str(ROOT / "scripts" / "boil-run-iteration.sh"), "iter-001", str(root))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_doctor_rejects_goal_without_requirements_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            boil = root / ".boil"
            (boil / "tickets").mkdir(parents=True)
            for name in ("goal.md", "memory.md", "implementation.md", "bugs.md", "routing.md"):
                (boil / name).write_text(f"# {name}\n", encoding="utf-8")
            proc = run_cmd(
                sys.executable,
                str(ROOT / "scripts" / "boil-doctor.py"),
                "--root",
                str(root),
                "--skill-root",
                str(ROOT),
                "--json",
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("goal-requirements-contract", proc.stdout)

    def test_iteration_verifier_accepts_summary_with_proof_demo_next(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iter_dir = root / ".boil" / "iterations" / "iter-001"
            iter_dir.mkdir(parents=True)
            (iter_dir / "summary.md").write_text(
                """# Iteration 1

Implemented the smoke check.

**Tests:** 1 passed in 0.01s

**Demo (30 seconds to verify):**
Run `python -m unittest`.

## Suggested next steps

1. Continue with T-0002.
""",
                encoding="utf-8",
            )
            (iter_dir / "demo.md").write_text("# Demo\nRun `python -m unittest`.\n", encoding="utf-8")
            (iter_dir / "verify.log").write_text("1 passed\n", encoding="utf-8")
            (iter_dir / "retest.log").write_text("exit=0\n", encoding="utf-8")
            proc = run_cmd("bash", str(ROOT / "scripts" / "boil-verify-iteration.sh"), "iter-001", str(root))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
