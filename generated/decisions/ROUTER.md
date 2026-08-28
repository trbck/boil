# Knowledge Router — Decision-making under uncertainty

Always-loaded map of this domain's corpus. Resolve a question to a small number of chapters, sections or rule shards, then load only those.

_Applying computer science to human decisions: when to stop searching, how to balance exploring against exploiting, sorting and caching, scheduling, Bayesian prediction, overfitting, constraint relaxation, deliberate randomness, and strategic interaction._

`domain: decisions`  ·  `corpus: 87eac9868cae`

## Packs

| Pack | Kind | Title | Authoritative on |
|---|---|---|---|
| `atlb` | book | Algorithms to Live By | `stopping`, `explore_exploit`, `scheduling`, `prediction`, `overfitting`, `relaxation`, `randomness`, `networking`, `game_theory` |

When packs disagree, prefer the one authoritative on the topic in question — and say that a disagreement existed. See `domains/decisions/conflicts.md`.

## Rule shards

| Topic | Rules | ~Tokens | File |
|---|---|---|---|
| `congestion` | 18 | ~492 | `generated/rules/congestion.md` |
| `explore_exploit` | 16 | ~513 | `generated/rules/explore_exploit.md` |
| `memory` | 19 | ~607 | `generated/rules/memory.md` |
| `ordering` | 18 | ~538 | `generated/rules/ordering.md` |
| `overfitting` | 17 | ~530 | `generated/rules/overfitting.md` |
| `prediction` | 16 | ~508 | `generated/rules/prediction.md` |
| `process_design` | 22 | ~683 | `generated/rules/process_design.md` |
| `randomness` | 20 | ~560 | `generated/rules/randomness.md` |
| `relaxation` | 18 | ~589 | `generated/rules/relaxation.md` |
| `scheduling` | 23 | ~710 | `generated/rules/scheduling.md` |
| `stopping` | 21 | ~672 | `generated/rules/stopping.md` |
| `strategic` | 20 | ~589 | `generated/rules/strategic.md` |

## Book chapters

| ID | Title | Governs | Topics | Rules |
|---|---|---|---|---|
| `ATLB-00` | Introduction: Algorithms to Live By | the frame for every other chapter — what an algorithm is, when borrowing one from computer science is legitim… |  | 9 |
| `ATLB-01` | Optimal Stopping | when to stop searching and commit, in any process where options arrive one at a time and passing means losing… | `stopping` | 15 |
| `ATLB-02` | Explore/Exploit | how to divide effort between trying new options and using the best one you have found, whenever the same choi… | `explore_exploit` | 15 |
| `ATLB-03` | Sorting | whether to impose order at all, and if so at what cost — over information, possessions, and people. | `ordering` | 16 |
| `ATLB-04` | Caching | what to keep close to hand, what to evict, and where to put things — across storage, workspaces, supply chain… | `memory` | 15 |
| `ATLB-05` | Scheduling | what to do, in what order, on a single machine — which is to say, how one person spends a day. | `scheduling` | 20 |
| `ATLB-06` | Bayes's Rule | predicting from very little evidence — often a single observation — and knowing which prediction rule the sit… | `prediction` | 14 |
| `ATLB-07` | Overfitting | how hard to think, how many factors to weigh, and how much to trust any measurement standing in for what you… | `overfitting` | 16 |
| `ATLB-08` | Relaxation | what to do once a problem is proven too hard to solve exactly — which is the normal case for real optimisatio… | `relaxation` | 13 |
| `ATLB-09` | Randomness | when to stop reasoning and start sampling — and how much chance to inject, in what form, at what point. | `randomness` | 16 |
| `ATLB-10` | Networking | communication under unreliability and overload — acknowledgment, retry, congestion, and queues, whether betwe… | `congestion` | 18 |
| `ATLB-11` | Game Theory | decisions where the outcome depends on what other people do — and where the cost of strategising is itself pa… | `strategic` | 20 |
| `ATLB-12` | Computational Kindness | how to judge your own decisions after the fact, and how to design problems — for yourself and for other peopl… | `process_design` | 16 |

## Notes & reports

_None yet. Drop markdown in `inbox/` and run `python3 scripts/ingest.py`._

## Standing caveats

- **`atlb`** — Popular-science synthesis, not a primary source. It reports results from optimal stopping, bandit theory, scheduling and Bayesian statistics accurately but informally; cite it for the decision heuristic, not for a proof.
- **`atlb`** — Numeric thresholds (37%, Gittins indices, Bayes rules) assume the stated model. Check the assumptions hold before transferring a constant.

## Retrieval

```bash
python3 scripts/lookup.py --domain decisions --search "..."
python3 scripts/lookup.py --rule ATLB-00-R1
python3 scripts/lookup.py --chapter ATLB-00
python3 scripts/lookup.py --section ATLB-00§1
```
