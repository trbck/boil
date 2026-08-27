#!/usr/bin/env python3
"""Build the knowledge-advisor retrieval artifacts.

Reads packs.json + taxonomy.json, parses every pack according to its kind, and
writes generated/: a small always-loadable ROUTER.md, topic-sharded rule files,
per-engine routers and heading indexes, and a machine-readable index.json.

The build is deterministic -- no timestamps -- so diffs stay reviewable and the
repo can be the master copy. Staleness is tracked by a corpus fingerprint.

Usage:
    python3 scripts/build_index.py [--quiet]
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

GEN = os.path.join(K.ROOT, "generated")
ROUTER_GOVERNS_CHARS = 110
ENGINE_DESC_CHARS = 90
# Weight a rule inherits from its parent chapter's topics, in units where one
# distinct keyword match is worth 3. Set near one match so subject matter wins
# over incidental vocabulary without freezing every rule to its chapter.
CHAPTER_BASE_WEIGHT = 4


def log(msg, quiet=False):
    if not quiet:
        print(msg)


def fingerprint(paths):
    digest = hashlib.sha1()
    for path in sorted(paths):
        digest.update(path.encode("utf-8"))
        try:
            with open(path, "rb") as fh:
                digest.update(hashlib.sha1(fh.read()).digest())
        except OSError:
            pass
    return digest.hexdigest()[:12]


def truncate(text, limit):
    if not text:
        return ""
    text = K.strip_md(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# --- pack builders -----------------------------------------------------------

def build_book(pack, taxonomy, files):
    chapters, rules = [], []
    for path in files:
        rec = K.parse_chapter(path, pack["prefix"])
        profile_text = " ".join(filter(None, [
            rec.get("governs"), rec.get("thesis"),
            " ".join(s["title"] for s in rec["sections"]),
        ]))
        rec["topics"] = rec["pinned_topics"] or K.score_topics(
            profile_text, taxonomy, title=rec.get("title"), max_topics=3, ratio=0.45)
        base = {t: CHAPTER_BASE_WEIGHT for t in rec["topics"]}

        for ordinal, text in enumerate(rec["rules"], 1):
            rid = "%s-R%d" % (rec["id"], ordinal)
            rules.append({
                "id": rid,
                "pack": pack["id"],
                "parent": rec["id"],
                "parent_title": rec["title"],
                "ordinal": ordinal,
                "text": text,
                "topics": K.score_topics(text, taxonomy, base=base) or rec["topics"][:1],
                "authority": "primary",
            })
        # Most distilled chapters carry no explicit **Source:** line. Rather than
        # editing the knowledge files, synthesise the citation from pack metadata so
        # every chapter can still be cited precisely.
        rec["citation"] = rec.get("source") or "%s, *%s*, Ch. %s" % (
            pack.get("author") or pack["title"], pack["title"], rec["number"])
        rec["rule_count"] = len(rec["rules"])
        del rec["rules"]
        chapters.append(rec)
    chapters.sort(key=lambda c: (c["number"] is None, c["number"] or 0))
    return chapters, rules


def build_notes(pack, taxonomy, files):
    notes, rules = [], []
    for path in files:
        rec = K.parse_note(path, pack["prefix"], root=K.ROOT)
        profile_text = " ".join(filter(None, [
            rec.get("category"),
            " ".join(s["title"] for s in rec["sections"]),
        ]))
        rec["topics"] = rec["pinned_topics"] or K.score_topics(
            profile_text, taxonomy, title=rec.get("title"), max_topics=3, ratio=0.45)
        base = {t: CHAPTER_BASE_WEIGHT for t in rec["topics"]}
        authority = rec.get("authority", "derived")

        for ordinal, text in enumerate(rec["rules"], 1):
            rules.append({
                "id": "%s-R%d" % (rec["id"], ordinal),
                "pack": pack["id"],
                "parent": rec["id"],
                "parent_title": rec["title"],
                "ordinal": ordinal,
                "text": text,
                "topics": K.score_topics(text, taxonomy, base=base) or rec["topics"][:1],
                "authority": authority,
                "source": rec.get("source"),
                "date": rec.get("date"),
            })
        rec["rule_count"] = len(rec["rules"])
        del rec["rules"]
        notes.append(rec)
    notes.sort(key=lambda n: (n.get("category") or "", n.get("date") or "", n["id"]))
    return notes, rules


def build_engine(pack, quiet=False):
    base = os.path.join(K.ROOT, pack["path"])
    sources = pack.get("sources", {})
    record = {"id": pack["id"], "title": pack["title"], "files": {}, "manifest_sections": 0}
    heading_index = {"pack": pack["id"], "files": {}}

    manifest_name = sources.get("manifest")
    groups = []
    if manifest_name:
        mpath = os.path.join(base, manifest_name)
        if os.path.exists(mpath):
            groups = K.parse_engine_manifest(mpath)
            record["manifest_sections"] = len(groups)
            record["manifest_entries"] = sum(len(g["entries"]) for g in groups)

    for role, name in sources.items():
        if role == "manifest":
            continue
        path = os.path.join(base, name)
        if not os.path.exists(path):
            log("    ! missing %s source: %s" % (role, name), quiet)
            continue
        entries = K.index_engine_file(path)
        heading_index["files"][role] = {
            "file": os.path.relpath(path, K.ROOT).replace(os.sep, "/"),
            "headings": entries,
        }
        record["files"][role] = {
            "file": os.path.relpath(path, K.ROOT).replace(os.sep, "/"),
            "headings": len(entries),
            "bytes": os.path.getsize(path),
        }
        log("    %-8s %6d headings  %8.1f MB" % (role, len(entries), os.path.getsize(path) / 1e6), quiet)

    K.write_json(os.path.join(GEN, "engines", "%s.index.json" % pack["id"]), heading_index)
    if groups:
        K.write_text(os.path.join(GEN, "engines", "%s.md" % pack["id"]),
                     render_engine_router(pack, groups, record))
    return record


# --- renderers ---------------------------------------------------------------

def render_engine_router(pack, groups, record):
    out = ["# %s — capability router" % pack["title"], ""]
    out.append("Curated map of what this engine can do. Use it to pick an area, then resolve "
               "concrete symbols with `scripts/lookup.py --engine %s --search <query>`." % pack["id"])
    out.append("")
    out.append("This file describes **capability, not method**. Whether a technique is sound "
               "comes from the book packs; this only says what the library supports.")
    out.append("")
    for group in groups:
        out.append("## %s" % group["section"])
        out.append("")
        for entry in group["entries"]:
            desc = truncate(entry["description"], ENGINE_DESC_CHARS)
            out.append("- **%s** — %s" % (entry["title"], desc) if desc else "- **%s**" % entry["title"])
        out.append("")
    for role, info in sorted(record.get("files", {}).items()):
        out.append("<!-- %s: %s headings indexed from %s -->" % (role, info["headings"], info["file"]))
    return "\n".join(out) + "\n"


def render_rule_shard(topic, spec, rules, packs_by_id):
    words = sum(len(r["text"].split()) for r in rules)
    out = ["# Rules — %s" % spec["label"], ""]
    out.append("`%d` rules · ~%d words · ~%d tokens" % (len(rules), words, K.approx_tokens(words)))
    out.append("")
    out.append("Cite by ID. `primary` rules come from books; `derived` rules come from your own "
               "notes and research and must never silently override a primary rule — if they "
               "conflict, say so.")
    out.append("")
    by_parent = {}
    for rule in rules:
        by_parent.setdefault((rule["pack"], rule["parent"], rule["parent_title"]), []).append(rule)
    for (pack_id, parent, parent_title) in sorted(by_parent, key=lambda k: (k[0], k[1])):
        group = by_parent[(pack_id, parent, parent_title)]
        pack = packs_by_id.get(pack_id, {})
        tag = "" if group[0]["authority"] == "primary" else "  *(derived)*"
        out.append("### %s — %s%s" % (parent, parent_title or "", tag))
        out.append("")
        out.append("<sub>%s</sub>" % pack.get("title", pack_id))
        out.append("")
        for rule in group:
            out.append("- **%s** — %s" % (rule["id"], rule["text"]))
        out.append("")
    return "\n".join(out) + "\n"


def render_rules_index(topics_used, taxonomy, rules_by_topic):
    out = ["# Rule shards", "",
           "Load the shard you need, not all of them. Each rule has a stable ID you can cite "
           "and audit against.", "",
           "| Topic | Focus | Rules | ~Tokens | File |", "|---|---|---|---|---|"]
    for topic in topics_used:
        rules = rules_by_topic[topic]
        words = sum(len(r["text"].split()) for r in rules)
        out.append("| `%s` | %s | %d | ~%d | `generated/rules/%s.md` |" % (
            topic, taxonomy["topics"][topic]["label"], len(rules), K.approx_tokens(words), topic))
    total = sum(len(v) for v in rules_by_topic.values())
    out.append("")
    out.append("Total: **%d** rule assignments across %d shards (rules spanning two topics "
               "appear in both)." % (total, len(topics_used)))
    return "\n".join(out) + "\n"


def render_router(packs, chapters, notes, engines, rules, rules_by_topic, taxonomy, fp):
    out = ["# Knowledge Router", ""]
    out.append("Always-loaded map of the corpus. Resolve a question to a small number of "
               "chapters, sections or rule shards, then load only those.")
    out.append("")
    out.append("`corpus: %s`" % fp)
    out.append("")

    out.append("## Packs")
    out.append("")
    out.append("| Pack | Kind | Title | Authoritative on |")
    out.append("|---|---|---|---|")
    for pack in packs:
        auth = ", ".join("`%s`" % t for t in pack.get("authoritative_on", [])) or "—"
        out.append("| `%s` | %s | %s | %s |" % (pack["id"], pack["kind"], pack["title"], auth))
    out.append("")
    out.append("When packs disagree, prefer the one authoritative on the topic in question — "
               "and say that a disagreement existed. See `references/conflicts.md`.")
    out.append("")

    out.append("## Rule shards")
    out.append("")
    out.append("| Topic | Rules | ~Tokens | File |")
    out.append("|---|---|---|---|")
    for topic in sorted(rules_by_topic):
        group = rules_by_topic[topic]
        words = sum(len(r["text"].split()) for r in group)
        out.append("| `%s` | %d | ~%d | `generated/rules/%s.md` |" % (
            topic, len(group), K.approx_tokens(words), topic))
    out.append("")

    if chapters:
        out.append("## Book chapters")
        out.append("")
        out.append("| ID | Title | Governs | Topics | Rules |")
        out.append("|---|---|---|---|---|")
        for ch in chapters:
            out.append("| `%s` | %s | %s | %s | %d |" % (
                ch["id"], ch.get("title") or "?", truncate(ch.get("governs"), ROUTER_GOVERNS_CHARS),
                " ".join("`%s`" % t for t in ch.get("topics", [])), ch.get("rule_count", 0)))
        out.append("")

    if notes:
        out.append("## Notes & reports")
        out.append("")
        out.append("| ID | Title | Category | Source | Date | Topics | Findings |")
        out.append("|---|---|---|---|---|---|---|")
        for note in notes:
            out.append("| `%s` | %s | %s | %s | %s | %s | %d |" % (
                note["id"], truncate(note.get("title"), 60), note.get("category", ""),
                note.get("source", ""), note.get("date") or "",
                " ".join("`%s`" % t for t in note.get("topics", [])), note.get("rule_count", 0)))
        out.append("")
    else:
        out.append("## Notes & reports")
        out.append("")
        out.append("_None yet. Drop markdown in `inbox/` and run `python3 scripts/ingest.py`._")
        out.append("")

    if engines:
        out.append("## Engine packs")
        out.append("")
        out.append("| ID | Title | Router | Indexed headings |")
        out.append("|---|---|---|---|")
        for eng in engines:
            total = sum(f["headings"] for f in eng.get("files", {}).values())
            router = "`generated/engines/%s.md`" % eng["id"]
            out.append("| `%s` | %s | %s | %d |" % (eng["id"], eng["title"], router, total))
        out.append("")
        out.append("Engine content is retrieved by symbol, never loaded whole: "
                   "`python3 scripts/lookup.py --engine <id> --search \"<query>\"`.")
        out.append("")

    caveats = [(p["id"], c) for p in packs for c in p.get("caveats", [])]
    if caveats:
        out.append("## Standing caveats")
        out.append("")
        for pack_id, caveat in caveats:
            out.append("- **`%s`** — %s" % (pack_id, caveat))
        out.append("")

    out.append("## Retrieval")
    out.append("")
    out.append("```bash")
    out.append("python3 scripts/lookup.py --search \"position sizing under drawdown\"")
    out.append("python3 scripts/lookup.py --rule ASSP-09-R7")
    out.append("python3 scripts/lookup.py --chapter ASSP-09")
    out.append("python3 scripts/lookup.py --section ASSP-09§5")
    out.append("python3 scripts/lookup.py --engine vbtpro --search \"from_signals stop loss\"")
    out.append("```")
    return "\n".join(out) + "\n"


# --- main --------------------------------------------------------------------

def collect_files(pack):
    base = os.path.join(K.ROOT, pack["path"])
    if not os.path.isdir(base):
        return []
    if pack.get("recursive"):
        found = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if name.endswith(".md") and not name.startswith("_"):
                    found.append(os.path.join(dirpath, name))
        return sorted(found)
    return sorted(os.path.join(base, f) for f in os.listdir(base)
                  if f.endswith(".md") and not f.startswith("_"))


def main():
    quiet = "--quiet" in sys.argv
    packs = K.load_json(os.path.join(K.ROOT, "packs.json"))["packs"]
    taxonomy = K.load_json(os.path.join(K.ROOT, "taxonomy.json"))
    packs_by_id = {p["id"]: p for p in packs}

    chapters, notes, engines, rules = [], [], [], []
    all_files = []
    problems = []

    for pack in packs:
        log("→ %s (%s)" % (pack["id"], pack["kind"]), quiet)
        if pack["kind"] == "engine":
            engines.append(build_engine(pack, quiet))
            base = os.path.join(K.ROOT, pack["path"])
            for name in pack.get("sources", {}).values():
                path = os.path.join(base, name)
                if os.path.exists(path):
                    all_files.append(path)
            continue

        files = collect_files(pack)
        all_files.extend(files)
        if not files:
            log("    (no files yet)", quiet)
            continue

        if pack["kind"] == "book":
            pack_chapters, pack_rules = build_book(pack, taxonomy, files)
            chapters.extend(pack_chapters)
            rules.extend(pack_rules)
            for ch in pack_chapters:
                for prob in ch["problems"]:
                    problems.append("%s (%s): %s" % (ch["id"], os.path.basename(ch["file"]), prob))
            log("    %d chapters, %d rules" % (len(pack_chapters), len(pack_rules)), quiet)
        elif pack["kind"] == "notes":
            pack_notes, pack_rules = build_notes(pack, taxonomy, files)
            notes.extend(pack_notes)
            rules.extend(pack_rules)
            log("    %d notes, %d findings" % (len(pack_notes), len(pack_rules)), quiet)
        else:
            log("    ! unknown kind %r — skipped" % pack["kind"], quiet)

    rules_by_topic = {}
    for rule in rules:
        for topic in rule["topics"]:
            rules_by_topic.setdefault(topic, []).append(rule)

    for path in list(os.listdir(os.path.join(GEN, "rules"))) if os.path.isdir(os.path.join(GEN, "rules")) else []:
        if path.endswith(".md"):
            os.remove(os.path.join(GEN, "rules", path))

    for topic in sorted(rules_by_topic):
        K.write_text(os.path.join(GEN, "rules", "%s.md" % topic),
                     render_rule_shard(topic, taxonomy["topics"][topic], rules_by_topic[topic], packs_by_id))
    K.write_text(os.path.join(GEN, "rules", "INDEX.md"),
                 render_rules_index(sorted(rules_by_topic), taxonomy, rules_by_topic))

    fp = fingerprint(all_files)
    K.write_text(os.path.join(GEN, "ROUTER.md"),
                 render_router(packs, chapters, notes, engines, rules, rules_by_topic, taxonomy, fp))
    K.write_json(os.path.join(GEN, "index.json"), {
        "corpus_fingerprint": fp,
        "packs": packs,
        "chapters": chapters,
        "notes": notes,
        "engines": engines,
        "rules": rules,
        "topics": {t: sorted(r["id"] for r in rs) for t, rs in rules_by_topic.items()},
        "problems": problems,
    })

    log("", quiet)
    log("built: %d chapters · %d notes · %d engines · %d rules · %d shards"
        % (len(chapters), len(notes), len(engines), len(rules), len(rules_by_topic)), quiet)
    log("corpus fingerprint: %s" % fp, quiet)
    if problems:
        log("", quiet)
        log("%d format problem(s) — run scripts/validate_pack.py for detail:" % len(problems), quiet)
        for prob in problems[:10]:
            log("  - %s" % prob, quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
