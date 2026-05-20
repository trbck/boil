# L-SDF — compact codebase index for cheap navigation inside boil

`boil` runs a lot of subagents. Each subagent that spelunks the
repository to find a file, a function, or a call edge pays in input
tokens twice — once when the orchestrator hands it ticket context,
again when the agent itself reads source. On a non-trivial repo this
is the single biggest cost driver inside the loop.

L-SDF ([lsdf-core on PyPI](https://pypi.org/project/lsdf-core/), repo
at [github.com/ec1980/lsdf-core](https://github.com/ec1980/lsdf-core))
solves this by generating two compact index files alongside the
source tree:

- `INDEX.lsdf` — structural map (dirs, file roles, key exports).
- `INDEX.detail.lsdf` — function signatures, schema fields, call edges.

Typical compression on a Python repo: **~13× vs reading source** (the
author's stated figure is 110K source tokens → 8K index tokens for a
mid-sized Python codebase). That maps directly to the orchestrator's
"hand a subagent enough context to start without making it grep" cost.

## When boil should use it

**Bootstrap (Phase 1).** After the initial scan, if the repo has
≥ 1,000 files OR a `pyproject.toml` / `package.json` / `go.mod` at
root, run:

```bash
lsdf init                      # one-time per repo
lsdf gen . --recursive         # build the index from current tree
lsdf stats                     # log the source-vs-index token ratio
```

Store the `lsdf stats` output line in `.boil/memory.md` under a
"Codebase index" section so a future iteration can see whether the
index is still earning its keep.

**Per-iteration (Step 2a, before dispatch).** If the working tree has
moved more than ~30 files since last `lsdf gen`, run:

```bash
lsdf gen . --recursive         # regenerate
lsdf sync --check              # exit non-zero if drift remains
```

The check is cheap (seconds on 100k LOC). A non-zero exit code is a
signal that the dispatch context the orchestrator is about to send is
stale; either regenerate, or let the agent fall back to direct file
reads for the files it touches.

**Per-agent dispatch prompt (Step 2b).** When dispatching, include in
the agent prompt:

```
INDEX:    INDEX.lsdf / INDEX.detail.lsdf at repo root.
USAGE:    `lsdf trans INDEX.lsdf` translates the structural map to
          plain markdown if you find the .lsdf format dense. Prefer
          the index for "where does X live?" — read source only for
          files you actually need to modify or run.
```

The agent then uses the index to navigate, only reading source for
the small set of files in its diff blast radius. This is the
boil-side equivalent of the "agent reads the codebase first" pattern
without paying for the read.

**Per-iteration verification (Step 2d, Pass 1).** Add this to the
checks that run on every iteration:

```bash
lsdf sync --check              # indices match the source tree
```

If it fails, the iteration's `git add` left stale indices. Add them
or regenerate; don't ship a commit where source has moved past index.

**CI integration (Phase 3).** When boil terminates, `lsdf init --ci`
writes a GitHub Actions / GitLab CI hook that runs `lsdf sync --check`
on every PR. This prevents downstream contributors from quietly
desynchronizing the index after boil's final demo.

## When boil should NOT use it

- **TypeScript / Go / Rust repos** as of L-SDF 1.1.x — the indexer
  is Python-first; TS / Go / Rust generators are on the upstream
  roadmap but not shipped. Skip the index step on non-Python repos
  until coverage catches up, and add a follow-up ticket
  (`tooling: revisit lsdf when TS/Go/Rust generators ship`).
- **Small repos** (< 100 files). The break-even is around 50 source
  files; below that the index adds churn without saving meaningful
  tokens. Skip silently.
- **Greenfield work** (the repo is empty or has < 10 files). The
  index has nothing useful to map.

## How L-SDF fits in `.boil/memory.md`

Inside `memory.md` ("what is true about the codebase RIGHT NOW that
this boil iteration needs to know"), add:

```markdown
## Codebase index (L-SDF)

- Last regen: <YYYY-MM-DD ts>, <N> files indexed.
- Compression: <SRC tokens> → <IDX tokens> (~<R>× — `lsdf stats`).
- Drift gate: `lsdf sync --check` runs in Step 2d Pass 1; the
  iteration is not done until it exits 0.
```

That paragraph is sticky — it survives every iteration's rewrite of
the dynamic sections of `memory.md` because it captures a
codebase-level invariant, not a per-iter fact.

## Failure modes to expect

- **`lsdf` not on PATH** — skip the index step, file a `tooling`
  ticket asking the operator to `pipx install lsdf-core` (or
  `pip install --user lsdf-core` if pipx is unavailable). Don't
  attempt to install it inside the loop.
- **`lsdf gen` raises** on a parser error in a malformed Python
  file — capture the error in `.boil/bugs.md` (real defect, not a
  boil issue) and continue.
- **`lsdf sync --check` flaps** across reruns when an iteration
  edits the index file itself (e.g. by formatting). Add the
  `INDEX.lsdf` + `INDEX.detail.lsdf` to `.gitattributes` as
  `merge=ours` so future merges don't try to hand-reconcile them.

## Quick sanity check

```bash
$ lsdf --version
1.1.6  # the version this skillset was integrated against

$ lsdf gen . --recursive && lsdf stats
# expect a 5–15× compression line; if you see < 2× the index isn't
# pulling its weight on this repo.
```
