# Demo Formats — The Cornerstone

The demo is what makes `boil` different from a black-box loop. Every iteration ends with a user-visible artifact that lets them verify the change in **30 seconds or less**, without needing to read code.

This file contains recipes per work type. Pick the one that matches what the iteration produced — or combine two if the work spans types.

## The principle

A demo answers three questions for the user, in this order:

1. **Is the thing actually working?** (proof of function)
2. **What changed to make it work?** (provenance — file:line, diff, commit)
3. **Where does this sit vs the goal?** (perspective — checklist progress)

Every demo recipe below covers all three. Skip any of them and the demo loses its purpose.

## Universal demo skeleton (always include)

In `iterations/iter-NNN/demo.md`, always have these four sections, regardless of recipe:

```markdown
## What changed (file-level)
- `<path>:<line>` — <one-line>
- `<path>:<line>` — <one-line>

## How to see it works (30 seconds)
**The action:** <ONE concrete thing the user does>
→ <recipe-specific content>

## Where this sits vs goal
- ✅ Closed: <goal checkboxes that just went green>
- 🟡 Moved forward: <progress without closing>
- ⬜ Untouched: <future iterations>

## Tests added / run
- `<name>` — <what it asserts> — `<verify cmd>` — <result>
```

The recipes below tell you what to put inside the `→` of the "How to see it works" section.

---

## Recipe: Web UI / dashboard / page

The user opens a URL and sees the change. Visual proof beats code proof.

**Steps:**
1. Start the dev server (background process via Bash `run_in_background: true`). Note the port.
2. **Take a screenshot** via the browser/screenshot tool available in the current client (Chrome MCP, Playwright, Puppeteer, or local browser automation). Save to `iterations/iter-NNN/artifacts/screenshot.png`.
3. If no browser tool is available, fall back to: a curl of the page HTML showing the new element, or a Playwright/Puppeteer one-shot if the project has one set up.
4. Provide the localhost URL the user can open themselves.

**Demo content:**

```markdown
**The action:** Open this in your browser → http://localhost:3000/admin/metrics

Or look at this screenshot if the dev server isn't running on your machine:
→ `iterations/iter-005/artifacts/dashboard-with-filter.png`

The new filter bar is at the top. Change the date range and the conversion chart re-renders within 200ms (verified by the perf test below).
```

**For visual changes:** include a before/after pair if you can — screenshot the prior commit too. The user instantly sees the delta.

---

## Recipe: API / backend endpoint

The user runs a `curl` and sees the response. Show input → output.

**Steps:**
1. Start the API server (background).
2. Run the actual `curl` command against it. Capture the response.
3. Save the captured response to `artifacts/api-response.json` if it's long.

**Demo content:**

```markdown
**The action:** Run this command (server is running at :8000):

    curl -s -X POST http://localhost:8000/api/orders \
      -H 'Content-Type: application/json' \
      -d '{"item_id": "sku-42", "qty": 2}' | jq

Expected response (captured fresh from the running server):

    {
      "order_id": "ord_01HX...",
      "status": "confirmed",
      "total_cents": 2998,
      "estimated_ship": "2026-05-08"
    }

Full response saved to: `iterations/iter-005/artifacts/api-response.json`

The endpoint did not exist before this iteration — see diff below.
```

**Always include the response captured fresh.** Don't write a fake "expected" response — run the real command, paste the real output.

---

## Recipe: CLI tool / script

The user runs the command and sees output change. Before/after is gold here.

**Steps:**
1. Run the command on real input.
2. Capture the full output (stdout + stderr + exit code).
3. If the change was a fix, capture the BEFORE behavior too — checkout the prior commit briefly, run, capture, restore. Or describe the prior failure mode if you have it from earlier iterations.

**Demo content:**

```markdown
**The action:** Run this command (uses a real input file):

    ./summarize examples/long-article.md --max-words 200

Output (captured fresh):

    [✓] Read 4,827 words from examples/long-article.md
    [✓] Summary generated (197 words, 4.1% of source)
    [✓] Saved to examples/long-article.summary.md

Before this iteration, the same command exited with:

    Error: --max-words flag not recognized

So now: same command, same input → success vs error.
```

---

## Recipe: Library / pure code change (no UI, no server)

Show the diff, show the test that now passes. The diff *is* the demo.

**Steps:**
1. Run `git diff <prior-iteration-commit>..HEAD -- <relevant-paths>`.
2. Trim to the meaningful chunk (≤30 lines). If the diff is too long, link to the full diff and excerpt the most important hunks.
3. Run the new test, capture the green output.

**Demo content:**

```markdown
**The action:** Read this diff (the actual change) and look at the test below:

    diff --git a/src/parser/dates.ts b/src/parser/dates.ts
    @@ -42,8 +42,15 @@
     export function parseRelativeDate(input: string): Date {
    -  const m = input.match(/(\d+) days? ago/);
    -  return m ? subDays(new Date(), parseInt(m[1])) : new Date(NaN);
    +  const m = input.match(/(\d+)\s*(day|week|month|year)s?\s*ago/i);
    +  if (!m) return new Date(NaN);
    +  const n = parseInt(m[1]);
    +  switch (m[2].toLowerCase()) {
    +    case 'day': return subDays(new Date(), n);
    +    case 'week': return subWeeks(new Date(), n);
    +    case 'month': return subMonths(new Date(), n);
    +    case 'year': return subYears(new Date(), n);
    +  }
     }

The new test (added this iteration) verifies all four units:

    $ npm test -- parser/dates.test.ts
    PASS  src/parser/dates.test.ts
      parseRelativeDate
        ✓ "3 days ago" (4 ms)
        ✓ "2 weeks ago" (1 ms)
        ✓ "5 months ago"
        ✓ "1 year ago"

Full file: src/parser/dates.ts:42-56
```

---

## Recipe: Bug fix

Show the failing test, the same test now green, the one-line root cause.

**Steps:**
1. Capture the failing-test output from before (use the iteration log if you have it; otherwise describe the symptom).
2. Run the same test now. Capture green output.
3. State the root cause in one sentence.

**Demo content:**

```markdown
**The action:** Run this test — it was red, now it's green:

    $ npm test -- cart/checkout.test.ts -t "applies discount before tax"
    PASS  src/cart/checkout.test.ts
      ✓ applies discount before tax (12 ms)

Before this iteration, the same command failed:

    expected: 9.50
    received: 10.45
    (discount was applied AFTER tax, inflating the total)

**Root cause (one sentence):** `applyTax()` was called before `applyDiscount()` in `checkout.ts:88`; swapped the order.

**The fix (3-line diff):** see `git show HEAD -- src/cart/checkout.ts`
```

---

## Recipe: Test-only iteration (added coverage, no behavior change)

Show the pass count delta and name the new tests.

**Demo content:**

```markdown
**The action:** Run the suite, see the count grew:

    $ npm test
    Tests:       7 added, 53 passed, 0 failed
    Time:        4.2s

New tests added this iteration:
- `cart/checkout.test.ts` → "rejects negative quantity" (covers B-003)
- `cart/checkout.test.ts` → "handles empty cart"
- `auth/login.test.ts` → "locks account after 5 failed attempts"
- ... (4 more)

**Coverage delta:** statements 71% → 78%, branches 64% → 72%
```

---

## Recipe: Performance work

Numbers. Same workload, before vs after. Don't trust micro-benchmarks unless they're the goal — prefer realistic load.

**Steps:**
1. Run the perf scenario on the prior commit (briefly check out, run, capture, restore).
2. Run it on HEAD. Capture.
3. Show both, side by side.

**Demo content:**

```markdown
**The action:** Same workload, two commits:

| Metric | Before (b3a47c) | After (this iter) | Delta |
|--------|----------------:|------------------:|------:|
| p50 latency | 142ms | 38ms | -73% |
| p95 latency | 410ms | 89ms | -78% |
| Throughput | 230 req/s | 920 req/s | +300% |
| Memory peak | 480 MB | 195 MB | -59% |

Workload: 1000 concurrent requests against `/api/search?q=common` for 30s
Tool: `wrk -t8 -c100 -d30s http://localhost:8000/api/search?q=common`

**What changed:** added the `search_idx` index on `documents(tsvector)` and switched the query to use `to_tsquery` instead of `ILIKE`. See diff: `db/migrations/20260505_search_idx.sql` + `src/search.ts:34-58`.
```

---

## Recipe: Documentation

Show the rendered output. If Markdown, the path the user opens; if a generated docs site, the URL.

**Demo content:**

```markdown
**The action:** Open the new section in your editor or preview:
→ `docs/api/orders.md` — added "Webhooks" section (lines 142-218)

Or view the generated site at http://localhost:4000/api/orders#webhooks (if the docs server is running).

**What was missing before:** there was no documentation for the four webhook event types (`order.created`, `order.updated`, `order.cancelled`, `order.shipped`). Each now has signature, payload schema, and a working curl example.
```

---

## Recipe: Refactor (no behavior change)

Behavior didn't change — so the demo is: tests still pass + the diff is cleaner. Show metrics.

**Demo content:**

```markdown
**The action:** Run the suite — all green, behavior unchanged:

    $ npm test
    Tests: 53 passed, 0 failed (no count change)

**What changed (structural metrics):**
- `src/orders/` — extracted `OrderRepository` from `OrderService` (-180 lines from service, +95 in repo, -85 net)
- Cyclomatic complexity of `OrderService.create`: 18 → 7
- Test setup boilerplate per file: ~40 lines → ~12 lines (shared fixture)

Diff: `git diff main -- src/orders/`

**Why this matters for the goal:** unblocks T-0019 (add subscription orders) which couldn't be cleanly added to the old monolithic service.
```

---

## When you cannot produce a demo

If the iteration's work genuinely doesn't lend itself to any of the recipes above, **that's a signal**:

- The work might be infrastructure (CI config, Docker, env setup) — demo by showing the new pipeline run, the new build artifact, the new env var being read.
- The work might be incomplete from a user perspective — file a `demo-prep` ticket for the next iteration to add the missing user-visible piece.
- The work might be exploratory (research, spike) — the demo is the research findings document. Write `iterations/iter-NNN/artifacts/findings.md` and link it.

**Never skip the demo by saying "no user-visible change this iteration."** Either find the demo angle, or admit that the iteration didn't move the goal and acknowledge that to the user honestly.

---

## Combining recipes

Real iterations often combine work types. Combine demos accordingly:

- **Frontend feature using a new backend endpoint:** UI screenshot + the curl of the endpoint that powers it.
- **Bug fix with new test:** the failing-then-green test (Bug Fix recipe) + the diff (Library recipe).
- **Perf work + new metric exposed in dashboard:** perf table + dashboard screenshot showing the metric.

Keep combined demos under ~40 lines total. The user shouldn't have to scroll a wall.

---

## Demo capability map (which formats actually reach the user)

The user's environment determines which demo formats land. At Phase 0 (or first time you need to demo), check:

| Format | Requires | Fallback if unavailable |
|--------|----------|-------------------------|
| Browser screenshot | Chrome MCP connected | Save HTML, link the path; describe what user sees |
| Localhost URL | User on same machine | Save curl response; describe state |
| Terminal output | Always works | — |
| Diff | Always works | — |
| Test green output | Project has runnable tests | Describe what tests would assert |
| Performance numbers | Reproducible benchmark setup | Describe what would be measured |

If you discover the user's environment can't surface a demo format you'd planned, switch to the best fallback and note it in the demo file.
