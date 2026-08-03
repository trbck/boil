#!/usr/bin/env python3
"""Lint boil ticket files for loop-safety invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print("ticket-lint: PyYAML is required", file=sys.stderr)
    sys.exit(2)


REQUIRED = {
    "id",
    "title",
    "type",
    "specialty",
    "status",
    "priority",
    "proof_strategy",
    "opened_by",
    "opened_at",
    "blocked_by",
    "working_on",
}
VALID_STATUS = {"open", "in-progress", "blocked", "done", "wontfix"}
VALID_PRIORITY = {"P0", "P1", "P2", "P3"}
VALID_PROOF = {
    "red-green",
    "characterization",
    "verification-only",
    "rendered-doc",
    "research-artifact",
    "perf-baseline",
}
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
]
CONFIDENCE_FIELDS = (
    "requirements_understood",
    "implementation_matches",
    "verification_working",
)
# Ticket types whose work is behavior, and therefore needs an external answer key
# before a builder is dispatched. See references/self-correcting-loop.md.
BEHAVIOR_TYPES = {"bug", "feature", "test", "refactor", "perf"}
VALID_KEY_KINDS = {"suite", "document", "checklist", "none"}
SELF_AUTHORED = {"builder", "agent", "self", "implementer"}


def lint_answer_key(path: Path, meta: dict[str, Any]) -> list[dict[str, str]]:
    """The answer key is what makes the judge a judge instead of a second opinion.
    These checks exist so a key can't be missing, self-authored, or quietly unfrozen."""
    issues: list[dict[str, str]] = []
    ttype = str(meta.get("type") or "")
    status = str(meta.get("status") or "")
    key = meta.get("answer_key")
    behavior = ttype in BEHAVIOR_TYPES

    if key is None:
        if behavior:
            issues.append(_issue(path, "error", "missing-answer-key",
                                 f"`answer_key` is required for `type: {ttype}` tickets"))
        return issues
    if not isinstance(key, dict):
        return [_issue(path, "error", "bad-answer-key", "`answer_key` must be a mapping")]

    kind = str(key.get("kind") or "")
    if kind not in VALID_KEY_KINDS:
        issues.append(_issue(path, "error", "bad-answer-key-kind",
                             f"`answer_key.kind` must be one of {sorted(VALID_KEY_KINDS)}, got `{kind}`"))
        return issues
    if kind == "none":
        if behavior:
            issues.append(_issue(path, "error", "answer-key-none-behavior",
                                 f"`answer_key.kind: none` is not allowed for `type: {ttype}` — "
                                 "a behavior ticket needs external ground truth"))
        if not str(key.get("reason") or "").strip():
            issues.append(_issue(path, "error", "answer-key-none-reason",
                                 "`answer_key.reason` is required when kind is `none`"))
        return issues

    if not str(key.get("ref") or "").strip():
        issues.append(_issue(path, "error", "missing-answer-key-ref", "`answer_key.ref` is required"))
    author = str(key.get("authored_by") or "").strip()
    specialty = str(meta.get("specialty") or "").strip()
    if not author:
        issues.append(_issue(path, "error", "missing-answer-key-author",
                             "`answer_key.authored_by` is required (and may not be the builder)"))
    elif author.lower() in SELF_AUTHORED or (
            specialty and author.lower() in {specialty.lower(), f"agent:{specialty}".lower()}):
        issues.append(_issue(path, "error", "answer-key-self-authored",
                             f"`answer_key.authored_by: {author}` is the builder's own specialty — "
                             "the key must come from the orchestrator, the user, or upstream"))
    if key.get("protected") is not True:
        issues.append(_issue(path, "error", "answer-key-unprotected",
                             "`answer_key.protected` must be true"))
    if status in {"in-progress", "done"} and not str(key.get("frozen_sha") or "").strip():
        issues.append(_issue(path, "error", "answer-key-unfrozen",
                             "`answer_key.frozen_sha` is empty — run `boil-loop.py init` to freeze "
                             "the key BEFORE the first build attempt"))
    if not str(key.get("frozen_at") or "").strip():
        issues.append(_issue(path, "warning", "answer-key-no-freeze-time",
                             "`answer_key.frozen_at` is not set"))
    return issues


def _frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated YAML frontmatter")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter is not a mapping")
    return meta, text


def _issue(path: Path, severity: str, code: str, message: str) -> dict[str, str]:
    return {
        "file": str(path),
        "severity": severity,
        "code": code,
        "message": message,
    }


def lint_ticket(path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    try:
        meta, text = _frontmatter(path)
    except Exception as exc:
        return [_issue(path, "error", "frontmatter", str(exc))]

    missing = sorted(k for k in REQUIRED if k not in meta)
    for key in missing:
        issues.append(_issue(path, "error", "missing-field", f"missing `{key}`"))

    if meta.get("id") and meta["id"] != path.stem:
        issues.append(_issue(path, "error", "id-mismatch", f"id `{meta['id']}` != filename `{path.stem}`"))
    if meta.get("status") and meta["status"] not in VALID_STATUS:
        issues.append(_issue(path, "error", "bad-status", f"unknown status `{meta['status']}`"))
    if meta.get("priority") and meta["priority"] not in VALID_PRIORITY:
        issues.append(_issue(path, "error", "bad-priority", f"unknown priority `{meta['priority']}`"))
    if meta.get("proof_strategy") and meta["proof_strategy"] not in VALID_PROOF:
        issues.append(_issue(path, "error", "bad-proof", f"unknown proof_strategy `{meta['proof_strategy']}`"))

    status = meta.get("status")
    confidence = meta.get("confidence")
    if status == "done":
        if not isinstance(confidence, dict):
            issues.append(_issue(path, "error", "missing-confidence", "`confidence` mapping required for done tickets"))
        else:
            for key in CONFIDENCE_FIELDS:
                value = confidence.get(key)
                if not isinstance(value, (int, float)) or value < 99:
                    issues.append(_issue(path, "error", "low-confidence", f"`confidence.{key}` must be >=99 for done tickets"))
            evidence = confidence.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                issues.append(_issue(path, "error", "missing-confidence-evidence", "`confidence.evidence` required for done tickets"))
            uncertainty = confidence.get("uncertainty")
            if uncertainty not in ([], None):
                issues.append(_issue(path, "error", "remaining-uncertainty", "`confidence.uncertainty` must be empty for done tickets"))
        proof = meta.get("proof")
        if meta.get("proof_strategy") == "red-green":
            if not isinstance(proof, dict):
                issues.append(_issue(path, "error", "missing-proof-map", "`proof` mapping required for done red-green tickets"))
            else:
                if not str(proof.get("red_test") or "").strip():
                    issues.append(_issue(path, "error", "missing-red-proof", "`proof.red_test` required for done red-green tickets"))
                if not str(proof.get("green_test") or "").strip():
                    issues.append(_issue(path, "error", "missing-green-proof", "`proof.green_test` required for done red-green tickets"))
    elif confidence is not None and not isinstance(confidence, dict):
        issues.append(_issue(path, "error", "bad-confidence", "`confidence` must be a mapping"))

    working_on = str(meta.get("working_on") or "").strip()
    if status in {"in-progress", "blocked"} and not working_on:
        issues.append(_issue(path, "error", "missing-working-on", "`working_on` required when active/blocked"))

    if meta.get("type") == "human-action":
        human = meta.get("human_action")
        if not isinstance(human, dict):
            issues.append(_issue(path, "error", "missing-human-action", "`human_action` mapping required"))
        else:
            if human.get("required") is not True:
                issues.append(_issue(path, "error", "human-required", "`human_action.required` must be true"))
            if not str(human.get("safe_summary") or "").strip():
                issues.append(_issue(path, "error", "human-safe-summary", "`human_action.safe_summary` required"))
            for key in ("susi_sync_status", "pushover_status"):
                value = str(human.get(key) or "").strip()
                if value and value not in {"pending", "created", "sent", "not_configured", "failed", "skipped"}:
                    issues.append(_issue(path, "warning", "human-status", f"unexpected `{key}` value `{value}`"))

    issues.extend(lint_answer_key(path, meta))

    if "closes_stories" in meta and not isinstance(meta["closes_stories"], list):
        issues.append(_issue(path, "error", "bad-closes-stories", "`closes_stories` must be a list"))
    if "blocked_by" in meta and not isinstance(meta["blocked_by"], list):
        issues.append(_issue(path, "error", "bad-blocked-by", "`blocked_by` must be a list"))

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            issues.append(_issue(path, "error", "possible-secret", "ticket contains a possible secret/token"))
            break
    return issues


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root containing .boil/")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    tickets_dir = root / ".boil" / "tickets"
    if not tickets_dir.exists():
        issues = [_issue(tickets_dir, "error", "missing-tickets-dir", ".boil/tickets missing")]
    else:
        issues = []
        ids: dict[str, Path] = {}
        for path in sorted(tickets_dir.glob("T-*.md")):
            issues.extend(lint_ticket(path))
            try:
                meta, _ = _frontmatter(path)
                tid = str(meta.get("id") or "")
                if tid:
                    if tid in ids:
                        issues.append(_issue(path, "error", "duplicate-id", f"duplicate id `{tid}` also in {ids[tid]}"))
                    ids[tid] = path
            except Exception:
                pass

    if args.json:
        print(json.dumps({"ok": not any(i["severity"] == "error" for i in issues), "issues": issues}, indent=2))
    else:
        if not issues:
            print("ticket-lint: ok")
        for item in issues:
            print(f"{item['severity']}: {item['file']}: {item['code']}: {item['message']}")
    return 1 if any(i["severity"] == "error" for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
