# Ch 12 — Computational Kindness

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Conclusion.
**Governs:** how to judge your own decisions after the fact, and how to design problems — for yourself and for other people — that are cheap to solve.
**Thesis:** three things follow from taking the computational view seriously. Some algorithms transfer directly. **A good process is a defence even when the outcome is bad.** And since we hand each other computational problems constantly, we can choose to hand over easy ones — *"computation is bad,"* and reducing someone's mental labour is a form of kindness.

> *"Relief by machines from many of our present demanding intellectual functions will finally give the human race time and incentive to learn how to live well together."* — Merrill Flood

---

## 1. Three pieces of wisdom

Any dynamic system under the constraints of space and time faces the same unavoidable problems, and those problems are computational — *"which makes computers not only our tools but also our comrades."*

**First: some algorithms port over directly.** The 37% Rule, Least Recently Used for an overflowing cache, the Upper Confidence Bound as a guide to exploration.

**Second: knowing you used an optimal algorithm should be a relief even when you did not get what you wanted.**

> **The 37% Rule fails 63% of the time.** LRU does not guarantee you find what you're looking for — *neither would clairvoyance*. UCB does not eliminate regret, only ensures it accumulates ever more slowly.

**This is why computer scientists distinguish "process" from "outcome."** Outcomes make headlines — they make the world we live in — so it is easy to fixate on them. **Processes are what we control.**

> Russell: *"it would seem we must take account of probability in judging of objective rightness… The objectively right act is the one which will probably be most fortunate. I shall define this as the wisest act."*
>
> **We can hope to be fortunate — but we should strive to be wise.** Call it computational Stoicism.

**Third: draw the line between tractable and intractable problems.** When stuck in an intractable one, heuristics, approximations and strategic randomness give workable solutions — *"sometimes 'good enough' really is good enough."* And **awareness of complexity lets you pick your problems**: where you control which situations you enter, choose the tractable ones.

---

## 2. The paradox that names the principle

Interviewees were **more likely to be available** for *"next Tuesday between 1:00 and 2:00 p.m. PST"* than for *"a convenient time this coming week."*

That looks absurd — the second offer is strictly more generous. But **people preferred a constrained problem, even with constraints plucked out of thin air, to a wide-open one.** Accommodating someone else's stated preference was easier than computing a better option from their own.

> A computer scientist would nod: this is the complexity gap between **verification** and **search** — *"about as wide as the gap between knowing a good song when you hear it and writing one on the spot."*

Which leads to an implicit principle of the field, odd as it sounds:

> **Computation is bad. The underlying directive of any good algorithm is to minimise the labour of thought.**

When we interact with people we hand them computational problems — not only explicit requests but the implicit work of **inferring our intentions, beliefs and preferences.** We can be **computationally kind** by framing things so that the underlying problem is easier.

---

## 3. The dark underbelly of politeness

A group of friends deciding where to eat. Everyone has preferences, possibly weak ones. Nobody states them, so they navigate by guesses and half-hints.

**It often works. It can also fail badly.** Brian and two friends in Spain dropped a planned bullfight for lack of time — and only while consoling one another discovered that **none of the three had wanted to go.** Each had adopted what they took to be the others' enthusiasm, thereby generating the enthusiasm the others adopted in turn.

> *"Oh, I'm flexible"* and *"What do you want to do tonight?"* have **the veneer of kindness** and do two alarming things:
>
> 1. **They pass the cognitive buck** — *"Here's a problem, you handle it."*
> 2. **By withholding your preferences, they invite others to simulate them** — and simulating another mind is among the most expensive computations any mind or machine performs.

> **Here computational kindness and conventional etiquette diverge.** Politely withholding your preferences dumps the inference problem on the group. **Politely asserting them — "Personally, I'm inclined toward x. What do you think?" — shoulders part of the load of reaching a resolution.**

**The complementary move is to shrink the option set** — two or three restaurants rather than ten, one or two concrete meeting times to accept or decline. If each person eliminates their least preferred option, the task gets easier for everyone.

*None of these is necessarily "polite." All of them significantly lower the computational cost of the interaction.*

---

## 4. Kindness as a design principle

**Shallit's coin.** Asked which new coin would most reduce the average number of coins needed to make change in the US, the answer was an **18-cent piece** — and he hesitated to recommend it.

Today change-making is trivial: take as many quarters as fit, then dimes, and so on. Fifty-four cents is two quarters and four pennies. **With an 18-cent piece that greedy algorithm stops being optimal** — fifty-four cents becomes three 18-cent pieces and no quarters. Shallit noted such denominations make change-making *"at least as hard … as the traveling salesman problem."* **That is a lot to ask of a cashier.** Factoring in ease of computation, the best additions are a **2- or 3-cent piece**: less exciting, nearly as good, *"computationally kinder by a long shot."*

> **The deeper point: subtle changes in design radically shift the kind of cognitive problem posed to the user.** Architects and urban planners choose how to structure the computational problems the rest of us must solve.

**The parking lot.** A stadium lot with many lanes forces a genuine optimal-stopping problem: pass a space hoping for better, reach the destination, work back down a neighbouring lane, decide whether to try a third. **A single helix winding upward has a computational load of zero** — drive forward, take the first space. Whatever else can be said for or against it, **it is cognitively humane.**

> **A chief goal of design ought to be protecting people from unnecessary tension, friction and mental labour** — and this is not abstract: when mall parking becomes stressful, shoppers spend less and return less often. Planners weigh space, materials and money routinely, **and almost never weigh the computational resources their designs consume.**

**Two more cases:**

- **Restaurant seating.** Open seating, where waiting customers hover until a table frees up, is **spinning**; taking your name and calling you is **blocking**. In computing this is a practical tradeoff — time lost spinning versus time lost context-switching. **In a restaurant, the resource being spent by spinning is not the restaurant's**: it is the customers' minds, *"trapped in a tedious but consuming vigilance."*
- **The bus stop.** A live display saying *"arriving in 10 minutes"* lets you **decide once** whether to wait, instead of treating each moment of non-arrival as a fresh piece of evidence and re-deciding continuously — and lets you look away for those ten minutes. Such acts *"could do as much for ridership, if not more, as subsidizing the fares: think of it as a cognitive subsidy."*

---

## 5. Being kinder to yourself

The intuitive standard for rational decision-making is to consider all available options carefully and take the best one. **Computers look like the paragon of that — and that picture is outdated.** Grinding to a perfect answer is *"a luxury afforded by an easy problem."*

Across every domain in the book, **the more real-world factors you include — incomplete information when interviewing candidates, a changing world in the explore/exploit dilemma, dependencies between tasks when scheduling — the more likely it becomes that finding the perfect solution takes unreasonably long.** And people are almost always in what computer science regards as the hard cases.

Against those, effective algorithms **make assumptions, bias toward simpler solutions, trade the cost of error against the cost of delay, and take chances.**

> **These aren't the concessions we make when we can't be rational. They're what being rational means.**

---

## Transferable rules

1. **Evaluate decisions by the process, not the outcome.** A provably optimal method still fails often; if you followed the best available process, the loss is not a mistake.
2. **State the failure rate of your method up front.** 37% optimal means 63% failure, and knowing that in advance is what makes a bad outcome bearable rather than evidence against the method.
3. **Recognise that even perfect information would not guarantee success** in many of these problems — the ceiling is lower than intuition assumes.
4. **Accept "good enough" on intractable problems** rather than paying unbounded cost for an answer you cannot reach.
5. **Choose tractable problems where you have the choice.** Complexity awareness is a filter on which situations to enter, not only a method for handling them.
6. **Treat every request you make as a computational problem you are imposing**, and minimise its cost — this is the core move.
7. **Prefer verification to search when asking something of someone.** A concrete proposal to accept or decline is far cheaper than an open-ended question.
8. **Offer constrained options, even somewhat arbitrary ones.** "Tuesday 1–2pm" gets more yeses than "any time that works."
9. **State your preferences rather than withholding them.** "I'm flexible" passes the cognitive buck and forces others to simulate your mind — the most expensive computation there is.
10. **Reduce the number of options you present**, and let others eliminate rather than construct.
11. **Beware of consensus assembled from mutual inference.** Groups reach decisions nobody wanted when each person mirrors the enthusiasm they read in the others.
12. **Design so the greedy algorithm stays optimal.** A slightly worse arrangement that keeps the decision simple usually beats an optimal one that makes every user solve a hard problem.
13. **Audit designs for the mental labour they impose**, alongside space, materials and money — the cost is real and rarely counted.
14. **Replace spinning with blocking wherever the waiting is done by people.** Notify rather than making people watch; convert a continuous re-decision into a single one.
15. **Publish the information that collapses a repeated inference into one decision** — a countdown, an ETA, a confirmed time.
16. **Stop treating assumption, approximation and chance as compromises.** On hard problems they are what rationality consists of.

---

## Cross-references

Ch. 0 introduction — the framing this closes · Ch. 1 optimal stopping — the 37% rule and the parking-lot problem · Ch. 2 explore/exploit — Upper Confidence Bound and regret that grows slowly · Ch. 4 caching — LRU · Ch. 5 scheduling — context switching and thrashing, the origin of spinning vs. blocking · Ch. 6 Bayes's Rule — inferring the next bus from the last one · Ch. 8 relaxation and Ch. 9 randomness — where "good enough" is formalised · Ch. 11 game theory — mechanism design, of which computational kindness is the everyday form.

**Named references:** Merrill Flood · Bertrand Russell · Jeffrey Shallit (University of Waterloo, 2003) · Alan Turing.
