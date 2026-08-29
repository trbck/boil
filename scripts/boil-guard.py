#!/usr/bin/env python3
"""boil-guard — a Claude Code PreToolUse hook: the worker never edits the ruler.

Wired into a session via `--settings` (print the file with `--settings-json`).
Claude Code runs this before every Write / Edit / MultiEdit / Bash call with the
tool call as JSON on stdin. Exit 2 BLOCKS the call and shows stderr to the model;
exit 0 allows it. Protected:

  * tests/                                  the project's test tree
  * every `protect` path in .boil/checks/frozen.json
  * .boil/checks/  and  .boil/milestones.json   the frozen ruler itself
  * any edit or shell write that puts an `EVIDENCE: … | human` line into goal.md
    or ladder.md — the human gate is the OPERATOR'S alone

Whoever is being measured never owns the ruler. FAILS CLOSED: any internal error
exits 2, because every other exit code is read as ALLOW. Denials are appended to
.boil/guard.jsonl so a worker probing the sensor surface is visible to the operator.

This is a heuristic pre-emptive layer, not the binding gate: it can be evaded by
write techniques it does not recognize, so the frozen hash checked by
`boil-check verify` remains the actual tamper detector of record.

Ported from helm's guard_hook.py (2026-08-29). Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ALWAYS_PROTECTED = (".boil/checks", ".boil/milestones.json", "tests")
EVIDENCE_TARGETS = (".boil/goal.md", ".boil/ladder.md")
HUMAN_EVIDENCE = re.compile(r"\|\s*human\b")
WRITE_REDIRECTS = (">", ">>")
# Word-bounded write operators: matched only as standalone tokens (see mentioned()'s
# boundary trick below) so "git add" is not "dd ", and "echo confirm results" is not "rm ".
WRITE_OP_WORDS = ("tee", "sed -i", "truncate", "dd", "cp", "mv", "rm", "rsync",
                  "install", "patch", "ln -s",
                  "python -c", "python3 -c", "perl -e", "ruby -e", "node -e")
_WRITE_OP_WORD_RE = re.compile("|".join(
    rf"(?<![A-Za-z0-9_./-]){re.escape(op)}(?![A-Za-z0-9_-])" for op in WRITE_OP_WORDS))
# open('path', 'w'/'a'/'w+'/... ) — a bare inline write even without a recognized interpreter flag.
_OPEN_WRITE_RE = re.compile(r"""open\(\s*['"][^'"]*['"]\s*,\s*['"][wa]""")


def protected_paths(root: Path) -> list[Path]:
    prots = [root / p for p in ALWAYS_PROTECTED]
    frozen = root / ".boil" / "checks" / "frozen.json"
    if frozen.is_file():
        try:
            for m in json.loads(frozen.read_text(encoding="utf-8")).get("milestones", []):
                for rel in m.get("protect", []):
                    prots.append(root / rel)
        except (json.JSONDecodeError, AttributeError):
            pass  # an unreadable freeze still leaves the ALWAYS set protected
    return prots


def _under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_protected(target: Path, root: Path, prots: list[Path]) -> str | None:
    t = target if target.is_absolute() else root / target
    # Compare both the lexical path and its resolved (symlink-following) realpath, so an
    # alias like src/alias.py -> ../tests/secret.py cannot be used to edit a protected
    # file under a name that itself looks unprotected.
    t_variants = {Path(os.path.normpath(t)), t.resolve()}
    for p in prots:
        p_variants = {Path(os.path.normpath(p)), p.resolve()}
        for t_v in t_variants:
            for p_v in p_variants:
                if t_v == p_v or _under(t_v, p_v):
                    try:
                        return str(p.relative_to(root))
                    except ValueError:
                        return str(p)
    return None


def mentioned(cmd: str, prot: Path, root: Path) -> bool:
    """The command references the protected path as an absolute path, a root-relative
    path, or a standalone path token (not a bare substring of an unrelated word)."""
    try:
        rel = str(prot.relative_to(root))
    except ValueError:
        rel = ""
    for s in (str(prot), rel):
        if s and re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(s)}(?![A-Za-z0-9_-])", cmd):
            return True
    return False


def has_write_op(cmd: str) -> bool:
    if any(op in cmd for op in WRITE_REDIRECTS):
        return True
    if _WRITE_OP_WORD_RE.search(cmd):
        return True
    if _OPEN_WRITE_RE.search(cmd):
        return True
    return False


def new_text_of(tool: str, tinput: dict) -> str:
    if tool == "Write":
        return str(tinput.get("content") or "")
    if tool == "Edit":
        return str(tinput.get("new_string") or "")
    if tool == "MultiEdit":
        return "\n".join(str(e.get("new_string") or "") for e in (tinput.get("edits") or []))
    return ""


def decide(tool: str, tinput: dict, root: Path) -> tuple[int, str]:
    prots = protected_paths(root)
    if tool == "Bash":
        cmd = str(tinput.get("command") or "")
        if not has_write_op(cmd):
            return 0, ""
        if HUMAN_EVIDENCE.search(cmd) and any(mentioned(cmd, root / t, root) for t in EVIDENCE_TARGETS):
            return 2, ("boil guard: a `| human` evidence line is the operator's sole authority — a "
                       "worker may not approve its own human gate. Leave the box open.")
        for p in prots:
            if mentioned(cmd, p, root):
                return 2, (f"boil guard: refusing a shell write that touches protected sensor "
                           f"{p.relative_to(root) if _under(p, root) else p}. The ruler is read-only; "
                           "make the real code change instead.")
        return 0, ""
    if tool not in ("Write", "Edit", "MultiEdit"):
        return 0, ""
    fp = str(tinput.get("file_path") or tinput.get("path") or "")
    if not fp:
        return 0, ""
    target = Path(fp)
    reason = is_protected(target, root, prots)
    if reason:
        return 2, (f"boil guard: refusing to edit {reason} — it is part of the ruler this goal is "
                   "measured by. A check may not be made to pass by editing the sensor. Make the "
                   "real code change instead.")
    t_abs = Path(os.path.normpath(target if target.is_absolute() else root / target))
    if any(t_abs == Path(os.path.normpath(root / e)) for e in EVIDENCE_TARGETS):
        if HUMAN_EVIDENCE.search(new_text_of(tool, tinput)):
            return 2, ("boil guard: a `| human` evidence line is the operator's sole authority — a "
                       "worker may not approve its own human gate. Leave the box open; auto evidence "
                       "(`| auto`) from a real command is fine.")
    return 0, ""


def audit(root: Path, tool: str, tinput: dict, reason: str) -> None:
    """Best-effort, after the verdict; must never change it or crash the hook."""
    try:
        target = (tinput.get("file_path") or tinput.get("path") or str(tinput.get("command") or "")[:200])
        rec = {"ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "tool": tool, "target": str(target), "reason": reason.split("—")[0].strip()[:160]}
        p = root / ".boil" / "guard.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(p, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(rec) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except BaseException:
        pass


def settings_json(root: Path) -> dict:
    me = Path(__file__).resolve()
    cmd = f"python3 '{me}' --root '{root}'"
    return {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|MultiEdit|Bash",
                                      "hooks": [{"type": "command", "command": cmd}]}]}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="project root (the dir containing .boil/)")
    ap.add_argument("--settings-json", action="store_true",
                    help="print the Claude Code --settings file that wires this hook, and exit")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if a.settings_json:
        print(json.dumps(settings_json(root), indent=2))
        return 0
    tool, tinput = "", {}
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name") or payload.get("tool") or ""
        tinput = payload.get("tool_input") or payload.get("input") or {}
        if not isinstance(tinput, dict):
            raise TypeError("tool_input is not an object")
        rc, reason = decide(str(tool), tinput, root)
    except BaseException as e:  # noqa: BLE001 — fail CLOSED: any other exit code means ALLOW
        sys.stderr.write(f"boil guard: internal error ({e}) — refusing this tool call. "
                         "The edit was NOT evaluated; this is a guard bug.\n")
        audit(root, str(tool), tinput if isinstance(tinput, dict) else {}, f"internal error: {e}")
        return 2
    if rc == 2:
        sys.stderr.write(reason + "\n")
        audit(root, str(tool), tinput, reason)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
