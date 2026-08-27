#!/usr/bin/env python3
"""Deterministic retrieval across every installed domain.

Exact-match or keyword-ranked, no embeddings and no server, because citations
must be reproducible: the same query returns the same rule IDs in six months.

Indexes from all domains are merged at load time and every record carries its
domain, so search spans domains by default and `--domain` narrows it.

Examples:
    python3 scripts/lookup.py --search "position sizing under drawdown"
    python3 scripts/lookup.py --domain trading --topic sizing
    python3 scripts/lookup.py --rule ASSP-09-R7
    python3 scripts/lookup.py --chapter ASSP-09
    python3 scripts/lookup.py --section "ASSP-09§5"
    python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
    python3 scripts/lookup.py --list domains|packs|chapters|topics|notes
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

STOP = set("the a an of to and or for with in on at by is are be as it its that this "
           "how what when why do does not no from into than then".split())


def load_indexes(domain_id=None):
    """Merge every domain's index, tagging records with their domain."""
    domains = K.load_domains(domain_id)
    if not domains:
        sys.exit("no domains found — expected domains/*/domain.json"
                 + (" matching %r" % domain_id if domain_id else ""))

    merged = {"domains": [], "chapters": [], "notes": [], "rules": [], "packs": [], "topics": {}}
    missing = []
    for dom in domains:
        path = os.path.join(dom["generated"], "index.json")
        if not os.path.exists(path):
            missing.append(dom["id"])
            continue
        idx = K.load_json(path)
        merged["domains"].append({
            "id": dom["id"], "title": idx.get("title"), "summary": idx.get("summary"),
            "generated": dom["generated"], "fingerprint": idx.get("corpus_fingerprint"),
            "chapters": len(idx.get("chapters", [])), "rules": len(idx.get("rules", [])),
        })
        for key in ("chapters", "notes", "rules", "packs"):
            for rec in idx.get(key, []):
                rec.setdefault("domain", dom["id"])
                merged[key].append(rec)
        merged["topics"][dom["id"]] = idx.get("topics", {})
    if missing:
        sys.exit("no index for domain(s) %s — run: python3 scripts/build_index.py"
                 % ", ".join(missing))
    return merged


def terms(query):
    return [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOP and len(t) > 1]


def score(text, query_terms, phrase):
    """Overlap score with a phrase bonus; deliberately simple and explainable."""
    low = text.lower()
    hits = sum(1 for t in query_terms if t in low)
    if not hits:
        return 0
    return hits * 2 + (5 if phrase and phrase in low else 0)


def tag(rec, multi):
    """Prefix an ID with its domain only when more than one domain is loaded."""
    return "%s:%s" % (rec["domain"], rec["id"]) if multi else rec["id"]


# --- commands ----------------------------------------------------------------

def cmd_search(idx, query, limit, pack_filter, kind):
    qt, phrase = terms(query), query.lower().strip()
    multi = len(idx["domains"]) > 1
    results = []

    if kind in ("all", "rules"):
        for rule in idx["rules"]:
            if pack_filter and rule["pack"] != pack_filter:
                continue
            s = score(rule["text"], qt, phrase)
            if s:
                results.append((s, "rule", tag(rule, multi), rule["text"],
                                "%s · %s" % (rule["parent"], ",".join(rule["topics"]))))

    if kind in ("all", "chapters"):
        for ch in idx["chapters"] + idx["notes"]:
            blob = " ".join(filter(None, [ch.get("title"), ch.get("governs"), ch.get("thesis")]))
            s = score(blob, qt, phrase)
            if s:
                results.append((s + 1, "chapter", tag(ch, multi), ch.get("title") or "",
                                K.strip_md(ch.get("governs") or "")[:120]))
            for sec in ch.get("sections", []):
                s2 = score(sec["title"], qt, phrase)
                if s2:
                    results.append((s2, "section", "%s§%s" % (tag(ch, multi), sec["key"]),
                                    sec["title"], ch.get("title") or ""))

    results.sort(key=lambda r: (-r[0], r[2]))
    if not results:
        print("no matches for %r" % query)
        return
    print("# %d match(es) for %r\n" % (len(results), query))
    for s, typ, ident, text, ctx in results[:limit]:
        print("[%2d] %-8s %-20s %s" % (s, typ, ident, K.strip_md(text)[:96]))
        if ctx:
            print("                %s" % ctx[:106])
    if len(results) > limit:
        print("\n... %d more (raise --limit)" % (len(results) - limit))


def _strip_domain(ref):
    """Accept both 'ASSP-09-R7' and 'trading:ASSP-09-R7'."""
    return ref.split(":", 1)[1] if ":" in ref else ref


def cmd_rule(idx, rule_id):
    want = _strip_domain(rule_id).upper()
    hits = [r for r in idx["rules"] if r["id"].upper() == want]
    if not hits:
        sys.exit("unknown rule id: %s" % rule_id)
    for rule in hits:
        print("# %s" % rule["id"])
        print()
        print(rule["text"])
        print()
        print("- domain   : %s" % rule.get("domain"))
        print("- parent   : %s — %s" % (rule["parent"], rule.get("parent_title") or ""))
        print("- pack     : %s" % rule["pack"])
        print("- topics   : %s" % ", ".join(rule["topics"]))
        print("- authority: %s" % rule.get("authority", "primary"))
        if len(hits) > 1:
            print()


def _find_doc(idx, doc_id):
    want = _strip_domain(doc_id).upper()
    for doc in idx["chapters"] + idx["notes"]:
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
    print("- domain: %s" % doc.get("domain"))
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
    sep = "§" if "§" in ref else ("#" if "#" in ref else None)
    if not sep:
        sys.exit("section ref must look like ASSP-09§5")
    doc_id, _, key = ref.partition(sep)
    doc = _find_doc(idx, doc_id)
    if not doc:
        sys.exit("unknown chapter/note id: %s" % doc_id)
    for sec in doc.get("sections", []):
        if str(sec["key"]).lower() == key.lower():
            lines = K.read_text(os.path.join(K.ROOT, doc["file"])).split("\n")
            print("<!-- %s§%s from %s -->" % (doc["id"], sec["key"], doc["file"]))
            print("\n".join(lines[sec["start_line"] - 1: sec["end_line"]]).strip())
            return
    keys = ", ".join(str(s["key"]) for s in doc.get("sections", []))
    sys.exit("unknown section %r in %s. available: %s" % (key, doc_id, keys))


def cmd_topic(idx, topic, domain_id):
    found = []
    for dom in idx["domains"]:
        if domain_id and dom["id"] != domain_id:
            continue
        path = os.path.join(dom["generated"], "rules", "%s.md" % topic)
        if os.path.exists(path):
            found.append((dom["id"], path))
    if not found:
        available = sorted({t for d in idx["topics"].values() for t in d})
        sys.exit("unknown topic %r. available: %s" % (topic, ", ".join(available)))
    for dom_id, path in found:
        if len(found) > 1:
            print("<!-- domain: %s -->" % dom_id)
        sys.stdout.write(K.read_text(path))


def cmd_engine(pack_id, query, symbol, show_offset, limit, max_bytes, role_filter, domain_id):
    path = None
    for dom in K.load_domains(domain_id):
        candidate = os.path.join(dom["generated"], "engines", "%s.index.json" % pack_id)
        if os.path.exists(candidate):
            path = candidate
            break
    if not path:
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
        for role, info in eng["files"].items():
            if role_filter and role != role_filter:
                continue
            for head in info["headings"]:
                sym = head["symbol"].lower()
                if sym == want or sym.endswith("." + want):
                    print("<!-- %s/%s :: %s -->" % (pack_id, role, head["name"]))
                    print(K.read_slice(os.path.join(K.ROOT, info["file"]),
                                       head["offset"], head["end_offset"], max_bytes))
                    return
        sys.exit("symbol %r not found — try --search" % symbol)

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
        print("[%2d] %-5s h%d  %-52s  --show-offset %d"
              % (s, role, head["level"], head["symbol"][:52], head["offset"]))
    if len(hits) > limit:
        print("\n... %d more (raise --limit)" % (len(hits) - limit))


def cmd_list(idx, what):
    if what == "domains":
        for dom in idx["domains"]:
            print("%-12s %-46s %3d chapters · %3d rules · %s"
                  % (dom["id"], (dom.get("title") or "")[:44], dom["chapters"],
                     dom["rules"], dom.get("fingerprint") or ""))
    elif what == "packs":
        for pack in idx["packs"]:
            print("%-10s %-8s %-7s %s" % (pack.get("domain", ""), pack["id"],
                                          pack["kind"], pack["title"]))
    elif what == "topics":
        for dom_id, topics in sorted(idx["topics"].items()):
            for topic in sorted(topics):
                print("%-10s %-14s %d rules" % (dom_id, topic, len(topics[topic])))
    elif what == "notes":
        for note in idx["notes"]:
            print("%-10s %-28s %-12s %s" % (note.get("domain", ""), note["id"],
                                            note.get("category", ""), note.get("title") or ""))
        if not idx["notes"]:
            print("(none — drop markdown in inbox/ and run scripts/ingest.py)")
    else:
        for ch in idx["chapters"]:
            print("%-10s %-9s %-42s %s" % (ch.get("domain", ""), ch["id"],
                                           (ch.get("title") or "")[:40],
                                           ",".join(ch.get("topics", []))))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", help="restrict to one domain")
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
                    choices=["domains", "packs", "chapters", "topics", "notes"])
    args = ap.parse_args()

    if args.engine:
        return cmd_engine(args.engine, args.search, args.symbol, args.show_offset,
                          args.limit, args.max_bytes, args.role, args.domain)

    idx = load_indexes(args.domain)
    if args.list_what:
        return cmd_list(idx, args.list_what)
    if args.rule:
        return cmd_rule(idx, args.rule)
    if args.chapter:
        return cmd_chapter(idx, args.chapter)
    if args.section:
        return cmd_section(idx, args.section)
    if args.topic:
        return cmd_topic(idx, args.topic, args.domain)
    if args.search:
        return cmd_search(idx, args.search, args.limit, args.pack, args.kind)
    ap.print_help()


if __name__ == "__main__":
    main()
