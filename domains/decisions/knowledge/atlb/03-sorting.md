# Ch 3 — Sorting

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 3.
**Governs:** whether to impose order at all, and if so at what cost — over information, possessions, and people.
**Thesis:** sorting has **dis**economies of scale, and its only justification is the searching it saves later. Since search is often cheap, **the right amount of order is frequently less than none at all**. And when what is being sorted is people, the choice between comparison and measurement is the choice between a fight and a race.

---

## 1. Scale hurts — the one counterintuitive fact

Ordinary intuition says bulk is efficient: cooking for two is barely harder than for one. **Sorting inverts this.** Sorting a hundred books takes *longer* than sorting two shelves of fifty — twice the items, and twice as many places each could go.

> *"To lower costs per unit of output, people usually increase the size of their operations… [but with sorting] the unit cost of sorting, instead of falling, rises."* (Hosken, 1955)

**The first lever is therefore never the algorithm — it is the batch size.** Doing laundry three times as often cuts sorting overhead roughly ninefold. Before optimising how you sort, ask whether you can sort less at a time.

---

## 2. Big-O — a yardstick for the worst case

Records care about the **best** case; computer science almost always cares about the **worst**, because worst-case bounds are what let you make guarantees. Big-O is deliberately imprecise: it discards constants to expose the *shape* of the relationship between size and cost.

| Class | Name | Dinner-party analogy |
|---|---|---|
| O(1) | constant | Cleaning the house — same work regardless of guests |
| O(n) | linear | Passing the roast — twice the guests, twice the time |
| O(n²) | quadratic | Everyone hugs everyone |
| O(2ⁿ) | exponential | Each guest doubles the work |
| O(n!) | factorial | Discussed mainly as a joke |

Crucially, **any linear factor swamps all constant factors**. Remodelling your dining room for three months and then passing the roast once is, at scale, equivalent to just passing the roast. This is the right instinct for large n, and the wrong instinct for small n — a caveat worth carrying.

---

## 3. The algorithms

| Algorithm | Cost | Idea |
|---|---|---|
| **Bubble Sort** | O(n²) | Repeatedly swap adjacent out-of-order pairs |
| **Insertion Sort** | O(n²) | Take items one at a time, insert each into its place |
| **Mergesort** | **O(n log n)** | Sort pairs, merge into fours, eights… "linearithmic" |
| **Bucket Sort** | **O(n)** | Group into m coarse buckets; no intra-bucket order |

**Mergesort is the ceiling for comparison sorting.** It is proven that fully ordering n items via head-to-head comparisons cannot be done in fewer than O(n log n) comparisons — a hard limit, not a lack of cleverness.

The improvement is not marginal. At census scale, linearithmic vs. quadratic is the difference between **29 passes and 300 million**. Mergesort also parallelises cleanly: split the books among friends, each sorts a pile, then merge pairwise.

**Bucket Sort beats the limit by not obeying its premise** — it does no item-to-item comparison and does not fully order anything. Grouping n items into m buckets costs O(nm), which rounds to linear when m is small.

> **The key to breaking the barrier is knowing the distribution in advance.** Badly chosen buckets achieve nothing (all books in one bin = no progress). Well-chosen ones split the load evenly.

Both real-world experts do exactly this. The Preston Sort Center runs **167 books/minute, 85,000/day into 96 bins**, with bin allocation driven by circulation statistics. Berkeley's student sorters bucket by call-number range using learned expectations of what the pile contains, then Insertion Sort the final ~25 books.

---

## 4. The central trade-off: sort is prophylaxis for search

> **The effort spent sorting is a pre-emptive strike against the effort of searching later.**

Which yields the chapter's most useful and least intuitive advice:

> ### Err on the side of messiness.
> **Sorting something you will never search is a complete waste; searching something you never sorted is merely inefficient.**

The asymmetry is the whole argument. One error is total, the other partial.

**When heavy sorting *is* right — the Google case.** All three conditions hold: (a) the data will certainly be searched, (b) repeatedly, and (c) sort time is cheaper than search time (machines sort in advance; users wait in the moment). Search engines are really *sort* engines: their advantage was never finding your text but ranking what it found.

**When it is wrong — the bookshelf and the inbox.** Domestic shelves meet none of the conditions: rare searches, low cost of an unsorted scan, and — decisively — **we search with quick eyes and sort with slow hands.** Whittaker's study, "Am I Wasting My Time Organizing Email?", answered emphatically *yes*. As search costs fall, sorting loses value.

> Mess is not always procrastination deferring a cost to your future self. **Sometimes mess is the optimal choice.**

---

## 5. Sorting people — tournaments as algorithms

| Format | Algorithm | Cost | Produces |
|---|---|---|---|
| Round-Robin | Comparison Counting | O(n²) | Full, robust ranking |
| Ladder | Bubble Sort | O(n²) | Full ranking |
| Bracket (March Madness) | Mergesort-ish | O(n log n) if complete | — |
| **Single Elimination** | — | **O(n)** — exactly n−1 games | **First place only** |

**Dodgson's complaint (Lewis Carroll, 1883): the silver medal is a lie.** The true second-best could be anyone the champion eliminated, not merely the last one. His numbers: the chance the second-best player gets second prize is **16/31**, and the odds against the top four all placing correctly are **12 to 1**.

March Madness runs 63 games, not the ~192 a full Mergesort would need, precisely because it leaves everyone but the winner unsorted. That is the trade: linear time, one answer.

**But minimising comparisons is not always the objective.** Michael Trick, who schedules MLB and NCAA conferences, points out that leagues deliberately run O(n²) seasons and design schedules so that **uncertainty is resolved as late as possible** — divisional rivals play each other in the final five weeks specifically to keep races alive. *In computer science an unnecessary comparison is waste. In sport, the games are the point.*

---

## 6. Noise — when efficiency becomes brittleness

Every algorithm above assumes flawless comparison. Allow a **noisy comparator** and the rankings invert.

The magnitudes are startling:

- In baseball, *"a team is going to lose 30% of their games and win 30% practically no matter who they are."*
- If the stronger team wins 70% of the time and a title needs 6 straight wins, the best team's chance of winning the tournament is 0.70⁶ ≈ **12%** — it would crown the truly best team about **once a decade**.
- In soccer, a **3:2** result gives the winner only a **5-in-8** chance of being the better team; even a **6:1** blowout leaves a **7%** chance of a fluke.

> **Mergesort's efficiency is exactly what makes it fragile.** Each comparison moves an item a long way, so an early error is catastrophic and permanent — like a first-round upset relegating a strong team to the unsorted bottom half. Bubble Sort's inefficiency — moving items one position at a time — makes it *robust*: a fluke costs one place.

**The most noise-robust sorting algorithm known is Comparison Counting Sort** — compare everything to everything, rank by tally. Quadratic, unfashionable, and exceptionally fault-tolerant. It is also, exactly, a **round-robin regular season**.

Hence the sports-bar verdict: *championship rings are not robust; divisional standings are as robust as it gets.* Losing in the playoffs is tough luck. **Missing the playoffs is tough truth.**

---

## 7. Dominance hierarchies are decentralised sorting

When no authority imposes order, sorting emerges from below — and it is the same trade-off.

**A pecking order is "the violence that preempts violence."** Establishing rank ahead of time is cheaper than fighting over every resource. **Displacement** — a subordinate leaving before a confrontation occurs — is the payoff, and it is precisely search-avoidance: the cost was paid at sort time.

Consequences that follow directly from the mathematics:

- **Confrontations grow at least logarithmically and perhaps quadratically with group size.** Studies of hens confirm aggressive acts per bird rise with flock size. **Ethical husbandry may therefore mean capping group size** — feral chickens roam in groups of 10–20, far below commercial flocks.
- **Debeaking backfires.** It removes the ability of individual fights to *resolve* the order, so the flock can never finish sorting and aggression *increases*.
- **Dominance hierarchies are information hierarchies** (Flack). Fights are minimised only insofar as every individual holds a detailed *and matching* model of the order. Where models disagree, conflict resumes — which is exactly why online poker cash games happen only when two players' rankings differ.

---

## 8. A race instead of a fight — ordinal to cardinal

The escape from all of this is to stop comparing and start **measuring**.

A marathon sorts tens of thousands of competitors in a single event; a round-robin among ten thousand would need a hundred million matchups. An Olympic boxer risks concussion O(log n) times; a ski jumper makes a **constant** number of gambles regardless of field size.

> **Moving from ordinal numbers (rank) to cardinal ones (measure) orders a set without pairwise comparison at all.** Having a benchmark — *any* benchmark — solves the problem of scaling a sort.

Examples of the same move: money (making software installations and oil futures comparable), the Fortune 500, national GDP setting G20 invitations, the maritime **Law of Gross Tonnage** (the smaller ship gives way), "respect your elders", and Silicon Valley's *"you go to the money, the money doesn't come to you"* — which lets any two people know who defers to whom without negotiating.

Benchmarks are always crude and imperfect. **That is not the point.** Their existence converts a linearithmic number of confrontations into a single reference — and where status disputes take military form, that saves not just time but lives.

Fish do this naturally: the bigger one is dominant, *"it's very simple"* — and because it is simple, it is peaceful. Chickens and primates shed blood; fish do not.

> The daily rat race is much bemoaned. **The fact that it is a race rather than a fight is a large part of what separates us from the monkeys, the chickens — and the rats.**

---

## Transferable rules

1. **Expect dis-economies of scale in any ordering task.** Doubling the batch more than doubles the work, which inverts the usual instinct to batch things up.
2. **Reduce the batch before optimising the method.** Sorting more often in smaller quantities beats a cleverer algorithm most of the time.
3. **Analyse the worst case, not the average or the best,** whenever you need to make a guarantee.
4. **Judge cost by growth class, not by constants** — but remember Big-O deliberately ignores constants, so it misleads at small n.
5. **Never sort what you will not search.** Sorting the unsearched is total waste; searching the unsorted is merely inefficient. Given uncertainty, **err toward messiness**.
6. **Justify heavy up-front sorting against three conditions**: it will certainly be searched, repeatedly, and sort time is cheaper than search time. Google clears all three; your bookshelf and inbox clear none.
7. **As search gets cheaper, sorting loses value.** Reassess filing habits whenever search improves, rather than carrying them forward.
8. **Use coarse buckets before fine ordering**, and derive the buckets from the known distribution — good buckets split the load evenly, bad ones achieve nothing.
9. **Do not confuse a single-elimination winner with a ranking.** Such a format determines first place and leaves everything else unsorted; second place is not evidence.
10. **Under noisy comparison, prefer robust methods over efficient ones.** Efficiency moves items far per comparison, so early errors become permanent.
11. **Trust accumulated round-robin standings over knockout results.** The long tally is the fault-tolerant measurement; the bracket is a lottery weighted by skill.
12. **Compute how much a series result actually establishes** before treating it as evidence of quality — six 70% rounds confer only ~12% confidence.
13. **Minimising comparisons is not always the objective.** Where the comparisons themselves have value, or where sustained uncertainty is the product, more of them is correct.
14. **Expect conflict to grow super-linearly with group size**, and treat capping group size as a legitimate intervention.
15. **Do not remove a group's means of resolving rank** and expect less conflict; an unfinishable sort produces more.
16. **Replace comparison with measurement wherever possible.** Any shared benchmark — however crude — converts a fight into a race and collapses the cost of establishing status from linearithmic to constant.

---

## Cross-references

Ch. 1 optimal stopping — another explicit cost-of-search calculation · Ch. 4 caching — what to keep near to hand once you stop sorting · Ch. 5 scheduling — ordering work rather than objects · Ch. 8 relaxation — accepting an approximate order to make the problem tractable · Ch. 11 game theory — hierarchies as equilibria.

**Named references:** Herman Hollerith (1890 census; the firm that became IBM) · John von Neumann (Mergesort, 1945) · J. C. Hosken (1955) · Charles Dodgson / Lewis Carroll (1883, "Lawn Tennis Tournaments") · Michael Trick (MLB/NCAA scheduling) · Dave Ackley (robustness) · Steve Whittaker (email) · Jessica Flack (information hierarchies) · Christof Neumann (macaque displacement) · Isaac Haxton (poker rankings) · Tom Murphy (soccer noise) · Preston Sort Center, King County Library System.
