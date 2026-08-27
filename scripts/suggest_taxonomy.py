#!/usr/bin/env python3
"""Propose a taxonomy for a domain by clustering its chapters.

Hand-authoring fourteen topics with keyword lists is the friction that stops
books getting added, so this drafts one from the corpus itself. The output is a
*suggestion* written to a separate file — never taxonomy.json — because topic
labels are a judgement call and the machine only sees vocabulary.

Method, all stdlib:
  1. Build a bag of unigrams and bigrams per chapter from its title, Governs,
     Thesis, section headings and rule text.
  2. Weight terms by tf-idf across chapters, so vocabulary that appears
     everywhere (the domain's own name) cannot define a topic.
  3. Average-linkage agglomerative clustering on cosine similarity.
  4. Label each cluster by its most distinctive terms; emit those as keywords.

Usage:
    python3 scripts/suggest_taxonomy.py --domain trading [--topics 14] [--out PATH]
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been before being
below between both but by can cannot could did do does doing down during each few for from further
had has have having he her here hers herself him himself his how i if in into is it its itself just
me more most my myself no nor not now of off on once only or other ought our ours ourselves out
over own same she should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where which while who whom
why with would you your yours yourself yourselves
one two three four five six seven eight nine ten first second third
chapter section rule rules book books page figure table example examples note notes
use used using make makes made get gets got give gives given take takes taken
thing things way ways case cases point points part parts kind sort lot
means mean matter matters need needs needed want wants
work works working good bad better best worse worst
new old high low big small large long short
time times often always never sometimes usually
because therefore however instead rather still yet even much many
what's it's don't doesn't isn't aren't won't can't
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z\-']{2,}")
MIN_DOC_FREQ = 2          # a term in one chapter is an accident, not a topic
MAX_DOC_FRAC = 0.5        # a term in most chapters describes the domain, not a topic
KEYWORDS_PER_TOPIC = 14


def chapter_docs(domain):
    """Collect one term-bag per chapter across every book pack in the domain."""
    docs = {}
    for pack in K.load_domain_packs(domain):
        if pack["kind"] != "book":
            continue
        base = pack["abs_path"]
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(".md") or name.startswith("_"):
                continue
            rec = K.parse_chapter(os.path.join(base, name), pack["prefix"])
            blob = " ".join(filter(None, [
                rec.get("title"), rec.get("title"),      # title counted twice: it is the label
                rec.get("governs"), rec.get("thesis"),
                " ".join(s["title"] for s in rec["sections"]),
                " ".join(s for sub in rec["sections"] for s in sub.get("subsections", [])),
                " ".join(rec["rules"]),
            ]))
            docs[rec["id"]] = {"title": rec.get("title") or rec["id"],
                               "terms": extract_terms(blob)}
    return docs


def normalise(word):
    """Strip possessives so 'chapter's' cannot survive a stoplist containing 'chapter'."""
    return word.replace("'s", "").replace("'", "").strip("-")


def extract_terms(text):
    words = [normalise(w) for w in TOKEN_RE.findall(K.strip_md(text).lower())]
    words = [w for w in words if len(w) > 2]
    counts = Counter()
    prev = None
    for word in words:
        if word not in STOPWORDS:
            counts[word] += 1
            if prev:
                counts["%s %s" % (prev, word)] += 1
        prev = None if word in STOPWORDS else word
    return counts


def tfidf(docs):
    n = len(docs)
    doc_freq = Counter()
    for rec in docs.values():
        doc_freq.update(set(rec["terms"]))
    keep = {t for t, df in doc_freq.items()
            if MIN_DOC_FREQ <= df <= max(MIN_DOC_FREQ, int(n * MAX_DOC_FRAC))}
    vectors = {}
    for cid, rec in docs.items():
        total = sum(rec["terms"].values()) or 1
        vec = {}
        for term, cnt in rec["terms"].items():
            if term not in keep:
                continue
            vec[term] = (cnt / total) * math.log(n / doc_freq[term])
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors[cid] = {t: v / norm for t, v in vec.items()}
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def cluster(vectors, k):
    """Average-linkage agglomerative clustering. n is small; O(n^2) is fine."""
    clusters = [[cid] for cid in sorted(vectors)]
    sims = {}
    for i, ca in enumerate(clusters):
        for j in range(i + 1, len(clusters)):
            sims[(i, j)] = cosine(vectors[ca[0]], vectors[clusters[j][0]])

    while len(clusters) > k:
        best, best_score = None, -1.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                score = sum(cosine(vectors[a], vectors[b])
                            for a in clusters[i] for b in clusters[j])
                score /= (len(clusters[i]) * len(clusters[j]))
                if score > best_score:
                    best_score, best = score, (i, j)
        if not best:
            break
        i, j = best
        clusters[i] = clusters[i] + clusters[j]
        clusters.pop(j)
    return clusters


def label_cluster(members, vectors, docs):
    agg = defaultdict(float)
    for cid in members:
        for term, weight in vectors[cid].items():
            agg[term] += weight
    ranked = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))
    keywords = [t for t, _ in ranked[:KEYWORDS_PER_TOPIC]]

    # Chapter titles are the author's own labels, so a term appearing in one is a
    # far better topic name than the highest-weighted stray bigram.
    titles = " ".join(normalise(w) for cid in members
                      for w in TOKEN_RE.findall((docs[cid]["title"] or "").lower()))
    in_title = [t for t, _ in ranked if t in titles]
    label = (next((t for t in in_title if " " in t), None)
             or next((t for t, _ in ranked if " " in t), None)
             or (in_title[0] if in_title else (ranked[0][0] if ranked else "topic")))
    return label, keywords


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--topics", type=int, default=0, help="default: ~1 per 3 chapters, 6..16")
    ap.add_argument("--out")
    args = ap.parse_args()

    domains = K.load_domains(args.domain)
    if not domains:
        sys.exit("unknown domain %r" % args.domain)
    domain = domains[0]

    docs = chapter_docs(domain)
    if len(docs) < 2:
        sys.exit("need at least 2 chapters to cluster; found %d" % len(docs))

    k = args.topics or max(6, min(16, round(len(docs) / 3)))
    vectors = tfidf(docs)
    clusters = cluster(vectors, k)

    topics, seen = {}, set()
    for members in sorted(clusters, key=lambda m: -len(m)):
        label, keywords = label_cluster(members, vectors, docs)
        key = K.slug(label, 24).replace("-", "_")
        while key in seen:
            key += "_x"
        seen.add(key)
        topics[key] = {
            "label": label.title(),
            "keywords": keywords,
            "_chapters": ["%s — %s" % (cid, docs[cid]["title"]) for cid in members],
        }

    out_path = args.out or os.path.join(domain["root"], "taxonomy.suggested.json")
    K.write_json(out_path, {
        "$schema": "internal://taxonomy.v1",
        "comment": ("SUGGESTED taxonomy — review before use. Rename each label to the concept you "
                    "actually mean, prune keywords that are incidental vocabulary, and add domain "
                    "terms the corpus happens not to repeat. Delete every _chapters key (it is "
                    "provenance for your review, not config), then save as taxonomy.json."),
        "topics": topics,
    })

    print("%d chapters -> %d topics" % (len(docs), len(topics)))
    print()
    for key, spec in topics.items():
        print("%-22s %s" % (key, ", ".join(spec["keywords"][:7])))
        for line in spec["_chapters"][:4]:
            print("%-22s   · %s" % ("", line[:72]))
        if len(spec["_chapters"]) > 4:
            print("%-22s   · … %d more" % ("", len(spec["_chapters"]) - 4))
        print()
    print("written: %s" % os.path.relpath(out_path, K.ROOT))
    print("Review it, then save as taxonomy.json — this never overwrites it for you.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
