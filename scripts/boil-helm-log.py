#!/usr/bin/env python3
"""boil-helm-log — the boil session's status logger, and its bridge into helm.

Two audiences, one write path:

  * the operator watching now  → helm's dashboard / `helm boil`, updated on every transition
  * the operator reading later → `.boil/status.jsonl` (append-only) + `.boil/STATUS.md`

The project-local files are ALWAYS written — boil never depends on helm being
installed. When helm is present the same snapshot is upserted into helm's session
store (`runs/boil/<session_id>.json`) and each transition is appended to helm's
chronological event log, so a boil session shows up as a first-class helm object
next to the goals it is burning down.

The on-disk contract with helm is deliberately files, not imports: both repos read
and write plain JSON in known places, so either can be upgraded alone.

Commands
  emit     append one status event, then re-sync the snapshot
  sync     rebuild the snapshot from .boil/ state (idempotent; safe to spam)
  session  print the current snapshot
  link     record the helm contract stem this session burns down

Layout written
  <project>/.boil/status.jsonl        append-only event log (canonical, project-local)
  <project>/.boil/STATUS.md           rendered operator overview
  <project>/.boil/session.json        the snapshot + session identity
  $HELM_DIR/runs/boil/<session>.json  the same snapshot, for helm's dashboard/CLI
  $HELM_DIR/runs/events/<YYYY-MM>.jsonl   one line per transition (kind: boil.*)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

MAX_EVENTS_IN_SNAPSHOT = 60
JUDGE_EXCERPT_CHARS = 1500


# ---------- helpers ----------------------------------------------------------


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _append_line(path: Path, line: str) -> None:
    """One O_APPEND write — the kernel serializes it, so parallel subagents and the
    orchestrator can all log without a lock. Same mechanism helm's event log uses."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def _frontmatter(path: Path) -> dict[str, Any]:
    if yaml is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            return {}
        end = text.find("\n---", 4)
        if end == -1:
            return {}
        meta = yaml.safe_load(text[4:end]) or {}
        return meta if isinstance(meta, dict) else {}
    except Exception:  # noqa: BLE001 — a malformed ticket must not break status logging
        return {}


def helm_dir() -> Path | None:
    """Where helm lives, or None. Explicit env wins; then the conventional checkouts."""
    env = os.environ.get("HELM_DIR")
    candidates = [Path(env)] if env else []
    candidates += [Path.home() / "workspace" / "helm", Path.home() / "wp" / "helm"]
    for c in candidates:
        if any((c / f).exists() for f in ("helm.py", "server.py", "helm_mcp.py")):   # v1 or v2 checkout
            return c
    return None


def helm_events_dir(hd: Path) -> Path:
    env = os.environ.get("HELM_EVENTS_DIR")
    return Path(env) if env else hd / "runs" / "events"


# ---------- session identity -------------------------------------------------


def _run_md_field(root: Path, field: str) -> str:
    p = root / ".boil" / "run.md"
    if not p.exists():
        return ""
    m = re.search(rf"^\s*[-*]?\s*{re.escape(field)}\s*:\s*(.+)$",
                  p.read_text(encoding="utf-8", errors="replace"), re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip().strip("`") if m else ""


def session_identity(root: Path, stem: str = "") -> dict[str, str]:
    """Stable per boil session. Persisted on first use so every later call — including
    ones from parallel subagents — lands on the same session object."""
    sp = root / ".boil" / "session.json"
    prior: dict[str, Any] = {}
    if sp.exists():
        try:
            prior = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prior = {}
    sid = (os.environ.get("BOIL_SESSION_ID") or prior.get("session_id")
           or f"boil-{root.name}-{time.strftime('%Y%m%d-%H%M%S')}")
    resolved_stem = (stem or os.environ.get("HELM_STEM") or prior.get("stem")
                     or _run_md_field(root, "helm_stem"))
    return {
        "session_id": sid,
        "stem": resolved_stem,
        "started_at": prior.get("started_at") or _now(),
    }


# ---------- reading .boil/ state --------------------------------------------


def _goal_progress(root: Path) -> dict[str, Any]:
    p = root / ".boil" / "goal.md"
    if not p.exists():
        return {"one_line": "", "green": 0, "total": 0, "checkboxes": []}
    text = p.read_text(encoding="utf-8", errors="replace")
    one = ""
    m = re.search(r"^\*\*One-line:\*\*\s*(.+)$", text, re.MULTILINE)
    if m:
        one = m.group(1).strip()
    boxes = [{"done": mark.lower() == "x", "text": label.strip()}
             for mark, label in re.findall(r"^\s*-\s*\[([ xX])\]\s*(.+)$", text, re.MULTILINE)]
    return {"one_line": one, "green": sum(1 for b in boxes if b["done"]),
            "total": len(boxes), "checkboxes": boxes[:40]}


def _loops(root: Path) -> dict[str, dict[str, Any]]:
    base = root / ".boil" / "loops"
    out: dict[str, dict[str, Any]] = {}
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        lp = d / "loop.json"
        if not lp.exists():
            continue
        try:
            loop = json.loads(lp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        # Attach the judge's reasoning so the dashboard can show WHY, not just the verdict.
        for att in loop.get("attempts", []):
            jf = d / f"attempt-{att.get('n')}" / "judge.md"
            if jf.exists():
                try:
                    att["judge_excerpt"] = jf.read_text(encoding="utf-8",
                                                        errors="replace")[:JUDGE_EXCERPT_CHARS]
                except Exception:  # noqa: BLE001
                    pass
        esc = d / "escalation.md"
        if esc.exists():
            try:
                loop["escalation"] = esc.read_text(encoding="utf-8", errors="replace")[:4000]
            except Exception:  # noqa: BLE001
                pass
        out[loop.get("ticket", d.name)] = loop
    return out


def _tickets(root: Path, loops: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    tdir = root / ".boil" / "tickets"
    rows: list[dict[str, Any]] = []
    if not tdir.is_dir():
        return rows
    for tp in sorted(tdir.glob("T-*.md")):
        meta = _frontmatter(tp)
        tid = str(meta.get("id") or tp.stem)
        key = meta.get("answer_key") if isinstance(meta.get("answer_key"), dict) else {}
        loop = loops.get(tid, {})
        atts = [a for a in loop.get("attempts", []) if a.get("verdict")]
        last = loop.get("attempts", [])[-1] if loop.get("attempts") else {}
        rows.append({
            "id": tid,
            "title": str(meta.get("title") or ""),
            "type": str(meta.get("type") or ""),
            "specialty": str(meta.get("specialty") or ""),
            "status": str(meta.get("status") or ""),
            "priority": str(meta.get("priority") or ""),
            "working_on": str(meta.get("working_on") or ""),
            "proof_strategy": str(meta.get("proof_strategy") or ""),
            "closes_goal_checkbox": meta.get("closes_goal_checkbox") or [],
            "closes_stories": meta.get("closes_stories") or [],
            "answer_key": {"kind": key.get("kind", ""), "ref": key.get("ref", ""),
                           "authored_by": key.get("authored_by", ""),
                           "frozen_sha": key.get("frozen_sha", "")},
            "loop": {
                "status": loop.get("status", ""),
                "attempts": len(atts),
                "max_revisions": loop.get("max_revisions", 0),
                "last_verdict": last.get("verdict", ""),
                "last_decision": last.get("decision", ""),
                "last_reason": last.get("reason", ""),
                "defect": last.get("judge_reason", ""),
                "failure_signature": last.get("failure_signature", ""),
                "terminal_reason": loop.get("terminal_reason", ""),
                "trail": [
                    {"n": a.get("n"), "verdict": a.get("verdict", ""),
                     "decision": a.get("decision", ""), "reason": a.get("reason", ""),
                     "defect": a.get("judge_reason", ""),
                     "signature": a.get("failure_signature", ""),
                     "key_integrity": a.get("key_integrity", ""),
                     "builder_family": a.get("builder_family", ""),
                     "judge_family": a.get("judge_family", ""),
                     "judge_excerpt": a.get("judge_excerpt", "")}
                    for a in loop.get("attempts", [])
                ],
                "escalation": loop.get("escalation", ""),
            } if loop else {},
            "human_action": meta.get("human_action") or {},
        })
    return rows


def _events(root: Path, limit: int = MAX_EVENTS_IN_SNAPSHOT) -> list[dict[str, Any]]:
    p = root / ".boil" / "status.jsonl"
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001 — a torn line never breaks the read
            continue
    return rows[::-1]  # newest first


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


def _milestones(root: Path) -> list[dict[str, Any]]:
    """The controller's DAG with each node's attempt history (frozen.json + attempts.jsonl)."""
    checks = root / ".boil" / "checks"
    if not (checks / "frozen.json").is_file():
        return []
    try:
        frozen = json.loads((checks / "frozen.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    ledger = _jsonl(checks / "attempts.jsonl")
    out = []
    for m in frozen.get("milestones", []):
        recs = [a for a in ledger if a.get("milestone") == m.get("id")]
        out.append({
            "id": m.get("id", "?"), "title": m.get("title", ""), "tier": m.get("tier", ""),
            "kind": m.get("kind", ""), "must_have": bool(m.get("must_have", True)),
            "after": list(m.get("after", [])),
            "attempts": max([int(a.get("attempt", 0) or 0) for a in recs], default=0),
            "result": recs[-1].get("result", "-") if recs else "-",
            "counterexample": next((a.get("counterexample", "") for a in reversed(recs) if a.get("counterexample")), ""),
            "spend_usd": round(sum(float(a.get("spent_usd", 0) or 0) for a in recs), 4),
        })
    return out


def _iteration_state(root: Path) -> tuple[str, bool]:
    """(`<M>#<attempt>`, in_flight) from the controller's iteration.json, or ('', False)."""
    p = root / ".boil" / "checks" / "iteration.json"
    if not p.is_file():
        return "", False
    try:
        it = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "", False
    if not it.get("milestone"):
        return "", False
    return f"{it['milestone']}#{it.get('attempt', 0)}", not it.get("scored")


def _current_iteration(root: Path) -> str:
    explicit = _run_md_field(root, "Current iteration")
    if explicit:
        return explicit
    iters = root / ".boil" / "iterations"
    if iters.is_dir():
        dirs = sorted(d.name for d in iters.iterdir() if d.is_dir() and d.name.startswith("iter-"))
        if dirs:
            return dirs[-1]
    return ""


def build_snapshot(root: Path, stem: str = "") -> dict[str, Any]:
    ident = session_identity(root, stem)
    loops = _loops(root)
    tickets = _tickets(root, loops)
    goal = _goal_progress(root)
    milestones = _milestones(root)
    ctrl_iteration, in_flight = _iteration_state(root)
    iteration = ctrl_iteration or _current_iteration(root)
    events = _events(root)

    blockers = [
        {"ticket": t["id"], "title": t["title"],
         "safe_summary": str((t.get("human_action") or {}).get("safe_summary") or ""),
         "reason": t["loop"].get("terminal_reason", "") if t.get("loop") else ""}
        for t in tickets
        if t["status"] == "blocked" or (t.get("loop") or {}).get("status") in {"escalated", "aborted"}
    ]
    decisions = [
        {"ticket": t["id"], "attempt": a["n"], "verdict": a["verdict"],
         "decision": a["decision"], "reason": a["reason"], "defect": a["defect"]}
        for t in tickets for a in (t.get("loop") or {}).get("trail", [])
        if a.get("decision")
    ][-40:]

    active = [t for t in tickets if t["status"] == "in-progress"]
    must = [m for m in milestones if m["must_have"]]
    ms_green = sum(1 for m in must if m["result"] == "PASS")
    ms_stopped = [m for m in milestones if m["result"] in {"STALL", "CAP", "TAMPER", "BUDGET"}]
    if blockers or ms_stopped:
        status = "blocked"
    elif (goal["total"] and goal["green"] >= goal["total"]) or (must and ms_green == len(must)):
        status = "done"
    elif in_flight or active or any((t.get("loop") or {}).get("status") == "running" for t in tickets):
        status = "running"
    else:
        status = "idle"
    for m in ms_stopped:
        blockers.append({"ticket": m["id"], "title": m["title"], "safe_summary": m["counterexample"][:200],
                         "reason": f"controller verdict {m['result']} — the user decides"})

    demo = ""
    if iteration and (root / ".boil" / "iterations" / iteration / "demo.md").exists():
        demo = f".boil/iterations/{iteration}/demo.md"

    return {
        "session_id": ident["session_id"],
        "stem": ident["stem"],
        "project": str(root),
        "project_name": root.name,
        "goal": goal["one_line"],
        "started_at": ident["started_at"],
        "updated_at": _now(),
        "status": status,
        "iteration": iteration,
        "goal_progress": {"green": goal["green"], "total": goal["total"]},
        "checkboxes": goal["checkboxes"],
        "milestones": milestones,
        "tickets": tickets,
        "decisions": decisions,
        "blockers": blockers,
        "events": events,
        "demo": demo,
        "counts": {
            "milestones": len(must),
            "milestones_green": ms_green,
            "tickets": len(tickets),
            "open": sum(1 for t in tickets if t["status"] == "open"),
            "in_progress": len(active),
            "done": sum(1 for t in tickets if t["status"] == "done"),
            "loops_running": sum(1 for l in loops.values() if l.get("status") == "running"),
            "loops_escalated": sum(1 for l in loops.values()
                                   if l.get("status") in {"escalated", "aborted"}),
        },
    }


# ---------- rendering --------------------------------------------------------


def render_status_md(snap: dict[str, Any]) -> str:
    g, c = snap["goal_progress"], snap["counts"]
    glyph = {"running": "🔄", "blocked": "🙋", "done": "✅", "idle": "·"}
    lines = [
        f"# boil status — {snap['project_name']}",
        "",
        f"_generated {snap['updated_at']} · session `{snap['session_id']}`"
        + (f" · helm goal `{snap['stem']}`" if snap["stem"] else "") + "_",
        "",
        f"**{glyph.get(snap['status'], '·')} {snap['status']}** · iteration "
        f"`{snap['iteration'] or 'none'}` · goal {g['green']}/{g['total']} green · "
        f"tickets {c['done']} done / {c['in_progress']} in progress / {c['open']} open",
        "",
        f"**Goal:** {snap['goal'] or '(see .boil/goal.md)'}",
        "",
    ]
    if snap["blockers"]:
        lines += ["## 🙋 Waiting on you", ""]
        for b in snap["blockers"]:
            lines.append(f"- **{b['ticket']}** — {b['safe_summary'] or b['title']}"
                         + (f"  \n  _{b['reason']}_" if b["reason"] else ""))
        lines.append("")

    if snap.get("milestones"):
        lines += ["## Milestones (the controller's ruler)", "",
                  f"{c['milestones_green']}/{c['milestones']} must-have green", "",
                  "| Milestone | Tier | Attempts | Result | Spend | Last counterexample |",
                  "|---|---|---:|---|---:|---|"]
        for m in snap["milestones"]:
            ce = (m["counterexample"] or "")[:70].replace("|", "\\|")
            lines.append(f"| {m['id']} | {m['tier']} | {m['attempts']} | {m['result']} | ${m['spend_usd']:.2f} | {ce} |")
        lines.append("")

    live = [t for t in snap["tickets"] if t["status"] in {"in-progress", "blocked"}
            or (t.get("loop") or {}).get("status") == "running"]
    if live:
        lines += ["## What the loop is doing right now", "",
                  "| Ticket | Status | Working on | Loop | Answer key |",
                  "|---|---|---|---|---|"]
        for t in live:
            lp = t.get("loop") or {}
            loop_cell = (f"{lp.get('attempts', 0)}/{lp.get('max_revisions', 0)} "
                         f"{lp.get('last_verdict', '')}" if lp else "—")
            key = t["answer_key"]
            key_cell = f"`{key['kind']}` {key['ref'][:44]}" if key.get("kind") else "—"
            lines.append(f"| {t['id']} | {t['status']} | {t['working_on'][:60] or '—'} "
                         f"| {loop_cell} | {key_cell} |")
        lines.append("")

    if snap["decisions"]:
        lines += ["## Recent manager decisions", ""]
        for d in snap["decisions"][-12:][::-1]:
            lines.append(f"- `{d['ticket']}` attempt {d['attempt']}: **{d['verdict']}** → "
                         f"**{d['decision']}** — {d['reason']}")
            if d.get("defect") and d["verdict"] != "PASS":
                lines.append(f"  - defect: {d['defect']}")
        lines.append("")

    if snap["events"]:
        lines += ["## Event log (newest first)", "", "```"]
        for e in snap["events"][:25]:
            lines.append(f"{e.get('ts', ''):20} {e.get('kind', ''):24} "
                         f"{e.get('ticket', ''):9} {e.get('status', ''):14} {e.get('detail', '')}"
                         .rstrip())
        lines += ["```", ""]

    if snap["demo"]:
        lines += [f"**Latest demo:** `{snap['demo']}`", ""]
    return "\n".join(lines)


# ---------- writes -----------------------------------------------------------


PHASE_BY_KIND = {"boil.session.start": "bootstrap", "boil.prepare": "attempt", "boil.score": "verdict",
                 "boil.iteration.gates": "gates", "boil.demo": "demo", "boil.blocker": "blocked"}
SHELL_MAX_EVENTS = 200


def _upsert_shell_session(hd: Path, snap: dict[str, Any], event: dict[str, Any] | None) -> None:
    """The cockpit's shell-session row: runs/sessions/<project>.json (+ .jsonl), in the schema
    helm_mcp.py writes for `helm_status`, so a controller-driven session shows up on the
    dashboard without the LLM calling any tool. Same flock + tmp/replace protocol; the
    operator-owned MCP fields (demo, blocked) are never touched here."""
    import fcntl
    import tempfile
    d = hd / "runs" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    name = snap["project_name"]
    jp = d / f"{name}.json"
    lock_fd = os.open(d / f"{name}.lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            s = json.loads(jp.read_text(encoding="utf-8")) if jp.is_file() else {}
        except (OSError, ValueError):
            s = {}
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000000Z"
        s.setdefault("project", name)
        s["path"] = snap["project"]
        s.setdefault("started", ts)
        s["updated"] = ts
        s["iteration"] = snap.get("iteration") or s.get("iteration")
        s["session"] = snap["session_id"]
        s["goal"] = snap.get("goal") or s.get("goal")
        s["progress"] = f"{snap['counts'].get('milestones_green', 0)}/{snap['counts'].get('milestones', 0)} milestones" \
            if snap["counts"].get("milestones") else f"{snap['goal_progress']['green']}/{snap['goal_progress']['total']} boxes"
        if event:
            kind = event.get("kind", "boil.event")
            text = " ".join(str(x) for x in (kind, event.get("ticket"), event.get("status"), event.get("detail")) if x)
            s["message"] = text[:500]
            s["phase"] = PHASE_BY_KIND.get(kind, kind.split(".")[1] if "." in kind else "loop")
            if event.get("ticket"):
                s["ticket"] = event["ticket"]
            ev = {"ts": ts, "kind": kind, "text": text[:500]}
            s["events"] = (s.get("events") or [])[-(SHELL_MAX_EVENTS - 1):] + [ev]
            fd_, tmp_name = tempfile.mkstemp(dir=d, prefix=f".{name}.", suffix=".json.tmp")
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd_, "w") as f:
                    f.write(json.dumps(s, indent=1))
                os.replace(tmp, jp)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
            _append_line(d / f"{name}.jsonl", json.dumps({**ev, "project": name}) + "\n")
        else:
            s.setdefault("message", snap.get("status", ""))
            s.setdefault("phase", "sync")
            fd_, tmp_name = tempfile.mkstemp(dir=d, prefix=f".{name}.", suffix=".json.tmp")
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd_, "w") as f:
                    f.write(json.dumps(s, indent=1))
                os.replace(tmp, jp)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def push_to_helm(snap: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, str]:
    """Upsert the session object + append the transition to helm's event log.
    Never raises: helm being absent, moved, or mid-upgrade must not break a boil run."""
    result = {"session": "skipped", "event": "skipped", "helm_dir": ""}
    hd = helm_dir()
    if hd is None:
        return result
    result["helm_dir"] = str(hd)
    try:
        _atomic_write(hd / "runs" / "boil" / f"{snap['session_id']}.json",
                      json.dumps(snap, indent=2, default=str) + "\n")
        result["session"] = "written"
    except Exception as exc:  # noqa: BLE001
        result["session"] = f"failed: {exc}"
    try:
        _upsert_shell_session(hd, snap, event)
        result["shell"] = "written"
    except Exception as exc:  # noqa: BLE001
        result["shell"] = f"failed: {exc}"
    if event:
        try:
            ts = event.get("ts") or _now()
            rec = {"ts": ts, "kind": event.get("kind", "boil.event"),
                   "stem": snap.get("stem", ""), "session": snap["session_id"],
                   "project": snap["project_name"]}
            for k in ("ticket", "attempt", "status", "detail"):
                if event.get(k):
                    rec[k] = event[k]
            _append_line(helm_events_dir(hd) / f"{ts[:7]}.jsonl", json.dumps(rec, default=str) + "\n")
            result["event"] = "written"
        except Exception as exc:  # noqa: BLE001
            result["event"] = f"failed: {exc}"
    return result


def sync(root: Path, stem: str = "", event: dict[str, Any] | None = None,
         no_helm: bool = False) -> tuple[dict[str, Any], dict[str, str]]:
    snap = build_snapshot(root, stem)
    _atomic_write(root / ".boil" / "session.json", json.dumps(snap, indent=2, default=str) + "\n")
    _atomic_write(root / ".boil" / "STATUS.md", render_status_md(snap))
    helm_result = {"session": "disabled", "event": "disabled", "helm_dir": ""}
    if not no_helm and not os.environ.get("BOIL_NO_HELM"):
        helm_result = push_to_helm(snap, event)
    return snap, helm_result


# ---------- commands ---------------------------------------------------------


def cmd_emit(args) -> int:
    root = Path(args.root).resolve()
    if not (root / ".boil").is_dir():
        print(f"boil-helm-log: no .boil/ at {root} — nothing to log", file=sys.stderr)
        return 2
    event = {"ts": _now(), "kind": args.kind, "ticket": args.ticket,
             "attempt": int(args.attempt or 0), "status": args.status, "detail": args.detail}
    _append_line(root / ".boil" / "status.jsonl",
                 json.dumps({k: v for k, v in event.items() if v not in ("", 0)}, default=str) + "\n")
    snap, helm_result = sync(root, args.stem, event, args.no_helm)
    if args.json:
        print(json.dumps({"event": event, "helm": helm_result,
                          "session_id": snap["session_id"]}, indent=2))
    else:
        where = "helm+local" if helm_result.get("session") == "written" else "local only"
        print(f"boil-helm-log: {args.kind} {args.ticket or ''} {args.status or ''} → {where}".replace("  ", " "))
    return 0


def cmd_sync(args) -> int:
    root = Path(args.root).resolve()
    if not (root / ".boil").is_dir():
        print(f"boil-helm-log: no .boil/ at {root}", file=sys.stderr)
        return 2
    snap, helm_result = sync(root, args.stem, None, args.no_helm)
    if args.json:
        print(json.dumps({"session_id": snap["session_id"], "status": snap["status"],
                          "helm": helm_result}, indent=2))
    else:
        print(f"boil-helm-log: synced {snap['session_id']} ({snap['status']}) — "
              f"helm session {helm_result['session']}"
              + (f" @ {helm_result['helm_dir']}" if helm_result.get("helm_dir") else ""))
    return 0


def cmd_session(args) -> int:
    root = Path(args.root).resolve()
    snap = build_snapshot(root, args.stem)
    print(json.dumps(snap, indent=2, default=str) if args.json else render_status_md(snap))
    return 0


def cmd_link(args) -> int:
    """Record which helm criterion contract this boil session is burning down, so the
    session lands on the right goal card instead of the unassigned pile."""
    root = Path(args.root).resolve()
    if not args.stem:
        print("boil-helm-log: link needs --stem <helm criterion stem>", file=sys.stderr)
        return 2
    sp = root / ".boil" / "session.json"
    prior = {}
    if sp.exists():
        try:
            prior = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prior = {}
    prior["stem"] = args.stem
    prior.setdefault("session_id", session_identity(root)["session_id"])
    prior.setdefault("started_at", _now())
    _atomic_write(sp, json.dumps(prior, indent=2, default=str) + "\n")
    snap, helm_result = sync(root, args.stem, None, args.no_helm)
    print(f"boil-helm-log: session {snap['session_id']} linked to helm goal `{args.stem}` "
          f"({helm_result['session']})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="boil-helm-log", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--root", default=".", help="project root containing .boil/")
        p.add_argument("--stem", default="", help="helm criterion stem this session serves")
        p.add_argument("--no-helm", action="store_true", help="write project-local files only")
        p.add_argument("--json", action="store_true")

    p = sub.add_parser("emit", help="append one status event, then re-sync")
    common(p)
    p.add_argument("--kind", required=True, help="e.g. boil.judge.verdict, boil.iteration.start")
    p.add_argument("--ticket", default="")
    p.add_argument("--attempt", type=int, default=0)
    p.add_argument("--status", default="", help="short state word: PASS, FAIL, REVISE, blocked…")
    p.add_argument("--detail", default="", help="one line of context")
    p.set_defaults(fn=cmd_emit)

    p = sub.add_parser("sync", help="rebuild the snapshot from .boil/ state")
    common(p)
    p.set_defaults(fn=cmd_sync)

    p = sub.add_parser("session", help="print the current snapshot")
    common(p)
    p.set_defaults(fn=cmd_session)

    p = sub.add_parser("link", help="link this session to a helm criterion contract")
    common(p)
    p.set_defaults(fn=cmd_link)
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
