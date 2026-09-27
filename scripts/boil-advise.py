#!/usr/bin/env python3
"""boil advise — the advisor corpus (advisor/) as a boil subcommand.

  lookup|check|ingest|build ARGS…   forward verbatim to advisor/scripts/<same>.py (same flags, same exit)
  retire ID --reason R [--by B]      tombstone a rule: hidden from search, still resolvable
  unretire ID                        undo it
  decide --question Q [--project .]  print a decision packet: question, goal excerpt, candidate rules
  record --question Q --verdict V    accept a cited verdict into .boil/decisions.md, or reject it
  sweep [--project .]                apply the vetoes written into .boil/decisions.md

Exit codes: 0 ok · 2 usage / unknown id · 3 rejected or advisor unavailable (the caller escalates
to the human exactly as it would have without the advisor).

BOIL_ADVISOR_ROOT overrides the corpus location (tests point it at a copy).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ADVISOR = Path(os.environ.get("BOIL_ADVISOR_ROOT") or SKILL_ROOT / "advisor")
FORWARD = {"lookup": "lookup.py", "check": "check_citations.py",
           "ingest": "ingest.py", "build": "build_index.py"}
EXIT_OK, EXIT_USAGE, EXIT_REJECT = 0, 2, 3

RULE_ID = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z0-9-]+-R\d+$")
VERDICT = re.compile(r"^ANSWER:\s*(?P<answer>.*?)\s*\|\s*RULES:\s*(?P<rules>.*?)\s*\|\s*WHY:\s*(?P<why>.*)$", re.S)
HEDGE = re.compile(r"\b(depends|either|unclear)\b", re.I)
HEADER = re.compile(r"^## (D-\d{4}) · (\S+) · ticket (\S*)\s*$")
FIELDS = ("question", "answer", "rules", "why", "veto")
NO_VETO = ("–", "-", "")
TICKET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Every character str.splitlines() breaks on: each is escaped so one field stays one line.
BREAKS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"


def _k():
    """advisor's ka_common, imported from the corpus ADVISOR points at (its ROOT follows its file)."""
    path = str(ADVISOR / "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)
    import ka_common as K  # noqa: E402
    return K


def _index_rules(K) -> dict[str, str]:
    """Rule id (upper-case) → domain, across every built index, retired rules included."""
    out = {}
    for dom in K.load_domains():
        path = Path(dom["generated"]) / "index.json"
        if path.exists():
            for r in K.load_json(str(path)).get("rules", []):
                out[r["id"].upper()] = dom["id"]
    return out


def _stored(K, dom: str) -> dict:
    """retired.json as stored: load_retired adds a `domain` key that is not part of the file."""
    return {rid: {k: v for k, v in meta.items() if k != "domain"}
            for rid, meta in K.load_retired(dom).items()}


def cmd_retire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    if not dom:
        print(f"boil advise: unknown rule id {args.id}", file=sys.stderr)
        return EXIT_USAGE
    data = _stored(K, dom)
    data[rid] = {"reason": args.reason, "date": dt.date.today().isoformat(), "by": args.by}
    K.save_retired(dom, data)
    print(f"retired {rid} ({dom}): {args.reason}")
    return EXIT_OK


def cmd_unretire(args) -> int:
    K = _k()
    rid = args.id.upper()
    dom = _index_rules(K).get(rid)
    data = _stored(K, dom) if dom else {}
    if rid not in data:
        print(f"boil advise: {args.id} is not retired", file=sys.stderr)
        return EXIT_USAGE
    del data[rid]
    K.save_retired(dom, data)
    print(f"unretired {rid}")
    return EXIT_OK


# ---- decisions -----------------------------------------------------------------------------

def _boil(project: str) -> Path:
    return Path(project).resolve() / ".boil"


def _qhash(q: str) -> str:
    return hashlib.sha1(" ".join(q.lower().split()).encode()).hexdigest()


def _esc(s: str) -> str:
    s = s.replace("\\", "\\\\")
    return "".join("\\n" if c == "\n" else f"\\u{ord(c):04x}" if c in BREAKS else c for c in s)


def _unesc(s: str) -> str:
    def one(m):
        tok = m.group(1)
        return "\n" if tok == "n" else "\\" if tok == "\\" else chr(int(tok[1:], 16))
    return re.sub(r"\\(\\|n|u[0-9a-f]{4})", one, s)


def _parse(text: str) -> tuple[list[dict], list[str]]:
    """(entries, ids of unparseable entries). Any `## ` line opens an entry; one that is not a
    well-formed header, or lacks a field, is reported and left alone — never guessed at."""
    raw, cur = [], None
    for n, line in enumerate(text.split("\n")):
        if line.startswith("## "):
            m = HEADER.match(line)
            cur = ({"id": m.group(1), "ts": m.group(2), "ticket": m.group(3) or ""} if m
                   else {"id": line[3:].split(" ", 1)[0], "_bad": True})
            raw.append(cur)
        elif cur is not None and ":" in line:
            key, val = line.split(":", 1)
            if key in FIELDS:
                cur[key] = val.strip()
                if key == "veto":
                    cur["_veto_line"] = n
    good, bad = [], []
    for e in raw:
        if e.get("_bad") or not all(k in e for k in FIELDS):
            bad.append(e["id"])
            continue
        for k in ("question", "answer", "why"):
            e[k] = _unesc(e[k])
        e["rules"] = [r.strip() for r in e["rules"].split(",") if r.strip()]
        e["vetoed"] = e["veto"] not in NO_VETO
        e["swept"] = e["veto"].endswith("(swept)")
        good.append(e)
    return good, bad


def parse_decisions(text: str) -> list[dict]:
    """Well-formed `.boil/decisions.md` entries in file order (helm's decisions.py mirrors this)."""
    return _parse(text)[0]


def _goal(project: str) -> tuple[str, list[str]]:
    p = _boil(project) / "goal.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    m = re.search(r"^advisor_domains:\s*(.+)$", text, re.M)
    return text, ([d.strip() for d in m.group(1).split(",") if d.strip()] if m else [])


def _available() -> bool:
    return (ADVISOR / "scripts" / "lookup.py").is_file()


def cmd_decide(args) -> int:
    if not _available():
        print("boil advise: advisor unavailable — escalate as usual", file=sys.stderr)
        return EXIT_REJECT
    K = _k()
    goal, doms = _goal(args.project)
    known = {d["id"] for d in K.load_domains()}
    for d in doms:
        if d not in known:
            print(f"boil advise: advisor_domains names unknown domain `{d}` — ignored", file=sys.stderr)
    doms = [d for d in doms if d in known] or [None]
    print(f"# Decision packet\n\nQuestion: {args.question}\n\n## Goal (excerpt)\n")
    print("\n".join(goal.splitlines()[:40]) or "(no .boil/goal.md)")
    print("\n## Candidate rules\n")
    for d in doms:
        cmd = [sys.executable, str(ADVISOR / "scripts" / "lookup.py"), "--search", args.question,
               "--kind", "rules", "--limit", str(args.limit)] + (["--domain", d] if d else [])
        print(subprocess.run(cmd, capture_output=True, text=True).stdout.rstrip())
    print("\n## Reply with exactly one line\n")
    print("ANSWER: <choice> | RULES: <ID>[, <ID>…] | WHY: <one line tying the rule to the goal>")
    print("ASK-HUMAN: <reason>          (no rule fits, or the rules disagree)")
    ticket = f" --ticket {args.ticket}" if args.ticket else " [--ticket T]"
    print(f'\nThen: boil advise record --question "…" --verdict "<that line>"{ticket}')
    print("A verdict is accepted only if every cited rule exists, is not retired, and no two of")
    print("them sit on opposite sides of a conflicts.md entry; otherwise escalate as usual.")
    return EXIT_OK


def _conflict(K, ids: list[str]) -> tuple[str, str] | None:
    """Two cited IDs on different rows of one `###` entry of a domain's conflicts.md.

    A `###` block ends at the next heading or `---`, so the one-row convergence tables that
    follow the conflict entries are never read as positions."""
    want = set(ids)
    for dom in K.load_domains():
        path = Path(dom["root"]) / "conflicts.md"
        if not path.exists():
            continue
        blocks, cur = [], None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                cur = []
                blocks.append(cur)
            elif line.startswith(("#", "---")):
                cur = None
            elif cur is not None and line.startswith("|"):
                cur.append(set(re.findall(r"`([A-Z][A-Z0-9-]*-R\d+)`", line)) & want)
        for rows in blocks:
            rows = [r for r in rows if r]
            for i, a in enumerate(rows):
                for b in rows[i + 1:]:
                    if a - b and b - a:
                        return sorted(a - b)[0], sorted(b - a)[0]
    return None


def _reject(prefix: str, msg: str) -> int:
    print(f"{prefix}: {msg}", file=sys.stderr)
    return EXIT_REJECT


def _vetoes(project: str) -> list[dict]:
    p = _boil(project) / "advisor-vetoes.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def cmd_record(args) -> int:
    v = args.verdict.strip()
    if v.upper().startswith("ASK-HUMAN"):
        return _reject("ask-human", v)
    m = VERDICT.match(v)
    if not m:
        return _reject("malformed", "expected `ANSWER: … | RULES: … | WHY: …`")
    answer, why = m.group("answer").strip(), m.group("why").strip()
    ids = [s.strip().upper() for s in m.group("rules").split(",") if s.strip()]
    if not ids or any(not RULE_ID.match(x) for x in ids):
        bad = ", ".join(x for x in ids if not RULE_ID.match(x)) or "none"
        return _reject("no-rule", f"cite rule IDs only (chapters and sections do not count): {bad}")
    boil = _boil(args.project)
    tpath = None
    if args.ticket:
        if not TICKET_ID.match(args.ticket):
            return _reject("malformed", f"bad ticket id {args.ticket!r}")
        tpath = _ticket_file(boil, args.ticket)
        if not tpath:
            return _reject("not-advisable", f"no ticket {args.ticket}")
        why_not = _advisable(tpath)
        if why_not:
            return _reject("not-advisable", f"{args.ticket}: {why_not}")
    if not _available():
        return _reject("unavailable", "advisor unavailable")
    K = _k()
    index = _index_rules(K)
    unknown = [x for x in ids if x not in index]
    if unknown:
        return _reject("unknown", ", ".join(unknown))
    retired = K.load_retired()
    gone = [x for x in ids if x in retired]
    if gone:
        return _reject("retired", ", ".join(gone))
    pair = _conflict(K, ids)
    if pair:
        return _reject("conflict", f"{pair[0]} vs {pair[1]} (see conflicts.md)")
    if not answer or HEDGE.search(answer):
        return _reject("hedged", "the answer must be a choice")
    qh = _qhash(args.question)
    if any(v.get("q") == qh or (args.ticket and v.get("ticket") == args.ticket) for v in _vetoes(args.project)):
        return _reject("vetoed", "the user vetoed an advisor answer to this question or ticket before")

    dpath = boil / "decisions.md"
    prior = dpath.read_text(encoding="utf-8") if dpath.exists() else ""
    n = len(re.findall(r"^## D-\d{4}", prior, re.M)) + 1
    did = f"D-{n:04d}"
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    entry = (f"## {did} · {ts} · ticket {args.ticket}\nquestion: {_esc(args.question)}\n"
             f"answer: {_esc(answer)}\nrules: {', '.join(ids)}\nwhy: {_esc(why)}\nveto: –\n\n")
    if [e["id"] for e in _parse(entry)[0]] != [did]:
        return _reject("malformed", "the entry would not read back; nothing written")
    with open(dpath, "a", encoding="utf-8") as f:
        f.write(entry)
    if tpath:
        _set_ticket(tpath, advised=did)
    _emit(args.project, args.no_log, "boil.advised", f"{did}: {answer[:80]} [{', '.join(ids)}]")
    print(f"{did} recorded: {answer}")
    return EXIT_OK


def _ticket_file(boil: Path, ticket: str) -> Path | None:
    """The ticket's file: exactly `<id>.md` or `<id>-<slug>.md`, never a longer id sharing a prefix."""
    tdir = boil / "tickets"
    if not tdir.is_dir() or not TICKET_ID.match(ticket or ""):
        return None
    hits = sorted([*tdir.glob(f"{ticket}.md"), *tdir.glob(f"{ticket}-*.md")])
    return hits[0] if hits else None


def _split(text: str) -> tuple[list[str], list[str]] | None:
    """(frontmatter lines, rest) — None when the file has no `---` frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[:i + 1], lines[i + 1:]
    return None


def _ha_block(fm: list[str]) -> tuple[int, int] | None:
    """[start, end) of the `human_action:` block in the frontmatter, start being the key line."""
    for i, line in enumerate(fm):
        if line.rstrip() == "human_action:":
            j = i + 1
            while j < len(fm) - 1 and fm[j].startswith((" ", "\t")):
                j += 1
            return i, j
    return None


def _advisable(path: Path) -> str:
    """Empty when the ticket is a human-action ticket marked `kind: decision`; else why not."""
    parts = _split(path.read_text(encoding="utf-8"))
    if not parts:
        return "no frontmatter"
    fm = parts[0]
    if not any(re.match(r"^type:\s*human-action\s*$", ln) for ln in fm):
        return "not a human-action ticket"
    blk = _ha_block(fm)
    if not blk or not any(re.match(r"^\s+kind:\s*decision\s*$", ln) for ln in fm[blk[0] + 1:blk[1]]):
        return "not `kind: decision` — brakes, credentials and access stay with the user"
    return ""


def _set_ticket(path: Path, *, advised: str = "", reopen: bool = False) -> bool:
    """Flip a human-action ticket: advised → open and not required; reopened → blocked and required.
    Only the frontmatter's top-level `status:` and the `human_action:` block are touched."""
    text = path.read_text(encoding="utf-8")
    parts = _split(text)
    blk = _ha_block(parts[0]) if parts else None
    if not blk:
        return False
    fm, rest = parts
    status, required = ("blocked", "true") if reopen else ("open", "false")
    fm = [f"status: {status}" if re.match(r"^status:", ln) else ln for ln in fm]
    head, block, tail = fm[:blk[0] + 1], fm[blk[0] + 1:blk[1]], fm[blk[1]:]
    block = [f"  required: {required}" if re.match(r"^\s+required:", ln) else ln for ln in block]
    if advised:
        block = [f"  advised: {advised}"] + [ln for ln in block if not re.match(r"^\s+advised:", ln)]
    path.write_text("\n".join(head + block + tail + rest), encoding="utf-8")
    return True


def _emit(project: str, quiet: bool, kind: str, detail: str) -> None:
    """Best-effort helm event; a logging failure never changes the outcome."""
    script = SKILL_ROOT / "scripts" / "boil-helm-log.py"
    if quiet or not script.exists():
        return
    try:
        subprocess.run([sys.executable, str(script), "emit", "--root", str(Path(project).resolve()),
                        "--kind", kind, "--detail", detail], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def cmd_sweep(args) -> int:
    boil = _boil(args.project)
    dpath = boil / "decisions.md"
    if not dpath.exists():
        print("0 reopened")
        return EXIT_OK
    text = dpath.read_text(encoding="utf-8")
    entries, bad = _parse(text)
    for b in bad:
        print(f"boil advise: skipped unparseable entry {b}", file=sys.stderr)
    todo = [e for e in entries if e["vetoed"] and not e["swept"]]
    if not todo:
        print("0 reopened")
        return EXIT_OK
    vetoes, reopened = _vetoes(args.project), 0
    lines = text.split("\n")
    for e in todo:
        tpath = _ticket_file(boil, e["ticket"]) if e["ticket"] else None
        if tpath and _set_ticket(tpath, reopen=True):
            reopened += 1
        key = {"q": _qhash(e["question"]), "rules": sorted(e["rules"]), "ticket": e["ticket"]}
        if key not in vetoes:
            vetoes.append(key)
        lines[e["_veto_line"]] = f"veto: {e['veto']} (swept)"
    text = "\n".join(lines)
    _atomic(boil / "advisor-vetoes.json", json.dumps(vetoes, indent=2) + "\n")
    _atomic(dpath, text)
    print(f"{reopened} reopened")
    return EXIT_OK


def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str]) -> int:
    if argv and argv[0] in FORWARD:
        script = ADVISOR / "scripts" / FORWARD[argv[0]]
        return subprocess.run([sys.executable, str(script), *argv[1:]]).returncode
    ap = argparse.ArgumentParser(prog="boil advise", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("retire", help="tombstone a rule")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.add_argument("--by", default="cli")
    p.set_defaults(fn=cmd_retire)
    p = sub.add_parser("unretire", help="undo a retire")
    p.add_argument("id")
    p.set_defaults(fn=cmd_unretire)
    p = sub.add_parser("decide", help="print a decision packet")
    p.add_argument("--question", required=True)
    p.add_argument("--ticket", default="", help="echoed into the record command")
    p.add_argument("--project", default=".")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_decide)
    p = sub.add_parser("record", help="accept or reject a cited verdict")
    p.add_argument("--question", required=True)
    p.add_argument("--verdict", required=True)
    p.add_argument("--ticket", default="")
    p.add_argument("--project", default=".")
    p.add_argument("--no-log", action="store_true")
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("sweep", help="apply vetoes from .boil/decisions.md")
    p.add_argument("--project", default=".")
    p.set_defaults(fn=cmd_sweep)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
