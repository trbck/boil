#!/usr/bin/env python3
"""Deterministic retrieval over the knowledge-advisor corpus.

Everything here is exact-match or keyword-ranked -- no embeddings, no server.
That matters because citations must be reproducible: the same query returns the
same rule IDs today and in six months.

Examples:
    python3 scripts/lookup.py --search "position sizing under drawdown"
    python3 scripts/lookup.py --rule ASSP-09-R7
    python3 scripts/lookup.py --chapter ASSP-09
    python3 scripts/lookup.py --section "ASSP-09§5"
    python3 scripts/lookup.py --topic sizing
    python3 scripts/lookup.py --engine vbtpro --search "from_signals stop loss"
    python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
    python3 scripts/lookup.py --list chapters
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

GEN = os.path.join(K.ROOT, "generated")
STOP = set("the a an of to and or for with in on at by is are be as it its that this "
           "how what when why do does not no from into than then".split())


def load_index():
    path = os.path.join(GEN, "index.json")
    if not os.path.exists(path):
        sys.exit("index.json missing — run: python3 scripts/build_index.py")
    return K.load_json(path)


def terms(query):
    return [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOP and len(t) > 1]


def score(text, query_terms, phrase):
    """Overlap score with a phrase bonus; deliberately simple and explainable."""
    low = text.lower()
    hits = sum(1 for t in query_terms if t in low)
    if not hits:
        return 0
    bonus = 5 if phrase and phrase in low else 0
    return hits * 2 + bonus


# --- commands ----------------------------------------------------------------

def cmd_search(idx, query, limit, pack_filter, kind):
    qt, phrase = terms(query), query.lower().strip()
    results = []

    if kind in ("all", "rules"):
        for rule in idx["rules"]:
            if pack_filter and rule["pack"] != pack_filter:
                continue
            s = score(rule["text"], qt, phrase)
            if s:
                results.append((s, "rule", rule["id"], rule["text"],
                                "%s · %s" % (rule["parent"], ",".join(rule["topics"]))))

    if kind in ("all", "chapters"):
        for ch in idx["chapters"] + idx.get("notes", []):
            blob = " ".join(filter(None, [ch.get("title"), ch.get("governs"), ch.get("thesis")]))
            s = score(blob, qt, phrase)
            if s:
                results.append((s + 1, "chapter", ch["id"], ch.get("title") or "",
                                K.strip_md(ch.get("governs") or "")[:120]))
            for sec in ch.get("sections", []):
                s2 = score(sec["title"], qt, phrase)
                if s2:
                    results.append((s2, "section", "%s§%s" % (ch["id"], sec["key"]),
                                    sec["title"], ch.get("title") or ""))

    results.sort(key=lambda r: (-r[0], r[2]))
    if not results:
        print("no matches for %r" % query)
        return
    print("# %d match(es) for %r\n" % (len(results), query))
    for s, typ, ident, text, ctx in results[:limit]:
        print("[%2d] %-8s %-16s %s" % (s, typ, ident, K.strip_md(text)[:100]))
        if ctx:
            print("            %s" % ctx[:110])
    if len(results) > limit:
        print("\n... %d more (raise --limit)" % (len(results) - limit))


def cmd_rule(idx, rule_id):
    want = rule_id.upper()
    for rule in idx["rules"]:
        if rule["id"].upper() == want:
            print("# %s" % rule["id"])
            print()
            print(rule["text"])
            print()
            print("- parent   : %s — %s" % (rule["parent"], rule.get("parent_title") or ""))
            print("- pack     : %s" % rule["pack"])
            print("- topics   : %s" % ", ".join(rule["topics"]))
            print("- authority: %s" % rule.get("authority", "primary"))
            return
    sys.exit("unknown rule id: %s" % rule_id)


def _find_doc(idx, doc_id):
    want = doc_id.upper()
    for doc in idx["chapters"] + idx.get("notes", []):
        if doc["id"].upper() == want:
            return doc
    return None


def cmd_chapter(idx, doc_id):
    doc = _find_doc(idx, doc_id)
    if not doc:
        sys.exit("unknown chapter/note id: %s" % doc_id)
    print("# %s — %s" % (doc["id"], doc.get("title") or ""))
    print()
    for field in ("citation", "governs", "thesis", "category", "authority", "date"):
        if doc.get(field):
            print("**%s:** %s" % (field.capitalize(), doc[field]))
    print()
    print("- file  : %s" % doc["file"])
    print("- topics: %s" % ", ".join(doc.get("topics", [])))
    print("- rules : %d" % doc.get("rule_count", 0))
    print()
    print("## Sections")
    for sec in doc.get("sections", []):
        print("- `%s§%s` — %s" % (doc["id"], sec["key"], sec["title"]))
        for sub in sec.get("subsections", [])[:6]:
            print("    · %s" % sub)


def cmd_section(idx, ref):
    if "§" in ref:
        doc_id, _, key = ref.partition("§")
    elif "#" in ref:
        doc_id, _, key = ref.partition("#")
    else:
        sys.exit("section ref must look like ASSP-09§5")
    doc = _find_doc(idx, doc_id)
    if not doc:
        sys.exit("unknown chapter/note id: %s" % doc_id)
    for sec in doc.get("sections", []):
        if str(sec["key"]).lower() == key.lower():
            path = os.path.join(K.ROOT, doc["file"])
            lines = K.read_text(path).split("\n")
            body = "\n".join(lines[sec["start_line"] - 1: sec["end_line"]])
            print("<!-- %s§%s from %s -->" % (doc["id"], sec["key"], doc["file"]))
            print(body.strip())
            return
    keys = ", ".join(str(s["key"]) for s in doc.get("sections", []))
    sys.exit("unknown section %r in %s. available: %s" % (key, doc_id, keys))


def cmd_topic(idx, topic):
    path = os.path.join(GEN, "rules", "%s.md" % topic)
    if not os.path.exists(path):
        available = sorted(idx.get("topics", {}))
        sys.exit("unknown topic %r. available: %s" % (topic, ", ".join(available)))
    sys.stdout.write(K.read_text(path))


def cmd_engine(pack_id, query, symbol, show_offset, limit, max_bytes, role_filter):
    path = os.path.join(GEN, "engines", "%s.index.json" % pack_id)
    if not os.path.exists(path):
        sys.exit("no engine index for %r — run build_index.py" % pack_id)
    eng = K.load_json(path)

    if show_offset is not None:
        for role, info in eng["files"].items():
            for head in info["headings"]:
                if head["offset"] == show_offset:
                    print("<!-- %s/%s :: %s -->" % (pack_id, role, head["name"]))
                    print(K.read_slice(os.path.join(K.ROOT, info["file"]),
                                       head["offset"], head["end_offset"], max_bytes))
                    return
        sys.exit("no heading at offset %d" % show_offset)

    if symbol:
        want = symbol.lower()
        best = None
        for role, info in eng["files"].items():
            if role_filter and role != role_filter:
                continue
            for head in info["headings"]:
                sym = head["symbol"].lower()
                if sym == want or sym.endswith("." + want):
                    best = (role, info, head)
                    break
            if best:
                break
        if not best:
            sys.exit("symbol %r not found — try --search" % symbol)
        role, info, head = best
        print("<!-- %s/%s :: %s -->" % (pack_id, role, head["name"]))
        print(K.read_slice(os.path.join(K.ROOT, info["file"]),
                           head["offset"], head["end_offset"], max_bytes))
        return

    if not query:
        sys.exit("pass --search, --symbol or --show-offset")

    qt, phrase = terms(query), query.lower().strip()
    hits = []
    for role, info in eng["files"].items():
        if role_filter and role != role_filter:
            continue
        for head in info["headings"]:
            s = score(head["name"], qt, phrase)
            if s:
                hits.append((s - head["level"], role, head))
    hits.sort(key=lambda h: (-h[0], h[2]["offset"]))
    if not hits:
        print("no engine matches for %r" % query)
        return
    print("# %d match(es) in %s for %r\n" % (len(hits), pack_id, query))
    for s, role, head in hits[:limit]:
        print("[%2d] %-5s h%d  %-52s  --show-offset %d" % (
            s, role, head["level"], head["symbol"][:52], head["offset"]))
    if len(hits) > limit:
        print("\n... %d more (raise --limit)" % (len(hits) - limit))


def cmd_list(idx, what):
    if what == "packs":
        for pack in idx["packs"]:
            print("%-8s %-7s %s" % (pack["id"], pack["kind"], pack["title"]))
    elif what == "topics":
        for topic in sorted(idx.get("topics", {})):
            print("%-14s %d rules" % (topic, len(idx["topics"][topic])))
    elif what == "notes":
        for note in idx.get("notes", []):
            print("%-28s %-12s %-10s %s" % (note["id"], note.get("category", ""),
                                            note.get("date") or "", note.get("title") or ""))
        if not idx.get("notes"):
            print("(none — drop markdown in inbox/ and run scripts/ingest.py)")
    else:
        for ch in idx["chapters"]:
            print("%-9s %-46s %s" % (ch["id"], (ch.get("title") or "")[:44],
                                     ",".join(ch.get("topics", []))))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search")
    ap.add_argument("--rule")
    ap.add_argument("--chapter")
    ap.add_argument("--section")
    ap.add_argument("--topic")
    ap.add_argument("--engine")
    ap.add_argument("--symbol")
    ap.add_argument("--show-offset", type=int)
    ap.add_argument("--role", help="engine source role: docs | api")
    ap.add_argument("--pack", help="restrict --search to one pack")
    ap.add_argument("--kind", default="all", choices=["all", "rules", "chapters"])
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--max-bytes", type=int, default=40000)
    ap.add_argument("--list", dest="list_what",
                    choices=["packs", "chapters", "topics", "notes"])
    args = ap.parse_args()

    if args.engine:
        return cmd_engine(args.engine, args.search, args.symbol, args.show_offset,
                          args.limit, args.max_bytes, args.role)

    idx = load_index()
    if args.list_what:
        return cmd_list(idx, args.list_what)
    if args.rule:
        return cmd_rule(idx, args.rule)
    if args.chapter:
        return cmd_chapter(idx, args.chapter)
    if args.section:
        return cmd_section(idx, args.section)
    if args.topic:
        return cmd_topic(idx, args.topic)
    if args.search:
        return cmd_search(idx, args.search, args.limit, args.pack, args.kind)
    ap.print_help()


if __name__ == "__main__":
    main()
