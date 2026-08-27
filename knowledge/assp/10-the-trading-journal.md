# Ch 10 — The Trading Journal

**Source:** Bernut, *Algorithmic Short Selling with Python*, 2nd ed. (Packt, 2026), Ch. 10.
**Governs:** adherence — the gap between what the system said and what you actually did — plus the post-trade analytics that P&L alone cannot produce.
**Thesis:** *"Debugging code is a solved problem. How do we debug the programmer?"* Beliefs and biases do not appear in stack traces; they reveal themselves across hundreds of trading days. The journal is the instrument that makes that gap **visible, quantifiable, and correctable.**

> *"We do not trade the markets. We trade our beliefs about the markets."* — Van Tharp

**Two systems, one base:** Part A automates trade reconciliation (analytics); Part B automates the psychology journal with gamification. An AI layer reads both as a trading psychologist would.

---

## 1. The six beliefs that cost traders money

| Belief | Mechanism | Cost |
|---|---|---|
| **Need to be right** | **The most destructive belief for a systematic trader.** Arbitrageurs are paid to be right about relative value; **trend followers are paid precisely for the discomfort of being wrong most of the time.** | Conflating *taking a loss* (process) with *being wrong* (identity) → cut winners early, hold losers long → **inverts the strategy's payoff profile entirely** |
| **Need for action** | Markets spend long periods doing nothing useful for a systematic short seller. *"It is not because we show up at our desk that we should be trading."* | Low-quality impulsive positions. **Not trading is an important trading decision.** |
| **Need for validation** | Attaches the trader to narratives. Price rises against a compelling thesis → **add rather than cut**, because the story feels more real than the mark-to-market loss | Story and the need to be right supersede the imperative to make money |
| **Loss aversion** (Kahneman & Tversky) | The **disposition effect**: sell winners early, hold losers long | For short sellers, coupled with scarcity mindset, it **prolongs the agony during short squeezes** |
| **Need for certainty** | Perfectionism — waiting for the perfect setup. **"Every box ticked has a price tag attached to it."** | Wait for all boxes → **show up only after shorts become crowded.** Certainty is an expensive luxury |
| **Locus of control** | External → blame ("they," the analysts, the price action). Internal → *"how can I improve tomorrow?"* | *"Victims do not build empires."* External locus delays learning. **The journal reinforces the internal locus, one entry at a time** |

**Two conditions must align:** a strategy with positive expected value, **and** a trader psychologically capable of executing it without interference. *"Most books address the first in detail and treat the second as an afterthought. In practice the second fails far more often."*

---

## 2. The Abraham Wald principle — the chapter's key structural insight

WWII: Allied forces studied bullet holes on returning aircraft. Damage concentrated on fuselage and wings; the intuitive fix was to reinforce there. **Abraham Wald saw the sampling error: those were the survivors.** The holes they carried were evidence of *survivable* damage. **The areas with no holes — engines, cockpit — were where damage caused planes not to return.**

> **Missed trades are the planes that never came back.**

Every signal ignored — because the stock felt too risky, the size felt too large, the market felt wrong — **is invisible in a standard trade log. The log shows only executed trades. It is the surviving fleet, and it tells half the story.**

**Log missed and executed trades side by side and study their distribution by motive.** Patterns emerge: skipping short entries after a losing streak, resizing after a winning or losing streak, overriding stops. **"Like the holes in the fuselage, the blanks in our strategies tell us a lot about who we are."**

### The three categories that carry the most information

| Category | Definition | Portfolio effect |
|---|---|---|
| **matched** | Order and fill share date + ticker + broker | Routed to a position handler |
| **missed** | Order exists, no fill — **the system spoke and you didn't act** | **Log only, no portfolio change** |
| **override** | Fill exists, no order — **reactive or manual trade outside the system** | **Log only, flagged for review** |

---

## 3. Two journals, one system

| | **Analytics journal** (TradeLog) | **Psychology journal** |
|---|---|---|
| Records | Objective facts: ticker, direction, entry/exit, quantity, commission, gross/net P&L — **plus missed trades and overrides** | Subjective facts: pre-open mindset, confidence, checklist, forecast + reasoning, evening reflection, what went well, kaizen, gratitude |
| Input | **Fully automated** — order file from strategies, execution reports from brokers, notebook does matching and Airtable updates | **Phone forms**: 2-minute morning, 5-minute evening |
| Cadence | Nightly | Twice daily; analyzed weekly |

**The reframing that matters:** *"We naturally conflate making money with being right, and losses with being wrong. **Trading right is doing the right thing even if it means losing money.**"* One reframe offered: *"sometimes we win, sometimes we learn, and today I am grateful for the lesson."*

### Why journaling initiatives fail, and the three counters

| Failure cause | Counter |
|---|---|
| **Friction** | Analytics fully automated (no manual entry). Psychology forms are phone-optimized, mostly dropdowns and numerics, with **pre-populated defaults** (`session="pre"` on the morning form, `"post"` on the evening one) reducing required decisions **to zero** |
| **Delayed gratification** | **Gamification** — scored out of 120 for completeness; streak multiplier `1 + streak/20` (day 20 = 2.0×, day 40 = 3.0×); auto-computed and patched back to Airtable. **Tip: set a SMART reward at 1,000 / 2,000 / 3,000 points** |
| **Excessive focus on failure** | Morning form asks *what is supposed to happen and why*; evening asks *what went well and how to improve*. Gratitude entries prime for positive signals. **AI prompts read the journal as a coaching conversation, not an audit** |

**Why the short side needs this more:** the market drifts upward over time; the short side is less forgiving. **Kaizen is not self-help — it is a survival mechanism.**

> *"Self-deception is a built-in feature that covers its own tracks."* Recurring patterns only become visible across dozens of entries. *"Repeat that entry 20 times, and we cannot ignore those symptoms of toxic shame anymore."* **The journal converts anecdote into pattern, and pattern into correctable behavior.**

---

## 4. Infrastructure

**Airtable, chosen for three reasons:** clean REST API callable from Python without an SDK; renders as a familiar spreadsheet; **form views turn any table into a mobile data-entry screen with zero front-end code.** Free tier suffices.

**Requirements:** Python 3.9+, `requests`, `pandas`. All communication via the REST API directly. Credentials in `.env`:

```
AIRTABLE_API_KEY=your_personal_access_token_here    # scopes: data.records:read, data.records:write
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX                  # from the base URL
AIRTABLE_TABLE=TradeLog
```

**Add `.env` to `.gitignore`.** On Windows, save as type **All Files** or Notepad writes `.env.txt` and the notebook won't find it.

### `TradeLog` table (case-sensitive)

| Field | Type | Purpose |
|---|---|---|
| `Ticker` | text | Stock symbol |
| `entry_date` / `exit_date` | date | **Empty `exit_date` means open** |
| `Strategy` | text | Strategy label — **position key together with ticker** |
| `Broker`, `order_type` | text | Executing broker; limit/market/stop |
| `quantity_order` / `quantity_exec` | number | **Signed** intended vs. executed quantity |
| `price_order` / `price_exec` / `price_exit` | number | Target, fill, exit fill |
| `stop_price`, `target_price`, `risk_pct` | number | Intent fields — preserved even for missed trades |
| `commission`, `gross_pnl`, `net_pnl` | number | |
| `trade_result` | text | win / loss / breakeven |
| **`missed_trade`** | text | **missed / override; blank = normal** |
| `record_id` | text | Broker execution reference |

### `journal` table (lowercase)

One row **per session per day** — a `pre` row from the morning form and a `post` row from the evening form.

**Morning form fields:** `date`, `session`, `mindset_pre` (1–5 fear/greed), `confidence_pre` (1–5), `checklist_done` (0/1), `perf_forecast` (%), `bc_1`, `bc_2`.

**Evening form fields:** `date`, `session`, `mindset_post`, `confidence_post`, `perf_actual`, `what_went_well_1/2/3`, `tomorrows_kaizen`, `notes`, `gratitude_1/2/3`.

**Computed fields:** `bulls_eye`, `score`, `streak`, `multiplier`, `final_score`.

**Field rationale:**
- **`checklist_done`** — *"the same confirmation that pilots, surgeons, soldiers check before the mission. Checklists are used by professionals whose jobs it is to save lives."*
- **`mindset_pre/post`, `confidence_pre/post`** — the **pre-vs-post delta** is the emotional-mastery tool. **The holy grail is to sit at 3 as much as possible.**
- **`perf_forecast` + `bc_1`, `bc_2`** — one-liners that force curiosity about the *drivers* of performance: a specific stock, gross or net exposure, position sizing. *"An invitation to dig deeper on how performance is actually generated."*
- **`what_went_well_1/2/3`** — *"Our brain evolved to look for the saber-tooth tiger in the bush."* Dwelling on failure makes journaling a chore. Looking for positives primes a positive outlook **and continuous improvement — we want to do more of what works.**
- **`gratitude_1/2/3`** — from *The Five Minute Journal*. **The objective is to increase financial capital and strengthen emotional capital.**

**Two operational gotchas:**
1. **Airtable's Meta API does not support `autoNumber` as a primary field.** Add it manually after setup (`tradeID` for TradeLog, `entry` for journal) and let it replace the existing primary column.
2. **Form views cannot be created programmatically** — create them once in the UI. **Form views survive table resets (record deletion); only deleting the table destroys them.** Paste the form links somewhere permanent before first running the setup notebook.

---

## 5. Part A — trade reconciliation (nightly, 10 cells)

**Cell 1 — setup.** `load_env()` reads `.env`, skips comments/blanks, sets each `KEY=VALUE` via **`os.environ.setdefault`** so **shell-exported variables are never overwritten**. Verifies all three keys.

**Cell 2 — Airtable helpers.** Three functions encapsulate every HTTP call:
- `at_list_open(ticker, strategy)` — GET open lots **sorted oldest-first** (for FIFO)
- `at_append(fields, url=None)` — POST; **strips `None`/`NaN` before sending**
- `at_patch(record_id, fields, url=None)` — PATCH by ID

**The optional `url` parameter is the design point:** Part B passes `AT_J_URL` to reuse the same functions for the journal table.

**Cell 3 — `load_csv`.** Returns an **empty DataFrame when the file doesn't exist**, so the notebook runs cleanly on day one.

**Cell 4 — the six scenarios that must be covered:**

| Ticker | Case | Description |
|---|---|---|
| KROX | **Build** | Pyramid short — adding a fourth tranche to a three-lot position |
| VEGA | **Full close** | Short entered three weeks ago, exited in full today |
| PULS | **Partial exit** | Two-lot pyramid — **FIFO closes only the oldest lot** |
| FLUX | **Reversal** | Short −150; buy +300 closes the short **and opens a new long** |
| NOVA | **Missed** | Order placed, never filled — **the Abraham Wald signal** |
| ORION | **Override** | Fill with no prior order — reactive, unplanned |

**Cell 5 — `_seed_portfolio`.** Writes existing positions as opening entries. **Checks `at_list_open` first, so it is idempotent.** *Positions built across multiple lots must be passed as separate rows, each with its own `entry_date`, so FIFO can consume them oldest-first.*

**Cell 6 — `_split_trades`.** **A single `pd.merge(how='outer', indicator=True)` on `(date, ticker, broker)` replaces three separate loops:**

```
_merge == 'both'        →  matched
_merge == 'left_only'   →  missed     (order, no fill)
_merge == 'right_only'  →  override   (fill, no order)
```

**Cell 7 — `_write_missed` / `_write_override`.** **Neither modifies the portfolio CSV.** Both write pure audit records tagged via `missed_trade` so they can be filtered and studied separately. `_write_missed` **preserves intent fields** (price, stop, target, risk); `_write_override` preserves execution fields only.

**Cell 8 — four position handlers:**

```python
def _open_new(row, port):
    """No existing position for (ticker, strategy). New TradeLog record + portfolio row."""
    at_append({'entry_date': row['date'], 'ticker': row['ticker'], 'strategy': row['strategy'],
               'broker': row['broker'], 'quantity_exec': int(row['quantity_exec']),
               'price_exec': float(row['price_exec']), 'stop_price': row.get('stop_price'),
               'target_price': row.get('target_price'), 'risk_pct': row.get('risk_pct'),
               'commission': row.get('commission')})
    new = pd.DataFrame([{'ticker': row['ticker'], 'strategy': row['strategy'],
                         'position': int(row['quantity_exec']),
                         'cost': round(float(row['price_exec']), 4), 'entry_date': row['date']}])
    return pd.concat([port, new], ignore_index=True)

def _add_lot(row, port):
    """Same direction. Weighted-average cost update."""
    at_append({...})
    mask = (port['ticker']==row['ticker']) & (port['strategy']==row['strategy'])
    op, oc = int(port.loc[mask,'position'].values[0]), float(port.loc[mask,'cost'].values[0])
    q = int(row['quantity_exec'])
    port.loc[mask,'position'] = op + q
    port.loc[mask,'cost'] = round((oc*abs(op) + float(row['price_exec'])*abs(q)) / abs(op+q), 4)
    return port

def _close_fifo(row, port):
    """Opposite direction. Consume open lots oldest-first; handles partial exits AND reversals."""
    to_close   = abs(int(row['quantity_exec']))
    price_exit = float(row['price_exec'])
    commission = float(row['commission']) if pd.notna(row.get('commission')) else 0.0
    open_lots  = at_list_open(ticker, strategy)
    if not open_lots: return port
    total_open = sum(abs(int(l['fields'].get('quantity_exec', 0))) for l in open_lots)
    remaining  = to_close
    for lot in open_lots:
        if remaining <= 0: break
        f = lot['fields']; qty = abs(int(f.get('quantity_exec', 0)))
        closed = min(qty, remaining); ep = float(f.get('price_exec', 0))
        sign = -1 if int(f.get('quantity_exec', 1)) < 0 else 1      # ← short/long P&L sign
        gpnl = round(sign * (price_exit - ep) * closed, 2)
        comm = round(commission * closed / to_close, 2)             # ← pro-rata commission
        at_patch(lot['id'], {'exit_date': row['date'], 'price_exit': price_exit,
                             'gross_pnl': gpnl, 'net_pnl': round(gpnl - comm, 2),
                             'trade_result': 'win' if gpnl>0 else 'loss' if gpnl<0 else 'breakeven'})
        remaining -= closed
    mask = (port['ticker']==ticker) & (port['strategy']==strategy)
    if to_close >= total_open:
        port = port[~mask].reset_index(drop=True)
        if to_close > total_open:                                   # ← REVERSAL
            surplus = to_close - total_open
            direction = 1 if int(row['quantity_exec']) > 0 else -1
            port = _open_new({**row, 'quantity_exec': direction*surplus}, port)
    else:                                                            # ← PARTIAL EXIT
        net = int(port.loc[mask,'position'].values[0]) + int(row['quantity_exec'])
        port.loc[mask,'position'] = net
        extra = port[(port['ticker']==ticker)&(port['strategy']==strategy)].index[1:]
        port = port.drop(extra).reset_index(drop=True)
    return port
```

**Cell 9 — `reconcile` (orchestrator).** Calls `_split_trades` once, writes the two exception categories, then routes each matched trade by comparing `sign(quantity_exec)` against the sign of the existing position:

```
no match in portfolio  → _open_new
same sign              → _add_lot
opposite sign          → _close_fifo
```

**Cell 10 — run.** In production replace sample DataFrames with `load_csv` calls on broker exports, and **make a timestamped copy of the portfolio CSV** — the save overwrites.

---

## 6. Part B — psychology analysis (weekly or on demand)

**Daily input requires no notebook.** The forms run on the phone. The notebook runs only when you want to analyze.

### The five computed fields

| Field | Formula | Meaning |
|---|---|---|
| **`bulls_eye`** | `sign(perf_forecast × perf_actual)` | +1 right call, −1 wrong, 0 neutral/missing |
| **`score`** | Weighted sum of filled fields | **Completeness reward, max 120 pts** |
| **`streak`** | Consecutive weekday entries | **One missed weekday forgiven; two consecutive misses reset to 1** |
| **`multiplier`** | `1 + streak/20` | Day 20 = 2×, day 40 = 3× |
| **`final_score`** | `score × multiplier` | Total gamified score |

**Scoring weights** — the two anchors get 20 points each because they are the most important daily habits:

```
checklist_done      20 pts    ← disciplined preparation
tomorrows_kaizen    20 pts    ← continuous improvement
gratitude tier      0 / 6 / 12 / 20 pts
text fields         5–10 pts each
────────────────────────────
maximum            120 pts
```

> **`bulls_eye` measures directional accuracy only, not forecast accuracy.** *"It takes time and training to develop a solid forecast accuracy. Let's take it one step at a time."*
>
> **A positive long-run average `bulls_eye` means directional judgment adds value beyond the systematic signal.**

**Cell 11 — `load_journal_session`.** Filter formula on `session='pre'`/`'post'`, sorted by date. **Airtable returns at most 100 records per page — follow the `offset` cursor until none is returned.** When the table is empty, **returns a DataFrame with a `date` column so the Cell 13 merge never raises `KeyError`.**

**Cell 13 — merge.** **Outer merge on `date`** so days with only a pre *or* only a post entry are kept — **nothing is silently dropped.** `merged` is initialized as an empty DataFrame **before** the guard block so Cells 14–15 always find it defined.

**Cell 14 — patch back.** Patches the five computed fields onto the **post** row; skips morning-only days. **Idempotent — patching the same values twice has no side effects.**

---

## 7. The AI layer — five prompts

**The governing principle:**

> **The AI does not evaluate performance. It looks for patterns in behavior. A bad week in P&L terms can reflect excellent psychology if execution was consistent. A strong week in P&L can mask deteriorating habits.**

| Prompt | Cadence | What it does |
|---|---|---|
| **Weekly analysis** | 5 days | Combines `bulls_eye` with reasoning quality (`bc_1`, `bc_2`). **On +1 days, compare stated reasoning against the actual session driver; on −1 days, identify whether the reasoning was structurally flawed or simply unlucky.** Explicitly: *do not evaluate P&L.* Ends with one concrete suggestion. |
| **Kaizen themes** | 30 days | Reads `tomorrows_kaizen` across days. **Determine per theme whether it recurs without evolution (intention not converting to behavior) or evolves (genuine improvement).** For the most persistent unresolved theme, suggest **one structural change — a rule, checklist item, or pre-market ritual addressing the root cause, not the symptom.** |
| **What went well** | 30 days | Most journaling systems focus on weakness. Identify the three recurring strengths and **how to systematically reinforce each.** Distinguish **structural** strengths (appear regardless of market conditions) from **conditional** ones (only on good days). *Do not comment on weaknesses.* |
| **Monthly synthesis** | 1 month | Dominant emotional pattern; **the three sessions where psychology most likely affected outcomes** (low confidence + low `bulls_eye` + weak `bc` reasoning). Two paragraphs: what's working, and the single most important pattern to address. **Focus exclusively on execution psychology — do not recommend strategy changes.** |
| **Streak recovery** | On break | What was different in the days before the gap (lower mindset scores, shorter entries, unusual notes). **Suggest one concrete friction-reduction change.** Under 200 words. |

---

## 8. TradeLog analytics — three minimal functions

> **"Focus on the losses and the profits will take care of themselves."**

None requires a live Airtable connection — they operate on a pandas DataFrame of closed trades.

### Maximum Adverse Excursion (MAE)

**Worst adverse price move from entry to exit, as % of entry price**, computed over the full holding period from **daily closes, not intraday**.

```
Short:  MAE = (max_close − entry) / entry × 100     # adverse = up
Long:   MAE = (entry − min_close) / entry × 100     # adverse = down
Clamp at 0  (a trade that never went against you has MAE = 0)
```

**Use for stop calibration:**
- **If MAE far exceeds the average stop loss → tighten stops.**
- **If the loss rate is too high → loosen stops and observe the MAE.**

**And for strategy classification — the strongest claim in the section:**

> **The MFE/MAE ratio is the most robust indicator for reclassifying strategies.**
> **Trend followers have MFE/MAE > 1. Mean reversion strategies have MFE/MAE < 1.**

(MFE = Maximum Favorable Excursion.) MAE matters most for left-skewed strategies.

### Drawdown analysis

Operates on **cumulative net P&L across closed trades in chronological order.** A drawdown period begins when cumulative P&L falls below its previous peak and ends when it recovers.

```python
cum   = net_pnl.cumsum()
peak  = cum.cummax()
dd    = (cum - peak) / peak          # negative below peak
# identify contiguous below-peak segments as distinct drawdown periods
```

Returns six metrics: `max_dd`, `avg_dd`, `max_dur` (in trades), `avg_dur`, `count`, `freq` (drawdown periods ÷ total trades).

The same three investor concerns as Ch. 9:
- **Magnitude** — never test the **stomach** of your investors
- **Frequency** — never test the **nerves** of your investors
- **Duration** — never test the **patience** of your investors

**Use `freq` to understand how much of the time you are underwater; use `max_dur` to plan how long you must psychologically tolerate a losing streak.**

### Consecutive loss analysis

Walk results in order, increment a counter on `'loss'`, append and reset on any other outcome, **flush the final counter if the log ends mid-streak.** Returns `max_run` and `avg_run`.

> **Reduce size in a losing streak to preserve emotional and financial capital.**
> **Use `max_run` to stress-test drawdown tolerance and position sizing.**

*"Every loss takes its toll on mental health. This is why it is much more important to focus on consecutive losses than wins."*

---

## 9. Transferable rules

1. **Log missed trades and overrides, not just fills.** The executed log is the surviving fleet; the missed signals are the planes that never came back.
2. **Classify with a single outer merge on (date, ticker, broker)** using `indicator=True`. Three categories fall out of one operation.
3. **Never let missed/override records mutate the portfolio.** They are pure audit rows, tagged for separate study.
4. **Preserve intent fields (price, stop, target, risk) on missed trades** — that is the data that reveals *why* you didn't act.
5. **FIFO with per-lot patching** handles pyramids, partial exits, and reversals in one code path. Pro-rate commission across closed lots; carry the position sign into the P&L calculation.
6. **Store lots as separate portfolio rows with their own `entry_date`** or FIFO cannot work.
7. **Make every write idempotent** (check-before-append, patch-same-values). Nightly jobs get re-run.
8. **Design against friction first.** Pre-populated defaults, dropdowns, phone forms. Automation everywhere data already exists.
9. **Reward completeness, not performance.** Score the process out of 120; compound a streak multiplier at `1 + streak/20`; forgive one missed weekday.
10. **Track directional accuracy (`bulls_eye`) *with* the stated reasoning.** Correct calls with bad reasoning are luck; that distinction is the whole point.
11. **Prompt the AI to analyze behavior, never P&L.** Good psychology can produce a bad week and vice versa.
12. **Ask whether kaizen entries evolve or merely repeat.** A recurring unchanged intention is a signal to make a structural change, not to try harder.
13. **Calibrate stops with MAE**, and classify strategies with **MFE/MAE** (>1 trend following, <1 mean reversion).
14. **Measure drawdowns on all three axes** (depth, duration, frequency) and consecutive losses on two (max run, average run). Size down during losing streaks.
15. **Watch the pre-vs-post mindset delta.** Sitting at 3 is the goal, not sitting at 5.

---

## 10. Cross-references

Ch. 1 the infinite game, accepting fallibility, judging a picker on what they keep · Ch. 2 emotional discipline on the short side · Ch. 5 gain expectancy, profit factor, and win-rate-vs-skew — the analytics here measure those inputs · Ch. 6 position sizing as the link between financial and emotional capital; reduce size in losing streaks · **Ch. 8 exposure management as "what you can control" (internal locus)** · **Ch. 9 the same three drawdown properties, and `max_drawdown_tolerance` which `max_run` stress-tests**.

**Named references:** Van Tharp · Carl Jung · **Abraham Wald / Statistical Research Group (survivorship bias)** · Kahneman & Tversky (loss aversion, disposition effect) · Warren Buffett (chains of habit) · Kaizen (改善) · *The Five Minute Journal*.

**Stack:** Python 3.9+, `requests` (Airtable REST API directly — no SDK), `pandas`, `pathlib`, `datetime`, `os`. Airtable free tier. Notebook: `trading-journal-v5.ipynb`.
