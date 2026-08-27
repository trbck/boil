# Ch 8 — Relaxation

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 8.
**Governs:** what to do once a problem is proven too hard to solve exactly — which is the normal case for real optimisation.
**Thesis:** when the perfect answer is unreachable, **neither grind forever nor give up: solve a deliberately easier problem instead.** Relaxation is wishful thinking done *consciously*, with the bonus that it yields bounds telling you how far from optimal you actually are.

---

## 1. Some problems are genuinely hard

Meghan Bellows realised her wedding seating chart was literally the protein-design problem from her PhD: guests as amino acids, relationships as binding energies. She scored every pair (0 unacquainted, 1 acquainted, 50 a couple), set constraints on table size and a minimum table score so no table became the awkward miscellaneous one, and maximised total relationship score.

**107 guests, 11 tables: about 11¹⁰⁷ arrangements** — a 112-digit number, more than 200 billion googols, dwarfing the merely 80-digit count of atoms in the observable universe. A lab cluster ran 36 hours and evaluated a vanishing fraction. It almost certainly never saw the optimum.

**It was still worth doing.** The output *"identified relationships that we were forgetting about"* — it proposed moving her parents off the family table to sit with old friends they hadn't seen in years, which nobody had considered. (The mother of the bride still made manual tweaks.)

### The formal boundary

The **Cobham–Edmonds thesis**: an algorithm is **efficient** if it runs in **polynomial time** — O(n²), O(n³), n to any fixed power. A problem is **tractable** if such an algorithm is known, **intractable** otherwise.

> **The central insight: the difficulty of a problem can be quantified. And some problems are just hard.** At anything but the smallest scale, intractable problems are beyond any computer, however powerful.

Note the reversal from Ch. 3, where O(n²) was the thing to escape: **here it counts as efficient.** The dividing line is not between fast and slow but between *polynomial* (n-to-the-something) and *exponential* (something-to-the-n). An exponential always overtakes a polynomial eventually — 2ⁿ passes n¹⁰ once you get past a few dozen items.

The travelling salesman problem — Lincoln's judicial circuit, the delivery-drone problem, whatever era names it — resisted the field's best minds for decades. Brute force is O(n!), *"the computational equivalent of sorting a deck of cards by throwing them in the air until they happen to land in order."* Karp linked it in 1972 to a borderline class never proven either way; no efficient solution has been found and most computer scientists believe none exists.

> **Intractability is not permission to stop.** Lenstra: *"When the problem is hard, it doesn't mean that you can forget about it, it means that it's just in a different status. It's a serious enemy, but you still have to fight it."*

---

## 2. Constraint Relaxation — remove a rule

Delete some constraints, solve the problem **you wish you had**, then bring the constraints back.

**On the travelling salesman:** let the salesman revisit towns and retrace steps for free. The result is the **minimum spanning tree**, which computes almost instantly. Two payoffs:

1. **A lower bound.** The relaxed answer can never be longer than the real one. A 100-mile spanning tree means the true route is at least 100 miles — so a found route of 110 miles is **at most 10% off optimal**, and you know that *without knowing the optimum*.
2. **A starting point.** The spanning tree is among the best places to begin the real search. This is how the world-scale travelling salesman problem — the shortest route visiting every town on Earth — was solved to **within 0.05%** of an optimum nobody knows.

**The human form is already familiar:** *What would you do if you weren't afraid? If you could not fail? If you won the lottery? If all jobs paid the same?*

> These are not idle daydreams. They are constraint relaxation: **make the intractable tractable in an idealised world, then port the answer back.**

---

## 3. Continuous Relaxation — allow fractions

Discrete problems — this town or that, table five or table six, a fire truck or no fire truck — are where things get hard. *"That's where a lot of problems become computationally hard, when you can't do half of this and half of that."*

Two canonical instances, both intractable:

- **Fire truck coverage** — the smallest set of locations from which every house is reachable in five minutes.
- **Party invitations** — the smallest subgroup of friends who between them know everyone else, so "bring everyone we know" reaches the whole circle. **The same problem as choosing whom to vaccinate** to protect a population, and as targeting political or marketing messages.

**The relaxation:** allow fractional answers. Send someone a quarter of an invitation, place π fire trucks. That is meaningless as an answer — but it computes, and you can convert back two ways:

- **Round** — invite everyone allocated half an invitation or more.
- **Treat as probability** — flip a coin where the solution says half a truck.

**And you get a guarantee:** rounding the invitation problem sends **at most twice** the optimal number of invitations while still reaching everyone.

> Not a magic bullet — only approximations. But *"delivering twice as many mailings or inoculations as optimal is still far better than the unoptimised alternatives."*

---

## 4. Lagrangian Relaxation — turn rules into costs

The most powerful of the three, and the most transferable.

An optimisation problem has **rules** and **scorekeeping**. Lagrangian Relaxation moves some rules **into the scoring**:

> **Take the impossible and downgrade it to costly.** Where the constraints say *"Do it, or else!"*, Lagrangian Relaxation replies: **"Or else what?"**

Brian's mother put it in one line: *"Technically, you don't have to do anything. You don't have to do what your teachers tell you… You don't even have to obey the law. There are consequences to everything, and you get to decide whether you want to face those consequences."*

**How Michael Trick actually schedules Major League Baseball and NCAA conferences.** The problem is far too complex for brute force, and continuous relaxation is useless here — *"if you end up with fractional games, you just don't get anything useful."* The integer constraints cannot bend. **So the constraints that bend are the league's own preferences.**

The revealing part is how declared-hard constraints dissolve under examination:

> *"Generally, when people first come to us with a sports schedule, they will claim 'We never do x and we never do y.' Then we look at their schedules and we say, 'Well, twice you did x and three times you did y last year.' Then 'Oh, yeah, well, okay. Then other than that we never do it.' And then we go back the year before…"*
>
> People in baseball believe the Yankees and Mets are never home at the same time. **It has never been true** — it happens three to six games a year, and across an 81-game home season people simply forget.

**The rock band version:** cramming songs into a set is the **knapsack problem**, famously intractable. Playing past curfew and paying the fine is a Lagrangian Relaxation — and *"even when you don't commit the infraction, simply imagining it can be illuminating."*

---

## 5. Why relaxation works

**It gives bounds from both directions.** The relaxed answer bounds how good the true answer could possibly be; the reconciled answer bounds how bad your practical solution is. Imagining you can teleport across town instantly establishes that **eight one-hour meetings is the absolute ceiling for a day** — useful for setting expectations before confronting the real calendar.

**It is wishful thinking with the sign flipped.** Booker's account of unconscious wishful thinking runs *dream → frustration → nightmare → explosion*. Relaxation is *"all about being consciously driven by wishful thinking"* — and the consciousness is what makes the difference, because a relaxation is designed from the start to be reconciled with reality.

| Technique | Move | Reconcile by |
|---|---|---|
| **Constraint Relaxation** | Delete a rule entirely | Use as bound and starting point |
| **Continuous Relaxation** | Allow fractions between discrete options | Round, or treat as probabilities |
| **Lagrangian Relaxation** | Convert a rule into a penalty | Pay the cost where it is worth it |

---

## Transferable rules

1. **Establish whether the problem is tractable before committing effort to an exact answer.** Difficulty is a measurable property, and many ordinary problems have no efficient solution.
2. **Treat intractability as a change of method, not as defeat.** The response is to relax, not to abandon or to grind.
3. **Solve the problem you wish you had first**, then bring the constraints back. If you cannot solve what is in front of you, solve an easier version and see whether it offers a starting point.
4. **Use the relaxed answer as a bound.** Knowing the best conceivable outcome tells you how far from optimal your practical answer is, without ever finding the optimum.
5. **Ask the fantasy questions deliberately** — what would you do without the fear, the money constraint, the travel time — as an analytical step rather than as consolation.
6. **When forced into either/or, imagine the blend, then round.** A fractional solution is not an answer, but converting it back is usually cheap and often provably close.
7. **Convert probabilities into decisions where averages cannot apply**, rather than discarding a fractional result as meaningless.
8. **Accept a bounded multiple of optimal.** Twice the optimal number of invitations or vaccinations, computed quickly, beats an unattainable perfect answer.
9. **Ask "or else what?" of every hard constraint.** Turning a prohibition into a priced penalty is what makes an intractable problem tractable.
10. **Audit which constraints are genuinely inviolable.** Stated absolutes frequently turn out to have been violated repeatedly and forgotten — check the record before designing around them.
11. **Consider paying a known penalty rather than accepting a large loss** to satisfy a rule; and note that merely imagining the infraction clarifies the real cost.
12. **Expect a good process to surface options nobody proposed.** The value of optimisation on an intractable problem is often the unconsidered arrangement, not the optimum.
13. **Distinguish conscious from unconscious wishful thinking.** Relaxation works because it is designed to be reconciled with reality; fantasy that is never reconciled ends in the collapse Booker describes.

---

## Cross-references

Ch. 3 sorting — where O(n²) was the enemy rather than the standard of efficiency · Ch. 5 scheduling — where 84% of classified problems are intractable, making relaxation the normal case · Ch. 7 overfitting — accepting a worse fit for a better outcome · Ch. 9 randomness — the other principal strategy for intractable problems · Ch. 11 game theory — constraints as equilibria.

**Named references:** Meghan Bellows (wedding seating) · Abraham Lincoln's Eighth Judicial Circuit · Karl Menger · Hassler Whitney · Merrill Flood · Julia Robinson (1949, "travelling salesman" in print) · Jack Edmonds & Alan Cobham (Cobham–Edmonds thesis) · Richard Karp (1972) · Jan Karel Lenstra · Joseph-Louis Lagrange · Michael Trick / Sports Scheduling Group · Laura Albert McLay (fire truck coverage) · Christopher Booker.
