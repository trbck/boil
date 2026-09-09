#!/usr/bin/env python3
"""boil-reviewer.py — which (agent, model) pair reviews the code right now.

WHY THIS EXISTS. roborev stores the review *agent* and the review *model* as two
independent settings. Nothing tied them together, so an explicit `--agent codex`
picked up whatever `review_model` happened to hold — and on 2026-09-04 that was
the Ollama tag `glm-5.3:cloud`, left over from the period when reviews ran on
Ollama. Every review then died the same way:

    The 'glm-5.3:cloud' model is not supported when using Codex with a ChatGPT account.

Six milestone reviews failed that way before anyone noticed, because a failed
review is silent: the loop just never gets a second opinion.

So this script owns the pair as a *pair*, and nothing else is allowed to pick
half of it:

  PAIR INTEGRITY  a model tag containing ':' is an Ollama tag. Ollama is only
        reachable through the `claude-code` agent (roborev's `claude_code_cmd`
        points at the `claude-ollama` wrapper). Handing such a tag to `codex`
        is the bug above, so the pair is repaired here, loudly, rather than
        being discovered by a 400 from the provider.

  FALLBACK  codex is the primary reviewer. When it reports a quota / rate-limit
        error the pair flips to the backup (`claude-code` + `glm-5.3:cloud`,
        i.e. Ollama Cloud) and a cooldown starts. Reviews keep happening on the
        backup instead of failing.

  SWITCH-BACK  the cooldown is a *lower bound*, not the decision. When it
        expires the primary is not simply assumed healthy — it is probed with
        `roborev check-agents --agent codex`, a real smoke-test call. Only a
        passing probe returns the loop to codex; a still-limited probe extends
        the cooldown one rung up the ladder (15m, 30m, 1h, 2h, 4h). This is why
        the loop comes back to codex *when codex is actually available* rather
        than when a timer happened to run out.

State lives in one JSON file, machine-wide rather than per-repo, because a codex
quota is an account fact and every repo on the box hits the same wall. It records
*which* agent is limited, so a codex wall never pushes a project that reviews with
some other agent onto a backup it never needed:

    ~/.boil/reviewer.json          (override: $BOIL_REVIEWER_STATE)

Commands
  resolve  [--root .] [--json]                 the pair to use now; probes if the cooldown is up
  report   --outcome ok|quota|incompatible|fail --agent A [--model M] [--detail D]
  probe    [--force]                           smoke-test the primary; a pass ends the fallback
  apply    [--root .] [--dry-run]              sync the primary + backup pairs into roborev's config
  status   [--root .]                          human-readable state
  reset    [--root .]                          forget the cooldown, back to primary

Exit codes: 0 fine, 1 the primary is unavailable (resolve still prints the backup), 2 usage.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The default pair. codex reviews; when codex is rate-limited, Ollama Cloud does.
PRIMARY_AGENT = "codex"
PRIMARY_MODEL = ""            # empty: no boil-level preference; roborev's own default applies
BACKUP_AGENT = "claude-code"  # roborev's claude_code_cmd -> claude-ollama wrapper
BACKUP_MODEL = "glm-5.3:cloud"

# Cooldown ladder, minutes. One rung per consecutive quota strike; the last rung repeats.
LADDER = (15, 30, 60, 120, 240)
PROBE_MIN_INTERVAL_S = 300    # never smoke-test the primary more often than this
HISTORY_MAX = 50

# An Ollama model tag: `name:tag`. Codex and Anthropic model ids never contain a colon.
OLLAMA_TAG = re.compile(r"^[^:\s]+:[^:\s]+$")

QUOTA_PATTERNS = re.compile(
    r"usage limit|rate.?limit|quota|too many requests|\b429\b|resource_exhausted|"
    r"insufficient_quota|overloaded|capacity",
    re.IGNORECASE,
)
# Deliberately narrow: only signatures that name a model the agent cannot run. A bare
# `invalid_request_error` covers ordinary 400s too (context length, a malformed payload,
# a bad tool call), and calling those a configuration bug would refuse the fallback and
# repeat the same failure on every milestone while the configuration was fine all along.
INCOMPATIBLE_PATTERNS = re.compile(
    r"not supported when using|unknown model|model .* is not available|"
    r"unsupported model|no such model|model_not_found",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------- time
def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def human(delta: timedelta) -> str:
    secs = int(max(delta.total_seconds(), 0))
    if secs >= 3600:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"
    if secs >= 60:
        return f"{secs // 60}m"
    return f"{secs}s"


# --------------------------------------------------------------------- state
def state_path() -> Path:
    env = os.environ.get("BOIL_REVIEWER_STATE")
    if env:
        return Path(env).expanduser()
    return Path(os.environ.get("BOIL_HOME") or (Path.home() / ".boil")).expanduser() / "reviewer.json"


def load_state() -> dict:
    p = state_path()
    if not p.is_file():
        return {"version": 1, "active": "primary", "strikes": 0, "history": []}
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "active": "primary", "strikes": 0, "history": []}
    if not isinstance(s, dict):
        return {"version": 1, "active": "primary", "strikes": 0, "history": []}
    s.setdefault("version", 1)
    s.setdefault("active", "primary")
    s.setdefault("strikes", 0)
    s.setdefault("history", [])
    return s


def save_state(s: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    s["history"] = (s.get("history") or [])[-HISTORY_MAX:]
    # One state file, many writers: boil-review.py shells out to `report` while other
    # projects on the same machine resolve and probe. A shared temp name would let two of
    # them replace each other's file mid-write, so each writer gets its own.
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
        tmp.replace(p)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


@contextlib.contextmanager
def state_lock():
    """Serialise read-modify-write on the shared state.

    Every mutation here is load -> decide -> save. Without a lock two concurrent quota
    reports both read `strikes: 1`, both write `2`, and one strike vanishes — the cooldown
    ladder then under-counts exactly when the wall is hardest. Fails open: a platform
    without flock still works, it just races as before."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    p = state_path().with_name(state_path().name + ".lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except OSError:
            yield                      # a filesystem without locking: proceed unserialised
            return
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def note(s: dict, event: str, **kw) -> None:
    s.setdefault("history", []).append({"ts": iso(now()), "event": event, **kw})


# -------------------------------------------------------------------- config
def _review_cfg(root: Path) -> dict:
    """The `review` object, preferring the frozen copy the controller actually runs on."""
    for rel in (".boil/checks/frozen.json", ".boil/milestones.json"):
        p = root / rel
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("review"), dict):
            return data["review"]
    return {}


def pairs(root: Path) -> tuple[dict, dict]:
    """(primary, backup) pairs, from config, then env, then the built-in defaults."""
    cfg = _review_cfg(root)
    primary = {
        "agent": os.environ.get("BOIL_REVIEW_AGENT") or cfg.get("agent") or PRIMARY_AGENT,
        "model": os.environ.get("BOIL_REVIEW_MODEL") or cfg.get("model") or PRIMARY_MODEL,
    }
    backup = {
        "agent": os.environ.get("BOIL_REVIEW_BACKUP_AGENT") or cfg.get("backup_agent") or BACKUP_AGENT,
        "model": os.environ.get("BOIL_REVIEW_BACKUP_MODEL") or cfg.get("backup_model") or BACKUP_MODEL,
    }
    return repair(primary), repair(backup)


def repair(pair: dict) -> dict:
    """Enforce pair integrity. An Ollama tag only ever rides with `claude-code`.

    This is the guard for the failure this script was written for: `--agent codex`
    inheriting `review_model=glm-5.3:cloud` from roborev's global config."""
    agent, model = (pair.get("agent") or "").strip(), (pair.get("model") or "").strip()
    warning = ""
    if model and OLLAMA_TAG.match(model) and agent != "claude-code":
        warning = (f"{agent!r} cannot run the Ollama tag {model!r} "
                   f"(Ollama is reachable only through the claude-code agent) — model dropped")
        model = ""
    return {"agent": agent, "model": model, "warning": warning}


def coherent(pair: dict) -> bool:
    return not pair.get("warning")


# ------------------------------------------------------------------- roborev
def roborev_bin() -> str | None:
    return os.environ.get("BOIL_ROBOREV") or shutil.which("roborev")


def probe_primary(agent: str, timeout: int = 90) -> tuple[bool, str]:
    """Smoke-test the primary agent. Returns (available, detail).

    `roborev check-agents` runs a real short prompt through the agent, so a
    quota-exhausted codex fails here exactly as a review would."""
    exe = roborev_bin()
    if not exe:
        return False, "roborev not on PATH"
    try:
        r = subprocess.run([exe, "check-agents", "--agent", agent, "--timeout", str(timeout - 20)],
                           text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"probe timed out after {timeout}s"
    except OSError as exc:
        return False, f"probe could not run: {exc}"
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    m = re.search(r"(\d+)\s+passed,\s+(\d+)\s+failed", out)
    if m:
        ok = int(m.group(1)) >= 1 and int(m.group(2)) == 0
    else:
        ok = r.returncode == 0 and re.search(rf"{re.escape(agent)}\b.*\bOK\b", out) is not None
    # On failure the reason is usually on the lines *after* the agent's own, so take the
    # agent line and what follows it. "codex ... FAIL" alone tells nobody whether this is
    # a usage limit worth waiting out or a broken install.
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    at = next((i for i, ln in enumerate(lines) if agent in ln), 0)
    return ok, " | ".join(lines[at:at + 3])[:400] if lines else ""


def global_pair_warning() -> str:
    """roborev's own global `review_agent` / `review_model`, checked as a pair.

    boil's config is not where the 2026-09-04 drift lived — roborev's global config was.
    Any path that does not go through boil-review.py (a repo's post-commit hook, a bare
    `roborev review`, the daemon) still reads those globals, so a doctor that only
    validates boil's view would pass while every other review 400'd."""
    exe = roborev_bin()
    if not exe:
        return ""

    def get(key: str) -> str | None:
        try:
            r = subprocess.run([exe, "config", "get", key], text=True, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if r.returncode != 0:
            return None
        out = (r.stdout or "").strip()
        return out.splitlines()[-1].strip() if out else ""

    # The fast tier is a second, independent pair, and `apply` writes both — so it can
    # drift on its own and break every review that asks for fast reasoning.
    warnings = []
    for akey, mkey in (("review_agent", "review_model"), ("review_agent_fast", "review_model_fast")):
        agent, model = get(akey), get(mkey)
        if agent is None or model is None or not model:
            continue
        fixed = repair({"agent": agent or PRIMARY_AGENT, "model": model})
        if fixed["warning"]:
            warnings.append(f"{akey}={agent or PRIMARY_AGENT!r} with {mkey}={model!r} — {fixed['warning']}")
    if not warnings:
        return ""
    return ("roborev global config pairs " + "; also ".join(warnings)
            + ". Run `boil-reviewer.py apply` to repair it")


def policy_drift_note(root: Path) -> str:
    """Does this project pin a reviewer the machine no longer routes to?

    A pin is legitimate — boil's own advice is to review with a different family from the
    implementer. What is not legitimate is a pin whose *meaning* changed underneath it.
    ttengine pinned `claude-code` when roborev's global model was an Ollama tag, so the pin
    meant "review on Ollama". When the global model was emptied, the same pin silently
    began meaning "review on real Claude" — a different provider and a different bill, with
    nothing in the config touched and nothing in the doctor failing, because the pair is
    perfectly coherent. Only the comparison against the machine policy shows it."""
    exe = roborev_bin()
    if not exe:
        return ""
    cfg = _review_cfg(root)
    pinned = (cfg.get("agent") or "").strip()
    if not pinned:
        return ""                       # no pin: the project follows the policy by default
    try:
        r = subprocess.run([exe, "config", "get", "review_agent"], text=True,
                           capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    out = (r.stdout or "").strip()
    policy = out.splitlines()[-1].strip() if r.returncode == 0 and out else ""
    if not policy or policy == pinned:
        return ""
    detail = ""
    if pinned == BACKUP_AGENT and not (cfg.get("model") or "").strip():
        detail = (f" — with no model pinned alongside it, {pinned} reviews on the provider "
                  f"itself, not on Ollama; add \"model\" if Ollama was what was meant")
    return (f"this project pins agent={pinned!r} while the machine reviews with "
            f"{policy!r}{detail}")


def classify(text: str) -> str:
    """What kind of failure is this? Order matters: an incompatible-model 400 also
    trips some quota words, and mis-reading it as a quota hit would hide the real bug."""
    if not text:
        return "fail"
    if INCOMPATIBLE_PATTERNS.search(text):
        return "incompatible"
    if QUOTA_PATTERNS.search(text):
        return "quota"
    return "fail"


# -------------------------------------------------------------------- policy
def cooldown_left(s: dict) -> timedelta:
    until = parse_iso(s.get("cooldown_until"))
    return (until - now()) if until else timedelta(0)


def start_cooldown(s: dict, detail: str = "", agent: str = PRIMARY_AGENT, model: str = "") -> dict:
    """A quota wall belongs to the agent that hit it, not to 'the reviewer' in general.

    The state file is machine-wide because a codex quota is an account fact — but a codex
    quota says nothing about a project that reviews with gemini, and forcing that project
    onto its backup would be a fallback nobody asked for. So the limited agent is recorded
    and the cooldown only binds the projects whose primary is that agent."""
    key = _key(agent, model)
    if s.get("limited") and s["limited"] != key:
        s["strikes"] = 0                       # a different reviewer's wall: its own ladder
    s["limited"] = key
    s["strikes"] = int(s.get("strikes") or 0) + 1
    minutes = LADDER[min(s["strikes"], len(LADDER)) - 1]
    s["active"] = "backup"
    s["cooldown_until"] = iso(now() + timedelta(minutes=minutes))
    s["since"] = s.get("since") or iso(now())
    note(s, "QUOTA", agent=agent, strikes=s["strikes"], cooldown_min=minutes, detail=detail[:300])
    return s


def clear_cooldown(s: dict, why: str) -> dict:
    s["active"] = "primary"
    s["strikes"] = 0
    for k in ("cooldown_until", "since", "limited"):
        s.pop(k, None)
    note(s, "RESTORED", detail=why[:300])
    return s


def _key(agent: str, model: str) -> dict:
    """The identity of a reviewer: both halves, stored self-describingly in the state."""
    return {"agent": agent, "model": model or ""}


def _shown(limited) -> str:
    """The stored key, as a person would say it."""
    if not limited:
        return "the primary reviewer"
    if isinstance(limited, str):
        return limited                          # state written before models were keyed
    return f"{limited.get('agent', '')} {limited.get('model', '')}".strip()


def cooldown_binds(s: dict, primary: dict) -> bool:
    """Is this project's primary the reviewer that is rate limited?

    Compared as a pair, not an agent. A project may legitimately run `claude-code` with no
    model as its primary and `claude-code` + an Ollama tag as its backup; keyed by agent
    alone, a success on the backup would clear the primary's cooldown and a wall on the
    backup would extend it — two different models moving each other's ladder."""
    if s.get("active") != "backup":
        return False
    limited = s.get("limited")
    if not limited:
        return PRIMARY_AGENT == primary["agent"]
    if isinstance(limited, str):
        return limited == primary["agent"]        # state written before models were keyed
    return limited == _key(primary["agent"], primary.get("model") or "")


def resolve_pair(root: Path, allow_probe: bool = True) -> tuple[dict, dict, dict]:
    """The pair to use now, the state after any probe, and a decision record."""
    primary, backup = pairs(root)
    s = load_state()

    if not cooldown_binds(s, primary):
        reason = "primary healthy"
        if s.get("active") == "backup":
            reason = (f"{_shown(s.get('limited'))} is rate limited, but this project reviews "
                      f"with {primary['agent']} — the cooldown does not apply")
        return primary, s, {"using": "primary", "reason": reason,
                            "warning": primary.get("warning") or backup.get("warning")}

    left = cooldown_left(s)
    if left > timedelta(0):
        return backup, s, {"using": "backup", "reason": f"{primary['agent']} on cooldown, {human(left)} left",
                           "cooldown_left_s": int(left.total_seconds()),
                           "warning": backup.get("warning")}

    if not allow_probe:
        return backup, s, {"using": "backup", "reason": "cooldown expired, probe suppressed",
                           "warning": backup.get("warning")}

    last = parse_iso((s.get("last_probe") or {}).get("ts"))
    if last and (now() - last).total_seconds() < PROBE_MIN_INTERVAL_S:
        return backup, s, {"using": "backup",
                           "reason": f"probed {human(now() - last)} ago and {primary['agent']} was still down",
                           "warning": backup.get("warning")}

    # The probe is a network call taking tens of seconds. It runs unlocked so it cannot
    # block another project's review, and the state is re-read under the lock afterwards
    # because someone else may have decided the same thing in the meantime.
    ok, detail = probe_primary(primary["agent"])
    with state_lock():
        s = load_state()
        s["last_probe"] = {"ts": iso(now()), "ok": ok, "detail": detail}
        if ok:
            clear_cooldown(s, f"probe passed: {detail}")
            save_state(s)
        else:
            start_cooldown(s, f"probe failed: {detail}", agent=primary["agent"],
                           model=primary.get("model") or "")
            save_state(s)
    if ok:
        return primary, s, {"using": "primary", "reason": f"{primary['agent']} answered its probe — switched back",
                            "switched_back": True, "warning": primary.get("warning")}
    why = f"{primary['agent']} still unavailable ({detail[:120]}) — cooldown extended to {human(cooldown_left(s))}"
    return backup, s, {"using": "backup", "reason": why, "warning": backup.get("warning")}


def pair_args(pair: dict) -> list[str]:
    """roborev flags for a pair. The model is passed whenever it is known, so roborev's
    own `review_model` default can never leak in behind an explicit `--agent`."""
    args = ["--agent", pair["agent"]]
    if pair.get("model"):
        args += ["--model", pair["model"]]
    return args


# ------------------------------------------------------------------ commands
def cmd_resolve(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    pair, _s, rec = resolve_pair(root, allow_probe=not a.no_probe)
    out = {"agent": pair["agent"], "model": pair["model"], **rec}
    if a.json:
        print(json.dumps(out))
    else:
        line = f"{pair['agent']}" + (f" {pair['model']}" if pair["model"] else " (agent default model)")
        print(f"{line}  # {rec['reason']}")
        if rec.get("warning"):
            print(f"warning: {rec['warning']}", file=sys.stderr)
    return 0 if rec["using"] == "primary" else 1


def cmd_report(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    primary, _backup = pairs(root)
    outcome = a.outcome
    if outcome == "auto":
        outcome = classify(a.detail or "")
        if not (a.detail or "").strip():
            outcome = "ok"

    with state_lock():
        s = load_state()
        _apply_report(s, a, primary, outcome)
        save_state(s)
    # Informational: `report` is called from inside boil-review, whose stdout is the
    # milestone verdict. Keep the channel clean.
    print(f"{outcome} recorded for {a.agent}"
          + (f"; on backup for {human(cooldown_left(s))}" if s.get("active") == "backup" else ""),
          file=sys.stderr)
    return 0


def _apply_report(s: dict, a: argparse.Namespace, primary: dict, outcome: str) -> None:
    if outcome == "ok":
        reported = {"agent": a.agent, "model": a.model or ""}
        if _key(a.agent, a.model or "") == _key(primary["agent"], primary.get("model") or "") \
                and cooldown_binds(s, primary):
            clear_cooldown(s, "a review on the primary succeeded")
        elif reported == {"agent": primary["agent"], "model": primary.get("model") or ""} \
                and not s.get("limited"):
            # The strike count is the ladder for whichever agent is limited. A green
            # review by some *other* project's reviewer says nothing about that agent, and
            # zeroing it here would quietly shorten the next cooldown for a wall that has
            # not moved.
            s["strikes"] = 0
        note(s, "OK", agent=a.agent, model=a.model or "")
    elif outcome == "quota":
        if _key(a.agent, a.model or "") == _key(primary["agent"], primary.get("model") or ""):
            start_cooldown(s, a.detail or "quota reported by the caller",
                           agent=a.agent, model=a.model or "")
        else:
            note(s, "BACKUP-QUOTA", agent=a.agent, detail=(a.detail or "")[:300])
    elif outcome == "incompatible":
        note(s, "INCOMPATIBLE", agent=a.agent, model=a.model or "", detail=(a.detail or "")[:300])
        print(f"incompatible pair: {a.agent} + {a.model or '(none)'} — this is a configuration bug, "
              f"not a quota limit; the fallback was NOT engaged", file=sys.stderr)
    else:
        note(s, "FAIL", agent=a.agent, model=a.model or "", detail=(a.detail or "")[:300])


def cmd_probe(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    primary, _backup = pairs(root)
    s = load_state()
    last = parse_iso((s.get("last_probe") or {}).get("ts"))
    if last and not a.force and (now() - last).total_seconds() < PROBE_MIN_INTERVAL_S:
        print(f"probed {human(now() - last)} ago; --force to probe anyway")
        return 0 if s.get("active") != "backup" else 1
    ok, detail = probe_primary(primary["agent"])   # slow, and deliberately unlocked
    with state_lock():
        s = load_state()
        s["last_probe"] = {"ts": iso(now()), "ok": ok, "detail": detail}
        restored = ok and cooldown_binds(s, primary)
        if restored:
            clear_cooldown(s, f"probe passed: {detail}")
        elif ok:
            if not s.get("limited"):
                s["strikes"] = 0
        else:
            # Any failed probe of the current primary advances the ladder. Skipping it when
            # a cooldown already binds would leave `cooldown_until` in the past, and every
            # later resolve would probe again immediately — the backoff would never happen.
            start_cooldown(s, f"probe failed: {detail}", agent=primary["agent"],
                           model=primary.get("model") or "")
        save_state(s)
    if restored:
        print(f"{primary['agent']} is back — reviews return to it")
        return 0
    if ok:
        print(f"{primary['agent']} OK")
        return 0
    print(f"{primary['agent']} unavailable: {detail}")
    return 1


def cmd_apply(a: argparse.Namespace) -> int:
    """Sync the reviewer *policy* into roborev's global config: the primary pair, and the
    backup pair roborev falls back to on its own.

    Deliberately the policy and not the momentary decision. Writing the backup into
    `review_agent` would have looked right — reviews really do run on the backup during a
    cooldown — but roborev has its own quota fallback keyed on `review_agent` being the
    primary. Overwriting it hands the daemon a config in which codex is no longer the
    reviewer at all, so roborev's own `agent_quota_cooldown` has nothing to return to, and
    anything that does not go through boil stays on the backup until a person notices.

    Two layers, each recovering by itself: roborev falls back and returns on its timer;
    boil-review.py falls back and returns on a verified probe. They agree because they are
    given the same two pairs."""
    root = Path(a.root).resolve()
    primary, backup = pairs(root)
    exe = roborev_bin()
    if not exe:
        print("roborev not on PATH — nothing to apply", file=sys.stderr)
        return 2

    def get(key: str) -> str:
        try:
            r = subprocess.run([exe, "config", "get", key], text=True, capture_output=True,
                               timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        out = (r.stdout or "").strip()
        return out.splitlines()[-1].strip() if r.returncode == 0 and out else ""

    def model_write(key: str, agent: str, wanted: str) -> list[tuple[str, str]]:
        """An empty `wanted` means "no boil-level preference", which is not the same as
        "clear it". Wiping a global model the agent can run would destroy the user's own
        choice — the very case `_seal_global_model` goes out of its way to preserve. Only
        an impossible one is cleared."""
        if wanted:
            return [(key, wanted)]
        current = get(key)
        if current and repair({"agent": agent, "model": current})["warning"]:
            return [(key, "")]
        return []

    plan: list[tuple[str, str]] = [("review_agent", primary["agent"])]
    plan += model_write("review_model", primary["agent"], primary.get("model") or "")
    plan += [("review_backup_agent", backup["agent"])]
    plan += model_write("review_backup_model", backup["agent"], backup.get("model") or "")
    # The fast tier is a pair of its own. It is only realigned when it has no agent yet or
    # its own pair is impossible; a deliberately different or cheaper fast reviewer stays.
    fast_agent, fast_model = get("review_agent_fast"), get("review_model_fast")
    broken = bool(fast_model and repair({"agent": fast_agent or primary["agent"], "model": fast_model})["warning"])
    if broken or not fast_agent:
        plan += [("review_agent_fast", primary["agent"])]
        plan += model_write("review_model_fast", primary["agent"], primary.get("model") or "")

    if a.dry_run:
        print(json.dumps({"set": dict(plan)}))
        return 0
    # A half-written pair is the drift this whole script exists to prevent, so a failure
    # partway through puts back what was already changed rather than leaving a config in
    # which the agent and the model disagree.
    undo: list[tuple[str, str]] = []
    for key, val in plan:
        prior = get(key)
        try:
            r = subprocess.run([exe, "config", "set", "--global", key, val],
                               text=True, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            r = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(exc))
        if r.returncode != 0:
            for ukey, uval in reversed(undo):
                subprocess.run([exe, "config", "set", "--global", ukey, uval],
                               text=True, capture_output=True, timeout=20)
            print(f"could not set {key}: {(r.stderr or r.stdout).strip()[:200]} — "
                  f"rolled back {len(undo)} earlier write(s); roborev config unchanged",
                  file=sys.stderr)
            return 2
        undo.append((key, prior))
    warn = primary.get("warning") or backup.get("warning")
    print(f"roborev reviews: {primary['agent']} {primary.get('model') or '(agent default model)'}, "
          f"falling back to {backup['agent']} {backup.get('model') or '(agent default model)'}"
          + (f"  [{warn}]" if warn else ""))
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    root = Path(a.root).resolve()
    primary, backup = pairs(root)
    s = load_state()
    active = s.get("active", "primary")
    binds = cooldown_binds(s, primary)
    pair = backup if binds else primary
    print(f"reviewer   {pair['agent']}" + (f" {pair['model']}" if pair["model"] else " (agent default model)")
          + f"   [{'backup' if binds else 'primary'}]")
    print(f"primary    {primary['agent']} {primary['model'] or '(agent default model)'}")
    print(f"backup     {backup['agent']} {backup['model'] or '(agent default model)'}")
    for p in (primary, backup):
        if p.get("warning"):
            print(f"warning    {p['warning']}")
    gw = global_pair_warning()
    if gw:
        print(f"warning    {gw}")
    # `note`, not `warning`: a deliberate pin is allowed, so this must be visible without
    # failing the doctor and teaching people to ignore it.
    dn = policy_drift_note(root)
    if dn:
        print(f"note       {dn}")
    if binds:
        left = cooldown_left(s)
        print(f"cooldown   {human(left)} left (strike {s.get('strikes')}), since {s.get('since')}")
    elif active == "backup":
        print(f"cooldown   {_shown(s.get('limited'))} is limited, but this project reviews "
              f"with {primary['agent']} — not affected")
    lp = s.get("last_probe") or {}
    if lp:
        print(f"last probe {lp.get('ts')}  {'OK' if lp.get('ok') else 'FAILED'}  {lp.get('detail', '')[:120]}")
    print(f"state      {state_path()}")
    if a.history:
        for h in (s.get("history") or [])[-15:]:
            print("  " + json.dumps(h))
    return 0 if not binds else 1


def cmd_reset(a: argparse.Namespace) -> int:
    with state_lock():
        s = load_state()
        clear_cooldown(s, "manual reset")
        save_state(s)
    print("cooldown cleared; reviews go back to the primary")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("resolve", help="print the (agent, model) pair to use now")
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-probe", action="store_true", help="never smoke-test the primary")
    p.set_defaults(fn=cmd_resolve)

    p = sub.add_parser("report", help="record how a review went")
    p.add_argument("--root", default=".")
    p.add_argument("--agent", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--outcome", default="auto", choices=["auto", "ok", "quota", "incompatible", "fail"])
    p.add_argument("--detail", default="")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("probe", help="smoke-test the primary; a pass ends the fallback")
    p.add_argument("--root", default=".")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("apply", help="sync the primary and backup pairs into roborev's global config")
    p.add_argument("--root", default=".")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("status", help="show the current reviewer and any cooldown")
    p.add_argument("--root", default=".")
    p.add_argument("--history", action="store_true")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("reset", help="forget the cooldown")
    p.add_argument("--root", default=".")
    p.set_defaults(fn=cmd_reset)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
