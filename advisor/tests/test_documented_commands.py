"""Run the commands the documentation tells you to run.

Every documented `ingest.py` invocation was wrong for as long as two domains had
been installed: the script refuses to guess a domain, and none of the examples
passed one. Nothing caught it, because documentation is not executed. This
executes it.

Only read-only commands are run. A test that ingests, rebuilds, or writes review
files would be a test that edits the corpus it is checking, and the first thing
anyone would do is stop running it.
"""

import os
import re
import shlex
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCS = ["templates/advisor-reference.md.tmpl", "README.md", "FORMAT.md", "inbox/README.md",
        "references/workflows.md", "references/compliance.md",
        "references/maintaining.md"]

# Placeholders a real value can stand in for. Anything else makes the line
# un-runnable, and it is skipped rather than guessed at.
SUBSTITUTIONS = {
    "<id>": "trading",
    "<domain>": "trading",
}

# Scripts that write. Never run from a test.
WRITERS = {"build_index.py", "suggest_taxonomy.py", "suggest_conflicts.py",
           "package_domain.py", "ingest.py", "research_note.py"}

# Needs a live research run on disk, which a checkout does not have.
NEEDS_RESEARCH_RUN = {"research_status.py", "research_note.py"}


def engine_sources_present():
    """Licensed engine docs are gitignored, so most machines legitimately lack them.

    Engine examples must still be checked wherever the files *are* present — that
    is the only place the commands can be wrong for a reason worth fixing.
    """
    import glob
    return bool(glob.glob(os.path.join(ROOT, "domains", "*", "knowledge", "*", "llms*.txt")))


def bash_blocks(text):
    return re.findall(r"```bash\n(.*?)```", text, re.DOTALL)


def documented_commands():
    """(source file, command line) for every command in a bash block."""
    out = []
    for rel in DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for block in bash_blocks(fh.read()):
                for line in block.splitlines():
                    line = line.split("#")[0].strip()
                    if line.startswith(("python3 ", "bin/")):
                        out.append((rel, line))
    return out


def runnable(cmd):
    """(command, reason-if-skipped). A skip is not a pass — the count is asserted."""
    for placeholder, value in SUBSTITUTIONS.items():
        cmd = cmd.replace(placeholder, value)
    if re.search(r"<[^>]+>|\.\.\.", cmd):
        return cmd, "unresolved placeholder"
    if cmd.startswith("bin/"):
        return cmd, "installer — mutates the machine"
    script = os.path.basename(shlex.split(cmd)[1]) if len(shlex.split(cmd)) > 1 else ""
    if script in NEEDS_RESEARCH_RUN:
        return cmd, "needs a live research run"
    if script in WRITERS and "--dry-run" not in cmd:
        return cmd, "writes to the corpus"
    if script == "rule_baseline.py" and "--update" in cmd:
        return cmd, "rewrites the baseline"
    if "--engine" in cmd and not engine_sources_present():
        return cmd, "engine sources absent here"
    if "pytest" in cmd or "unittest" in cmd:
        # Documenting how to run the tests means this extractor will find that
        # line and run the suite from inside the suite. Once.
        return cmd, "would re-enter the test suite"
    for arg in shlex.split(cmd)[2:]:
        # An illustrative filename (`check_citations.py answer.md`) is not a
        # command that should work — it is an example of a shape.
        if arg.endswith((".md", ".txt", ".json")) and not os.path.exists(
                os.path.join(ROOT, arg)):
            return cmd, "example filename, not a real path"
    return cmd, None


class DocumentedCommandsTest(unittest.TestCase):
    def setUp(self):
        self.commands = documented_commands()

    def test_the_extractor_actually_found_commands(self):
        # A regex that quietly matches nothing would make every other assertion vacuous.
        self.assertGreater(len(self.commands), 10)

    def test_enough_of_them_are_runnable_to_be_worth_checking(self):
        live = [c for c, skip in map(runnable, (c for _, c in self.commands)) if not skip]
        self.assertGreater(len(live), 5,
                           "almost every documented command was skipped — the "
                           "substitutions or the allowlist have drifted")

    def test_every_runnable_documented_command_succeeds(self):
        failures = []
        for source, raw in self.commands:
            cmd, skip = runnable(raw)
            if skip:
                continue
            proc = subprocess.run(shlex.split(cmd), cwd=ROOT, capture_output=True,
                                  text=True, timeout=120)
            if proc.returncode != 0:
                failures.append("%s: `%s` exited %d\n    %s"
                                % (source, cmd, proc.returncode,
                                   (proc.stderr or proc.stdout).strip().splitlines()[-1:]))
        self.assertEqual(failures, [], "documented commands that do not work:\n"
                         + "\n".join(failures))


if __name__ == "__main__":
    for source, raw in documented_commands():
        cmd, skip = runnable(raw)
        print("%-8s %-22s %s" % ("SKIP" if skip else "RUN", skip or "", cmd))
    sys.exit(unittest.main())
