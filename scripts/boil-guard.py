#!/usr/bin/env python3
"""boil-guard — a Claude Code PreToolUse hook: the worker never edits the ruler.

Wired into a session via `--settings` (print the file with `--settings-json`).
Claude Code runs this before every Write / Edit / MultiEdit / Bash call with the
tool call as JSON on stdin. Exit 2 BLOCKS the call and shows stderr to the model;
exit 0 allows it. Protected:

  * tests/                                  the project's test tree
  * every `protect` path in .boil/checks/frozen.json
  * .boil/checks/  and  .boil/milestones.json   the frozen ruler itself
  * any edit that writes, removes or downgrades an `EVIDENCE: … | human` line in
    goal.md or ladder.md, and ANY shell write to those two files at all — the human
    gate is the OPERATOR'S alone, and a blind shell write is not inspectable

Whoever is being measured never owns the ruler. FAILS CLOSED: any internal error
exits 2, because every other exit code is read as ALLOW. Denials are appended to
.boil/guard.jsonl so a worker probing the sensor surface is visible to the operator.

This is a heuristic pre-emptive layer, not the binding gate: it can be evaded by
write techniques it does not recognize, so the frozen hash checked by
`boil-check verify` remains the actual tamper detector of record.

Known-open classes (deliberately NOT caught, because catching them reliably needs a
shell, not a regex): path obfuscation — `te\\sts/x.py`, a glob like `test*/x.py`, or a
name assembled from a variable (`d=tests; echo x > $d/t.py`); a write performed by a
script already on disk (`./fix.sh`, `make regen`), whose body this hook never sees;
and a hardlink (`ln tests/t.py alias.py`) that reaches the same inode under a name no
realpath can distinguish. All of these still change the harness bytes, so
`boil-check.py verify` reports TAMPER (exit 50) and the milestone cannot go green.
The guard raises the cost of the obvious moves; the frozen hash is what binds.

Ported from helm's guard_hook.py (2026-08-29). Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import sys
from pathlib import Path

ALWAYS_PROTECTED = (".boil/checks", ".boil/milestones.json", "tests")
EVIDENCE_TARGETS = (".boil/goal.md", ".boil/ladder.md")
HUMAN_EVIDENCE = re.compile(r"\|\s*human\b")
# Word-bounded write operators: matched only as standalone tokens (see mentioned()'s
# boundary trick below) so "git add" is not "dd ", and "echo confirm results" is not "rm ".
WRITE_OP_WORDS = ("tee", "sed -i", "truncate", "dd", "cp", "mv", "rm", "rsync",
                  "install", "patch", "ln", "touch", "mkdir", "unlink", "shred", "tar",
                  "curl -o", "curl -O", "wget -O", "sort -o",
                  "python -c", "python3 -c", "perl -e", "ruby -e", "node -e")
# Write forms that need a pattern rather than a literal word.
WRITE_OP_PATTERNS = (
    r"git\s+(?:checkout|restore|stash|apply|reset|clean|rm|mv)\b",   # git can clobber a worktree
    r"sed\s+-[A-Za-z]*i\b", r"sed\s+--in-place", r"perl\s+-[A-Za-z]*i\b",
    r"find\b[^;&|]*\s-delete\b",
    r"(?:python3?|node|perl|ruby)\s+-(?![A-Za-z0-9_-])",   # interpreter reading a program on stdin
    r"(?:sh|bash|zsh)\b[^\n]*<<",                          # ... or from a heredoc
)
_WRITE_OP_WORD_RE = re.compile("|".join(
    [rf"(?<![A-Za-z0-9_.-]){re.escape(op)}(?![A-Za-z0-9_-])" for op in WRITE_OP_WORDS]
    + [rf"(?<![A-Za-z0-9_.-])(?:{pat})" for pat in WRITE_OP_PATTERNS]))
# Inline writes in an interpreter one-liner or heredoc, even without a recognized flag.
_OPEN_WRITE_RE = re.compile(
    r"""open\(\s*['"][^'"]*['"]\s*,\s*['"][wa]"""
    r"""|write_text\(|write_bytes\("""
    r"""|mode\s*=\s*['"][wax]"""
    r"""|shutil\.(?:copy|move|rmtree)""")
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./~-]+")
# Quoted runs, MASKED (not deleted) before redirect parsing: their punctuation must not
# parse as an operator, but a quoted redirect target must survive to be checked.
_QUOTED_RE = re.compile("'[^']*'" + r'|"[^"]*"')
_MASK_RE = re.compile("\x00Q(\\d+)\x00")
# One pass over a command finds fd duplications (2>&1 — NOT a write) and real redirects
# (>, >>, >|, &>, 2>) together with the token each one writes to.
_REDIRECT_RE = re.compile(
    r"(?P<dup>\d*>&\s*\d+)"
    r"|(?<![-<>=])(?P<redir>&>>|&>|\d*>>|\d*>\||\d*>)\s*(?P<target>[^\s;|&()<>]*)")
_NON_WRITE_TARGETS = ("/dev/null", "/dev/stdout", "/dev/stderr")


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


def _path_variants(p: Path) -> set[Path]:
    """The lexical (normpath) form of an absolute path, plus its symlink-resolved form
    when the filesystem can produce one. A symlink loop makes resolve() raise
    RuntimeError on 3.11 and a dangling mount makes it raise OSError; neither is a
    reason to refuse the call, so an unresolvable path is compared textually only."""
    out = {Path(os.path.normpath(p))}
    try:
        out.add(p.resolve())
    except (OSError, RuntimeError):
        pass
    return out


def _same_or_under(target: Path, candidate: Path) -> bool:
    """True when absolute `target` IS `candidate` or lives under it — comparing both the
    lexical and the realpath form of each, so an alias like src/alias.py ->
    ../tests/secret.py cannot reach a protected file under an unprotected-looking name.
    The single place symlink aliasing is resolved: protected paths and evidence targets
    both go through here."""
    for t_v in _path_variants(target):
        for c_v in _path_variants(candidate):
            if t_v == c_v or _under(t_v, c_v):
                return True
    return False


def _abs(p: Path, root: Path) -> Path:
    return p if p.is_absolute() else root / p


def is_protected(target: Path, root: Path, prots: list[Path]) -> str | None:
    t = _abs(target, root)
    for p in prots:
        if _same_or_under(t, p):
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


def _resolve_bash_token(tok: str, root: Path) -> Path | None:
    """Best-effort realpath of a path-like Bash token, following symlinks — so an alias
    like src/alias.py -> ../tests/secret.py resolves onto the file it really points at,
    not the unprotected-looking name it was written through."""
    if not tok or tok in (".", ".."):
        return None
    try:
        if tok.startswith("~"):
            return Path(os.path.expanduser(tok)).resolve()
        p = Path(tok)
        return p.resolve() if p.is_absolute() else (root / p).resolve()
    except (OSError, RuntimeError):   # a symlink loop is not a reason to refuse the call
        return None


def bash_path_tokens(cmd: str) -> list[str]:
    """Path-shaped words in a shell command: anything with a slash, or a dotted
    suffix like .py — not bare flags or plain words such as `pwned` or `-p1`."""
    return [t for t in _PATH_TOKEN_RE.findall(cmd)
            if "/" in t or re.search(r"\.[A-Za-z0-9]{1,8}$", t)]


def _mask_quoted(cmd: str) -> tuple[str, list[str]]:
    """Replace each quoted run with a placeholder that holds its PLACE but hides its
    punctuation, and return the placeholder table. Deleting quoted runs instead would
    silence `> 'tests/x.py'` — the target would come back empty and the write would look
    like no write at all. The placeholder contains no shell metacharacter, so it cannot
    parse as an operator and cannot end a target token."""
    parts: list[str] = []

    def take(m: re.Match) -> str:
        parts.append(m.group(0)[1:-1])     # the quoted content, quotes dropped
        return f"\x00Q{len(parts) - 1}\x00"

    return _QUOTED_RE.sub(take, cmd), parts


def _unmask(tok: str, parts: list[str]) -> str:
    """Put the quoted content back, joining it to whatever sat beside it —
    `"tests"/x.py` and `.boil/"goal.md"` both come back as one ordinary path."""
    return _MASK_RE.sub(lambda m: parts[int(m.group(1))], tok)


def redirect_targets(cmd: str) -> list[str]:
    """The files this command REDIRECTS output into. `>` is not a write on its own:
    `2>&1` duplicates an fd, `2>/dev/null` discards, and `'->'` inside a quoted grep
    pattern is not a redirect at all (quoted runs are masked before the scan). Only
    the token that follows a real redirect operator is a write target — which is why
    `pytest tests/ > /tmp/out` is allowed while `echo x > tests/t.py` is not. Quoting
    the target changes nothing: the mask is unwound before the token is returned."""
    masked, parts = _mask_quoted(cmd)
    targets = []
    for m in _REDIRECT_RE.finditer(masked):
        if m.group("dup") or not m.group("redir"):
            continue                       # 2>&1 and friends move an fd, they write nothing
        tok = _unmask((m.group("target") or "").strip(), parts).strip()
        if not tok or tok in _NON_WRITE_TARGETS:
            continue
        targets.append(tok)
    return targets


def has_verb_write(cmd: str) -> bool:
    """A command that writes through a verb (rm, sed -i, tee, git checkout, an inline
    interpreter write, ...) rather than through a redirect."""
    return bool(_WRITE_OP_WORD_RE.search(cmd) or _OPEN_WRITE_RE.search(cmd))


def has_write_op(cmd: str) -> bool:
    return has_verb_write(cmd) or bool(redirect_targets(cmd))


def target_hits(tok: str, path: Path, root: Path) -> bool:
    """A redirect target names `path` — textually (the token spells it out) or after
    resolving the token through any symlink on the way."""
    return mentioned(tok, path, root) or _same_or_under(_abs(Path(tok), root), path)


def new_text_of(tool: str, tinput: dict) -> str:
    if tool == "Write":
        return str(tinput.get("content") or "")
    if tool == "Edit":
        return str(tinput.get("new_string") or "")
    if tool == "MultiEdit":
        return "\n".join(str(e.get("new_string") or "") for e in (tinput.get("edits") or []))
    return ""


def old_text_of(tool: str, tinput: dict) -> str:
    """What an edit REMOVES. A worker deleting or downgrading a `| human` line is
    tampering with the gate just as surely as one writing a new one."""
    if tool == "Edit":
        return str(tinput.get("old_string") or "")
    if tool == "MultiEdit":
        return "\n".join(str(e.get("old_string") or "") for e in (tinput.get("edits") or []))
    return ""


def _human_lines(text: str) -> list[str]:
    return [ln.rstrip() for ln in text.splitlines() if HUMAN_EVIDENCE.search(ln)]


def human_gate_breach(tool: str, tinput: dict, target: Path) -> bool:
    """True when this Write/Edit/MultiEdit would add, remove or alter a `| human` line.

    Edit/MultiEdit: either side of the swap carrying `| human` is a breach — new_string
    writes the operator's approval, old_string deletes or downgrades it.
    Write: the whole file is replaced, so compare human lines against what is on disk —
    every existing one must survive verbatim, and no new one may appear."""
    if tool in ("Edit", "MultiEdit"):
        return bool(HUMAN_EVIDENCE.search(new_text_of(tool, tinput))
                    or HUMAN_EVIDENCE.search(old_text_of(tool, tinput)))
    try:
        on_disk = _human_lines(target.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        on_disk = []
    incoming = _human_lines(new_text_of(tool, tinput))
    return any(ln not in incoming for ln in on_disk) or any(ln not in on_disk for ln in incoming)


def _rel(p: Path, root: Path) -> str:
    return str(p.relative_to(root)) if _under(p, root) else str(p)


def decide_bash(cmd: str, root: Path, prots: list[Path]) -> tuple[int, str]:
    verb = has_verb_write(cmd)
    redirs = redirect_targets(cmd)
    if not verb and not redirs:
        return 0, ""
    # The goal/ladder evidence column is never writable from the shell — not even to fix a
    # typo. `sed -i` on goal.md is indistinguishable from `sed -i` that rewrites a human
    # date, so the whole file is off-limits to blind shell writes; Edit is inspectable.
    for e in EVIDENCE_TARGETS:
        ev = root / e
        if (verb and mentioned(cmd, ev, root)) or any(target_hits(tok, ev, root) for tok in redirs):
            return 2, (f"boil guard: refusing a shell write to {e} — its evidence column is the "
                       "operator's authority and a blind shell write is not inspectable. Use the "
                       "Edit tool for goal/ladder text; a `| human` line is the operator's alone.")
    # A verb write (rm, sed -i, tee, git checkout, ...) is judged on the WHOLE command: any
    # protected path it names, or that one of its path tokens resolves onto, is a refusal.
    if verb:
        for p in prots:
            if mentioned(cmd, p, root):
                return 2, (f"boil guard: refusing a shell write that touches protected sensor "
                           f"{_rel(p, root)}. The ruler is read-only; make the real code change "
                           "instead.")
        for tok in bash_path_tokens(cmd):
            t_real = _resolve_bash_token(tok, root)
            if t_real is None:
                continue
            for p in prots:
                if _same_or_under(t_real, p):
                    return 2, (f"boil guard: refusing a shell write that resolves onto protected "
                               f"sensor {_rel(p, root)} (via `{tok}`, an alias or symlink). The "
                               "ruler is read-only; make the real code change instead.")
    # A redirect is judged on its TARGET only: `git diff -- tests/ > /tmp/out.diff` reads the
    # sensor and writes somewhere harmless, which the worker needs to be able to do.
    for tok in redirs:
        for p in prots:
            if target_hits(tok, p, root):
                return 2, (f"boil guard: refusing a shell redirect onto protected sensor "
                           f"{_rel(p, root)} (via `{tok}`). The ruler is read-only; make the real "
                           "code change instead.")
    return 0, ""


def decide(tool: str, tinput: dict, root: Path) -> tuple[int, str]:
    prots = protected_paths(root)
    if tool == "Bash":
        return decide_bash(str(tinput.get("command") or ""), root, prots)
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
    t_abs = _abs(target, root)
    if any(_same_or_under(t_abs, root / e) for e in EVIDENCE_TARGETS):
        if human_gate_breach(tool, tinput, t_abs):
            return 2, ("boil guard: a `| human` evidence line is the operator's sole authority — a "
                       "worker may not write, remove or downgrade one. Leave the box open; auto "
                       "evidence (`| auto`) from a real command is fine.")
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
    cmd = f"python3 {shlex.quote(str(me))} --root {shlex.quote(str(root))}"
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
