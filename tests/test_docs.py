"""W5 — one loop in the docs. The skill, the slash command and the README must describe the
controller that exists (prepare → one implementer → score), not the ticket loop they replaced."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocsTest(unittest.TestCase):
    def test_skill_phase_2_is_prepare_dispatch_score(self) -> None:
        skill = (ROOT / "SKILL.md").read_text()
        phase2 = skill.split("## Phase 2")[1].split("## Phase 3")[0]
        self.assertIn("boil-check.py prepare", phase2)
        self.assertIn("boil-check.py score", phase2)
        self.assertNotIn("boil-check.py next --root", phase2)          # the seven-command protocol is gone
        self.assertNotIn("boil-brakes.py tick", phase2)                 # score ticks
        self.assertIn("subagent", phase2)                               # the implementer is one subagent

    def test_the_slash_command_sells_the_controller_not_ticket_tiers(self) -> None:
        cmd = (ROOT / "commands" / "boil.md").read_text()
        self.assertIn("prepare", cmd)
        self.assertIn("score", cmd)
        self.assertNotIn("T3 adversarial", cmd)
        self.assertNotIn("next concrete actions", cmd)

    def test_readme_names_the_two_commands_and_the_bench(self) -> None:
        readme = (ROOT / "README.md").read_text()
        self.assertIn("boil-check.py prepare", readme)
        self.assertIn("boil-check.py score", readme)
        self.assertIn("bench/run.py", readme)
        self.assertIn("boil-check.py report", readme)

    def test_legacy_loop_is_parked_behind_the_router(self) -> None:
        skill = (ROOT / "SKILL.md").read_text()
        self.assertTrue((ROOT / "references" / "legacy-ticket-loop.md").is_file())
        self.assertIn("legacy-ticket-loop.md", skill)

    def test_state_files_document_box_and_the_iteration_ledgers(self) -> None:
        sf = (ROOT / "references" / "state-files.md").read_text()
        for needle in ("`box`", "compile.jsonl", "iteration.json", "prepare", "score"):
            self.assertIn(needle, sf)

    def test_hard_rule_count_matches_the_list(self) -> None:
        skill = (ROOT / "SKILL.md").read_text()
        rules = skill.split("## Hard rules")[1].split("Baseline conduct")[0]
        n = len(re.findall(r"^\d+\. \*\*", rules, re.M))
        words = {8: "Eight", 9: "Nine", 10: "Ten"}
        self.assertIn(f"{words[n]}, each mechanically checkable", rules)


if __name__ == "__main__":
    unittest.main()
