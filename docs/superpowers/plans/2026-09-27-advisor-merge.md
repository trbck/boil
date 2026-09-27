# Advisor → boil Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** advisor's corpus and scripts live in `boil/advisor/`. `boil advise` exposes them with
the same API, and it answers `kind: decision` blockers when a valid rule is cited. helm can retire
rules and veto decisions.

**Architecture:**
- A subtree merge keeps advisor's history under `advisor/`.
- `scripts/boil-advise.py` forwards to advisor's scripts and adds `decide`, `record`, `sweep`,
  `retire` and `unretire`.
- Tombstones live in `advisor/domains/<d>/retired.json`, and every reader honours them.
- helm's existing `advisor.py` is repointed and extended.

**Tech Stack:** Python 3 stdlib, unittest (boil and advisor), pytest runner (helm), git.

**Spec:** `docs/superpowers/specs/2026-09-27-advisor-merge-design.md`

## Global Constraints

- Merge source: `origin/skill-review-fixes` of `git@github.com:trbck/advisor.git`, into prefix
  `advisor/`.
- The `lookup.py` flags and output must not change. `boil advise lookup …` output is
  byte-identical to `python3 advisor/scripts/lookup.py …`.
- Never advisable: `ESCALATE-BUDGET`, `-INFRA`, `-LIMIT`, `-VISIBILITY`, `ABORT-TAMPER`, CAP,
  REVIEW 70, and human-action tickets without `kind: decision`.
- `boil advise record`: exit 0 means accepted, exit 3 means rejected (the caller escalates). The
  advisor must never block an escalation.
- `.boil/decisions.md` is append-only, and its entries have the IDs `D-NNNN`.
- `SKILL.md` must be ≤350 lines, and its frontmatter `description` must be ≤984 chars (1024 minus
  40 for the YAML).
- Commits carry **no** AI attribution trailers (boil-commit-guard, hard rule 20).
- Work only in the worktrees:
  - boil: `/home/trbck/workspace/boil/.worktrees/advisor-merge`
  - helm: `/home/trbck/workspace/helm/.worktrees/advisor-retire`
  - The main checkouts of both repos hold another session's uncommitted work: never switch
    branches in them, never use bare `git stash`.
- Tests:
  - boil: `python3 -m unittest discover -s tests`
  - advisor: `python3 -m unittest discover -s advisor/tests -t advisor/tests`
  - helm: `python3 -m pytest -q tests`

## Review Focus

1. **A rule is retired between `decide` and `record`.** `record` must re-check the retirement at
   record time and reject. → Task 4 `test_retired_after_decide_rejected`.
2. **A question containing newlines, or `|` or `:` characters.** `decisions.md` must stay
   parseable, with the question stored on one line with `\n` escaped. → Task 4
   `test_multiline_question_roundtrips`.
3. **The verdict cites a chapter ID (`ATLB-01`) or a section instead of a rule.** It is rejected:
   only rule IDs count as a citation. → Task 4 `test_chapter_citation_rejected`.
4. **A domain named in `advisor_domains:` does not exist.** `decide` prints a warning and falls
   back to all domains; it does not crash. → Task 4 `test_unknown_domain_falls_back`.
5. **A veto in helm for an entry that `sweep` already processed.** The veto is idempotent and the
   ticket is not reopened twice. → Task 4 `test_sweep_idempotent`.

---

### Task 1: Subtree-merge advisor into `advisor/`

**Files:**
- Create (via merge): `advisor/**`
- Delete: `advisor/SKILL.md`, `advisor/bin/advisor-sync`
- Modify: `advisor/README.md` (becomes a pointer), `README.md` (a new "Advisor" section),
  `.github/workflows/boil-guardrails.yml`, `advisor/tests/test_documented_commands.py`

**Interfaces:**
- Produces: `advisor/scripts/{lookup,check_citations,ingest,build_index}.py`, all runnable from
  any cwd.

- [ ] **Step 1: Fetch and subtree-merge**

```bash
cd /home/trbck/workspace/boil/.worktrees/advisor-merge
git remote add advisor-src git@github.com:trbck/advisor.git
git fetch advisor-src skill-review-fixes
git merge -s ours --no-commit --allow-unrelated-histories advisor-src/skill-review-fixes
git read-tree --prefix=advisor/ -u advisor-src/skill-review-fixes
git commit -m "advisor: subtree-merge trbck/advisor@skill-review-fixes under advisor/"
git remote remove advisor-src
```

- [ ] **Step 2: Verify the advisor tests pass in place, with cwd set to the boil root**

Run: `python3 -m unittest discover -s advisor/tests -t advisor/tests`
Expected: 39 tests OK. If `test_documented_commands` assumes cwd is the advisor root, it already
uses its own `ROOT`, so no change is needed. Only a failure would call for a fix.

- [ ] **Step 3: Remove the skill shell and point the docs**

```bash
git rm -q advisor/SKILL.md advisor/bin/advisor-sync
```

In `advisor/tests/test_documented_commands.py`, remove `"SKILL.md"` from `DOCS` for now. Task 6
adds `references/advisor.md` in its place.

Replace `advisor/README.md` with:

```markdown
# advisor (merged into boil)

This directory is the advisor corpus and its scripts, merged from `trbck/advisor` on 2026-09-27
(history preserved). Use it through `boil advise` — see `../references/advisor.md` and the
"Advisor" section of `../README.md`. Adding knowledge: `FORMAT.md`, `references/maintaining.md`.
```

Append to `README.md`:

```markdown
## Advisor

`advisor/` holds 798 rules distilled from books (decision-making, trading), each with a stable ID.
`boil advise lookup …` retrieves them with the same flags `lookup.py` always had; `boil advise
decide/record` lets a loop answer a `kind: decision` blocker from a cited rule instead of asking
you, logged to `.boil/decisions.md` for veto. Retire a rule with `boil advise retire ID --reason`.
```

- [ ] **Step 4: CI runs the advisor tests**

In `.github/workflows/boil-guardrails.yml`, after the line `- run: python -m unittest discover -s tests`,
add:

```yaml
      - run: python -m unittest discover -s advisor/tests -t advisor/tests
```

- [ ] **Step 5: Run both suites and commit**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3 && python3 -m unittest discover -s advisor/tests -t advisor/tests 2>&1 | tail -3`
Expected: both OK.

```bash
git add -A && git commit -m "advisor: drop the standalone skill shell; CI runs the advisor suite"
```

---

### Task 2: Retirement tombstones in the advisor

**Files:**
- Modify: `advisor/scripts/ka_common.py` (add `load_retired`, `save_retired`)
- Modify: `advisor/scripts/lookup.py` (`load_indexes`, `cmd_rule`, `main`)
- Modify: `advisor/scripts/check_citations.py` (report RETIRED)
- Test: `advisor/tests/test_retired.py`

**Interfaces:**
- Produces:
  - `K.load_retired(domain_id=None) -> dict[str, dict]`: rule ID (upper-case) → `{"reason", "date", "by", "domain"}`
  - `K.save_retired(domain_id: str, data: dict) -> None`: an atomic write of
    `domains/<d>/retired.json`
  - `lookup.py --include-retired`
  - `check_citations.py` JSON gains a `"retired": [...]` list, and the text output gains a
    `RETIRED` line

- [ ] **Step 1: Write the failing tests**

```python
"""Retired rules: tombstones that hide a rule from retrieval but keep its ID resolvable."""
import json, os, shutil, subprocess, sys, tempfile, unittest

ADV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULE = "ATLB-01-R9"


class RetiredTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "advisor")
        shutil.copytree(ADV, self.root, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        with open(os.path.join(self.root, "domains", "decisions", "retired.json"), "w") as f:
            json.dump({RULE: {"reason": "test", "date": "2026-09-27", "by": "test"}}, f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_script(self, *args):
        return subprocess.run([sys.executable, *args], cwd=self.root, capture_output=True, text=True)

    def test_search_hides_retired(self):
        out = self.run_script("scripts/lookup.py", "--domain", "decisions",
                              "--search", "never reconsider an option you passed on").stdout
        self.assertNotIn(RULE, out)

    def test_include_retired_shows_it(self):
        out = self.run_script("scripts/lookup.py", "--domain", "decisions", "--include-retired",
                              "--search", "never reconsider an option you passed on").stdout
        self.assertIn(RULE, out)

    def test_rule_lookup_still_resolves_and_marks(self):
        p = self.run_script("scripts/lookup.py", "--rule", RULE)
        self.assertEqual(p.returncode, 0)
        self.assertIn("RETIRED", p.stdout)

    def test_check_citations_flags_retired(self):
        p = subprocess.run([sys.executable, "scripts/check_citations.py", "--json", "-"],
                           cwd=self.root, input="per %s we stop" % RULE, capture_output=True, text=True)
        self.assertIn(RULE, json.loads(p.stdout)["retired"])
        strict = subprocess.run([sys.executable, "scripts/check_citations.py", "--strict", "-"],
                                cwd=self.root, input="per %s we stop" % RULE, capture_output=True, text=True)
        self.assertEqual(strict.returncode, 1)

    def test_save_retired_is_atomic_and_roundtrips(self):
        sys.path.insert(0, os.path.join(self.root, "scripts"))
        try:
            import importlib, ka_common
            importlib.reload(ka_common)
            ka_common.save_retired("decisions", {"ATLB-01-R3": {"reason": "x", "date": "d", "by": "t"}})
            self.assertIn("ATLB-01-R3", ka_common.load_retired("decisions"))
            self.assertFalse([f for f in os.listdir(os.path.join(self.root, "domains", "decisions"))
                              if f.endswith(".tmp")])
        finally:
            sys.path.pop(0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s advisor/tests -t advisor/tests -p test_retired.py`
Expected: FAIL (the search still shows the rule; `--include-retired` is unrecognised).

Also check how `check_citations.py` reads its input: if it does not accept `-` for stdin, the
tests pass `-` and the script must treat `-` as stdin. Read `main()` first and adapt the test
invocation to the existing convention if one exists.

- [ ] **Step 3: Implement in `ka_common.py`**

```python
def load_retired(domain_id=None):
    """Rule IDs a human retired: hidden from retrieval, still resolvable, never citable as live."""
    out = {}
    for dom in load_domains(domain_id):
        path = os.path.join(dom["root"], "retired.json")
        if os.path.exists(path):
            for rid, meta in load_json(path).items():
                out[rid.upper()] = dict(meta, domain=dom["id"])
    return out


def save_retired(domain_id, data):
    path = os.path.join(DOMAINS_DIR, domain_id, "retired.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
```

- [ ] **Step 4: Implement in `lookup.py`**
  - Give `load_indexes(domain_id=None, include_retired=False)` a final step, after the merge loop:
    ```python
    retired = K.load_retired(domain_id)
    if not include_retired:
        merged["rules"] = [r for r in merged["rules"] if r["id"].upper() not in retired]
    merged["retired"] = retired
    ```
  - In `cmd_rule`, look rules up from an index loaded with `include_retired=True`. After printing
    `- authority`, add
    `if rule["id"].upper() in idx["retired"]: print("- RETIRED  : %s" % idx["retired"][rule["id"].upper()]["reason"])`.
  - In `main()`, add `ap.add_argument("--include-retired", action="store_true")`. Call
    `load_indexes(args.domain, include_retired=args.include_retired or bool(args.rule))`.

- [ ] **Step 5: Implement in `check_citations.py`**
  - After resolving, compute `retired = [c for c in found if c.upper() in K.load_retired()]`.
  - Add `"retired": retired` to the JSON output.
  - In text mode, print `RETIRED  <id>` for each one.
  - Under `--strict`, a non-empty `retired` list sets the exit status to 1.

- [ ] **Step 6: Run the advisor suite and commit**

Run: `python3 -m unittest discover -s advisor/tests -t advisor/tests`
Expected: all OK (39 + 5).

```bash
git add advisor && git commit -m "advisor: retired.json tombstones — hidden from search, resolvable, flagged by check_citations"
```

---

### Task 3: `boil-advise.py`: passthrough, retire and unretire

**Files:**
- Create: `scripts/boil-advise.py`
- Test: `tests/test_advise.py`

**Interfaces:**
- Consumes: `K.load_retired`, `K.save_retired` (Task 2)
- Produces:
  - CLI: `boil-advise.py {lookup,check,ingest,build} [args…]` forward to the script with the
    same name; `boil-advise.py retire ID --reason R [--by B]`; `boil-advise.py unretire ID`
  - Module-level constants `ADVISOR = SKILL_ROOT / "advisor"` and
    `FORWARD = {"lookup": "lookup.py", "check": "check_citations.py", "ingest": "ingest.py", "build": "build_index.py"}`
  - Env override: `BOIL_ADVISOR_ROOT` (tests point it at a copied corpus)

- [ ] **Step 1: Write the failing tests** (`tests/test_advise.py`, first part)

```python
"""boil advise: the advisor as a boil subcommand, and the decide/record contract.

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
    """Each test gets a private copy of the corpus, so retiring never touches the real one."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.adv = self.tmp / "advisor"
        shutil.copytree(ADVISOR, self.adv, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "tests"))
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
    def test_retire_then_unretire(self):
        p = run("retire", "ATLB-01-R9", "--reason", "superseded", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads((self.adv / "domains" / "decisions" / "retired.json").read_text())
        self.assertEqual(data["ATLB-01-R9"]["reason"], "superseded")
        self.assertEqual(run("unretire", "ATLB-01-R9", env=self.env).returncode, 0)
        data = json.loads((self.adv / "domains" / "decisions" / "retired.json").read_text())
        self.assertNotIn("ATLB-01-R9", data)

    def test_retire_unknown_id_fails(self):
        p = run("retire", "ATLB-99-R99", "--reason", "x", env=self.env)
        self.assertEqual(p.returncode, 2)

    def test_retire_requires_reason(self):
        self.assertNotEqual(run("retire", "ATLB-01-R9", env=self.env).returncode, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_advise`
Expected: FAIL (`boil-advise.py` does not exist).

- [ ] **Step 3: Implement `scripts/boil-advise.py`** (this skeleton is extended by Task 4)

```python
#!/usr/bin/env python3
"""boil advise — the advisor corpus as a boil subcommand.

  lookup|check|ingest|build ARGS…   forward verbatim to advisor/scripts/<same>.py (same flags, same exit)
  retire ID --reason R [--by B]      tombstone a rule: hidden from search, still resolvable
  unretire ID                        undo it
  decide / record / sweep            answer a `kind: decision` blocker from a cited rule (see
                                     references/advisor.md § Decisions)

Exit codes: 0 ok · 2 usage / unknown id · 3 record rejected (caller escalates as before).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ADVISOR = Path(os.environ.get("BOIL_ADVISOR_ROOT") or SKILL_ROOT / "advisor")
FORWARD = {"lookup": "lookup.py", "check": "check_citations.py",
           "ingest": "ingest.py", "build": "build_index.py"}
EXIT_OK, EXIT_USAGE, EXIT_REJECT = 0, 2, 3


def _k():
    """advisor's ka_common, imported from whichever corpus ADVISOR points at."""
    sys.path.insert(0, str(ADVISOR / "scripts"))
    import ka_common as K  # noqa: E402
    return K


def _index_rules(K) -> dict[str, str]:
    """rule id (upper) -> domain, across every built index, retired included."""
    out = {}
    for dom in K.load_domains():
        path = Path(dom["generated"]) / "index.json"
        if path.exists():
            for r in K.load_json(str(path)).get("rules", []):
                out[r["id"].upper()] = dom["id"]
    return out


def cmd_retire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    if not dom:
        print(f"boil advise: unknown rule id {args.id}", file=sys.stderr)
        return EXIT_USAGE
    data = {k: v for k, v in K.load_retired(dom).items()}
    for v in data.values():
        v.pop("domain", None)
    data[rid] = {"reason": args.reason, "date": dt.date.today().isoformat(), "by": args.by}
    K.save_retired(dom, data)
    print(f"retired {rid} ({dom}): {args.reason}")
    return EXIT_OK


def cmd_unretire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    retired = K.load_retired(dom) if dom else {}
    if rid not in retired:
        print(f"boil advise: {args.id} is not retired", file=sys.stderr)
        return EXIT_USAGE
    data = {k: {kk: vv for kk, vv in v.items() if kk != "domain"} for k, v in retired.items() if k != rid}
    K.save_retired(dom, data)
    print(f"unretired {rid}")
    return EXIT_OK


def main(argv: list[str]) -> int:
    if argv and argv[0] in FORWARD:
        script = ADVISOR / "scripts" / FORWARD[argv[0]]
        return subprocess.run([sys.executable, str(script), *argv[1:]]).returncode
    ap = argparse.ArgumentParser(prog="boil advise", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("retire"); p.add_argument("id"); p.add_argument("--reason", required=True)
    p.add_argument("--by", default="cli"); p.set_defaults(fn=cmd_retire)
    p = sub.add_parser("unretire"); p.add_argument("id"); p.set_defaults(fn=cmd_unretire)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Note: `ka_common.ROOT` is derived from its own file location, so importing it from
`ADVISOR / "scripts"` makes it read and write the corpus that `BOIL_ADVISOR_ROOT` points at.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_advise`
Expected: 6 OK.

- [ ] **Step 5: Commit**

```bash
git add scripts/boil-advise.py tests/test_advise.py
git commit -m "advise: boil advise forwards to the advisor scripts; retire/unretire write tombstones"
```

---

### Task 4: `decide`, `record` and `sweep`

**Files:**
- Modify: `scripts/boil-advise.py`
- Test: `tests/test_advise.py` (append)

**Interfaces:**
- Consumes: Task 3's `_k()`, `_index_rules()`, `ADVISOR`, the exit codes
- Produces:
  - `decide --question Q [--project DIR] [--limit 8]` prints a packet. Exit 0; exit 3 when the
    advisor is unavailable.
  - `record --question Q --verdict V [--ticket T] [--project DIR] [--no-log]`: exit 0 appends
    `D-NNNN` to `.boil/decisions.md`; exit 3 rejects, with the reason on stderr.
  - `sweep [--project DIR]`: processes the `veto:` lines, is idempotent, and prints the number of
    tickets it reopened.
  - `parse_decisions(text: str) -> list[dict]`: keys `id, ts, ticket, question, answer, rules
    (list), why, veto, swept (bool)`. helm (Task 7) re-implements the same parse, so the format is
    fixed here.
  - The `.boil/decisions.md` entry format:
    ```
    ## D-0001 · 2026-09-27T14:02Z · ticket T-041
    question: <one line; newlines escaped as \n>
    answer: <text>
    rules: ATLB-01-R3, ATLB-01-R9
    why: <text>
    veto: –
    ```
    After a sweep, `veto: <reason> (swept)`.
  - `.boil/advisor-vetoes.json`: `[{"q": "<sha1 of normalised question>", "rules": ["ID", …]}]`

Rejection rules (spec §B), each with a stable message prefix:

| Condition | stderr prefix |
|---|---|
| verdict starts `ASK-HUMAN` | `ask-human:` |
| verdict does not parse as `ANSWER: … \| RULES: … \| WHY: …` | `malformed:` |
| RULES has no rule-shaped ID (chapter or section IDs don't count) | `no-rule:` |
| ID not in any index | `unknown:` |
| ID retired | `retired:` |
| two cited IDs sit in different rows of the same `###` entry of a domain `conflicts.md` | `conflict:` |
| answer empty, or whole-word `depends`, `either` or `unclear` | `hedged:` |
| (question hash, sorted rule set) already in vetoes | `vetoed:` |

A rule-shaped ID matches `^[A-Z][A-Z0-9]*-[A-Z0-9-]+-R\d+$`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_advise.py`)

```python
GOAL = """# Goal: tune the entry filter

advisor_domains: decisions

- [ ] Pick an entry filter within 20 variants
"""
GOOD = "ANSWER: Stop and commit to the current best | RULES: ATLB-01-R9 | WHY: goal caps search at 20 variants"


class DecideRecordCase(CorpusCase):
    def setUp(self):
        super().setUp()
        self.proj = self.tmp / "proj"
        (self.proj / ".boil").mkdir(parents=True)
        (self.proj / ".boil" / "goal.md").write_text(GOAL)

    def record(self, verdict, question="Stop tuning or keep searching?", *extra):
        return run("record", "--project", str(self.proj), "--question", question,
                   "--verdict", verdict, "--no-log", *extra, env=self.env)

    def decisions(self):
        p = self.proj / ".boil" / "decisions.md"
        return p.read_text() if p.exists() else ""


class DecideTest(DecideRecordCase):
    def test_packet_has_question_goal_and_rules(self):
        p = run("decide", "--project", str(self.proj), "--question", "when to stop searching", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("when to stop searching", p.stdout)
        self.assertIn("Pick an entry filter", p.stdout)
        self.assertIn("ATLB-01", p.stdout)
        self.assertIn("ANSWER:", p.stdout)          # the packet states the verdict format

    def test_retired_rules_absent_from_packet(self):
        run("retire", "ATLB-01-R9", "--reason", "x", env=self.env)
        p = run("decide", "--project", str(self.proj), "--question", "never reconsider an option you passed on", env=self.env)
        self.assertNotIn("ATLB-01-R9", p.stdout)

    def test_unknown_domain_falls_back(self):
        (self.proj / ".boil" / "goal.md").write_text(GOAL.replace("decisions", "astrology"))
        p = run("decide", "--project", str(self.proj), "--question", "when to stop searching", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("astrology", p.stderr)
        self.assertIn("ATLB-01", p.stdout)

    def test_advisor_missing_exits_3(self):
        env = dict(self.env, BOIL_ADVISOR_ROOT=str(self.tmp / "nope"))
        p = run("decide", "--project", str(self.proj), "--question", "q", env=env)
        self.assertEqual(p.returncode, 3)


class RecordTest(DecideRecordCase):
    def test_accepts_and_logs(self):
        p = self.record(GOOD)
        self.assertEqual(p.returncode, 0, p.stderr)
        text = self.decisions()
        self.assertIn("## D-0001", text)
        self.assertIn("rules: ATLB-01-R9", text)
        self.assertIn("veto: –", text)
        self.assertEqual(self.record(GOOD, "another question").returncode, 0)
        self.assertIn("## D-0002", self.decisions())

    def assertRejected(self, verdict, prefix, question="Stop tuning or keep searching?"):
        p = self.record(verdict, question)
        self.assertEqual(p.returncode, 3, p.stdout)
        self.assertTrue(p.stderr.startswith(prefix), p.stderr)

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

    def test_multiline_question_roundtrips(self):
        q = "line one\nline two | with: colons"
        self.assertEqual(self.record(GOOD, q).returncode, 0)
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("ba", ADVISE)
            ba = importlib.util.module_from_spec(spec); spec.loader.exec_module(ba)
            entries = ba.parse_decisions(self.decisions())
        finally:
            sys.path.pop(0)
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
        self.tpath = self.proj / ".boil" / "tickets" / "T-0041.md"
        self.tpath.write_text(TICKET)

    def test_accept_unblocks_ticket_and_veto_reblocks(self):
        self.assertEqual(self.record(GOOD, "Stop tuning or keep searching?", "--ticket", "T-0041").returncode, 0)
        t = self.tpath.read_text()
        self.assertIn("status: todo", t)
        self.assertIn("required: false", t)
        self.assertIn("advised: D-0001", t)
        d = self.proj / ".boil" / "decisions.md"
        d.write_text(d.read_text().replace("veto: –", "veto: wrong domain"))
        p = run("sweep", "--project", str(self.proj), env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        t = self.tpath.read_text()
        self.assertIn("status: blocked", t)
        self.assertIn("required: true", t)
        self.assertIn("veto: wrong domain (swept)", d.read_text())
        # the same question + rules can no longer auto-decide
        self.assertEqual(self.record(GOOD, "Stop tuning or keep searching?").returncode, 3)

    def test_sweep_idempotent(self):
        self.record(GOOD, "Stop tuning or keep searching?", "--ticket", "T-0041")
        d = self.proj / ".boil" / "decisions.md"
        d.write_text(d.read_text().replace("veto: –", "veto: no"))
        run("sweep", "--project", str(self.proj), env=self.env)
        before = (self.tpath.read_text(), d.read_text())
        p = run("sweep", "--project", str(self.proj), env=self.env)
        self.assertIn("0 reopened", p.stdout)
        self.assertEqual(before, (self.tpath.read_text(), d.read_text()))

    def test_malformed_entry_skipped_not_rewritten(self):
        d = self.proj / ".boil" / "decisions.md"
        d.write_text("## D-0001 · garbage\nnot a field\n")
        p = run("sweep", "--project", str(self.proj), env=self.env)
        self.assertEqual(p.returncode, 0)
        self.assertIn("skipped", p.stderr)
        self.assertEqual(d.read_text(), "## D-0001 · garbage\nnot a field\n")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_advise`
Expected: the new tests FAIL (unknown subcommands); Task 3's tests still pass.

- [ ] **Step 3: Implement.** Add to `scripts/boil-advise.py`:

```python
import hashlib
import re

RULE_ID = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z0-9-]+-R\d+$")
VERDICT = re.compile(r"^ANSWER:\s*(?P<answer>.*?)\s*\|\s*RULES:\s*(?P<rules>.*?)\s*\|\s*WHY:\s*(?P<why>.*)$", re.S)
HEDGE = re.compile(r"\b(depends|either|unclear)\b", re.I)
HEADER = re.compile(r"^## (D-\d{4}) · (\S+) · ticket (\S*)\s*$")
FIELDS = ("question", "answer", "rules", "why", "veto")


def _boil(project: str) -> Path:
    return Path(project).resolve() / ".boil"


def _qhash(q: str) -> str:
    return hashlib.sha1(" ".join(q.lower().split()).encode()).hexdigest()


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n")


def _unesc(s: str) -> str:
    return re.sub(r"\\(\\|n)", lambda m: "\n" if m.group(1) == "n" else "\\", s)


def parse_decisions(text: str) -> list[dict]:
    """Entries in file order. An entry missing any field is skipped (reported by the caller via `_bad`)."""
    out, cur = [], None
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            cur = {"id": m.group(1), "ts": m.group(2), "ticket": m.group(3) or ""}
            out.append(cur)
            continue
        if cur is not None and ":" in line:
            key, val = line.split(":", 1)
            if key in FIELDS:
                cur[key] = val.strip()
    good = []
    for e in out:
        if all(k in e for k in FIELDS):
            e["question"] = _unesc(e["question"])
            e["rules"] = [r.strip() for r in e["rules"].split(",") if r.strip()]
            e["swept"] = e["veto"].endswith("(swept)")
            good.append(e)
    parse_decisions.bad = [e["id"] for e in out if e not in good]
    return good


def _goal(project: str) -> tuple[str, list[str]]:
    p = _boil(project) / "goal.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    m = re.search(r"^advisor_domains:\s*(.+)$", text, re.M)
    doms = [d.strip() for d in m.group(1).split(",")] if m else []
    return text, doms


def cmd_decide(args) -> int:
    if not (ADVISOR / "scripts" / "lookup.py").is_file():
        print("boil advise: advisor unavailable — escalate as usual", file=sys.stderr)
        return EXIT_REJECT
    K = _k()
    goal, doms = _goal(args.project)
    known = {d["id"] for d in K.load_domains()}
    for d in [d for d in doms if d not in known]:
        print(f"boil advise: advisor_domains names unknown domain `{d}` — ignored", file=sys.stderr)
    doms = [d for d in doms if d in known] or [None]
    print(f"# Decision packet\n\nQuestion: {args.question}\n\n## Goal (excerpt)\n")
    print("\n".join(goal.splitlines()[:40]) or "(no .boil/goal.md)")
    print("\n## Candidate rules\n")
    for d in doms:
        cmd = [sys.executable, str(ADVISOR / "scripts" / "lookup.py"), "--search", args.question,
               "--kind", "rules", "--limit", str(args.limit)] + (["--domain", d] if d else [])
        print(subprocess.run(cmd, capture_output=True, text=True).stdout.rstrip())
    print("\n## Reply with exactly one line\n")
    print("ANSWER: <choice> | RULES: <ID>[, <ID>…] | WHY: <one line tying the rule to the goal>")
    print("ASK-HUMAN: <reason>          (no rule fits, or rules disagree)")
    print("\nThen: boil advise record --question \"…\" --verdict \"<that line>\" [--ticket T]")
    return EXIT_OK


def _conflict(K, ids: list[str]) -> tuple[str, str] | None:
    """Two cited IDs in different table rows of the same `###` entry of any conflicts.md."""
    want = set(ids)
    for dom in K.load_domains():
        path = Path(dom["root"]) / "conflicts.md"
        if not path.exists():
            continue
        for block in re.split(r"^### ", path.read_text(encoding="utf-8"), flags=re.M)[1:]:
            rows = [set(re.findall(r"`([A-Z][A-Z0-9-]+-R\d+)`", ln)) & want
                    for ln in block.splitlines() if ln.startswith("|")]
            rows = [r for r in rows if r]
            for i, a in enumerate(rows):
                for b in rows[i + 1:]:
                    if a - b and b - a:
                        return sorted(a - b)[0], sorted(b - a)[0]
    return None


def _reject(prefix: str, msg: str) -> int:
    print(f"{prefix}: {msg}", file=sys.stderr)
    return EXIT_REJECT


def _vetoes(project: str) -> list[dict]:
    p = _boil(project) / "advisor-vetoes.json"
    return json.loads(p.read_text()) if p.exists() else []


def cmd_record(args) -> int:
    v = args.verdict.strip()
    if v.upper().startswith("ASK-HUMAN"):
        return _reject("ask-human", v)
    m = VERDICT.match(v)
    if not m:
        return _reject("malformed", "expected `ANSWER: … | RULES: … | WHY: …`")
    answer, why = m.group("answer").strip(), m.group("why").strip()
    ids = [x.strip().upper() for x in m.group("rules").split(",") if x.strip()]
    ids = [x for x in ids if RULE_ID.match(x)]
    if not ids:
        return _reject("no-rule", "cite at least one rule ID (chapters and sections do not count)")
    if not (ADVISOR / "scripts" / "lookup.py").is_file():
        return _reject("unavailable", "advisor unavailable")
    K = _k()
    index = _index_rules(K)
    if unknown := [x for x in ids if x not in index]:
        return _reject("unknown", ", ".join(unknown))
    retired = K.load_retired()
    if gone := [x for x in ids if x in retired]:
        return _reject("retired", ", ".join(gone))
    if pair := _conflict(K, ids):
        return _reject("conflict", f"{pair[0]} vs {pair[1]} (see conflicts.md)")
    if not answer or HEDGE.search(answer):
        return _reject("hedged", "the answer must be a choice")
    key = {"q": _qhash(args.question), "rules": sorted(ids)}
    if key in _vetoes(args.project):
        return _reject("vetoed", "this question with these rules was vetoed before")
    boil = _boil(args.project)
    dpath = boil / "decisions.md"
    prior = dpath.read_text(encoding="utf-8") if dpath.exists() else ""
    n = len(re.findall(r"^## D-\d{4}", prior, re.M)) + 1
    did = f"D-{n:04d}"
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    entry = (f"## {did} · {ts} · ticket {args.ticket}\nquestion: {_esc(args.question)}\n"
             f"answer: {_esc(answer)}\nrules: {', '.join(ids)}\nwhy: {_esc(why)}\nveto: –\n\n")
    with open(dpath, "a", encoding="utf-8") as f:
        f.write(entry)
    if args.ticket:
        _set_ticket(boil, args.ticket, advised=did)
    _emit(args, "boil.advised", f"{did}: {answer[:80]} [{', '.join(ids)}]")
    print(f"{did} recorded: {answer}")
    return EXIT_OK


def _ticket_file(boil: Path, ticket: str) -> Path | None:
    hits = sorted((boil / "tickets").glob(f"{ticket}*.md")) if (boil / "tickets").is_dir() else []
    return hits[0] if hits else None


def _set_ticket(boil: Path, ticket: str, *, advised: str = "", reopen: bool = False) -> bool:
    """Flip a human-action ticket between advised (todo, not required) and blocked (required)."""
    path = _ticket_file(boil, ticket)
    if not path:
        return False
    t = path.read_text(encoding="utf-8")
    if reopen:
        t = re.sub(r"^status: .*$", "status: blocked", t, count=1, flags=re.M)
        t = re.sub(r"^  required: .*$", "  required: true", t, count=1, flags=re.M)
    else:
        t = re.sub(r"^status: .*$", "status: todo", t, count=1, flags=re.M)
        t = re.sub(r"^  required: .*$", "  required: false", t, count=1, flags=re.M)
        t = re.sub(r"^(human_action:\n)", rf"\1  advised: {advised}\n", t, count=1, flags=re.M)
    path.write_text(t, encoding="utf-8")
    return True


def _emit(args, kind: str, detail: str) -> None:
    if getattr(args, "no_log", False):
        return
    script = SKILL_ROOT / "scripts" / "boil-helm-log.py"
    if script.exists():
        subprocess.run([sys.executable, str(script), "emit", "--root", str(Path(args.project).resolve()),
                        "--kind", kind, "--detail", detail], capture_output=True)


def cmd_sweep(args) -> int:
    boil = _boil(args.project)
    dpath = boil / "decisions.md"
    if not dpath.exists():
        print("0 reopened")
        return EXIT_OK
    text = dpath.read_text(encoding="utf-8")
    entries = parse_decisions(text)
    for bad in parse_decisions.bad:
        print(f"boil advise: skipped unparseable entry {bad}", file=sys.stderr)
    vetoes, reopened = _vetoes(args.project), 0
    for e in entries:
        if e["veto"] in ("–", "-", "") or e["swept"]:
            continue
        if e["ticket"] and _set_ticket(boil, e["ticket"], reopen=True):
            reopened += 1
        key = {"q": _qhash(e["question"]), "rules": sorted(e["rules"])}
        if key not in vetoes:
            vetoes.append(key)
        text = re.sub(rf"(^## {e['id']} ·.*?^veto: )(.*)$", lambda m: m.group(1) + m.group(2) + " (swept)",
                      text, count=1, flags=re.M | re.S)
    (boil / "advisor-vetoes.json").write_text(json.dumps(vetoes, indent=2) + "\n")
    tmp = dpath.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dpath)
    print(f"{reopened} reopened")
    return EXIT_OK
```

Register the subcommands in `main()`:

```python
    p = sub.add_parser("decide"); p.add_argument("--question", required=True)
    p.add_argument("--project", default="."); p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_decide)
    p = sub.add_parser("record"); p.add_argument("--question", required=True)
    p.add_argument("--verdict", required=True); p.add_argument("--ticket", default="")
    p.add_argument("--project", default="."); p.add_argument("--no-log", action="store_true")
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("sweep"); p.add_argument("--project", default="."); p.set_defaults(fn=cmd_sweep)
```

Check `boil-helm-log.py emit` for the real name of the detail flag (`--detail` or `--status`)
before relying on it; `log_event` in `boil-loop.py:254` shows the flags it accepts.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_advise`
Expected: all OK. If `test_unknown_domain_falls_back` shows ATLB missing, the search needs the
`None` domain path: confirm `doms` falls back to `[None]`.

- [ ] **Step 5: `boil-now.py` runs sweep.** In `scripts/boil-now.py`, next to the existing
  `subprocess.run([... "status" ...])` call (line ~86), add a best-effort call:

```python
    advise = SKILL_ROOT / "scripts" / "boil-advise.py"
    if advise.exists() and (root / ".boil" / "decisions.md").exists():
        subprocess.run([sys.executable, str(advise), "sweep", "--project", str(root)],
                       capture_output=True, timeout=30)
```

  Use the variable names `boil-now.py` actually uses for the skill root and the project root. Read
  the file first.

- [ ] **Step 6: Run the full boil suite and commit**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK.

```bash
git add scripts/boil-advise.py scripts/boil-now.py tests/test_advise.py
git commit -m "advise: decide/record/sweep — a cited, live, non-conflicting rule answers a decision blocker; veto reopens it"
```

---

### Task 5: Escalation hook: STALL tickets become `kind: decision`

**Files:**
- Modify: `scripts/boil-loop.py` (`_convert_ticket`, `cmd_escalate`)
- Modify: `references/ticket-system.md` (document `human_action.kind` and `advised`)
- Test: `tests/test_selfcorrect.py` (append)

**Interfaces:**
- Consumes: `boil-advise.py decide/record` (Task 4)
- Produces:
  - `_convert_ticket(root, ticket, safe_summary, kind="")` writes `  kind: decision` when kind is
    set.
  - `cmd_escalate` prints the line
    `  advisable: boil advise decide --question "<safe>" --ticket <T>` only for ESCALATE-STALL.

- [ ] **Step 1: Write the failing tests.** Read the existing escalate tests in
  `tests/test_selfcorrect.py` to see how the suite drives a loop to `ESCALATE-STALL` and to
  `ESCALATE-BUDGET`, and reuse those helpers verbatim. Then add:

```python
class AdvisableEscalationTest(unittest.TestCase):
    """Only a stall is a judgment question; the brakes never reach the advisor."""

    def test_stall_ticket_is_kind_decision_with_hint(self):
        root, out = self._escalate_to("ESCALATE-STALL")      # helper built from the suite's existing stall setup
        self.assertIn("kind: decision", self._ticket_text(root))
        self.assertIn("advisable: boil advise decide", out)

    def test_budget_ticket_is_not_advisable(self):
        root, out = self._escalate_to("ESCALATE-BUDGET")
        self.assertNotIn("kind: decision", self._ticket_text(root))
        self.assertNotIn("advisable:", out)

    def test_tamper_is_not_advisable(self):
        root, out = self._escalate_to("ABORT-TAMPER")
        self.assertNotIn("kind: decision", self._ticket_text(root))
        self.assertNotIn("advisable:", out)
```

  `_escalate_to(reason)` is the one helper you write: create the temp project and ticket exactly
  as the existing stall test does, then run `boil-loop.py escalate --root R --ticket T-0001
  --convert-ticket --force --reason <reason> --no-log`, and return `(root, stdout)`.
  `_ticket_text` reads `.boil/tickets/T-0001*.md`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_selfcorrect.AdvisableEscalationTest`
Expected: the stall test FAILS; the budget and tamper tests pass already.

- [ ] **Step 3: Implement.** In `boil-loop.py`:

```python
ADVISABLE = ("ESCALATE-STALL",)
```

  - In `cmd_escalate`, after `safe = _human_question(loop)`:
    ```python
    advisable = loop.get("terminal_reason", "").startswith(ADVISABLE)
    ```
    and pass `kind="decision" if advisable else ""` to `_convert_ticket`.
  - After the existing prints:
    ```python
    if advisable:
        print(f'  advisable: boil advise decide --question "{safe}" --ticket {args.ticket}')
    ```
  - In `_convert_ticket`, add `kind: str = ""`, and when kind is set, append the line
    `f"  kind: {kind}"` after `"  required: true",`.

- [ ] **Step 4: Document it.** In `references/ticket-system.md`, in the `human_action:` block
  description (lines ~137–160), add:

```markdown
- `kind: decision` — optional. Marks a product/design judgment the advisor may answer
  (`boil advise decide`, then `record`). Absent = not advisable. Never set it for credentials,
  access, hardware, accounts, budget, or tamper.
- `advised: D-NNNN` — written by `boil advise record` when a cited rule answered it; the ticket
  goes back to `status: todo`, `required: false`. A veto in `.boil/decisions.md` reverses both.
```

- [ ] **Step 5: Run the tests and commit**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK.

```bash
git add scripts/boil-loop.py references/ticket-system.md tests/test_selfcorrect.py
git commit -m "loop: a stall escalation is a decision the advisor may answer; the brakes never are"
```

---

### Task 6: Router, description, `references/advisor.md`, and SKILL.md ≤350

**Files:**
- Modify: `advisor/scripts/build_index.py` (`render_skill`, `compose_description`)
- Move: `advisor/templates/SKILL.md.tmpl` → `advisor/templates/advisor-reference.md.tmpl`
  (drop the frontmatter; rewrite `python3 scripts/` to `python3 advisor/scripts/` and explain
  that `boil advise lookup` is equivalent)
- Create (generated): `references/advisor.md`
- Modify: `SKILL.md` (description sentence, router row, the decision line, trims to ≤350)
- Modify: `advisor/tests/test_documented_commands.py` (`DOCS` gains `../references/advisor.md`,
  with its cwd rule adjusted)
- Test: `tests/test_docs.py` (append)

**Interfaces:**
- Produces:
  - The description marker `Knowledge questions (route to \`boil advise\`): `. Everything after
    it on the `description:` line is generated.
  - `build_index.py` writes `references/advisor.md` and splices the description.
  - `compose_description(indexes, budget=None)`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_docs.py`)

```python
class AdvisorRoutingTest(unittest.TestCase):
    SKILL = (ROOT / "SKILL.md").read_text()

    def test_skill_md_line_budget(self):
        self.assertLessEqual(len(self.SKILL.splitlines()), 350)

    def test_description_under_cap_and_carries_advisor_triggers(self):
        desc = re.search(r"^description: (.*)$", self.SKILL, re.M).group(1)
        self.assertLessEqual(len(desc), 984)
        self.assertIn("Knowledge questions (route to `boil advise`):", desc)
        self.assertIn("backtesting", desc)

    def test_router_has_advisor_row(self):
        self.assertIn("`references/advisor.md`", self.SKILL)

    def test_description_matches_generator(self):
        before = self.SKILL
        subprocess.run([sys.executable, str(ROOT / "advisor" / "scripts" / "build_index.py"), "--quiet"],
                       check=True, capture_output=True)
        self.assertEqual((ROOT / "SKILL.md").read_text(), before,
                         "SKILL.md description is stale — run advisor/scripts/build_index.py")

    def test_decision_line_present(self):
        self.assertIn("boil advise decide", self.SKILL)
```

  Check `tests/test_docs.py`'s imports (it needs `re`, `subprocess`, `sys`, and `ROOT`) and add
  whichever are missing. Check whether `build_index.py` has a `--quiet` flag; if not, use the one
  it has, or no flag.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_docs.AdvisorRoutingTest`
Expected: FAIL (358 lines, no marker, no router row).

- [ ] **Step 3: Move the template and change `render_skill`**

```bash
git mv advisor/templates/SKILL.md.tmpl advisor/templates/advisor-reference.md.tmpl
```

  Edit the moved template:
  - delete the 4 frontmatter lines (`---`, `name:`, `description: {{DESCRIPTION}}`, `---`)
  - change the GENERATED comment to name the new template
  - replace every `python3 scripts/` with `python3 advisor/scripts/`
  - add after the first heading: `Every command below also runs as \`boil advise lookup|check|ingest|build …\` with identical flags.`

  In `build_index.py`:

```python
BOIL_ROOT = os.path.dirname(K.ROOT)
DESC_MARKER = "Knowledge questions (route to `boil advise`): "


def splice_description(skill_path, indexes, quiet):
    """Replace the generated tail of boil's description; the hand-written head stays."""
    text = K.read_text(skill_path)
    m = re.search(r"^description: (.*)$", text, re.M)
    if not m or DESC_MARKER not in m.group(1):
        log("! SKILL.md description has no advisor marker — left untouched", quiet)
        return []
    head = m.group(1).split(DESC_MARKER)[0]
    tail, dropped = compose_description(indexes, budget=MAX_FRONTMATTER_CHARS - 40 - len(head) - len(DESC_MARKER))
    new = "description: " + head + DESC_MARKER + tail
    K.write_text(skill_path, text[:m.start()] + new + text[m.end():])
    return dropped
```

  - `compose_description(indexes, budget=None)`: when `budget` is given, use it in place of the
    computed one. When it is given, the `tail` sentence becomes the shorter
    `"Also for what the books say, or reviewing work against them."`.
  - In `render_skill`:
    - read `advisor-reference.md.tmpl`
    - write `os.path.join(BOIL_ROOT, "references", "advisor.md")` in place of `SKILL.md`
    - set `dropped = splice_description(os.path.join(BOIL_ROOT, "SKILL.md"), indexes, quiet)`
    - keep the dropped-phrase warning
  - Check whether `re` is already imported in `build_index.py`.

- [ ] **Step 4: Edit `SKILL.md`**
  - Frontmatter `description:`: append ` Knowledge questions (route to \`boil advise\`): x`. The
    build replaces the `x`.
  - Router table: add
    `| \`references/advisor.md\` | a knowledge or what-do-the-books-say question, or \`boil advise\` runs |`
  - Where SKILL.md says "Ask the user only what the workspace cannot answer" (line ~51), add the
    sentence: `Before filing a \`kind: decision\` human-action ticket, run \`boil advise decide\`; file it only if \`record\` exits 3.`
  - Trim to ≤350 lines:
    - `wc -l SKILL.md` after the additions gives the target cut (expected about 12).
    - Cut only passages that repeat a reference already listed in the router, and replace each
      with a one-line pointer to that reference.
    - List every cut in the commit message.

- [ ] **Step 5: Regenerate and run everything**

```bash
python3 advisor/scripts/build_index.py
python3 -m unittest discover -s tests 2>&1 | tail -3
python3 -m unittest discover -s advisor/tests -t advisor/tests 2>&1 | tail -3
```

  Expected: both OK. `references/advisor.md` exists, and `SKILL.md` has ≤350 lines and a
  description of ≤984 chars. If the build prints dropped trigger phrases, shorten the head of
  boil's description until at least 2 scope phrases per domain fit.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "skill: boil routes knowledge questions to boil advise; advisor reference generated; SKILL.md back under 350"
```

---

### Task 7: helm: repoint, retire and unretire, the decisions panel

Repo: `/home/trbck/workspace/helm`. Create the worktree first. The main checkout has another
session's uncommitted work: do not touch it.

```bash
cd /home/trbck/workspace/helm && git worktree add -b advisor-retire .worktrees/advisor-retire main
grep -q '^.worktrees/' .gitignore || echo "(check .gitignore covers .worktrees/ before committing)"
```

**Files:**
- Modify: `advisor.py` (`ROOT` default, `retire`, `unretire`, `retired`)
- Create: `decisions.py`
- Modify: `server.py` (routes), `static/index.html` (Retire/Unretire, Retired filter,
  Decisions panel)
- Test: `tests/test_advisor.py` (append), `tests/test_decisions.py`

**Interfaces:**
- Consumes: `boil-advise.py retire|unretire` (Task 3), and the decisions.md format plus the sweep
  semantics (Task 4)
- Produces:
  - `advisor.retire(rule_id, reason, root=None) -> dict`, `advisor.unretire(rule_id, root=None) -> dict`
    (the `_run` result dict)
  - `advisor.retired(root=None) -> dict`
  - `decisions.list_decisions(project: Path) -> {"entries": [...], "skipped": [ids]}`
  - `decisions.veto(project: Path, did: str, reason: str) -> dict`, which raises
    `KeyError(did)` for an unknown ID
  - routes: `GET /api/advisor/retired`, `POST /api/advisor/rule/<id>/retire {reason}`,
    `POST /api/advisor/rule/<id>/unretire`, `GET /api/project/<p>/decisions`,
    `POST /api/project/<p>/decision/<D-id>/veto {reason}`

- [ ] **Step 1: Read first.** Read `advisor.py` (`ROOT`, `_run`, `_inside`), the existing
  `_advisor_get` and `_advisor_post` in `server.py`, and `tests/test_advisor.py`'s fixture setup.
  Match those patterns exactly.

- [ ] **Step 2: Write the failing tests**

`tests/test_decisions.py`:

```python
import tempfile, unittest
from pathlib import Path

import decisions

ENTRY = """## D-0001 · 2026-09-27T14:02Z · ticket T-0041
question: Stop tuning or keep searching?
answer: Stop
rules: ATLB-01-R9
why: goal caps search
veto: –

"""


class DecisionsTest(unittest.TestCase):
    def setUp(self):
        self.proj = Path(tempfile.mkdtemp())
        (self.proj / ".boil").mkdir()
        self.f = self.proj / ".boil" / "decisions.md"
        self.f.write_text(ENTRY + "## D-0002 · broken\nnope\n")

    def test_list_parses_and_reports_skipped(self):
        out = decisions.list_decisions(self.proj)
        self.assertEqual([e["id"] for e in out["entries"]], ["D-0001"])
        self.assertEqual(out["entries"][0]["rules"], ["ATLB-01-R9"])
        self.assertEqual(out["skipped"], ["D-0002"])

    def test_veto_writes_line_once(self):
        decisions.veto(self.proj, "D-0001", "wrong call")
        self.assertIn("veto: wrong call\n", self.f.read_text())
        decisions.veto(self.proj, "D-0001", "again")          # already vetoed → unchanged
        self.assertIn("veto: wrong call\n", self.f.read_text())

    def test_veto_unknown_raises(self):
        with self.assertRaises(KeyError):
            decisions.veto(self.proj, "D-0099", "x")

    def test_no_file_is_empty(self):
        self.f.unlink()
        self.assertEqual(decisions.list_decisions(self.proj), {"entries": [], "skipped": []})
```

Append to `tests/test_advisor.py`, reusing its fixture root (a temp copy of an advisor corpus,
whatever that file already builds):

```python
    def test_retire_unretire_roundtrip(self):
        r = advisor.retire("ATLB-01-R9", "superseded", root=self.root)
        self.assertEqual(r["returncode"], 0, r)
        self.assertIn("ATLB-01-R9", advisor.retired(root=self.root))
        advisor.unretire("ATLB-01-R9", root=self.root)
        self.assertNotIn("ATLB-01-R9", advisor.retired(root=self.root))

    def test_retire_rejects_path_shaped_id(self):
        with self.assertRaises(ValueError):
            advisor.retire("../../etc", "x", root=self.root)
```

  If the existing fixture is not a full corpus with `ATLB-01-R9`, build the fixture from
  `/home/trbck/workspace/boil/.worktrees/advisor-merge/advisor`, copied into a tempdir.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /home/trbck/workspace/helm/.worktrees/advisor-retire && python3 -m pytest -q tests/test_decisions.py tests/test_advisor.py`
Expected: FAIL (there is no `decisions` module and no `advisor.retire`).

- [ ] **Step 4: Implement `advisor.py` additions**

```python
ROOT = Path(os.environ.get("HELM_ADVISOR_ROOT") or Path.home() / "workspace" / "boil" / "advisor")
_RULE_ID = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z0-9-]+-R\d+$")


def _boil_advise(root: Path) -> Path:
    return root.parent / "scripts" / "boil-advise.py"


def retire(rule_id: str, reason: str, root: Path | None = None) -> dict:
    root = root or ROOT
    rid = rule_id.upper()
    if not _RULE_ID.match(rid) or not reason.strip():
        raise ValueError("a rule id and a reason are required")
    return _run_advise(["retire", rid, "--reason", reason.strip(), "--by", "helm"], root)


def unretire(rule_id: str, root: Path | None = None) -> dict:
    root = root or ROOT
    rid = rule_id.upper()
    if not _RULE_ID.match(rid):
        raise ValueError("not a rule id")
    return _run_advise(["unretire", rid], root)


def retired(root: Path | None = None) -> dict:
    root = root or ROOT
    out = {}
    for p in sorted((root / "domains").glob("*/retired.json")):
        for rid, meta in _read_json(p).items():
            out[rid] = dict(meta, domain=p.parent.name)
    return out
```

  - `_run_advise(args, root)` runs `[sys.executable, str(_boil_advise(root)), *args]` with
    `env=dict(os.environ, BOIL_ADVISOR_ROOT=str(root))`, and returns the same dict shape as the
    existing `_run` (reuse `_run`'s internals: read it first).
  - When `_boil_advise(root)` does not exist (a fixture corpus outside boil), fall back to boil's
    real script at `Path.home()/"workspace"/"boil"/"scripts"/"boil-advise.py"`, still with
    `BOIL_ADVISOR_ROOT=root`.
  - Update the module docstring's path from `~/src/advisor` to `~/workspace/boil/advisor`.

- [ ] **Step 5: Implement `decisions.py`**

```python
"""decisions — the operator's view of `.boil/decisions.md`: what the advisor decided, and a veto.

Format and semantics are boil's (`scripts/boil-advise.py`, `parse_decisions`). helm only writes
the `veto:` line; `boil advise sweep` (run by boil-now) reopens the ticket and records the veto.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

HEADER = re.compile(r"^## (D-\d{4}) · (\S+) · ticket (\S*)\s*$")
FIELDS = ("question", "answer", "rules", "why", "veto")


def _unesc(s: str) -> str:
    return re.sub(r"\\(\\|n)", lambda m: "\n" if m.group(1) == "n" else "\\", s)


def _parse(text: str) -> tuple[list[dict], list[str]]:
    out, cur = [], None
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            cur = {"id": m.group(1), "ts": m.group(2), "ticket": m.group(3) or ""}
            out.append(cur)
        elif cur is not None and line.startswith("## "):
            cur = {"id": line[3:].split(" ", 1)[0], "_bad": True}
            out.append(cur)
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            if k in FIELDS:
                cur[k] = v.strip()
    good, bad = [], []
    for e in out:
        if not e.get("_bad") and all(k in e for k in FIELDS):
            e["question"], e["answer"], e["why"] = (_unesc(e[k]) for k in ("question", "answer", "why"))
            e["rules"] = [r.strip() for r in e["rules"].split(",") if r.strip()]
            e["vetoed"] = e["veto"] not in ("–", "-", "")
            e["swept"] = e["veto"].endswith("(swept)")
            good.append(e)
        else:
            bad.append(e["id"])
    return good, bad


def list_decisions(project: Path) -> dict:
    f = Path(project) / ".boil" / "decisions.md"
    if not f.exists():
        return {"entries": [], "skipped": []}
    good, bad = _parse(f.read_text(encoding="utf-8"))
    return {"entries": good, "skipped": bad}


def veto(project: Path, did: str, reason: str) -> dict:
    f = Path(project) / ".boil" / "decisions.md"
    text = f.read_text(encoding="utf-8") if f.exists() else ""
    good, _ = _parse(text)
    entry = next((e for e in good if e["id"] == did), None)
    if entry is None:
        raise KeyError(did)
    if entry["vetoed"]:
        return {"id": did, "changed": False}
    reason = " ".join(reason.split()) or "vetoed in helm"
    new = re.sub(rf"(^## {re.escape(did)} ·.*?^veto: )–$", lambda m: m.group(1) + reason,
                 text, count=1, flags=re.M | re.S)
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(tmp, f)
    return {"id": did, "changed": True}
```

  Note: the header regex in `_parse` treats `## D-0002 · broken` as a bad entry because it does
  not match `HEADER`. The `elif line.startswith("## ")` branch records it as skipped. Keep that
  branch *after* the `HEADER` match.

- [ ] **Step 6: Routes.** Follow the exact patterns of `_advisor_get`, `_advisor_post` and the
  `/api/project/<p>/…` handlers in `server.py`.
  - GET `/api/advisor/retired` → `{"retired": advisor.retired()}`
  - POST `/api/advisor/rule/<id>/retire`, body `{reason}` → `advisor.retire`. A `ValueError`
    returns 400.
  - POST `/api/advisor/rule/<id>/unretire` → `advisor.unretire`
  - GET `/api/project/<p>/decisions` → `decisions.list_decisions(p)`
  - POST `/api/project/<p>/decision/<D-id>/veto`, body `{reason}` → `decisions.veto`. A
    `KeyError` returns 404, and a D-id that does not match `^D-\d{4}$` returns 400.

  Add route tests to `tests/test_server.py`, following its existing request helper: one 200, one
  400 and one 404.

- [ ] **Step 7: UI in `static/index.html`**
  - In the advisor tab's rule view: add a **Retire** button that uses `prompt()` for the reason,
    rejects an empty reason, POSTs, and refreshes.
  - Add a **Retired** filter chip that lists `/api/advisor/retired`, each row with an
    **Unretire** button.
  - In the project detail view, add a **Decisions** fold (hidden when there are no entries). Each
    entry shows its ID, question, answer, rule chips (a click opens the existing rule view) and
    `why`. Show a **Veto** button when not vetoed; show "vetoed: reason" when vetoed, plus
    "(reopened)" once swept.
  - Reuse the existing classes and fetch helpers: read how the advisor tab renders a rule and how
    folds are built, and copy that.

- [ ] **Step 8: Run the tests, look at the UI, commit**

```bash
python3 -m pytest -q tests 2>&1 | tail -3
```

  Expected: every test passes except the 2 known failures that come from the other session's
  uncommitted work. Those do not occur in this worktree, because it is built from `main`, so
  expect all passing.

  Visual check: start the server from the worktree on a spare port with `HELM_WORKSPACE` pointed
  at a temp workspace containing one project with a `decisions.md`, then capture it with the iris
  `capture` tool. Check the Decisions fold and the Retire button.

```bash
git add -A && git commit -m "advisor: retire/unretire rules and a decisions panel with veto; corpus root is boil/advisor"
```

---

### Task 8: Integrate and cut over

- [ ] **Step 1: Whole-branch review of boil `advisor-merge`**
  - Run both suites.
  - Run `python3 scripts/boil-advise.py lookup --domain trading --search "kelly"` from `/tmp` to
    prove it is cwd-independent.
  - Dispatch one fresh reviewer (the code-review skill) over `git diff main...advisor-merge`, and
    over helm's `git diff main...advisor-retire`.

- [ ] **Step 2: Merge**
  - boil: from the worktree, `git switch` is not possible in the main checkout, so merge with
    `git -C /home/trbck/workspace/boil/.worktrees/advisor-merge rebase main`. Report to the user
    that `advisor-merge` is ready for a fast-forward into `main`; do not touch the main checkout
    while it holds another session's changes.
  - helm: same approach for the `advisor-retire` branch.

- [ ] **Step 3: Cutover (ASK THE USER first, as agreed in the spec)**
  - `rm ~/.claude/skills/advisor`: removes the symlink only. Neither clone is deleted.
  - Push a pointer README to `trbck/advisor` and archive the repository with
    `gh repo archive trbck/advisor` — `gh` is not installed here, so the user archives it (GitHub → Settings → Archive).

- [ ] **Step 4: Update the memory note** `advisor-merge-decision.md` with what shipped and what
  remains.
