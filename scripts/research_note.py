#!/usr/bin/env python3
"""Turn a hyperresearch final report into an advisor inbox note.

    python3 scripts/research_note.py --report path/to/final_report.md \
            [--question "..."] [--category research] [--topics a,b] \
            [--domain trading] [--dry-run] [--out inbox/]

    python3 scripts/research_note.py --run <vault_tag> [--research-root ~/.advisor-research] ...

`--report` takes an explicit path and always works. `--run` is convenience: it
resolves `<research-root>/research/runs/<tag>/final_report.md` and, if present,
reads the question from `<...>/query.md`.

The note is written in the `notes` contract from FORMAT.md so `scripts/ingest.py`
files it and its findings become citable `derived` rules. Findings headings the
indexer already recognises as a synonym (Findings, Recommendations, Takeaways,
Key takeaways, Conclusions, Transferable rules) are renamed to the canonical
`## Key findings` for consistency; a report with no such section is filed anyway,
with a warning that no rules will be created.
"""

import argparse
import datetime
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K          # noqa: E402
from ingest import render_frontmatter, unique_path  # noqa: E402

H1_RE = re.compile(r"^#\s+(.+?)\s*$")


def find_h1(text):
    """First level-1 heading in the text, or None."""
    for line in text.split("\n"):
        m = H1_RE.match(line.rstrip())
        if m:
            return m.group(1).strip()
    return None


def sanitize_scalar(value):
    """Make `value` safe as a `key: value` line for `ka_common.parse_frontmatter`.

    A colon or a `#` in the middle of the value already round-trips fine: the
    parser splits the key off at the *first* colon only, and only a line whose
    first non-space character is `#` is treated as a comment. The one shape
    that genuinely breaks is a value that itself looks like an inline list
    (`[...]`) or that is empty — those get quoted so the parser's list check
    and its accompanying `strip("'\\"")` see plain text instead.
    """
    value = " ".join(str(value).split())  # collapse newlines/whitespace to one line
    looks_like_list = value.startswith("[") and value.endswith("]")
    if not value or looks_like_list:
        return '"%s"' % value.replace('"', "'")
    return value


def normalize_findings_heading(body):
    """Rename the first recognised findings heading to the canonical spelling.

    Returns (new_body, found). `ka_common.FINDINGS_HEAD_RE` is the indexer's own
    recogniser (Key findings, Findings, Transferable rules, Recommendations,
    Takeaways, Key takeaways, Conclusions) -- imported rather than re-listed so
    this can never drift from what actually becomes rules.
    """
    lines = body.split("\n")
    fence = None
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        new_fence = K.fence_step(stripped, fence)
        if new_fence != fence:
            fence = new_fence
            continue
        if fence:
            continue
        m = K.FINDINGS_HEAD_RE.match(stripped)
        if m:
            hashes = re.match(r"^(#{2,4})", stripped).group(1)
            lines[i] = "%s Key findings" % hashes
            return "\n".join(lines), True
    return body, False


def compute_rules(title, body):
    """Rules that would be extracted, via the same parser build_index.py uses.

    Writes a throwaway note to a temp file rather than re-implementing the
    numbered/bulleted-item walk, so this can never disagree with what actually
    gets indexed.
    """
    text = "# %s\n\n%s" % (title, body)
    fd, path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        rec = K.parse_note(path, "NOTE", root=K.ROOT)
    finally:
        os.remove(path)
    return rec["id"], rec["rules"]


def build_meta(title, category, topics, run_tag, question, domain, date=None):
    meta = {
        "title": sanitize_scalar(title),
        "category": sanitize_scalar(category or "research"),
        "source": "hyperresearch",
        "date": date or datetime.date.today().isoformat(),
        "authority": "derived",
    }
    if topics:
        items = topics if isinstance(topics, list) else [t.strip() for t in topics.split(",")]
        items = [t for t in items if t]
        if items:
            meta["topics"] = items
    if run_tag:
        meta["run"] = sanitize_scalar(run_tag)
    if question:
        meta["question"] = sanitize_scalar(question)
    if domain:
        meta["domain"] = sanitize_scalar(domain)
    return meta


def resolve_report_path(args):
    """Return (report_path, run_dir). run_dir is None unless --run was used."""
    if args.report:
        return args.report, None
    root = os.path.expanduser(args.research_root)
    run_dir = os.path.join(root, "research", "runs", args.run)
    return os.path.join(run_dir, "final_report.md"), run_dir


def resolve_question(args, run_dir):
    if args.question:
        return args.question
    if run_dir:
        query_path = os.path.join(run_dir, "query.md")
        if os.path.exists(query_path):
            return " ".join(K.read_text(query_path).split())
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--report", help="path to a hyperresearch final_report.md")
    src.add_argument("--run", help="vault tag; resolves the report under --research-root")
    ap.add_argument("--research-root", default="~/.advisor-research",
                    help="root that holds research/runs/<tag>/ (used with --run)")
    ap.add_argument("--question", help="the research question, for provenance")
    ap.add_argument("--title", help="override the note title (default: the report's H1)")
    ap.add_argument("--category", default="research", help="notes category (default: research)")
    ap.add_argument("--topics", help="comma-separated topics; omit to let the indexer infer them")
    ap.add_argument("--domain", help="informational only; recorded as frontmatter metadata")
    ap.add_argument("--out", default="inbox", help="directory to write the note into (default: inbox/)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print frontmatter and the would-be rules; write nothing")
    ap.add_argument("--require-findings", action="store_true",
                    help="exit non-zero if the report has no findings section")
    args = ap.parse_args(argv)

    report_path, run_dir = resolve_report_path(args)
    if not os.path.exists(report_path):
        sys.exit("no report at %s" % report_path)

    text = K.read_text(report_path)
    meta_in, body = K.parse_frontmatter(text)

    title = args.title or meta_in.get("title") or find_h1(body) or find_h1(text)
    if not title:
        sys.exit("report has no H1 and no --title was given; the note contract requires a title")

    body, found_findings = normalize_findings_heading(body)
    note_id, rules = compute_rules(title, body)

    question = resolve_question(args, run_dir)
    run_tag = args.run

    meta = build_meta(title, args.category, args.topics, run_tag, question, args.domain)

    if not found_findings:
        msg = "warning: no findings section found in %s; no rules will be created" % report_path
        print(msg, file=sys.stderr)
        if args.require_findings:
            sys.exit(1)

    if args.dry_run:
        print(render_frontmatter(meta).rstrip())
        print()
        if rules:
            print("would-be rules:")
            for n, text in enumerate(rules, 1):
                print("  %s-R%d: %s" % (note_id, n, text))
        else:
            print("would-be rules: none")
        return 0

    os.makedirs(args.out, exist_ok=True)
    date_prefix = meta["date"]
    base = "%s-%s" % (date_prefix, K.slug(title, 50))
    dest = unique_path(args.out, base)
    K.write_text(dest, render_frontmatter(meta) + body.lstrip("\n"))
    print("wrote %s" % dest)
    if rules:
        print("%d rule(s) will be created on ingest: %s-R1..R%d" % (len(rules), note_id, len(rules)))
    else:
        print("no rules will be created (no findings section)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
