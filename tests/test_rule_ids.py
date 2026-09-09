"""The rule-ID contract, enforced.

`tests/rule-ids.baseline` sat in the repo unread for its whole life. A baseline
nothing checks is a comment. These tests make it load-bearing: the corpus may
grow freely, but an ID that has been cited somewhere must keep pointing at the
same rule forever.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts"))

import rule_baseline as R  # noqa: E402


class BaselineTest(unittest.TestCase):
    def test_no_baselined_id_has_disappeared_or_changed_meaning(self):
        breaking, _added = R.check()
        self.assertEqual(breaking, [], "\n".join(
            ["rule IDs are the skill's contract and this change breaks it:"] + breaking
            + ["", "If the change is deliberate, fix the citations that pointed at the old "
               "IDs, then run: python3 scripts/rule_baseline.py --update"]))

    def test_the_baseline_is_not_empty(self):
        # A truncated or unwritten baseline passes every other check vacuously.
        self.assertGreater(len(R.load_baseline()), 500)


class HashTest(unittest.TestCase):
    def test_whitespace_changes_do_not_count_as_a_rewrite(self):
        # Reflowing a paragraph is not a change of meaning; treating it as one
        # would train people to run --update reflexively.
        self.assertEqual(R.text_hash("shift signals   forward\none bar"),
                         R.text_hash("shift signals forward one bar"))

    def test_a_real_edit_changes_the_hash(self):
        self.assertNotEqual(R.text_hash("shift signals forward one bar"),
                            R.text_hash("shift signals forward two bars"))


class CorpusIntegrityTest(unittest.TestCase):
    def test_every_rule_id_is_unique_across_domains(self):
        # Rule IDs embed a pack prefix; two packs sharing one would mint colliding
        # IDs, and a citation would resolve to whichever domain was searched first.
        seen, dupes = set(), []
        import glob
        import ka_common as K
        for path in sorted(glob.glob(os.path.join(K.ROOT, "generated", "*", "index.json"))):
            for rule in K.load_json(path).get("rules", []):
                if rule["id"] in seen:
                    dupes.append(rule["id"])
                seen.add(rule["id"])
        self.assertEqual(dupes, [])

    def test_no_rule_has_empty_text(self):
        empty = [i for i, r in R.current_rules().items() if not (r.get("text") or "").strip()]
        self.assertEqual(empty, [], "a rule with no text is a citable ID that says nothing")


if __name__ == "__main__":
    unittest.main()
