#!/usr/bin/env python3
"""boil-loop — the manager of boil's self-correcting builder/judge/manager loop.

The manager is the only deterministic role in the triad. The builder and the judge
are LLMs; this script is the state machine that bounds them: it freezes the answer
key before the first attempt, refuses a key the builder could have authored, applies
the decision table, and escalates to a human at a hard retry limit instead of
granting one more try.

Protocol: references/self-correcting-loop.md

Commands
  init         freeze the answer key + create .boil/loops/<T>/loop.json
  record-build store a builder's report for an attempt (+ key-integrity check)
  record-judge store a judge's verdict for an attempt
  decide       apply the decision table → ACCEPT | REVISE | ESCALATE-* | ABORT-TAMPER
  escalate     write the human packet and (optionally) convert the ticket
  status       show every loop's state
  audit        loop-safety gate for boil-run-iteration.sh

Exit codes
  0  command succeeded; decision was ACCEPT or REVISE
  2  usage / validation error (bad or unfreezable key, malformed ticket)
  3  the loop reached a terminal human-facing state (any ESCALATE-*, ABORT-TAMPER)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print("boil-loop: PyYAML is required", file=sys.stderr)
    sys.exit(2)


SKILL_ROOT = Path(__file__).resolve().parents[1]

VALID_KINDS = {"suite", "document", "checklist", "none"}
VALID_VERDICTS = {"PASS", "FAIL", "INDETERMINATE", "INVALID"}
DEFAULT_MAX_REVISIONS = 3

# Ticket types whose work is behavior and therefore needs an external answer key.
BEHAVIOR_TYPES = {"bug", "feature", "test", "refactor", "perf"}

TERMINAL_DECISIONS = {
    "ABORT-TAMPER",
    "ESCALATE-BUDGET",
    "ESCALATE-INFRA",
    "ESCALATE-LIMIT",
    "ESCALATE-STALL",
    "ESCALATE-VISIBILITY",
}


# ---------- small io helpers -------------------------------------------------


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _iso(value: Any) -> str:
    """Normalize a frontmatter timestamp to `YYYY-MM-DDTHH:MM:SSZ`. PyYAML turns an
    unquoted ISO stamp into a datetime, so a naive str() would round-trip a different
    format back into the ticket every time."""
    if value in (None, ""):
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", text)
    return f"{m.group(1)}T{m.group(2)}Z" if m else text


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _die(msg: str, code: int = 2) -> None:
    print(f"boil-loop: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{path}: unterminated YAML frontmatter")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    return meta, text


def _set_top_level(text: str, key: str, block: str) -> str:
    """Replace one top-level frontmatter key (and its indented continuation) with
    `block`, or append it just before the closing `---`. Surgical on purpose: a
    yaml round-trip would silently drop the schema comments tickets carry."""
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated YAML frontmatter")
    head, tail = text[4:end], text[end:]
    lines = head.splitlines()
    out: list[str] = []
    i, replaced = 0, False
    while i < len(lines):
        line = lines[i]
        if re.match(rf"^{re.escape(key)}\s*:", line):
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                i += 1
            out.extend(block.rstrip("\n").splitlines())
            replaced = True
            continue
        out.append(line)
        i += 1
    if not replaced:
        out.extend(block.rstrip("\n").splitlines())
    return "---\n" + "\n".join(out) + tail


# ---------- paths ------------------------------------------------------------


def _boil(root: Path) -> Path:
    return root / ".boil"


def _ticket_path(root: Path, ticket: str) -> Path:
    return _boil(root) / "tickets" / f"{ticket}.md"


def _loop_dir(root: Path, ticket: str) -> Path:
    return _boil(root) / "loops" / ticket


def _loop_path(root: Path, ticket: str) -> Path:
    return _loop_dir(root, ticket) / "loop.json"


def _load_loop(root: Path, ticket: str) -> dict[str, Any]:
    p = _loop_path(root, ticket)
    if not p.exists():
        _die(f"{ticket}: no loop.json — run `boil-loop.py init --ticket {ticket}` first")
    return json.loads(p.read_text(encoding="utf-8"))


def _save_loop(root: Path, ticket: str, loop: dict[str, Any]) -> None:
    loop["updated_at"] = _now()
    _atomic_write(_loop_path(root, ticket), json.dumps(loop, indent=2) + "\n")


# ---------- the answer key ---------------------------------------------------


def key_paths(root: Path, key: dict[str, Any]) -> list[Path]:
    """Files whose content IS the key. `ref` may carry a selector suffix
    (`tests/x.py::test_y`, `spec.md#section`); the file part is what gets hashed."""
    explicit = key.get("key_paths")
    refs = list(explicit) if isinstance(explicit, list) and explicit else [str(key.get("ref") or "")]
    out: list[Path] = []
    for ref in refs:
        head = re.split(r"::|#", str(ref).strip(), maxsplit=1)[0].strip()
        if not head:
            continue
        p = Path(head)
        out.append(p if p.is_absolute() else (root / head))
    return out


def key_hash(root: Path, key: dict[str, Any]) -> tuple[str, list[str]]:
    """sha256 over the key's files, plus the list of paths that are missing.
    A key that cannot be read cannot be a setpoint — the caller must treat a
    non-empty `missing` as fatal at init and as TAMPER mid-loop."""
    h = hashlib.sha256()
    missing: list[str] = []
    for p in key_paths(root, key):
        try:
            h.update(p.read_bytes())
        except OSError:
            missing.append(str(p))
    return h.hexdigest()[:12], missing


def validate_key(ticket_meta: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Structural validation of `answer_key`, independent of the filesystem.
    Returns (key, errors)."""
    key = ticket_meta.get("answer_key")
    errors: list[str] = []
    ttype = str(ticket_meta.get("type") or "")
    if not isinstance(key, dict):
        if ttype in BEHAVIOR_TYPES:
            errors.append(f"`answer_key` is required for `type: {ttype}` tickets")
        return {}, errors

    kind = str(key.get("kind") or "")
    if kind not in VALID_KINDS:
        errors.append(f"`answer_key.kind` must be one of {sorted(VALID_KINDS)}, got `{kind}`")
    if kind == "none":
        if ttype in BEHAVIOR_TYPES:
            errors.append(f"`answer_key.kind: none` is not allowed for `type: {ttype}`")
        if not str(key.get("reason") or "").strip():
            errors.append("`answer_key.reason` is required when kind is `none`")
        return key, errors

    if not str(key.get("ref") or "").strip():
        errors.append("`answer_key.ref` is required")

    # The judge's whole value is that the key came from somewhere the builder isn't.
    author = str(key.get("authored_by") or "").strip()
    specialty = str(ticket_meta.get("specialty") or "").strip()
    if not author:
        errors.append("`answer_key.authored_by` is required (and may not be the builder)")
    elif author.lower() in {"builder", "agent", "self", "implementer"} or (
        specialty and author.lower() in {specialty.lower(), f"agent:{specialty}".lower()}
    ):
        errors.append(
            f"`answer_key.authored_by: {author}` is the builder's own specialty — "
            "the key must be authored by the orchestrator, the user, or an upstream source"
        )
    if key.get("protected") is not True:
        errors.append("`answer_key.protected` must be true")
    return key, errors


# ---------- status logging ---------------------------------------------------


def log_event(root: Path, kind: str, *, ticket: str = "", attempt: int = 0,
              status: str = "", detail: str = "", quiet: bool = False) -> None:
    """Best-effort status emit. A logging failure must never break the loop."""
    if quiet:
        return
    script = SKILL_ROOT / "scripts" / "boil-helm-log.py"
    if not script.exists():
        return
    cmd = [sys.executable, str(script), "emit", "--root", str(root), "--kind", kind]
    if ticket:
        cmd += ["--ticket", ticket]
    if attempt:
        cmd += ["--attempt", str(attempt)]
    if status:
        cmd += ["--status", status]
    if detail:
        cmd += ["--detail", detail[:400]]
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=20)
    except Exception:  # noqa: BLE001 — never break the loop for a log line
        pass


# ---------- commands ---------------------------------------------------------


def cmd_init(args) -> int:
    root = Path(args.root).resolve()
    tpath = _ticket_path(root, args.ticket)
    if not tpath.exists():
        _die(f"no such ticket: {tpath}")
    meta, _ = _frontmatter(tpath)

    key, errors = validate_key(meta)
    if errors:
        for e in errors:
            print(f"error: {args.ticket}: {e}", file=sys.stderr)
        return 2
    if not key or key.get("kind") == "none":
        reason = str(key.get("reason") or "no answer_key declared")
        print(f"boil-loop: {args.ticket} runs without a self-correcting loop ({reason}). "
              "It may not close a goal checkbox on its own.")
        return 0

    lp = _loop_path(root, args.ticket)
    if lp.exists() and not args.force:
        _die(f"{args.ticket}: loop.json already exists (use --force to re-init)")

    digest, missing = key_hash(root, key)
    if missing:
        _die(f"{args.ticket}: answer key is unreadable, so it cannot be frozen: {', '.join(missing)}")

    declared = str(key.get("frozen_sha") or "").strip()
    if declared and declared != digest:
        _die(f"{args.ticket}: answer_key.frozen_sha `{declared}` != current key hash `{digest}` — "
             "the key changed after it was frozen; restore it or re-freeze deliberately with --force")

    frozen_at = _iso(key.get("frozen_at")) or _now()
    loop = {
        "ticket": args.ticket,
        "title": str(meta.get("title") or ""),
        "specialty": str(meta.get("specialty") or ""),
        "closes_goal_checkbox": meta.get("closes_goal_checkbox") or [],
        "status": "running",
        "created_at": _now(),
        "updated_at": _now(),
        "answer_key": {
            "kind": key.get("kind"),
            "ref": key.get("ref"),
            "expect": key.get("expect", "pass"),
            "authored_by": key.get("authored_by"),
            "frozen_at": frozen_at,
            "frozen_sha": digest,
            "paths": [str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
                      for p in key_paths(root, key)],
        },
        "max_revisions": int(args.max_revisions),
        "budget": {
            "usd_cap": float(args.budget_usd or 0),
            "usd_spent": 0.0,
            "wall_clock_cap_min": int(args.wall_clock_min or 0),
        },
        "attempts": [],
        "escalated_to_ticket": "",
        "terminal_reason": "",
    }
    _save_loop(root, args.ticket, loop)
    if not declared:
        # Stamp the freeze back onto the ticket so the ticket is self-describing and
        # ticket-lint can check the key without reading loop.json.
        _freeze_into_ticket(tpath, key, digest, frozen_at)
    log_event(root, "boil.loop.init", ticket=args.ticket, status=str(key.get("kind")),
              detail=f"{key.get('ref')} frozen@{digest}", quiet=args.no_log)
    print(f"boil-loop: {args.ticket} loop armed — key {key.get('kind')} `{key.get('ref')}` "
          f"frozen at {digest}, max_revisions={args.max_revisions}")
    return 0


def _freeze_into_ticket(tpath: Path, key: dict[str, Any], digest: str, frozen_at: str) -> None:
    """Write the computed hash + freeze time back into the ticket's `answer_key`.
    This block is machine-managed from here on — inline comments inside it are not
    preserved (every other frontmatter key is left byte-for-byte alone)."""
    merged = {k: (_iso(v) if k in {"frozen_at"} else v) for k, v in key.items()}
    merged["frozen_sha"] = digest
    merged["frozen_at"] = frozen_at
    body = yaml.safe_dump(merged, sort_keys=False, default_flow_style=False, allow_unicode=True)
    block = "answer_key:\n" + "".join(f"  {line}\n" for line in body.rstrip("\n").splitlines())
    text = tpath.read_text(encoding="utf-8")
    _atomic_write(tpath, _set_top_level(text, "answer_key", block))


def _attempt(loop: dict[str, Any], n: int) -> dict[str, Any]:
    for a in loop["attempts"]:
        if a["n"] == n:
            return a
    a = {"n": n, "started_at": _now(), "verdict": "", "failure_signature": "",
         "decision": "", "reason": "", "cost_usd": 0.0, "key_integrity": "",
         "builder_family": "", "judge_family": "", "judge_runs": 0}
    loop["attempts"].append(a)
    return a


def cmd_record_build(args) -> int:
    root = Path(args.root).resolve()
    loop = _load_loop(root, args.ticket)
    n = int(args.attempt)
    att = _attempt(loop, n)

    report = sys.stdin.read() if args.report == "-" else (
        Path(args.report).read_text(encoding="utf-8") if args.report else "")
    if report:
        _atomic_write(_loop_dir(root, args.ticket) / f"attempt-{n}" / "build.md", report)

    # Key integrity — the one thing checked mechanically, not by an LLM.
    digest, missing = key_hash(root, loop["answer_key"])
    frozen = loop["answer_key"]["frozen_sha"]

    def _rel(p: str) -> str:
        """Compare key paths and reported changed files on the same footing — a builder
        may report either `tests/x.py` or an absolute path."""
        path = Path(p)
        if not path.is_absolute():
            path = root / path
        try:
            return str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            return str(path)

    key_files = {_rel(p) for p in loop["answer_key"].get("paths", [])}
    touched = sorted(key_files.intersection({_rel(c) for c in (args.changed_file or [])}))
    if missing or digest != frozen or touched:
        att["key_integrity"] = "TAMPERED"
        why = ("key files deleted: " + ", ".join(missing)) if missing else (
            "key files in the builder's diff: " + ", ".join(touched)) if touched else (
            f"key hash {digest} != frozen {frozen}")
        att["tamper_detail"] = why
    else:
        att["key_integrity"] = "VERIFIED"
    att["builder_family"] = args.builder_family or att.get("builder_family", "")
    att["changed_files"] = list(args.changed_file or [])
    att["build_recorded_at"] = _now()
    _save_loop(root, args.ticket, loop)
    log_event(root, "boil.build.done", ticket=args.ticket, attempt=n,
              status=att["key_integrity"], detail=f"{len(att['changed_files'])} files changed",
              quiet=args.no_log)
    print(f"boil-loop: {args.ticket} attempt {n} build recorded — key {att['key_integrity']}")
    return 0


def _parse_judge_file(text: str) -> dict[str, str]:
    """Pull the machine-relevant fields out of a judge verdict file. The trace is for
    humans; these four lines are what the manager branches on."""
    def grab(pattern: str) -> str:
        # `[ \t]*`, never `\s*`: `\s` eats the newline, so an EMPTY field would silently
        # capture the next line's text (an empty "Failure signature:" grabbing the Reason).
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return (m.group(1).strip() if m else "").strip("`* ")

    decision = grab(r"^\*\*Decision:\*\*[ \t]*(.+)$")
    integrity = grab(r"^\*\*Key integrity:\*\*[ \t]*(.+)$")
    return {
        "verdict": decision.split()[0].upper() if decision else "",
        "signature": grab(r"^\*\*Failure signature:\*\*[ \t]*(.+)$"),
        "reason": grab(r"^\*\*Reason.*?:\*\*[ \t]*(.+)$"),
        "integrity": integrity.split()[0].upper() if integrity else "",
        # A verdict with no cited evidence is the self-agreement failure mode wearing
        # a uniform. No Evidence line → INVALID, regardless of what Decision says.
        "has_evidence": "yes" if re.search(r"^\*\*Evidence:\*\*[ \t]*\S", text, re.MULTILINE) else "no",
    }


def cmd_record_judge(args) -> int:
    root = Path(args.root).resolve()
    loop = _load_loop(root, args.ticket)
    n = int(args.attempt)
    att = _attempt(loop, n)

    verdict, signature, reason, has_evidence = args.verdict, args.signature, args.defect, "yes"
    if args.file:
        text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        _atomic_write(_loop_dir(root, args.ticket) / f"attempt-{n}" / "judge.md", text)
        parsed = _parse_judge_file(text)
        verdict = (verdict or parsed["verdict"]).upper()
        signature = signature or parsed["signature"]
        reason = reason or parsed["reason"]
        has_evidence = parsed["has_evidence"]
        if parsed["integrity"] == "TAMPERED":
            att["key_integrity"] = "TAMPERED"
            att.setdefault("tamper_detail", "judge reported key tampering")

    verdict = (verdict or "").upper()
    if verdict not in VALID_VERDICTS:
        _die(f"--verdict must be one of {sorted(VALID_VERDICTS)}, got `{verdict}`")
    if verdict == "PASS" and has_evidence == "no":
        # Downgrade, don't trust. This is the shared-blind-spot brake.
        verdict = "INVALID"
        reason = "PASS with no cited key evidence — downgraded to INVALID"
    if verdict == "FAIL" and not signature:
        signature = f"{loop['answer_key']['kind']}:{loop['answer_key']['ref']}:unspecified"

    att["judge_runs"] = int(att.get("judge_runs", 0)) + 1
    # Counted per verdict class, not as one total: an INDETERMINATE followed by an
    # INVALID must still get the INVALID its own re-run, not inherit the other's count.
    if verdict in {"INVALID", "INDETERMINATE"}:
        ckey = f"{verdict.lower()}_runs"
        att[ckey] = int(att.get(ckey, 0)) + 1
    att["verdict"] = verdict
    att["failure_signature"] = signature
    att["judge_reason"] = reason
    att["judge_family"] = args.judge_family or att.get("judge_family", "")
    att["judge_recorded_at"] = _now()
    _save_loop(root, args.ticket, loop)
    log_event(root, "boil.judge.verdict", ticket=args.ticket, attempt=n, status=verdict,
              detail=signature or reason, quiet=args.no_log)
    print(f"boil-loop: {args.ticket} attempt {n} verdict {verdict}"
          + (f" — {signature}" if signature else ""))
    return 0


def decide(loop: dict[str, Any], n: int) -> tuple[str, str]:
    """The decision table from references/self-correcting-loop.md, in order.
    Pure function of loop state — no filesystem, no model, no judgment."""
    att = next((a for a in loop["attempts"] if a["n"] == n), None)
    if att is None:
        return "ERROR", f"no attempt {n} recorded"
    prev = [a for a in loop["attempts"] if a["n"] < n]
    verdict = att.get("verdict", "")
    max_rev = int(loop.get("max_revisions", DEFAULT_MAX_REVISIONS))
    budget = loop.get("budget", {})

    if att.get("key_integrity") == "TAMPERED":
        return "ABORT-TAMPER", att.get("tamper_detail", "the answer key changed during the loop")

    cap = float(budget.get("usd_cap") or 0)
    spent = float(budget.get("usd_spent") or 0)
    if cap and spent > cap:
        return "ESCALATE-BUDGET", f"spent ${spent:.2f} of a ${cap:.2f} cap"

    if verdict == "INVALID":
        if int(att.get("invalid_runs", 1)) <= 1:
            return "RERUN-JUDGE", "verdict cited no key evidence; re-running the judge (attempt not consumed)"
        return "ESCALATE-INFRA", "the judge returned an unusable verdict twice — the key or the judge route is broken"

    if verdict == "INDETERMINATE":
        # "Consecutive" spans both re-judges of THIS attempt and the previous attempt:
        # either way, two blind verdicts in a row mean a third won't see anything new.
        repeated = int(att.get("indeterminate_runs", 1)) >= 2 or (
            prev and prev[-1].get("verdict") == "INDETERMINATE")
        if repeated:
            return "ESCALATE-VISIBILITY", "two consecutive INDETERMINATE verdicts — the work cannot be observed"
        return "REVISE-VISIBILITY", "artifacts missing or unreadable; file a demo-prep ticket (attempt not consumed)"

    if verdict == "PASS":
        return "ACCEPT", "the answer key is satisfied with cited evidence"

    if verdict == "FAIL":
        if n >= max_rev:
            return "ESCALATE-LIMIT", f"{n} of {max_rev} revisions failed — handing the full history to a human"
        sig = att.get("failure_signature", "")
        if prev and sig and prev[-1].get("failure_signature") == sig:
            return "ESCALATE-STALL", f"identical failure twice (`{sig}`) — the revisions are not converging"
        return "REVISE", f"attempt {n} of {max_rev} failed with a new failure signature"

    return "ERROR", f"attempt {n} has no verdict yet"


def cmd_decide(args) -> int:
    root = Path(args.root).resolve()
    loop = _load_loop(root, args.ticket)
    n = int(args.attempt)
    att = _attempt(loop, n)
    if args.cost_usd:
        att["cost_usd"] = float(args.cost_usd)
        loop["budget"]["usd_spent"] = round(
            sum(float(a.get("cost_usd") or 0) for a in loop["attempts"]), 4)

    decision, reason = decide(loop, n)
    if decision == "ERROR":
        _die(f"{args.ticket}: {reason}")

    att["decision"] = decision
    att["reason"] = reason
    att["decided_at"] = _now()
    if decision == "ACCEPT":
        loop["status"] = "accepted"
    elif decision in TERMINAL_DECISIONS:
        loop["status"] = "aborted" if decision == "ABORT-TAMPER" else "escalated"
        loop["terminal_reason"] = f"{decision}: {reason}"
    _save_loop(root, args.ticket, loop)

    manager = {
        "attempt": n,
        "verdict": att.get("verdict", ""),
        "decision": decision,
        "reason": reason,
        "defect_brief": att.get("judge_reason", ""),
        "failure_signature": att.get("failure_signature", ""),
        "builder_family": att.get("builder_family", ""),
        "judge_family": att.get("judge_family", ""),
        "cost_usd": float(att.get("cost_usd") or 0),
        "decided_at": att["decided_at"],
    }
    _atomic_write(_loop_dir(root, args.ticket) / f"attempt-{n}" / "manager.json",
                  json.dumps(manager, indent=2) + "\n")
    log_event(root, "boil.manager.decision", ticket=args.ticket, attempt=n, status=decision,
              detail=reason, quiet=args.no_log)

    if args.json:
        print(json.dumps(manager, indent=2))
    else:
        print(f"boil-loop: {args.ticket} attempt {n} → {decision} — {reason}")
        if decision == "REVISE":
            print(f"  defect brief for the next builder: {manager['defect_brief'] or '(none recorded)'}")
        if decision in TERMINAL_DECISIONS:
            print(f"  write the human packet: boil-loop.py escalate --root {root} "
                  f"--ticket {args.ticket} --convert-ticket")
    return 3 if decision in TERMINAL_DECISIONS else 0


def _escalation_md(loop: dict[str, Any]) -> str:
    key = loop["answer_key"]
    decision = loop.get("terminal_reason", "").split(":", 1)[0] or "ESCALATE"
    spent = float(loop.get("budget", {}).get("usd_spent") or 0)
    attempts = loop["attempts"]
    sigs = [a.get("failure_signature", "") for a in attempts if a.get("failure_signature")]
    constant = sigs[-1] if sigs and len(set(sigs)) == 1 else (
        "the failures differed each attempt — see the history" if sigs else "no failure signature recorded")

    lines = [
        f"# Escalation — {loop['ticket']} — {decision}",
        "",
        f"**Ticket:** {loop['ticket']} — {loop.get('title', '')}",
        f"**Goal checkbox:** {', '.join(loop.get('closes_goal_checkbox') or []) or '(none declared)'}",
        f"**Answer key:** {key['kind']} — `{key['ref']}` (frozen {key['frozen_at']} at "
        f"`{key['frozen_sha']}`, authored by {key.get('authored_by', '?')})",
        f"**Attempts:** {len([a for a in attempts if a.get('verdict')])} of {loop['max_revisions']}"
        f"   **Spent:** ${spent:.2f}",
        f"**Why it stopped:** {loop.get('terminal_reason', '(unknown)')}",
        "",
        "## What the human has to decide",
        _human_question(loop),
        "",
        "## Attempt history",
    ]
    for a in attempts:
        lines += [
            f"### Attempt {a['n']} — {a.get('verdict') or 'no verdict'}"
            + (f" — `{a['failure_signature']}`" if a.get("failure_signature") else ""),
            f"- Built: {len(a.get('changed_files') or [])} file(s)"
            + (f" — {', '.join((a.get('changed_files') or [])[:6])}" if a.get("changed_files") else ""),
            f"- Key integrity: {a.get('key_integrity') or 'not checked'}",
            f"- Judge found: {a.get('judge_reason') or '(no reason recorded)'}",
            f"- Manager: {a.get('decision') or '(pending)'} — {a.get('reason', '')}",
        ]
    lines += [
        "",
        "## What stayed constant",
        constant,
        "",
        "## Artifacts",
        f"- Judge traces: `.boil/loops/{loop['ticket']}/attempt-*/judge.md`",
        f"- Build reports: `.boil/loops/{loop['ticket']}/attempt-*/build.md`",
        f"- Manager decisions: `.boil/loops/{loop['ticket']}/attempt-*/manager.json`",
        f"- Key files: {', '.join(f'`{p}`' for p in key.get('paths', [])) or '(none)'}",
        "",
    ]
    return "\n".join(lines)


def _human_question(loop: dict[str, Any]) -> str:
    reason = loop.get("terminal_reason", "")
    if reason.startswith("ABORT-TAMPER"):
        return ("The builder changed the answer key. Decide whether the key was wrong "
                "(then re-author and re-freeze it) or the attempt was dishonest (then revert and re-dispatch).")
    if reason.startswith("ESCALATE-BUDGET"):
        return "Is this ticket worth more spend, or should the goal checkbox be re-scoped?"
    if reason.startswith("ESCALATE-INFRA"):
        return "The judge could not produce a usable verdict — is the answer key executable and unambiguous?"
    if reason.startswith("ESCALATE-VISIBILITY"):
        return "The work cannot be observed. What artifact would make it visible?"
    if reason.startswith("ESCALATE-STALL"):
        return ("The same failure survived every revision. Is the answer key correct, or is the "
                "ticket impossible as specified?")
    return ("Three revisions failed against a frozen key. Decide: is the key right, is the task "
            "possible as specified, or do two requirements conflict?")


def cmd_escalate(args) -> int:
    root = Path(args.root).resolve()
    loop = _load_loop(root, args.ticket)
    if loop.get("status") not in {"escalated", "aborted"} and not args.force:
        _die(f"{args.ticket}: loop status is `{loop.get('status')}` — nothing to escalate "
             "(use --force to write the packet anyway)")
    if not loop.get("terminal_reason"):
        loop["terminal_reason"] = f"{args.reason or 'ESCALATE-LIMIT'}: forced by operator"
        loop["status"] = "escalated"
        _save_loop(root, args.ticket, loop)

    packet = _escalation_md(loop)
    dest = _loop_dir(root, args.ticket) / "escalation.md"
    _atomic_write(dest, packet)

    safe = _human_question(loop)
    if args.convert_ticket:
        _convert_ticket(root, args.ticket, safe)
    log_event(root, "boil.loop.escalate", ticket=args.ticket,
              status=loop.get("terminal_reason", "").split(":", 1)[0],
              detail=safe, quiet=args.no_log)
    print(f"boil-loop: wrote {dest}")
    print(f"  human decision needed: {safe}")
    if args.convert_ticket:
        print(f"  {args.ticket} converted to a blocked human-action ticket (P0)")
    return 3


def _convert_ticket(root: Path, ticket: str, safe_summary: str) -> None:
    tpath = _ticket_path(root, ticket)
    meta, text = _frontmatter(tpath)
    text = _set_top_level(text, "type", "type: human-action")
    text = _set_top_level(text, "status", "status: blocked")
    text = _set_top_level(text, "priority", "priority: P0")
    text = _set_top_level(text, "working_on",
                          f'working_on: "blocked on user decision: {safe_summary[:120]}"')
    human = "\n".join([
        "human_action:",
        "  required: true",
        f'  reason: "self-correcting loop escalated after exhausting its retry limit"',
        f'  safe_summary: "{safe_summary}"',
        f'  susi_task_id: ""',
        "  susi_sync_status: pending",
        "  pushover_status: pending",
    ])
    text = _set_top_level(text, "human_action", human)
    note = (f"\n\n## Escalation ({_now()})\n"
            f"The self-correcting loop stopped: see `.boil/loops/{ticket}/escalation.md` "
            f"for the full attempt history.\n")
    _atomic_write(tpath, text.rstrip("\n") + note)


def _loops(root: Path) -> list[dict[str, Any]]:
    base = _boil(root) / "loops"
    out = []
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        p = d / "loop.json"
        if p.exists():
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                out.append({"ticket": d.name, "status": "unreadable"})
    return out


def cmd_status(args) -> int:
    root = Path(args.root).resolve()
    loops = [l for l in _loops(root) if not args.ticket or l.get("ticket") == args.ticket]
    if args.json:
        print(json.dumps(loops, indent=2))
        return 0
    if not loops:
        print("boil-loop: no loops yet (.boil/loops/)")
        return 0
    glyph = {"running": "○", "accepted": "✓", "escalated": "🙋", "aborted": "⚠"}
    print(f"boil loops ({len(loops)})\n")
    for l in loops:
        atts = l.get("attempts", [])
        last = atts[-1] if atts else {}
        key = l.get("answer_key", {})
        print(f"  {glyph.get(l.get('status'), '·')} {l.get('ticket', '?'):<9} "
              f"{l.get('status', '?'):<10} attempt {len([a for a in atts if a.get('verdict')])}"
              f"/{l.get('max_revisions', '?')}  key={key.get('kind', '?')}:{str(key.get('ref', ''))[:40]}")
        if last.get("decision"):
            print(f"      last: {last.get('verdict', '')} → {last['decision']} — {last.get('reason', '')}")
        if l.get("terminal_reason"):
            print(f"      ⤷ {l['terminal_reason']}")
    return 0


def cmd_audit(args) -> int:
    """Loop-safety gate. Run it from boil-run-iteration.sh: it fails the iteration
    when a ticket claims done without a satisfied external key, or when a loop is
    parked past its retry limit without an escalation packet."""
    root = Path(args.root).resolve()
    issues: list[dict[str, str]] = []
    tickets_dir = _boil(root) / "tickets"

    loops = {l.get("ticket"): l for l in _loops(root)}
    for tp in sorted(tickets_dir.glob("T-*.md")) if tickets_dir.is_dir() else []:
        try:
            meta, _ = _frontmatter(tp)
        except Exception as exc:  # noqa: BLE001
            issues.append({"ticket": tp.stem, "code": "frontmatter", "message": str(exc)})
            continue
        tid = str(meta.get("id") or tp.stem)
        ttype, tstatus = str(meta.get("type") or ""), str(meta.get("status") or "")
        key, errors = validate_key(meta)
        for e in errors:
            issues.append({"ticket": tid, "code": "answer-key", "message": e})
        if ttype not in BEHAVIOR_TYPES or tstatus != "done":
            continue
        loop = loops.get(tid)
        if loop is None:
            issues.append({"ticket": tid, "code": "no-loop",
                           "message": "behavior ticket is done but has no .boil/loops/ record"})
            continue
        if loop.get("status") != "accepted":
            issues.append({"ticket": tid, "code": "unaccepted-loop",
                           "message": f"ticket is done but its loop status is `{loop.get('status')}`"})
        digest, missing = key_hash(root, {"ref": "", "key_paths": loop["answer_key"].get("paths", [])})
        if missing:
            issues.append({"ticket": tid, "code": "key-missing",
                           "message": "the answer key files are gone: " + ", ".join(missing)})
        elif digest != loop["answer_key"]["frozen_sha"]:
            issues.append({"ticket": tid, "code": "key-drift",
                           "message": f"key hash {digest} != frozen {loop['answer_key']['frozen_sha']} "
                                      "— the ruler moved after the ticket closed"})

    for tid, loop in loops.items():
        atts = [a for a in loop.get("attempts", []) if a.get("verdict")]
        if loop.get("status") == "running" and len(atts) >= int(loop.get("max_revisions", 3)):
            last = loop["attempts"][-1]
            if last.get("verdict") == "FAIL":
                issues.append({"ticket": tid, "code": "past-limit",
                               "message": "loop is at its retry limit but still `running` — decide + escalate it"})
        if loop.get("status") in {"escalated", "aborted"} and not (
                _loop_dir(root, tid) / "escalation.md").exists():
            issues.append({"ticket": tid, "code": "missing-escalation",
                           "message": "terminal loop has no escalation.md — the human packet was never written"})

    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    else:
        if not issues:
            print("boil-loop audit: ok")
        for i in issues:
            print(f"error: {i['ticket']}: {i['code']}: {i['message']}")
    return 1 if issues else 0


# ---------- cli --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="boil-loop", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, ticket=True):
        p.add_argument("--root", default=".", help="project root containing .boil/")
        if ticket:
            p.add_argument("--ticket", required=True, help="ticket id, e.g. T-0042")
        p.add_argument("--no-log", action="store_true", help="do not emit status events")

    p = sub.add_parser("init", help="freeze the answer key and arm the loop")
    common(p)
    p.add_argument("--max-revisions", type=int, default=DEFAULT_MAX_REVISIONS,
                   help="hard retry limit (default 3; lower it while validating a new key)")
    p.add_argument("--budget-usd", type=float, default=0.0, help="cumulative cap; 0 = unlimited")
    p.add_argument("--wall-clock-min", type=int, default=0, help="wall-clock cap in minutes; 0 = none")
    p.add_argument("--force", action="store_true", help="re-freeze an existing loop")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("record-build", help="store a builder report + check key integrity")
    common(p)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--report", help="path to the builder's report, or `-` for stdin")
    p.add_argument("--changed-file", action="append", help="repeatable; the builder's changed files")
    p.add_argument("--builder-family", default="", help="model family that built (for blind-spot audit)")
    p.set_defaults(fn=cmd_record_build)

    p = sub.add_parser("record-judge", help="store a judge verdict")
    common(p)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--file", help="path to the judge's verdict markdown, or `-` for stdin")
    p.add_argument("--verdict", default="", help="PASS | FAIL | INDETERMINATE | INVALID")
    p.add_argument("--signature", default="", help="normalized failure signature")
    p.add_argument("--defect", default="", help="the judge's one-sentence defect")
    p.add_argument("--judge-family", default="", help="model family that judged")
    p.set_defaults(fn=cmd_record_judge)

    p = sub.add_parser("decide", help="apply the decision table")
    common(p)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--cost-usd", type=float, default=0.0, help="this attempt's spend")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_decide)

    p = sub.add_parser("escalate", help="write the human packet")
    common(p)
    p.add_argument("--convert-ticket", action="store_true",
                   help="also convert the ticket to a blocked P0 human-action ticket")
    p.add_argument("--reason", default="", help="terminal reason when forcing")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_escalate)

    p = sub.add_parser("status", help="show loop state")
    common(p, ticket=False)
    p.add_argument("--ticket", default="", help="limit to one ticket")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("audit", help="loop-safety gate for the iteration runner")
    common(p, ticket=False)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_audit)
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
