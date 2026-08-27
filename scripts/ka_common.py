"""Shared parsing and scoring helpers for the knowledge-advisor toolchain.

Stdlib only, Python 3.8+. Every consumer (build_index, ingest, validate, lookup)
imports from here so the format contract lives in exactly one place.
"""

import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAINS_DIR = os.path.join(ROOT, "domains")
GENERATED = os.path.join(ROOT, "generated")


# --- domain registry ---------------------------------------------------------

def load_domains(domain_id=None):
    """Discover domains by globbing domains/*/domain.json.

    Self-registering on purpose: adding a domain is dropping a directory in,
    not editing a central list that then drifts out of sync with the tree.
    """
    out = []
    if not os.path.isdir(DOMAINS_DIR):
        return out
    for name in sorted(os.listdir(DOMAINS_DIR)):
        manifest = os.path.join(DOMAINS_DIR, name, "domain.json")
        if not os.path.exists(manifest) or (domain_id and name != domain_id):
            continue
        dom = load_json(manifest)
        dom.setdefault("id", name)
        dom["root"] = os.path.join(DOMAINS_DIR, name)
        dom["generated"] = os.path.join(GENERATED, dom["id"])
        out.append(dom)
    return out


def domain_path(domain, key, default):
    return os.path.join(domain["root"], domain.get(key, default))


def load_domain_packs(domain):
    """Packs with paths resolved against the domain root, not the repo root."""
    packs = load_json(domain_path(domain, "packs", "packs.json"))["packs"]
    for pack in packs:
        pack["domain"] = domain["id"]
        pack["abs_path"] = os.path.join(domain["root"], pack["path"])
    return packs


def load_domain_taxonomy(domain):
    return load_json(domain_path(domain, "taxonomy", "taxonomy.json"))

# --- format contract regexes -------------------------------------------------
# Chapter H1 accepts em dash, en dash or hyphen because editors silently swap them.
CH_RE = re.compile(r"^#\s+Ch\s+(\d+)\s*[—–-]\s*(.+?)\s*$")
META_RE = re.compile(r"^\*\*(Source|Governs|Thesis):\*\*\s*(.+?)\s*$", re.I)
HEAD_RE = re.compile(r"^(#{1,6})\s+(?:(\d+)\.\s*)?(.+?)\s*$")
RULES_HEAD_RE = re.compile(r"^#{2,4}\s*(?:\d+\.\s*)?transferable rules\b", re.I)
XREF_HEAD_RE = re.compile(r"^#{2,4}\s*(?:\d+\.\s*)?cross[- ]references\b", re.I)
# Sections in a note whose items graduate into the rule constitution.
FINDINGS_HEAD_RE = re.compile(
    r"^#{2,4}\s*(?:\d+\.\s*)?(key findings|findings|transferable rules|recommendations|takeaways|key takeaways|conclusions)\b",
    re.I,
)
NUM_ITEM_RE = re.compile(r"^(\d+)\.\s+(.+)$")
BULLET_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def fence_step(line, state):
    """Track fenced-code state per CommonMark.

    A naive `startswith('```')` toggle desyncs on nested or longer fences, and a
    single desync in an 18 MB vendor file silently hides thousands of headings.
    Closing fences must use the same character, be at least as long, and carry
    no info string.

    `state` is None (outside) or a (char, length) tuple (inside).
    """
    m = FENCE_RE.match(line)
    if not m:
        return state
    marker, rest = m.group(1), m.group(2).strip()
    char, length = marker[0], len(marker)
    if state is None:
        if char == "`" and "`" in rest:
            return None          # backtick info strings may not contain backticks
        return (char, length)
    open_char, open_len = state
    if char == open_char and length >= open_len and not rest:
        return None
    return state


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=False)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def slug(text, maxlen=40):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen].strip("-") or "untitled"


def strip_md(text):
    """Flatten inline markdown so keyword scoring sees words, not syntax."""
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_>#|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --- frontmatter -------------------------------------------------------------

def parse_frontmatter(text):
    """Minimal `key: value` frontmatter. Scalars and inline lists only.

    Deliberately not YAML: the repo must run anywhere with stdlib alone, and a
    permissive parser silently accepting broken YAML is worse than a strict
    small one that only claims to do a little.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, min(len(lines), 60)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        else:
            meta[key] = val.strip("'\"")
    return meta, "\n".join(lines[end + 1:])


# --- topic scoring -----------------------------------------------------------

KW_WEIGHT_SINGLE = 3      # one-word keyword: weak evidence, many are ambiguous
KW_WEIGHT_PHRASE = 5      # multi-word keyword: strong evidence, rarely accidental
TITLE_MULTIPLIER = 2.0    # a hit in the title says far more than one in the body

_KW_CACHE = {}


def _keyword_regex(kw):
    """Compile a keyword to a word-start match.

    Plain substring matching produces silent nonsense -- 'rag' matches "ave*rag*e"
    and 'metric' matches "geo*metric*" -- which quietly misroutes rules. Anchoring
    at a word boundary kills that while still letting deliberately truncated stems
    like 'simulat' or 'psycholog' match their inflections.
    """
    if kw not in _KW_CACHE:
        _KW_CACHE[kw] = re.compile(r"\b" + re.escape(kw), re.I)
    return _KW_CACHE[kw]


def _match_topics(text, taxonomy):
    """Return {topic: weighted score} for one blob of text."""
    if not text:
        return {}
    lowered = strip_md(text).lower()
    scores = {}
    for topic, spec in taxonomy["topics"].items():
        total = 0
        for kw in spec["keywords"]:
            if _keyword_regex(kw).search(lowered):
                total += KW_WEIGHT_PHRASE if " " in kw else KW_WEIGHT_SINGLE
        if total:
            scores[topic] = total
    return scores


def score_topics(text, taxonomy, base=None, title=None, max_topics=2, ratio=0.6):
    """Score text against the taxonomy; return up to max_topics topic ids.

    Distinct keywords are scored, not occurrences, so repeating one generic word
    cannot outrank several specific matches. Phrases outweigh single words and
    title hits outweigh body hits, which is what breaks the otherwise common
    multi-way ties -- ties previously fell through to alphabetical order, which
    is how the position-sizing chapter ended up filed under "backtesting".

    `base` lets a rule inherit its chapter's topic profile, so a sizing rule in a
    sizing chapter stays put unless another topic is clearly better supported.
    """
    scores = dict(_match_topics(text, taxonomy))
    for topic, val in _match_topics(title, taxonomy).items():
        scores[topic] = scores.get(topic, 0) + val * TITLE_MULTIPLIER
    if base:
        for topic, val in base.items():
            scores[topic] = scores.get(topic, 0) + val
    if not scores:
        return []
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ordered[0][1]
    picked = [ordered[0][0]]
    for topic, val in ordered[1:max_topics]:
        if val >= top * ratio:
            picked.append(topic)
    return picked


# --- chapter parsing ---------------------------------------------------------

def parse_chapter(path, prefix, root=None):
    """Parse one book-pack chapter file into a structured record.

    Fenced code blocks are skipped so `# comments` inside Python samples are not
    mistaken for headings -- the distilled chapters are full of them.
    """
    raw = read_text(path)
    front, body = parse_frontmatter(raw)
    lines = body.split("\n")

    rec = {
        "file": os.path.relpath(path, root or ROOT).replace(os.sep, "/"),
        "pinned_topics": front.get("topics") or [],
        "number": None,
        "title": None,
        "source": None,
        "governs": None,
        "thesis": None,
        "sections": [],
        "rules": [],
        "cross_references": None,
        "problems": [],
    }

    fence = None
    mode = None           # None | 'rules' | 'xref'
    buf = None            # in-flight rule text
    cur = None            # in-flight section
    xref_lines = []

    def flush_rule():
        if buf:
            rec["rules"].append(buf.strip())

    def close_section(end_line):
        if cur is not None:
            cur["end_line"] = end_line
            rec["sections"].append(cur)

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()

        new_fence = fence_step(line, fence)
        if new_fence != fence:
            fence = new_fence
            continue
        if fence:
            continue

        head = HEAD_RE.match(line)
        if head:
            level = len(head.group(1))
            explicit_no = head.group(2)
            name = head.group(3).strip()

            if level == 1:
                m = CH_RE.match(line)
                if m and rec["number"] is None:
                    rec["number"] = int(m.group(1))
                    rec["title"] = m.group(2).strip()
                continue

            if mode == "rules":
                flush_rule()
                buf = None
            mode = None

            if RULES_HEAD_RE.match(line):
                close_section(idx)
                cur = None
                mode = "rules"
                continue
            if XREF_HEAD_RE.match(line):
                close_section(idx)
                cur = None
                mode = "xref"
                continue

            if level == 2:
                close_section(idx)
                key = explicit_no if explicit_no else slug(name, 24)
                cur = {
                    "key": key,
                    "number": int(explicit_no) if explicit_no else None,
                    "title": name,
                    "start_line": idx + 1,
                    "end_line": None,
                    "subsections": [],
                }
            elif level == 3 and cur is not None:
                cur["subsections"].append(name)
            continue

        if mode == "rules":
            item = NUM_ITEM_RE.match(line)
            if item:
                flush_rule()
                buf = item.group(2).strip()
            elif not line.strip():
                flush_rule()
                buf = None
            elif buf is not None:
                buf += " " + line.strip()
            continue

        if mode == "xref":
            if line.strip():
                xref_lines.append(line.strip())
            continue

        meta = META_RE.match(line)
        if meta:
            rec[meta.group(1).lower()] = meta.group(2).strip()

    flush_rule()
    close_section(len(lines))
    if xref_lines:
        rec["cross_references"] = " ".join(xref_lines)

    if rec["number"] is None:
        rec["problems"].append("missing or malformed H1 (expected '# Ch <N> — <Title>')")
    if not rec["governs"]:
        rec["problems"].append("missing '**Governs:**' line")
    if not rec["sections"]:
        rec["problems"].append("no '## ' sections found")
    if not rec["rules"]:
        rec["problems"].append("no '## Transferable rules' items found")

    if rec["number"] is not None:
        rec["id"] = "%s-%02d" % (prefix, rec["number"])
    else:
        rec["id"] = "%s-%s" % (prefix, slug(os.path.basename(path), 16))
    return rec


# --- note parsing ------------------------------------------------------------

def parse_note(path, prefix, root=None):
    """Parse a free-form note. Only an H1 is genuinely required."""
    raw = read_text(path)
    meta, body = parse_frontmatter(raw)
    lines = body.split("\n")

    rel = os.path.relpath(path, root or ROOT).replace(os.sep, "/")
    rec = {
        "file": rel,
        "title": meta.get("title"),
        "category": meta.get("category") or _category_from_path(path),
        "source": meta.get("source", "manual"),
        "date": meta.get("date"),
        "authority": meta.get("authority", "derived"),
        "pinned_topics": meta.get("topics") or [],
        "sections": [],
        "rules": [],
        "meta": {k: v for k, v in meta.items()
                 if k not in ("title", "category", "source", "date", "authority", "topics")},
        "problems": [],
    }

    fence = None
    mode = None
    buf = None
    cur = None

    def flush_rule():
        if buf:
            rec["rules"].append(buf.strip())

    def close_section(end_line):
        if cur is not None:
            cur["end_line"] = end_line
            rec["sections"].append(cur)

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        new_fence = fence_step(line, fence)
        if new_fence != fence:
            fence = new_fence
            continue
        if fence:
            continue

        head = HEAD_RE.match(line)
        if head:
            level = len(head.group(1))
            explicit_no = head.group(2)
            name = head.group(3).strip()

            if level == 1:
                if not rec["title"]:
                    rec["title"] = name
                continue

            if mode == "findings":
                flush_rule()
                buf = None
            mode = None

            if FINDINGS_HEAD_RE.match(line):
                close_section(idx)
                cur = None
                mode = "findings"
                continue

            if level == 2:
                close_section(idx)
                cur = {
                    "key": explicit_no if explicit_no else slug(name, 24),
                    "number": int(explicit_no) if explicit_no else None,
                    "title": name,
                    "start_line": idx + 1,
                    "end_line": None,
                    "subsections": [],
                }
            elif level == 3 and cur is not None:
                cur["subsections"].append(name)
            continue

        if mode == "findings":
            item = NUM_ITEM_RE.match(line)
            bullet = BULLET_ITEM_RE.match(line)
            if item:
                flush_rule()
                buf = item.group(2).strip()
            elif bullet:
                flush_rule()
                buf = bullet.group(1).strip()
            elif not line.strip():
                flush_rule()
                buf = None
            elif buf is not None:
                buf += " " + line.strip()
            continue

    flush_rule()
    close_section(len(lines))

    if not rec["title"]:
        rec["title"] = os.path.splitext(os.path.basename(path))[0].replace("-", " ")
        rec["problems"].append("no H1 found; title inferred from filename")
    if not rec["date"]:
        try:
            import datetime
            rec["date"] = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
        except Exception:
            rec["date"] = None

    rec["id"] = "%s-%s" % (prefix, slug(rec["title"], 32))
    return rec


def _category_from_path(path):
    parent = os.path.basename(os.path.dirname(path))
    if parent in ("notes", "knowledge", ""):
        return "general"
    return parent


def looks_like_chapter(text):
    """Cheap detector used by ingest routing."""
    _, body = parse_frontmatter(text)
    has_h1 = False
    has_rules = False
    fence = None
    for line in body.split("\n"):
        new_fence = fence_step(line, fence)
        if new_fence != fence:
            fence = new_fence
            continue
        if fence:
            continue
        if CH_RE.match(line.rstrip()):
            has_h1 = True
        if RULES_HEAD_RE.match(line.rstrip()):
            has_rules = True
    return has_h1 and has_rules


# --- engine indexing ---------------------------------------------------------

def index_engine_file(path, max_level=3):
    """Record every heading with its byte offset so sections can be sliced.

    Byte offsets rather than line numbers because these files reach 18 MB and we
    never want to read one end to end just to reach a symbol.
    """
    entries = []
    offset = 0
    fence = None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            blen = len(line.encode("utf-8"))
            stripped = line.rstrip("\n")
            new_fence = fence_step(stripped, fence)
            if new_fence != fence:
                fence = new_fence
                offset += blen
                continue
            if not fence and stripped.startswith("#"):
                head = HEAD_RE.match(stripped)
                if head:
                    level = len(head.group(1))
                    if level <= max_level:
                        name = head.group(3).strip()
                        symbol = name.split("|")[0].strip()
                        kind = ""
                        parts = [p.strip() for p in name.split("|")]
                        if len(parts) > 1:
                            kind = parts[1]
                        entries.append({
                            "level": level,
                            "name": name,
                            "symbol": symbol,
                            "kind": kind,
                            "line": lineno,
                            "offset": offset,
                        })
            offset += blen
    for i, entry in enumerate(entries):
        entry["end_offset"] = entries[i + 1]["offset"] if i + 1 < len(entries) else offset
    return entries


MANIFEST_ENTRY_RE = re.compile(r"^-\s*\[([^\]]+)\]\(([^)]*)\)\s*:?\s*(.*)$")


def parse_engine_manifest(path):
    """Parse an llms.txt-style curated link list into grouped entries."""
    groups = []
    current = None
    for line in read_text(path).split("\n"):
        line = line.rstrip()
        head = HEAD_RE.match(line)
        if head and len(head.group(1)) == 2:
            current = {"section": head.group(3).strip(), "entries": []}
            groups.append(current)
            continue
        item = MANIFEST_ENTRY_RE.match(line.strip())
        if item and current is not None:
            current["entries"].append({
                "title": item.group(1).strip(),
                "url": item.group(2).strip(),
                "description": item.group(3).strip(),
            })
    return [g for g in groups if g["entries"]]


def read_slice(path, offset, end_offset, max_bytes=40000):
    """Read one indexed section without loading the surrounding file."""
    length = min(end_offset - offset, max_bytes)
    with open(path, "rb") as fh:
        fh.seek(offset)
        blob = fh.read(length)
    text = blob.decode("utf-8", errors="replace")
    if end_offset - offset > max_bytes:
        text += "\n\n[... truncated at %d bytes; pass --max-bytes to extend ...]" % max_bytes
    return text


def approx_tokens(words):
    """Rough words -> tokens factor for prose with markdown scaffolding."""
    return int(words * 1.35)
