#!/usr/bin/env python3
"""Ingest markdown dropped in inbox/ into the knowledge packs.

Another skill (or you) writes .md files into inbox/; this classifies each one,
files it into the right pack, and rebuilds the index.

Ingest is non-destructive: originals move to inbox/processed/ rather than being
deleted, so a bad classification is always recoverable.

Routing, in order:
  1. frontmatter `pack:`         -> explicit, wins
  2. matches the chapter contract -> that book pack, but only if `pack:` names it
  3. everything else              -> notes pack, filed under `category`

Books are never auto-created: a lone chapter without its siblings would mint
chapter IDs that collide or mislead, so it is refused with an explanation.

Usage:
    python3 scripts/ingest.py [--dry-run] [--no-build] [--category NAME] [--source NAME]
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

INBOX = os.path.join(K.ROOT, "inbox")
PROCESSED = os.path.join(INBOX, "processed")

RESERVED = {"readme.md", "readme.markdown"}


def packs_by_kind():
    packs = K.load_json(os.path.join(K.ROOT, "packs.json"))["packs"]
    return {p["id"]: p for p in packs}


def unique_path(directory, base, ext=".md"):
    candidate = os.path.join(directory, base + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, "%s-%d%s" % (base, n, ext))
        n += 1
    return candidate


def render_frontmatter(meta):
    lines = ["---"]
    for key in ("title", "category", "source", "date", "authority", "topics"):
        if key in meta and meta[key] not in (None, "", []):
            val = meta[key]
            if isinstance(val, list):
                lines.append("%s: [%s]" % (key, ", ".join(str(v) for v in val)))
            else:
                lines.append("%s: %s" % (key, val))
    for key in sorted(meta):
        if key not in ("title", "category", "source", "date", "authority", "topics"):
            lines.append("%s: %s" % (key, meta[key]))
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def classify(path, text, registry, default_category, default_source):
    meta, body = K.parse_frontmatter(text)
    declared = meta.get("pack")

    if declared:
        if declared not in registry:
            return None, meta, body, "frontmatter names unknown pack %r" % declared
        return registry[declared], meta, body, None

    if K.looks_like_chapter(text):
        return None, meta, body, (
            "looks like a book chapter but no `pack:` in frontmatter. Books are not "
            "auto-created — add `pack: <id>` (and register the pack in packs.json) "
            "or strip the '# Ch N —' heading to file it as a note")

    notes = registry.get("notes")
    if not notes:
        return None, meta, body, "no pack with kind 'notes' registered"
    meta.setdefault("category", default_category)
    meta.setdefault("source", default_source)
    return notes, meta, body, None


def title_of(meta, body, path):
    if meta.get("title"):
        return meta["title"]
    for line in body.split("\n"):
        m = re.match(r"^#\s+(.+?)\s*$", line.rstrip())
        if m:
            return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report routing, change nothing")
    ap.add_argument("--no-build", action="store_true", help="skip the index rebuild")
    ap.add_argument("--category", default="general", help="default category for notes")
    ap.add_argument("--source", default="inbox", help="default provenance label")
    args = ap.parse_args()

    if not os.path.isdir(INBOX):
        sys.exit("no inbox/ directory")

    candidates = sorted(
        f for f in os.listdir(INBOX)
        if f.endswith(".md") and f.lower() not in RESERVED and not f.startswith(".")
    )
    if not candidates:
        print("inbox is empty — nothing to ingest")
        return 0

    registry = packs_by_kind()
    ingested, refused = [], []

    for name in candidates:
        src = os.path.join(INBOX, name)
        text = K.read_text(src)
        pack, meta, body, problem = classify(src, text, registry, args.category, args.source)

        if problem:
            refused.append((name, problem))
            print("✗ %s\n    %s" % (name, problem))
            continue

        title = title_of(meta, body, src)
        meta["title"] = title
        meta.setdefault("date", datetime.date.fromtimestamp(os.path.getmtime(src)).isoformat())
        if pack["kind"] == "notes":
            meta.setdefault("authority", "derived")
            category = K.slug(str(meta.get("category") or args.category), 32)
            meta["category"] = category
            dest_dir = os.path.join(K.ROOT, pack["path"], category)
        else:
            dest_dir = os.path.join(K.ROOT, pack["path"])
        meta.pop("pack", None)

        dest = unique_path(dest_dir, K.slug(title, 60))
        rel = os.path.relpath(dest, K.ROOT).replace(os.sep, "/")
        print("→ %s\n    %s  [%s]" % (name, rel, pack["id"]))

        if args.dry_run:
            continue

        os.makedirs(dest_dir, exist_ok=True)
        K.write_text(dest, render_frontmatter(meta) + body.lstrip("\n"))
        os.makedirs(PROCESSED, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.move(src, unique_path(PROCESSED, "%s-%s" % (stamp, os.path.splitext(name)[0])))
        ingested.append(rel)

    print()
    print("ingested %d · refused %d" % (len(ingested), len(refused)))
    if args.dry_run:
        print("(dry run — nothing written)")
        return 0

    if ingested and not args.no_build:
        print()
        subprocess.call([sys.executable, os.path.join(K.ROOT, "scripts", "build_index.py")])
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
