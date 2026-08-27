# Ch 4 — Caching

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 4.
**Governs:** what to keep close to hand, what to evict, and where to put things — across storage, workspaces, supply chains and memory.
**Thesis:** forgetting is not failure; it is **cache management**, and it has a provably good policy. The nearest thing available to clairvoyance is to assume **history repeats itself backwards** — what you used most recently is what you will need next.

---

## 1. The memory hierarchy

The founding trade-off is **size against speed**. Burks, Goldstine and von Neumann proposed the fix in 1946: since limitless fast storage is impossible, build *"a hierarchy of memories, each of which has greater capacity than the preceding but which is less quickly accessible."*

The library is the everyday instance: rather than returning to the stacks each time, you check books out to your desk. **The desk is a cache.**

**Why the pressure keeps rising:** Moore's Law improved processing, but memory speed did not keep pace, so the *relative* cost of fetching from main memory grows exponentially. By the 1990s this was called the **memory wall**. The defence has been ever more elaborate hierarchies — modern phones and laptops run roughly **six levels**.

> **Even unlimited fast memory would not remove the need for caches.** Size alone impairs speed: *"If you make a city bigger, it takes longer to get from point A to point B."* (Hennessy) Processors carry two on-chip cache levels for exactly this reason.

---

## 2. Eviction — what to throw out

Bélády's 1966 paper (the most-cited work in computer science for fifteen years) defines the target: minimise **cache misses**. And the optimal policy is trivially statable and useless:

> **Evict whatever you will need again longest from now.**

That is **Bélády's Algorithm** — *clairvoyant*, requiring data from the future. Engineers joke about "implementation difficulties." The real question is what comes closest without it.

| Policy | Rule | Martha Stewart's version |
|---|---|---|
| **Random Eviction** | Overwrite at random | — |
| **FIFO** | Evict what has been there longest | *"How long have I had it?"* |
| **LRU** | Evict what has gone longest untouched | *"When was the last time I used it?"* |

Two findings worth carrying:

1. **Random eviction is "not half bad."** Merely *having* a cache makes a system more efficient, however you manage it — frequently used items find their way back in regardless. Do not let the search for the right policy prevent you from having a cache at all.
2. **LRU consistently performs closest to clairvoyance**, and beats FIFO decisively. Stewart's two questions are not interchangeable; **one of them is much better than the other**.

**Why LRU works: temporal locality.** If something was needed once, it is likely to be needed again soon. This holds for how machines solve problems (loops) and for how people do (switching among a handful of applications).

> **Unless you have good reason to think otherwise, your best guide to the future is a mirror image of the past.**

You already rely on this: window Z-order, and the Alt-Tab / Command-Tab list, are both LRU.

---

## 3. Placement — where to put what you keep

**Turn the library inside out.** Most libraries display *newly acquired* books in the lobby — a FIFO cache, privileging what was last *added*. But by temporal locality, the most valuable shelf in the building is the **rough-sorting area of recently returned books**, which is hidden from patrons and continuously dismantled by staff doing their jobs. Put acquisitions in the back and recent returns in the lobby: more efficient *and* more socially interesting, since the campus would encounter what the campus is actually reading.

**Caching is about proximity, not only speed.** No difference in storage material is needed for a cache to pay — scarcity of *nearness* is enough.

- **Akamai** handles roughly a quarter of all internet traffic by keeping copies near users. *"It's our belief — and we build the company around the fact — that distance matters."* An Australian streaming the BBC never reaches London.
- **Amazon warehouses** deliberately abandon human-legible organisation — batteries beside pencil sharpeners, located by barcode — with **one exception**: high-demand items sit in a separate, faster-access area. That area is the cache. Their "anticipatory package shipping" patent is a CDN for physical goods: ship regionally popular items to a regional warehouse *before* anyone orders. Predicting one person is hard; predicting a few thousand is the law of large numbers.
- **Netflix** local favourites: people overwhelmingly watch films set where they live, so the files live there too.

**At home,** three moves follow directly:

1. **Use LRU, not FIFO, to decide what to discard.** Keep the college T-shirt you still wear occasionally; release the trousers untouched for years.
2. **Exploit geography** — put things in the cache nearest where they are used. The doctor who keeps vacuum bags *behind the living-room couch* looks eccentric and is right: that is where the vacuum is used and where the bag runs out.
3. **Build multiple levels** — closet, basement, storage locker, in decreasing access speed, with LRU governing demotion between them. And consider adding a level *faster* than the closet: a valet stand is a one-outfit cache.

---

## 4. Arrangement — the pile is optimal

The unanimous advice from organising experts is to group **like with like**. Yukio Noguchi's system does the opposite: *"a very fundamental principle in my method is **not** to group files according to content."*

**The Noguchi filing system:** insert every file at the **left-hand end** of the box. When you use a file, return it to the left. Search from the left. It began as laziness — reinserting where it came from was harder — and turned out to be efficient.

Computer science supplies the guarantee that organising gurus cannot. The relevant problem is **self-organising lists** (Sleator & Tarjan, 1985): search linearly from the front, then replace the item anywhere.

> **If you always return the item to the front, your total search time will never exceed twice what it would have been with perfect knowledge of the future.** No other algorithm offers that guarantee.

So Noguchi's system is not merely efficient — it is **optimal within a factor of two of clairvoyance**.

**Now turn the box on its side and it becomes a pile.** Piles are searched top-down, and used items go back on top — which is exactly LRU.

> The heap of papers on your desk is not a guilt-inducing mess. It is a **self-organising mess**, and tossing things back on top is the best you can do short of knowing the future. You do not need to organise it. **You already have.**

Note this is a *different* argument from Ch. 3's "err toward messiness". There the point was that sorting may not be worth its cost; here the point is that the apparent mess **is already the right structure**.

Practical corollary: set your file browser to sort by **Last Opened** rather than **Name**.

---

## 5. Human memory is a cache

Ebbinghaus (1879) established the **forgetting curve** by memorising nonsense syllables and testing himself for a year. It described the shape but explained nothing.

**Anderson's reframing:** the constraint is not storage but **organisation**. The mind has effectively unlimited capacity but finite time to search — a library with one arbitrarily long shelf, where what sits near the front is found fastest. **Good memory then requires the same thing as a good cache: predicting what will be needed.**

**The striking empirical result** (Anderson & Schooler): they ran Ebbinghaus-style analysis not on minds but on *environments* — New York Times headlines, parents speaking to children, and an email inbox. In every one, a word is most likely to recur right after use, with likelihood decaying over time.

> **Reality itself has a statistical structure that mimics the forgetting curve.** Which suggests the curve is not a defect but **a precise tuning of the brain to the world**, keeping available exactly what is most likely to be needed.

*"In any system responsible for managing a vast data base there must be failures of retrieval. It is just too expensive to maintain access to an unbounded number of items."*

---

## 6. The tyranny of experience

If the constraint is organisation and the brain is well tuned, then much of what is called **cognitive decline** is something else.

Ramscar's group showed by simulation that **simply knowing more makes recognition slower** — of words, names, even letters. No organisational scheme escapes it: more items means longer search.

The scale is easy to underestimate. A two-year-old knows ~200 words; an adult ~30,000. A child has two dozen schoolmates; an adult has thousands of contacts across several cities. Each year adds a third of a million waking minutes of episodic memory.

> **Older brains are literally solving harder computational problems every day.** *"It's not that we're forgetting; it's that we're remembering. We're becoming archives."* And: *"A lot of what is currently called decline is simply learning."*

The vocabulary correction is the useful part: say **cache miss**, not "brain fart". The occasional lag is the visible price of having everything else at the front of your mind — and its rarity is evidence the arrangement is working.

---

## Transferable rules

1. **Build a hierarchy rather than choosing between fast and large.** Small-and-fast backed by large-and-slow beats either alone, and applies to physical storage as much as digital.
2. **Have a cache even if you cannot manage it well.** Random eviction is far better than nothing; do not let policy debates block the basic structure.
3. **Evict by Least Recently Used, not First In First Out.** "When did I last use it?" is a much better question than "how long have I had it?", though both sound equally sensible.
4. **Assume temporal locality unless you know otherwise** — what was just used is most likely to be used next, and the longest-untouched is the safest to discard.
5. **Treat recency as your substitute for clairvoyance.** Where the future is unknown, the reversed past is the best available predictor.
6. **Cache by proximity, not just by speed.** When nearness is the scarce resource, keeping copies near the point of use is the whole win.
7. **Place items in the cache closest to where they are used**, even when that violates category logic. Vacuum bags behind the couch beats vacuum bags with the cleaning supplies.
8. **Add levels above and below your main cache**, and demote between them by LRU.
9. **Do not group like with like by default.** Content-based grouping costs sorting time and delivers no retrieval guarantee.
10. **Always return a used item to the front.** This bounds your worst-case search time at twice the theoretical optimum — a guarantee no other placement rule provides.
11. **Recognise a working pile as a self-organising structure**, not disorder to be corrected. Reorganising it by category makes retrieval worse.
12. **Display collections by last-accessed rather than alphabetically**, wherever the interface allows it.
13. **Surface what was recently *used*, not what was recently *added*.** Most displays privilege new arrivals; recency of use is the better predictor of demand.
14. **Predict aggregate demand rather than individual demand** when pre-positioning resources — the law of large numbers makes the group tractable where the person is not.
15. **Expect retrieval to slow as expertise grows, and do not read it as decline.** A larger store is a harder search problem; the lag is evidence of the size of the archive, not the failure of the mechanism.

---

## Cross-references

Ch. 1 optimal stopping — deciding when to stop searching · Ch. 3 sorting — when ordering is worth its cost at all, and the complementary case for messiness · Ch. 6 Bayes's Rule — predicting recurrence from history · Ch. 7 overfitting — why remembering everything is not the goal.

**Named references:** Burks, Goldstine & von Neumann (1946 memory hierarchy) · Atlas supercomputer (1962) · Maurice Wilkes (the cache idea) · IBM 360/85 (the name) · László Bélády (1966, optimal eviction) · Gordon Moore · John Hennessy · Daniel Sleator & Robert Tarjan (1985, self-organising lists) · Yukio Noguchi (filing system) · Hermann Ebbinghaus (1879, forgetting curve) · John Anderson & Lael Schooler · Michael Ramscar · Akamai (Stephen Ludin) · Aza Raskin · Rik Belew · William Jones, *Keeping Found Things Found*.
