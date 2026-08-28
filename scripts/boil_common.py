#!/usr/bin/env python3
"""Shared parsing helpers for the boil scripts (stdlib only)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CHECKBOX = re.compile(r"^\s*-\s*\[( |x|X)\]")


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Read simple `key: value` frontmatter. Returns {} when absent."""
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition(":")
            out[key.strip()] = val.split("  #", 1)[0].split("\t#", 1)[0].strip().strip('"')
    return out


def checkbox_counts(path: Path) -> tuple[int, int]:
    """Return (green, total) checkboxes in a markdown file."""
    if not path.is_file():
        return (0, 0)
    green = total = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CHECKBOX.match(line)
        if m:
            total += 1
            if m.group(1) in ("x", "X"):
                green += 1
    return (green, total)


def state_dir(root: Path) -> Path:
    return Path(root) / ".boil"


def charter_path(root: Path) -> Path:
    """`.boil/charter.md`, falling back to a not-yet-migrated `.gate/charter.md`."""
    boil = state_dir(root) / "charter.md"
    if boil.is_file():
        return boil
    legacy = Path(root) / ".gate" / "charter.md"
    return legacy if legacy.is_file() else boil


def ladder_path(root: Path) -> Path:
    boil = state_dir(root) / "ladder.md"
    if boil.is_file():
        return boil
    legacy = Path(root) / ".gate" / "ladder.md"
    return legacy if legacy.is_file() else boil


def open_tickets(root: Path) -> list[dict[str, Any]]:
    """Actionable tickets: status open or in-progress. Blocked ones are listed separately."""
    tickets: list[dict[str, Any]] = []
    tdir = state_dir(root) / "tickets"
    if not tdir.is_dir():
        return tickets
    for path in sorted(tdir.glob("T-*.md")):
        if path.name.endswith((".plain.md", ".judge.md")):
            continue
        meta = parse_frontmatter(path)
        if not meta:
            continue
        meta["_path"] = str(path)
        tickets.append(meta)
    return tickets


def by_status(tickets: list[dict[str, Any]], *statuses: str) -> list[dict[str, Any]]:
    wanted = set(statuses)
    return [t for t in tickets if str(t.get("status", "")).strip() in wanted]
