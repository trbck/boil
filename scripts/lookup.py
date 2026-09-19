#!/usr/bin/env python3
"""Deterministic retrieval across every installed domain.

Exact-match or keyword-ranked, no embeddings and no server, because citations
must be reproducible: the same query returns the same rule IDs in six months.

Indexes from all domains are merged at load time and every record carries its
domain, so search spans domains by default and `--domain` narrows it.

Examples:
    python3 scripts/lookup.py --search "position sizing under drawdown"
    python3 scripts/lookup.py --domain trading --topic sizing
    python3 scripts/lookup.py --rule ASSP-09-R7 ASSP-06-R4      # verify every ID you cite, in one call
    python3 scripts/lookup.py --conflicts ASSP-09-R7            # registry entries citing an ID (or a word)
    python3 scripts/lookup.py --chapter ASSP-09
    python3 scripts/lookup.py --section "ASSP-09§5"
    python3 scripts/lookup.py --engine vbtpro --symbol Portfolio.from_signals
    python3 scripts/lookup.py --list domains|packs|chapters|topics|notes
"""

import argparse
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

STOP = set("the a an of to and or for with in on at by is are be as it its that this "
           "how what when why do does not no from into than then".split())

# --- BM25 (used only by cmd_search's ranked search) ---------------------------
#
# score()/terms() above stay untouched — --engine's ranking still uses them,
# unchanged, exactly as before. Free-text --search gets its own tokenizer and
# Okapi BM25 (k1=1.5, b=0.75) instead: no substring matching (a document
# containing "brisk" no longer matches a query for "risk"), and IDF so a term
# that appears in most of the corpus stops dominating ranking. Stats are
# corpus-wide but computed fresh per call — the indexed corpus is small enough
# (rules + chapter blobs + section titles: low thousands of tokens) that this
# is microseconds, and it keeps the CLI a pure function of the on-disk index
# with nothing to invalidate.
#
# The STOP set is still applied here (reused from above, just against real
# tokens instead of substrings). IDF alone was tried and measured worse: many
# documents in this corpus are short (section titles average ~6 words), so a
# coincidental match on two stopwords ("when", "and") in a 6-word title still
# outscores a genuine topical match buried in a 30-word rule, because BM25's
# length normalization amplifies every term's contribution in short documents.
# Dropping stopwords before scoring — not just discounting them via IDF —
# is what tests/retrieval-questions.json showed was actually needed.

BM25_K1 = 1.5
BM25_B = 0.75
# Verbatim phrase match is real signal (the user typed almost exactly what the
# rule says) but must not swamp term-overlap ranking now that scores are
# unbounded floats instead of small integers. Tuned against
# tests/retrieval-questions.json — see the eval report for the sweep.
PHRASE_BONUS = 2.0
# Favours a chapter's own framing over its rules/sections when they're
# fighting over the same handful of query terms. Swept 0.5-12 against the
# eval set: hit@1 climbs from 0.467 at 0 up to 0.500 by ~3 and plateaus
# there; MRR peaks (0.579) around 5 and falls off past ~10 as a chapter
# starts beating its own more-specific rule outright on generic queries.
# 5 sits at the plateau on hit@1 while still at MRR's peak — see the eval
# report for the full sweep and the one rule-level regression it causes.
CHAPTER_BOOST = 5.0

_BM25_TOKEN_RE = re.compile(r"[a-z0-9_]+(?:[.%][a-z0-9_]+)*%?")


def bm25_tokens(text):
    """Word-boundary tokens for BM25: lowercase, keep v1.2 / 20% / work_mem
    intact, drop the existing STOP set — see the note above for why IDF alone
    isn't enough here."""
    return [t for t in _BM25_TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOP]


def _bm25_idf(doc_freq, n_docs):
    """Robertson–Sparck Jones IDF with +1 smoothing so it never goes negative
    even for a term in every document."""
    return math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)


def build_bm25_stats(token_lists):
    """Document frequency and count over a list of already-tokenized documents.
    This *is* "the merged corpus" — whatever run_search is about to score, in
    the same call, is what IDF is computed from."""
    n = len(token_lists)
    df = {}
    for toks in token_lists:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    return df, n


def avg_len_by_type(typed_token_lists):
    """Average document length per record type (rule / chapter / section).

    Rule text (~14 tokens), a chapter's title+governs+thesis blob (~44) and a
    bare section title (~3-4) are different *kinds* of document, not samples
    of one distribution. A single corpus-wide avgdl makes BM25's length
    normalization systematically favour section titles — a title matching one
    query word outscores a chapter or rule matching the same word, purely
    because the title is short — which was measured to actively hurt ranking
    (see the eval report). Normalizing each type against its own average
    (BM25F-style) fixes that while df/IDF above still comes from the one
    merged corpus, as specified."""
    totals, counts = {}, {}
    for typ, toks in typed_token_lists:
        totals[typ] = totals.get(typ, 0) + len(toks)
        counts[typ] = counts.get(typ, 0) + 1
    return {typ: (totals[typ] / counts[typ]) for typ in totals}


def bm25_score(tokens, query_terms, df, avgdl, n_docs, k1=BM25_K1, b=BM25_B):
    """Okapi BM25 of one document against a query's (already deduped) terms."""
    if not tokens or not query_terms:
        return 0.0
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    dl = len(tokens)
    length_norm = 1 - b + b * (dl / avgdl if avgdl else 1.0)
    total = 0.0
    for t in query_terms:
        f = tf.get(t, 0)
        if not f:
            continue
        idf = _bm25_idf(df.get(t, 0), n_docs)
        total += idf * (f * (k1 + 1)) / (f + k1 * length_norm)
    return total


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

def run_search(idx, query, pack_filter=None, kind="all"):
    """Rank every rule/chapter/section against `query` with BM25 and return
    results, sorted best-first, as (score, type, ident, text, ctx) tuples.

    Split out from cmd_search so callers other than the CLI (the retrieval
    eval harness) can get the ranked list without scraping stdout.
    """
    query_terms = list(dict.fromkeys(bm25_tokens(query)))  # dedup, order-stable
    phrase = query.lower().strip()
    multi = len(idx["domains"]) > 1

    # Pass 1: collect every candidate document — this list *is* the corpus BM25's
    # IDF is computed from, so stats reflect exactly what this call scans (a
    # `--kind rules` search gets IDF over rules alone, not the whole index).
    candidates = []  # (typ, ident, display_text, ctx, raw_text, tokens)

    if kind in ("all", "rules"):
        for rule in idx["rules"]:
            if pack_filter and rule["pack"] != pack_filter:
                continue
            candidates.append(("rule", tag(rule, multi), rule["text"],
                                "%s · %s" % (rule["parent"], ",".join(rule["topics"])),
                                rule["text"], bm25_tokens(rule["text"])))

    if kind in ("all", "chapters"):
        for ch in idx["chapters"] + idx["notes"]:
            blob = " ".join(filter(None, [ch.get("title"), ch.get("governs"), ch.get("thesis")]))
            candidates.append(("chapter", tag(ch, multi), ch.get("title") or "",
                                K.strip_md(ch.get("governs") or "")[:120],
                                blob, bm25_tokens(blob)))
            for sec in ch.get("sections", []):
                candidates.append(("section", "%s§%s" % (tag(ch, multi), sec["key"]),
                                    sec["title"], ch.get("title") or "",
                                    sec["title"], bm25_tokens(sec["title"])))

    df, n_docs = build_bm25_stats([c[5] for c in candidates])
    avgdl_by_type = avg_len_by_type([(c[0], c[5]) for c in candidates])

    results = []
    for typ, ident, display_text, ctx, raw_text, tokens in candidates:
        overlap = any(t in tokens for t in query_terms)
        if not overlap:
            continue
        s = bm25_score(tokens, query_terms, df, avgdl_by_type[typ], n_docs)
        if phrase and phrase in raw_text.lower():
            s += PHRASE_BONUS
        if typ == "chapter":
            s += CHAPTER_BOOST
        results.append((s, typ, ident, display_text, ctx))

    results.sort(key=lambda r: (-r[0], r[2]))
    return results


def cmd_search(idx, query, limit, pack_filter, kind):
    results = run_search(idx, query, pack_filter, kind)
    if not results:
        print("no matches for %r" % query)
        return
    print("# %d match(es) for %r\n" % (len(results), query))
    for s, typ, ident, text, ctx in results[:limit]:
        print("[%4.1f] %-8s %-20s %s" % (s, typ, ident, K.strip_md(text)[:96]))
        if ctx:
            print("                %s" % ctx[:106])
    if len(results) > limit:
        print("\n... %d more (raise --limit)" % (len(results) - limit))


def _strip_domain(ref):
    """Accept both 'ASSP-09-R7' and 'trading:ASSP-09-R7'."""
    return ref.split(":", 1)[1] if ":" in ref else ref


def cmd_rule(idx, rule_ids):
    """Print one or more rules. Several at once, because verifying every ID an
    answer cites is the normal case, and a shell loop of single lookups is what
    blows the retrieval budget. Exit status is 1 if any ID did not resolve."""
    missing = []
    hits = []
    for rule_id in rule_ids:
        want = _strip_domain(rule_id).upper()
        found = [r for r in idx["rules"] if r["id"].upper() == want]
        if not found:
            missing.append(rule_id)
        hits.extend(found)
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
    if missing:
        sys.exit("unknown rule id%s: %s" % ("s" if len(missing) > 1 else "", ", ".join(missing)))


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

    # A licensed source is gitignored, so a clone keeps the index but not the bytes.
    # Every query then returns "no matches", which reads as "the engine cannot do that"
    # — the opposite of the truth, and enough to send a caller off writing by hand what
    # the tool already implements. Say which failure this actually is.
    present = {r: i for r, i in eng["files"].items()
               if os.path.exists(os.path.join(K.ROOT, i["file"]))}
    if not present:
        names = (", ".join(sorted(i["file"] for i in eng["files"].values()))
                 or "none of its declared sources are on disk")
        sys.exit("engine %r is indexed but its sources are absent: %s\n"
                 "Engine RETRIEVAL is unavailable — the capability is unknown, not missing. "
                 "Do not conclude the tool lacks a feature from this result.\n"
                 "Licensed files are gitignored by design; copy them back to enable it."
                 % (pack_id, names))
    if len(present) < len(eng["files"]):
        sys.stderr.write("warning: %d of %d %s sources absent — results are partial\n"
                         % (len(eng["files"]) - len(present), len(eng["files"]), pack_id))
    eng["files"] = present

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


# --- conflict registry ---------------------------------------------------------

_ENTRY_HEAD = re.compile(r"^### +([A-Z]+\d+) +[—–-]+ +(.*)$")
_ROW_ENTRY = re.compile(r"^\| +([A-Z]+\d+) +\| +(.*?) +\|")
_ID_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*-\d+(?:-R\d+|§\d+)?\b")


def registry_entries(domain_id=None):
    """Parse each domain's conflicts.md into addressable entries.

    Two shapes occur: headed blocks (`### C3 — title` followed by a table and a
    resolution) and one-row convergences in a table (`| V6 | conclusion | ids | ids |`).
    Both become {domain, id, title, body, ids}. The file is hand-curated, so this
    parser is deliberately lenient: an entry it cannot parse is skipped, never
    guessed at.
    """
    out = []
    for dom in K.load_domains(domain_id):
        path = K.domain_path(dom, "conflicts", "conflicts.md")
        if not os.path.exists(path):
            continue
        lines = K.read_text(path).split("\n")
        i = 0
        while i < len(lines):
            m = _ENTRY_HEAD.match(lines[i])
            if m:
                j = i + 1
                while j < len(lines) and not (lines[j].startswith("#") or lines[j].startswith("---")):
                    j += 1
                body = "\n".join(lines[i:j]).rstrip()
                out.append({"domain": dom["id"], "id": m.group(1), "title": m.group(2).strip(),
                            "body": body, "ids": set(_ID_TOKEN.findall(body))})
                i = j
                continue
            m = _ROW_ENTRY.match(lines[i])
            if m and not lines[i].startswith("| #"):
                title = re.sub(r"\*\*", "", m.group(2)).strip()
                out.append({"domain": dom["id"], "id": m.group(1), "title": title,
                            "body": lines[i], "ids": set(_ID_TOKEN.findall(lines[i]))})
            i += 1
    return out


def cmd_conflicts(query, domain_id):
    entries = registry_entries(domain_id)
    if not entries:
        sys.exit("no conflict registry found" + (" for domain %s" % domain_id if domain_id else ""))
    if not query:
        for e in entries:
            print("%-10s %-4s %s" % (e["domain"], e["id"], e["title"][:100]))
        print()
        print("(%d entries; `--conflicts <rule or chapter ID | topic | word>` prints the matching ones)"
              % len(entries))
        return
    q = _strip_domain(query).strip()
    qid = q.upper()
    hits = []
    for e in entries:
        if e["id"] == qid:
            hits.append(e)
        elif any(cid == qid or cid.startswith(qid + "-") or cid.startswith(qid + "§") for cid in e["ids"]):
            hits.append(e)
        elif q.lower() in e["body"].lower():
            hits.append(e)
    if not hits:
        print("no registry entry cites or mentions %r" % query)
        print("(that is a finding, not an error: say the conflict registry does not cover it)")
        return
    print("# %d registry entr%s for %r" % (len(hits), "y" if len(hits) == 1 else "ies", query))
    for e in hits:
        print()
        print("<!-- %s:%s from domains/%s/conflicts.md -->" % (e["domain"], e["id"], e["domain"]))
        print(e["body"])


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
    ap.add_argument("--rule", nargs="+", metavar="ID",
                    help="print one or more rules; exits 1 if any is unknown")
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
    ap.add_argument("--conflicts", nargs="?", const="", metavar="QUERY",
                    help="conflict/convergence registry entries citing an ID or mentioning a word; "
                         "no argument lists every entry")
    ap.add_argument("--list", dest="list_what",
                    choices=["domains", "packs", "chapters", "topics", "notes"])
    args = ap.parse_args()

    if args.engine:
        return cmd_engine(args.engine, args.search, args.symbol, args.show_offset,
                          args.limit, args.max_bytes, args.role, args.domain)

    if args.conflicts is not None:
        return cmd_conflicts(args.conflicts, args.domain)

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
