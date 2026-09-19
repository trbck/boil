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

ROUTER_GOVERNS_CHARS = 110
# Scope phrases contributed by each domain to the generated skill description.
# Capped so a fifth domain cannot dilute the description into uselessness --
# the description is the sole determinant of whether the skill fires at all.
SCOPE_PER_DOMAIN = 10
# Frontmatter is capped at 1024 characters by the skill spec, and it is loaded into
# every conversation whether or not the skill fires. The trigger phrases are the only
# part that decides whether it fires, so they are the last thing trimmed.
MAX_FRONTMATTER_CHARS = 1024
ENGINE_DESC_CHARS = 90
# Weight a rule inherits from its parent chapter's topics, in units where one
# distinct keyword match is worth 3. Set near one match so subject matter wins
# over incidental vocabulary without freezing every rule to its chapter.
CHAPTER_BASE_WEIGHT = 4


def log(msg, quiet=False):
    if not quiet:
        print(msg)


def fingerprint(paths):
    """Hash the corpus, not the machine it lives on.

    Paths arrive absolute, so hashing them verbatim made the fingerprint depend on
    the checkout directory: the same corpus produced a different id on a clone, in
    a packaging staging tree, and on another machine — which defeats the one thing
    the fingerprint is for, telling you whether two builds saw the same corpus.
    """
    digest = hashlib.sha1()
    for path in sorted(paths):
        rel = os.path.relpath(path, K.ROOT).replace(os.sep, "/")
        digest.update(rel.encode("utf-8"))
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


def build_engine(pack, gen, quiet=False):
    base = pack["abs_path"]
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

    K.write_json(os.path.join(gen, "engines", "%s.index.json" % pack["id"]), heading_index)
    if groups:
        K.write_text(os.path.join(gen, "engines", "%s.md" % pack["id"]),
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


def render_router(domain, packs, chapters, notes, engines, rules, rules_by_topic, taxonomy, fp):
    out = ["# Knowledge Router — %s" % domain.get("title", domain["id"]), ""]
    out.append("Always-loaded map of this domain's corpus. Resolve a question to a small number "
               "of chapters, sections or rule shards, then load only those.")
    out.append("")
    if domain.get("summary"):
        out.append("_%s_" % domain["summary"])
        out.append("")
    out.append("`domain: %s`  ·  `corpus: %s`" % (domain["id"], fp))
    out.append("")

    out.append("## Packs")
    out.append("")
    out.append("| Pack | Kind | Title | Authoritative on |")
    out.append("|---|---|---|---|")
    unindexed = {e["id"] for e in engines if not e.get("files")}
    for pack in packs:
        auth = ", ".join("`%s`" % t for t in pack.get("authoritative_on", [])) or "—"
        kind = pack["kind"]
        if pack["id"] in unindexed:
            # Registered but not retrievable here. Saying so beats a row that reads
            # like an available pack and a `--engine` call that returns nothing.
            kind += " · **sources absent**"
        out.append("| `%s` | %s | %s | %s |" % (pack["id"], kind, pack["title"], auth))
    out.append("")
    out.append("When packs disagree, prefer the one authoritative on the topic in question — "
               "and say that a disagreement existed. See `domains/%s/%s`."
               % (domain["id"], domain.get("conflicts", "conflicts.md")))
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

    engines = [e for e in engines if e.get("files")]   # unindexed == unavailable
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
    # Examples are drawn from this domain's own index. A router that demonstrates
    # `--rule ASSP-09-R7` inside the decisions corpus teaches the model to cite an
    # ID that does not exist here — the one failure this whole design prevents.
    example_rule = rules[0]["id"] if rules else "<ID>"
    example_chapter = chapters[0] if chapters else None
    chap_id = example_chapter["id"] if example_chapter else "<CHAPTER>"
    sec_id = ("%s§%s" % (chap_id, example_chapter["sections"][0]["key"])
              if example_chapter and example_chapter.get("sections") else None)
    out.append("python3 scripts/lookup.py --domain %s --search \"...\"" % domain["id"])
    out.append("python3 scripts/lookup.py --rule %s" % example_rule)
    out.append("python3 scripts/lookup.py --chapter %s" % chap_id)
    if sec_id:
        out.append("python3 scripts/lookup.py --section %s" % sec_id)
    for eng in engines:
        out.append("python3 scripts/lookup.py --engine %s --search \"<capability>\"" % eng["id"])
    out.append("```")
    return "\n".join(out) + "\n"


# --- main --------------------------------------------------------------------

def collect_files(pack):
    base = pack["abs_path"]
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


def corpus_fingerprint(domain):
    """Recompute a domain's fingerprint from disk without building anything.

    The point of the fingerprint is to say whether two builds saw the same corpus.
    That is only useful if something checks it: a generated/ tree older than the
    knowledge it indexes answers questions from a snapshot while claiming to answer
    from the corpus, and nothing about the output looks wrong.
    """
    files = []
    for pack in K.load_domain_packs(domain):
        if pack["kind"] == "engine":
            files += [p for p in (os.path.join(pack["abs_path"], n)
                                  for n in pack.get("sources", {}).values())
                      if os.path.exists(p)]
        else:
            files += collect_files(pack)
    return fingerprint(files)


def build_domain(domain, quiet=False):
    """Build every artifact for one domain into generated/<domain-id>/."""
    packs = K.load_domain_packs(domain)
    taxonomy = K.load_domain_taxonomy(domain)
    packs_by_id = {p["id"]: p for p in packs}
    gen = domain["generated"]

    chapters, notes, engines, rules = [], [], [], []
    all_files, problems = [], []

    for pack in packs:
        log("  → %s (%s)" % (pack["id"], pack["kind"]), quiet)
        if pack["kind"] == "engine":
            engines.append(build_engine(pack, gen, quiet))
            for name in pack.get("sources", {}).values():
                path = os.path.join(pack["abs_path"], name)
                if os.path.exists(path):
                    all_files.append(path)
            continue

        files = collect_files(pack)
        all_files.extend(files)
        if not files:
            log("      (no files yet)", quiet)
            continue

        if pack["kind"] == "book":
            pack_chapters, pack_rules = build_book(pack, taxonomy, files)
            chapters.extend(pack_chapters)
            rules.extend(pack_rules)
            for ch in pack_chapters:
                for problem in ch["problems"]:
                    problems.append("%s (%s): %s"
                                    % (ch["id"], os.path.basename(ch["file"]), problem))
            log("      %d chapters, %d rules" % (len(pack_chapters), len(pack_rules)), quiet)
        elif pack["kind"] == "notes":
            pack_notes, pack_rules = build_notes(pack, taxonomy, files)
            notes.extend(pack_notes)
            rules.extend(pack_rules)
            log("      %d notes, %d findings" % (len(pack_notes), len(pack_rules)), quiet)
        else:
            log("      ! unknown kind %r — skipped" % pack["kind"], quiet)

    rules_by_topic = {}
    for rule in rules:
        rule["domain"] = domain["id"]
        for topic in rule["topics"]:
            rules_by_topic.setdefault(topic, []).append(rule)

    rules_dir = os.path.join(gen, "rules")
    if os.path.isdir(rules_dir):
        for name in os.listdir(rules_dir):
            if name.endswith(".md"):
                os.remove(os.path.join(rules_dir, name))

    for topic in sorted(rules_by_topic):
        K.write_text(os.path.join(rules_dir, "%s.md" % topic),
                     render_rule_shard(topic, taxonomy["topics"][topic],
                                       rules_by_topic[topic], packs_by_id))
    K.write_text(os.path.join(rules_dir, "INDEX.md"),
                 render_rules_index(sorted(rules_by_topic), taxonomy, rules_by_topic))

    fp = fingerprint(all_files)
    K.write_text(os.path.join(gen, "ROUTER.md"),
                 render_router(domain, packs, chapters, notes, engines, rules,
                               rules_by_topic, taxonomy, fp))

    # abs_path is machine-specific scaffolding; keep it out of the committed index.
    clean_packs = [{k: v for k, v in p.items() if k != "abs_path"} for p in packs]
    K.write_json(os.path.join(gen, "index.json"), {
        "domain": domain["id"],
        "title": domain.get("title"),
        "summary": domain.get("summary"),
        "scope": domain.get("scope", []),
        "corpus_fingerprint": fp,
        "packs": clean_packs,
        "chapters": chapters,
        "notes": notes,
        "engines": engines,
        "rules": rules,
        "topics": {t: sorted(r["id"] for r in rs) for t, rs in rules_by_topic.items()},
        "problems": problems,
    })
    return {"id": domain["id"], "chapters": len(chapters), "notes": len(notes),
            "engines": len(engines), "rules": len(rules),
            "shards": len(rules_by_topic), "fingerprint": fp, "problems": problems}


def join_and(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return items[0] if items else ""
    return "%s and %s" % (", ".join(items[:-1]), items[-1])


def compose_description(indexes):
    """Compose the skill's frontmatter description from installed domains.

    Generated rather than hand-written because a multi-domain skill otherwise
    needs a description broad enough to cover everything, which is exactly the
    kind of vague description that fails to trigger.

    Returns (text, dropped): the phrases that did not fit are returned so the
    build can say so. The 1024-character cap is enforced silently by the runtime,
    and a trigger that was trimmed to fit is indistinguishable from one that was
    never written -- the skill simply stops firing for that topic.
    """
    titles = [ix.get("title") for ix in indexes if ix.get("title")]
    # Kept per domain so that trimming for length sheds evenly instead of silently
    # muting whichever domain happens to be listed last.
    groups = [list((ix.get("scope") or [])[:SCOPE_PER_DOMAIN]) for ix in indexes]
    dropped = [p for ix in indexes for p in (ix.get("scope") or [])[SCOPE_PER_DOMAIN:]]

    # Triggering conditions only, and "Use when" first: a description that recites
    # what the skill does, or how, becomes a shortcut the model follows instead of
    # reading the skill body -- and every character spent on it is a trigger that
    # no longer fits under the cap.
    tail = ("Also use when they ask what the literature says, want work reviewed against it, "
            "or are adding markdown to the corpus, even if they never mention books or this skill.")
    # Domain titles are deliberately not in the description: the Installed-domains
    # table in the body names them, and the characters buy another trigger phrase.
    covers = ""

    def compose():
        phrases = [p for g in groups for p in g]
        parts = []
        if phrases:
            parts.append("Use when the user is working on " + "; ".join(phrases) + ".")
        parts.append(tail)
        if covers:
            parts.append(covers)
        return " ".join(parts)

    # `name: advisor` plus `description: ` plus the YAML fences the caller adds.
    budget = MAX_FRONTMATTER_CHARS - (len("description: ") + 40)
    while len(compose()) > budget and any(len(g) > 1 for g in groups):
        dropped.append(max(groups, key=len).pop())
    return compose(), dropped


def render_description(indexes):
    return compose_description(indexes)[0]


README_STATS_MARK = "<!-- STATS: rewritten by scripts/build_index.py"


def stamp_readme_stats(indexes, quiet=False):
    """Keep README's headline counts honest.

    A hand-typed corpus size is wrong the first time anything is ingested, and it is
    the first number a reader sees. Engine symbol counts are deliberately excluded:
    licensed sources are absent on most machines, so including them would make the
    line flip back and forth between checkouts.
    """
    path = os.path.join(K.ROOT, "README.md")
    if not os.path.exists(path):
        return
    text = K.read_text(path)
    if README_STATS_MARK not in text:
        return
    stats = "%d domain%s · %d rules · %d book chapters · %d topic shards" % (
        len(indexes), "" if len(indexes) == 1 else "s",
        sum(len(ix.get("rules", [])) for ix in indexes),
        sum(len(ix.get("chapters", [])) for ix in indexes),
        sum(len(ix.get("topics", {})) for ix in indexes))
    head, sep, rest = text.partition(README_STATS_MARK)
    line_end = rest.index("\n") + 1
    body = rest[line_end:]
    start = body.index("```") + 3
    end = body.index("```", start)
    new = head + sep + rest[:line_end] + body[:start] + "\n" + stats + "\n" + body[end:]
    if new != text:
        K.write_text(path, new)
        log("README.md stats stamped (%s)" % stats, quiet)


def render_domains_table(indexes):
    out = ["| Domain | Covers | Chapters | Rules | Router |", "|---|---|---|---|---|"]
    for ix in indexes:
        out.append("| `%s` | %s | %d | %d | `generated/%s/ROUTER.md` |" % (
            ix["domain"], truncate(ix.get("summary") or ix.get("title") or "", 90),
            len(ix.get("chapters", [])), len(ix.get("rules", [])), ix["domain"]))
    return "\n".join(out)


MAX_UPFRONT_CAVEATS = 6


def render_caveats(indexes):
    lines = []
    for ix in indexes:
        for pack in ix.get("packs", []):
            for caveat in pack.get("caveats", []):
                lines.append("- **`%s`** (%s) — %s" % (pack["id"], ix["domain"], caveat))
    if not lines:
        return "_None recorded._"
    shown, rest = lines[:MAX_UPFRONT_CAVEATS], lines[MAX_UPFRONT_CAVEATS:]
    text = ("The standing caveats are also in each ROUTER, but these matter often enough to "
            "state up front:\n\n" + "\n".join(shown))
    if rest:
        text += ("\n\n_%d further caveat(s) in the domain ROUTERs — read them before relying "
                 "on a pack you have not used before._" % len(rest))
    return text


def render_modes_table(modes):
    out = ["| Mode | Trigger | Output |", "|---|---|---|"]
    for mode in modes:
        trig = " · ".join('"%s"' % t for t in mode.get("triggers", [])[:2])
        out.append("| **%s** | %s | %s |" % (mode["id"], trig, mode.get("output", "")))
    return "\n".join(out)


def render_gates_summary(domains):
    blocks = []
    for dom in domains:
        gates = K.load_optional(dom, "gates")
        if not gates:
            continue
        names = ", ".join(i["name"] for i in gates.get("items", []))
        blocks.append("**%s** (`%s`, domain `%s`) — %s. %s"
                      % (gates.get("label", "Gates"), gates.get("source", ""), dom["id"],
                         names, gates.get("rationale", "")))
    if not blocks:
        return ("_No installed domain defines gates. In `plan` mode, say that explicitly "
                "instead of improvising a gate list._")
    return "\n\n".join(blocks)


def render_workflows(domains, quiet=False):
    out = ["# Workflows", "",
           "<!-- GENERATED by scripts/build_index.py from templates/modes.default.json and each",
           "     domain's gates.json / checklists.json — do not edit this file. -->", "",
           "Playbooks for each mode. They exist so retrieval is not improvised and output is "
           "checkable rather than merely plausible.", "",
           "All modes share two obligations: **cite what you assert**, and **name what you could "
           "not ground**. An honest \"the corpus does not cover this, here is my own reasoning\" "
           "is worth more than a confident paragraph with no IDs.", ""]

    seen = {}
    for dom in domains:
        for mode in K.load_modes(dom):
            seen.setdefault(mode["id"], mode)

    out.append("## Modes")
    out.append("")
    for mode in seen.values():
        out.append("### %s" % mode["id"])
        out.append("")
        if mode.get("triggers"):
            out.append("*%s*" % " · ".join('"%s"' % t for t in mode["triggers"]))
            out.append("")
        for i, step in enumerate(mode.get("steps", []), 1):
            out.append("%d. %s" % (i, step))
        out.append("")
        out.append("**Output:** %s" % mode.get("output", ""))
        out.append("")

    for dom in domains:
        gates = K.load_optional(dom, "gates")
        if gates:
            out.append("## Gates — %s" % dom.get("title", dom["id"]))
            out.append("")
            out.append("_%s_" % gates.get("rationale", ""))
            out.append("")
            out.append("| # | Gate | Must state |")
            out.append("|---|---|---|")
            for n, item in enumerate(gates.get("items", []), 1):
                out.append("| %d | **%s** | %s |" % (n, item["name"], item["must_state"]))
            out.append("")
            extra = gates.get("additional", [])
            if extra:
                out.append("Also settle, for this domain:")
                out.append("")
                for item in extra:
                    ids = " ".join("`%s`" % r for r in item.get("rules", []))
                    out.append(("- **%s** — %s %s" % (item["name"], item["must_state"], ids))
                               .rstrip())
                out.append("")
        else:
            out.append("## Gates — %s" % dom.get("title", dom["id"]))
            out.append("")
            out.append("_This domain defines no gates. `plan` mode's gate step does not apply "
                       "here — say so in the plan rather than inventing gates to fill the "
                       "section, and carry the domain's own standing caveats instead._")
            out.append("")

        checklists = K.load_optional(dom, "checklists")
        if checklists:
            for cid, chk in checklists.get("checklists", {}).items():
                out.append("## Checklist: %s — %s" % (cid, dom.get("title", dom["id"])))
                out.append("")
                out.append("| Severity | Defect | Rules |")
                out.append("|---|---|---|")
                order = {"high": 0, "medium": 1, "low": 2}
                for item in sorted(chk.get("items", []),
                                   key=lambda i: order.get(i.get("severity", "low"), 3)):
                    ids = " ".join("`%s`" % r for r in item.get("rules", []))
                    out.append("| %s | %s | %s |"
                               % (item.get("severity", ""), item["defect"], ids))
                out.append("")
        else:
            out.append("## Checklist: review — %s" % dom.get("title", dom["id"]))
            out.append("")
            out.append("_This domain ships no review checklist. Walk the target against the "
                       "governing rule shards instead, and say in the findings that no curated "
                       "checklist covered it — an uncovered review is weaker evidence than a "
                       "checklisted one, and the reader is entitled to know which they have._")
            out.append("")

    out.append("## Retrieval budget")
    out.append("")
    out.append("A good pass is three to six lookups. Past ten, the question was too broad — narrow "
               "it, or answer the part the corpus covers and say which part it does not.")
    K.write_text(os.path.join(K.ROOT, "references", "workflows.md"), "\n".join(out) + "\n")
    log("references/workflows.md regenerated (%d modes)" % len(seen), quiet)


TOKENS_PER_BYTE = 0.25   # ~4 bytes per token for English prose; good enough for a load warning


def _first(seq, default=None):
    for item in seq:
        return item
    return default


def render_id_examples(indexes):
    """Cite real IDs from the installed corpus, not remembered ones.

    A hardcoded `ASSP-09-R7` in this file is an invitation to cite it in a
    domain where it does not exist, which is the one failure the skill exists
    to prevent.
    """
    out = []
    for ix in indexes[:2]:
        rule = _first(ix.get("rules", []))
        if rule:
            out.append("`%s`" % rule["id"])
        for chapter in ix.get("chapters", []):
            if chapter.get("sections"):
                out.append("`%s§%s`" % (chapter["id"], chapter["sections"][0]["key"]))
                break
    return ", ".join(out[:3]) if out else "`PACK-01-R1`, `PACK-01§1`"


def render_corpus_tokens(indexes):
    """Size the *loadable* corpus. Engine packs are byte-sliced, never read whole,
    so counting them here would overstate what a careless `cat` would cost."""
    total = 0
    for ix in indexes:
        for item in list(ix.get("chapters", [])) + list(ix.get("notes", [])):
            path = os.path.join(K.ROOT, item["file"])
            if os.path.exists(path):
                total += os.path.getsize(path)
    tokens = int(total * TOKENS_PER_BYTE)
    if tokens >= 1000:
        return "%dk" % round(tokens / 1000.0)
    return str(tokens)


def render_router_example(indexes):
    dom = indexes[0]["domain"] if indexes else "<domain>"
    return "generated/%s/ROUTER.md" % dom


def render_retrieval_examples(indexes):
    """Build the retrieval cheatsheet from real IDs, topics and scope phrases."""
    if not indexes:
        return "python3 scripts/lookup.py --search \"<question>\""
    ix = indexes[0]
    query = (ix.get("scope") or [ix.get("title", "the topic")])[0]
    topic = _first(sorted(ix.get("topics", {}) or {}), "<topic>")
    rules = ix.get("rules", [])
    rule_id = rules[0]["id"] if rules else "<ID>"
    rule_ids = " ".join(r["id"] for r in rules[:2]) if rules else "<ID> <ID>"
    chapter = _first([c for c in ix.get("chapters", []) if c.get("sections")],
                     _first(ix.get("chapters", [])))
    chap_id = chapter["id"] if chapter else "<CHAPTER>"
    sec_id = ("%s§%s" % (chap_id, chapter["sections"][0]["key"])
              if chapter and chapter.get("sections") else "<CHAPTER>§1")

    # Unscoped BM25 leaks across domains: a trading question phrased in plain English
    # can rank a decisions chapter first. Scoping is the default form, not the footnote.
    multi = len(indexes) > 1
    scope = ("--domain %s " % indexes[0]["domain"]) if multi else ""
    rows = [
        ('python3 scripts/lookup.py %s--search "%s"' % (scope, truncate(query, 46)),
         "rank rules+chapters+sections"),
        ("python3 scripts/lookup.py --topic %s" % topic, "one rule shard"),
        ("python3 scripts/lookup.py --rule %s" % rule_ids, "verify every ID you cite, one call"),
        ("python3 scripts/lookup.py --conflicts %s" % rule_id, "registry entries citing an ID, or mentioning a word"),
        ("python3 scripts/lookup.py --chapter %s" % chap_id, "metadata + section map"),
        ('python3 scripts/lookup.py --section "%s"' % sec_id, "one section's text"),
    ]
    width = max(len(cmd) for cmd, _ in rows)
    lines = ["%-*s  # %s" % (width, cmd, note) for cmd, note in rows]
    lines.append("%-*s  # or: chapters, topics, packs, notes"
                 % (width, "python3 scripts/lookup.py --list domains"))
    if multi:
        lines.append("%-*s  # every domain at once — leakier; only when the domain is "
                     "genuinely unclear" % (width, 'python3 scripts/lookup.py --search "..."'))
    return "\n".join(lines)


def engine_packs(indexes):
    # An engine whose sources are absent (a fresh clone of a repo that gitignores
    # licensed docs) indexed no headings. Instructions for slicing it would tell the
    # model to run a command that returns nothing. A committed index outlives the bytes
    # it was built from, so presence in the index is not evidence the files are here —
    # check the disk.
    return [(ix["domain"], eng) for ix in indexes for eng in ix.get("engines", [])
            if any(os.path.exists(os.path.join(K.ROOT, f["file"]))
                   for f in (eng.get("files") or {}).values())]


def render_engine_rule(indexes):
    """Emitted only when an engine pack is installed — a bundle without one must
    not carry instructions for slicing documentation it does not ship."""
    engines = engine_packs(indexes)
    if not engines:
        return ""
    names = join_and(sorted({"`%s`" % eng["id"] for _, eng in engines}))
    return ("- **Engines describe capability, not method.** %s tells you what the tool *can* do. "
            "Whether you\n  *should* comes from the book packs.\n" % names)


def render_engine_retrieval(indexes):
    engines = engine_packs(indexes)
    if not engines:
        return ""
    dom, eng = engines[0]
    lines = ["## Engine packs", "",
             "Vendor documentation, indexed by byte offset and never loaded whole. `--search` and",
             "`--symbol` return offsets; `--show-offset` reads that slice and nothing else.", "",
             "```bash",
             'python3 scripts/lookup.py --engine %s --search "<capability>"' % eng["id"],
             "python3 scripts/lookup.py --engine %s --symbol <Symbol.name>" % eng["id"],
             "python3 scripts/lookup.py --engine %s --show-offset <offset> --max-bytes 8000"
             % eng["id"],
             "```", ""]
    return "\n".join(lines) + "\n"


def render_skill(indexes, quiet=False):
    tmpl_path = os.path.join(K.ROOT, "templates", "SKILL.md.tmpl")
    if not os.path.exists(tmpl_path):
        log("! templates/SKILL.md.tmpl missing — SKILL.md left untouched", quiet)
        return
    text = K.read_text(tmpl_path)
    total = sum(len(ix.get("rules", [])) for ix in indexes)
    domains = K.load_domains()
    modes = {}
    for dom in domains:
        for mode in K.load_modes(dom):
            modes.setdefault(mode["id"], mode)
    description, dropped = compose_description(indexes)
    for key, val in (("DESCRIPTION", description),
                     ("RULE_TOTAL", str(total)),
                     ("DOMAINS", render_domains_table(indexes)),
                     ("ID_EXAMPLES", render_id_examples(indexes)),
                     ("CORPUS_TOKENS", render_corpus_tokens(indexes)),
                     ("ROUTER_EXAMPLE", render_router_example(indexes)),
                     ("RETRIEVAL_EXAMPLES", render_retrieval_examples(indexes)),
                     ("ENGINE_RULE", render_engine_rule(indexes)),
                     ("ENGINE_RETRIEVAL", render_engine_retrieval(indexes)),
                     ("MODES", render_modes_table(list(modes.values()))),
                     ("GATES", render_gates_summary(domains)),
                     ("CAVEATS", render_caveats(indexes))):
        text = text.replace("{{%s}}" % key, val)
    K.write_text(os.path.join(K.ROOT, "SKILL.md"), text)
    stamp_readme_stats(indexes, quiet)
    log("SKILL.md regenerated (%d domains, %d rules, description %d chars)"
        % (len(indexes), total, len(description)), quiet)
    if dropped:
        log("  ! description at the %d-char frontmatter cap: %d trigger phrase(s) omitted, "
            "so the skill will not fire on them --" % (MAX_FRONTMATTER_CHARS, len(dropped)), quiet)
        for phrase in dropped:
            log("      - %s" % phrase, quiet)
        log("    shorten the `scope` phrases in domain.json to fit more.", quiet)


def main():
    quiet = "--quiet" in sys.argv
    only = None
    if "--domain" in sys.argv:
        idx = sys.argv.index("--domain")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1]

    domains = K.load_domains(only)
    if not domains:
        sys.exit("no domains found — expected domains/*/domain.json"
                 + (" matching %r" % only if only else ""))

    results = []
    for domain in domains:
        log("→ domain: %s" % domain["id"], quiet)
        results.append(build_domain(domain, quiet))
        log("", quiet)

    indexes = [K.load_json(os.path.join(d["generated"], "index.json"))
               for d in K.load_domains()]
    render_workflows(K.load_domains(), quiet)
    render_skill(indexes, quiet)
    log("", quiet)

    total_problems = []
    for res in results:
        log("%-12s %2d chapters · %2d notes · %d engines · %3d rules · %2d shards · %s"
            % (res["id"], res["chapters"], res["notes"], res["engines"],
               res["rules"], res["shards"], res["fingerprint"]), quiet)
        total_problems += res["problems"]

    if total_problems:
        log("", quiet)
        log("%d format problem(s) — run scripts/validate_pack.py for detail:"
            % len(total_problems), quiet)
        for problem in total_problems[:10]:
            log("  - %s" % problem, quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
