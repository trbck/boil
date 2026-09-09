"""W5 — one loop in the docs. The skill, the slash command and the README must describe the
controller that exists (prepare → one implementer → score), not the ticket loop they replaced."""

from __future__ import annotations

import ast
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




class TestFileHygieneTest(unittest.TestCase):
    """A `unittest.main()` guard above a test class silently disables it.

    Run as `python tests/test_x.py`, execution stops at the guard, so every class defined
    below it is never created — the suite reports OK having skipped them without saying so.
    It had happened in six of these files, `test_verifier_first.py` hiding thirteen
    classes, and twice in `test_review.py` during this change alone. Both times by the most
    natural action there is: appending a class to the end of the file. Position cannot be
    remembered, so it is checked.

    Read with `ast`, not string search: the guard's own name appears inside string literals
    in this very file, and a text scan trips over them."""

    def test_the_main_guard_is_the_last_thing_in_every_test_file(self) -> None:
        hidden = {}
        for path in sorted((ROOT / "tests").glob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            guard = next((n for n in tree.body
                          if isinstance(n, ast.If) and "__main__" in ast.dump(n.test)), None)
            if guard is None:
                continue
            below = [n.name for n in tree.body
                     if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.lineno > guard.lineno]
            if below:
                hidden[path.name] = below
        self.assertEqual(
            hidden, {},
            "these test classes sit below a unittest.main() guard, so running the file "
            "directly never creates them: " + repr(hidden))


# At the very bottom on purpose, and checked there by TestFileHygieneTest in test_docs.py.
# Run as `python tests/<file>.py`, execution stops here, so any class defined below this
# guard is never created and the suite reports OK having silently skipped it.
if __name__ == "__main__":
    unittest.main()
