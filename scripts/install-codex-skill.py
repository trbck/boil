#!/usr/bin/env python3
"""Install or update this checkout as the user-wide Codex boil skill."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any


SKILL_NAME = "boil"
EXCLUDED_NAMES = {".git", ".susi-human-blockers", "__pycache__", ".pytest_cache"}


def default_source() -> Path:
    return Path(__file__).resolve().parents[1]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def _is_excluded(rel: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in rel.parts)


def collect_tree(root: Path) -> tuple[set[Path], set[Path]]:
    dirs: set[Path] = set()
    files: set[Path] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_NAMES]
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir != Path("."):
            dirs.add(rel_dir)
        for filename in filenames:
            if filename in EXCLUDED_NAMES:
                continue
            rel = rel_dir / filename
            if not _is_excluded(rel):
                files.add(rel)
    return dirs, files


def remove_path(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def backup_existing(dest: Path, backups_dir: Path, *, dry_run: bool) -> Path | None:
    if not dest.exists():
        return None
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backups_dir / f"{SKILL_NAME}-{stamp}.tar.gz"
    if dry_run:
        return backup
    backups_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(backup, "w:gz") as tar:
        tar.add(dest, arcname=SKILL_NAME)
    return backup


def sync_tree(source: Path, dest: Path, *, dry_run: bool) -> dict[str, int]:
    source_dirs, source_files = collect_tree(source)
    copied = 0
    removed = 0
    created_dirs = 0

    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        for dirpath, dirnames, filenames in os.walk(dest, topdown=False):
            rel_dir = Path(dirpath).relative_to(dest)
            for filename in filenames:
                rel = rel_dir / filename
                if rel == Path(filename):
                    rel = Path(filename)
                if _is_excluded(rel):
                    continue
                if rel not in source_files:
                    remove_path(Path(dirpath) / filename, dry_run=dry_run)
                    removed += 1
            for dirname in dirnames:
                rel = rel_dir / dirname
                if rel == Path(dirname):
                    rel = Path(dirname)
                if _is_excluded(rel):
                    continue
                target = Path(dirpath) / dirname
                if rel not in source_dirs:
                    remove_path(target, dry_run=dry_run)
                    removed += 1

    for rel in sorted(source_dirs):
        target = dest / rel
        if target.exists() and not target.is_dir():
            remove_path(target, dry_run=dry_run)
            removed += 1
        if not target.exists():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            created_dirs += 1

    for rel in sorted(source_files):
        src = source / rel
        target = dest / rel
        if target.exists() and target.is_dir():
            remove_path(target, dry_run=dry_run)
            removed += 1
        target_changed = not target.exists()
        if target.exists() and not target_changed:
            target_changed = not file_matches(src, target)
        if target_changed:
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
            copied += 1

    return {"copied": copied, "removed": removed, "created_dirs": created_dirs}


def file_matches(left: Path, right: Path) -> bool:
    try:
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as lf, right.open("rb") as rf:
            while True:
                lb = lf.read(1024 * 1024)
                rb = rf.read(1024 * 1024)
                if lb != rb:
                    return False
                if not lb:
                    return True
    except OSError:
        return False


def compare_tree(source: Path, dest: Path) -> dict[str, list[str]]:
    source_dirs, source_files = collect_tree(source)
    dest_dirs, dest_files = collect_tree(dest)
    missing = sorted(str(rel) for rel in source_files - dest_files)
    extra = sorted(str(rel) for rel in dest_files - source_files)
    changed = sorted(
        str(rel) for rel in source_files & dest_files
        if not file_matches(source / rel, dest / rel)
    )
    missing_dirs = sorted(str(rel) for rel in source_dirs - dest_dirs)
    extra_dirs = sorted(str(rel) for rel in dest_dirs - source_dirs)
    return {
        "missing": missing + [f"{rel}/" for rel in missing_dirs],
        "extra": extra + [f"{rel}/" for rel in extra_dirs],
        "changed": changed,
    }


def check_pyyaml() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-c", "import yaml"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "ok": proc.returncode == 0,
        "python": sys.executable,
        "message": "PyYAML import ok" if proc.returncode == 0 else proc.stderr.strip(),
    }


def validate_source(source: Path) -> None:
    required = ("SKILL.md", "README.md", "commands/boil.md")
    missing = [rel for rel in required if not (source / rel).exists()]
    if missing:
        raise SystemExit(f"source does not look like boil skill root; missing: {', '.join(missing)}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(default_source()), help="boil checkout to install")
    ap.add_argument("--codex-home", default=str(default_codex_home()), help="Codex home; defaults to $CODEX_HOME or ~/.codex")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen without writing")
    ap.add_argument("--no-backup", action="store_true", help="skip backup of an existing installed skill")
    ap.add_argument("--skip-dependency-check", action="store_true", help="skip PyYAML import check")
    ap.add_argument("--json", action="store_true", help="print machine-readable result")
    args = ap.parse_args(argv)

    source = Path(args.source).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()
    dest = codex_home / "skills" / SKILL_NAME
    backups_dir = codex_home / "skills" / ".backups"

    validate_source(source)
    backup = None
    if not args.no_backup:
        backup = backup_existing(dest, backups_dir, dry_run=args.dry_run)

    sync_stats = sync_tree(source, dest, dry_run=args.dry_run)
    parity = {"missing": [], "extra": [], "changed": []}
    if not args.dry_run:
        parity = compare_tree(source, dest)

    dependency = {"ok": True, "python": sys.executable, "message": "skipped"}
    if not args.skip_dependency_check:
        dependency = check_pyyaml()

    ok = not any(parity.values()) and bool(dependency["ok"])
    result: dict[str, Any] = {
        "ok": ok,
        "source": str(source),
        "destination": str(dest),
        "backup": str(backup) if backup else "",
        "dry_run": args.dry_run,
        "sync": sync_stats,
        "parity": parity,
        "dependency": dependency,
        "restart_required": True,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        action = "Would install" if args.dry_run else "Installed"
        print(f"{action} {SKILL_NAME} to {dest}")
        if backup:
            print(f"Backup: {backup}")
        print(
            "Sync: "
            f"{sync_stats['copied']} copied, "
            f"{sync_stats['removed']} removed, "
            f"{sync_stats['created_dirs']} dirs created"
        )
        print(f"PyYAML: {dependency['message']}")
        if any(parity.values()):
            print("Parity check failed:", file=sys.stderr)
            print(json.dumps(parity, indent=2), file=sys.stderr)
        if not dependency["ok"]:
            print(
                "Install PyYAML for story-run.py, for example: "
                "python3 -m pip install --user PyYAML",
                file=sys.stderr,
            )
        print("Restart Codex to pick up the updated skill.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
