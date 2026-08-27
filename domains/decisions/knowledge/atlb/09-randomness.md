# Ch 9 — Randomness

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 9.
**Governs:** when to stop reasoning and start sampling — and how much chance to inject, in what form, at what point.
**Thesis:** randomness is not surrender. On hard problems it **outperforms** exhaustive reasoning, and often it is the only method that returns an answer at all. But it has to be dosed: front-loaded, proportioned to how bad a move is, and cooled over time.

> *"It is efficient, it works; but why and how is absolutely mysterious."* — Michael Rabin

---

## 1. Sampling beats analysis when the space explodes

Buffon (1777) computed the odds of a dropped needle crossing a ruled line; **Laplace** saw the implication in reverse — **you could estimate π by dropping needles**.

> **When you want to know something about a complex quantity, estimate it by sampling from it.**

**Ulam's solitaire.** Convalescing from brain surgery, Ulam asked what fraction of shuffles yield a winnable game. Fifty-two possibilities after the first card, fifty-one more after the second — the combinatorics are hopeless. His answer was beautiful in its simplicity: **just play the game, many times, and count.**

> *"In a sufficiently complicated problem, actual sampling is better than an examination of all the chains of possibilities."*

Note precisely what "better" means. Sampling carries error, reducible only by taking more samples. **It is better because it gives you an answer at all, where nothing else does.**

This became the **Monte Carlo Method** (Ulam, von Neumann, Metropolis), used on nuclear chain reactions — another branching process where exact calculation is impossible but simulation is easy — and now a cornerstone of scientific computing.

---

## 2. Randomness works even on questions with no chance in them

Solitaire and particle physics are *intrinsically* probabilistic. The surprise is that dice help with strictly true-or-false questions.

**The Miller–Rabin primality test.** Miller found equations always true when n is prime; the flaw was false positives. Rabin's contribution was to bound them: **for a random x, at most a one-in-four chance of falsely declaring a composite prime** — and each additional random test multiplies the error by another ¼.

| Tests | Chance of a false prime |
|---|---|
| 10 | < 1 in a million |
| 15 | < 1 in a billion |
| **40** | **< 1 in a million billion billion** — fewer than the grains of sand on Earth |

Forty tests is the modern cryptographic standard. **You are never fully certain — but you get awfully close, awfully quick.**

A deterministic primality test was found in 2002, and randomized methods are still what your phone actually uses, because they are faster. For **polynomial identity testing** — are these two expressions the same function? — plugging in a few random values is the *only* practical method known.

---

## 3. In praise of sampling

The intuition is already yours: given two devices, you press random buttons rather than open the cases; a buyer knifes open a few random bundles to judge a shipment.

**Where we fail to sample and should.** Rawls's **veil of ignorance** asks what society you would choose without knowing who you would be. It is a fine principle and **computationally impossible to execute** — evaluating a single insurance change requires compounding the probability of being born a midwestern town clerk, by plan distributions, by injury actuarials, by procedure costs. *We can barely evaluate one injured shin, let alone hundreds of millions of lives.*

Aaronson's point about what computer science offers philosophy: **quantitative gaps become qualitative ones.** *"One might think that… whether it takes 10 seconds or 20 seconds to compute is obviously the concern of engineers rather than philosophers. But that conclusion would not be so obvious, if the question were one of 10 seconds versus 10¹⁰¹⁰ seconds!"* — the difference between reading a 400-page book and reading every possible such book.

**The two things we are normally offered, and why both fail:**

| Offered | Strength | Failure |
|---|---|---|
| **Cherry-picked anecdotes** | Rich and vivid | Unrepresentative — any policy leaves *someone* better and someone worse off |
| **Aggregate statistics** | Comprehensive | Thin — they obscure heterogeneity, and **often you don't even know which statistic you need** |

> **Random sampling is the third option**, and it is the one that cuts through complexity too great to digest whole.

**GiveDirectly does exactly this.** Rather than publishing success stories, every Wednesday they select a cash recipient **at random**, send a field officer, and **publish the notes verbatim, no matter what.** The problem with other charities' glowing stories is not that they are untrue — it is that *having been chosen for being glowing*, they carry no information.

---

## 4. The third axis: certainty

Computer science trades time against space. Randomized algorithms add a third dimension.

> Mitzenmacher: *"We're going to come up with an answer which saves you in time and space and trades off this third dimension: **error probability**."*

**Bloom filters** are the canonical example. A search engine crawling over a trillion URLs, each ~77 characters, cannot afford to store and search every one it has seen — *"the cure is worse than the disease."* A Bloom filter checks for "witnesses" that a URL is new, exactly as Miller–Rabin checks for witnesses against primality. **Accept a 1–2% error rate and you save enormous time and space.** They ship in browsers to check URLs against malicious-site lists, and are used in Bitcoin.

> *"People don't realize in their own lives how much they do that and accept that."*

---

## 5. Escaping local maxima

For hard optimisation — a ten-city itinerary is already 10! ≈ 3.6 million permutations — the tactical use of randomness may matter more than relaxation.

**The ladder of methods:**

1. **Greedy (myopic)** — always take the best next step. Fast, usually not terrible, rarely near best.
2. **Hill Climbing** — perturb the solution, keep improvements, repeat until nothing nearby is better.

**Hill climbing's failure is the local maximum.** *"The hill-climbing landscape is a misty one. You can know that you're standing on a mountaintop because the ground falls away in all directions — but there might be a higher mountain just across the next valley, hidden behind clouds."*

> **The lobster trap is a local maximum made of wire — a local maximum that kills.** Escaping requires going *deeper into* the cage first.

**Three ways out, all using randomness:**

| Method | Move |
|---|---|
| **Jitter** | When stuck, make a few random small changes — even bad ones — then resume climbing |
| **Random-Restart ("Shotgun") Hill Climbing** | On reaching a local max, scramble completely and start over. Best when local maxima are plentiful — as in code-breaking, where text that looks *nearly* like English is often a dead end |
| **Metropolis Algorithm** | Use a little randomness at *every* step: always accept improvements, and accept worsenings with **probability inversely related to how much worse** |

**Simulated Annealing** unifies them. Kirkpatrick's insight was that in physics, temperature *is* random motion — directly analogous to jitter. Anneal a material too fast and you get defects or glass; cool it slowly through the freezing point and you get a single crystal.

> Start "hot" — pick a solution entirely at random. Cool gradually: accept worse moves on a 2-or-more, then 3-or-more, then only on a 6, then never. **You end as pure hill climbing.**

Mathematicians initially distrusted it as too metaphorical — *"I couldn't convince math people that this messy stuff with temperatures… was real."* Then it beat IBM's in-house chip-layout guru. Kirkpatrick and Gelatt published in *Science* rather than becoming gurus themselves; the paper has been cited some **32,000 times**.

---

## 6. Randomness, evolution and creativity

**Luria's slot machine.** Watching a colleague hit a jackpot, Luria realised bacterial resistance would show one of two signatures: if resistance were a *response* to the virus, every lineage would show similar amounts; if it came from **random mutation**, the distribution would be lumpy like slot-machine payouts — most lineages nothing, occasionally a whole lineage resistant. He found the jackpot, and later a Nobel.

**The discovery was about chance and also due to chance** — the pattern behind Newton's apple, Archimedes' bathtub, and the neglected petri dish. Walpole coined **"serendipity"** in 1754 for *"discoveries, by accidents and sagacity, of things they were not in quest of."*

**Randomness as the engine of creativity** is an old idea. William James (1880) described new ideas as *"random images, fancies, accidental out-births of spontaneous variation"* that the environment then **selects**, exactly as it selects morphological variation — and described creative minds as *"a seething caldron of ideas, where everything is fizzling and bobbing about"* (note the temperature metaphor again). Campbell (1960) formalised it as **"Blind Variation and Selective Retention."** Mach put it bluntly: Newton, Mozart and Wagner said thoughts and melodies *"poured in upon them, and that they had simply retained the right ones."*

**Deliberate jitter is a practice.** Eno and Schmidt's **Oblique Strategies** cards exist to break context: *"When you're very in the middle of something, you forget the most obvious things… These are just ways of throwing you out of the frame."* Lower-tech versions: a random Wikipedia article as your homepage, a CSA vegetable box, a book- or wine-of-the-month club — all ways to be knocked out of a local maximum in your rotation.

*A side benefit of consuming genuine randomness: you calibrate what randomness actually looks like, and become better at judging "coincidences" elsewhere.*

---

## 7. How much randomness — the three rules

*The Dice Man*'s narrator hands every decision to dice and ends up somewhere nobody would want. The problem is not randomness but dosage. Computer science gives three corrections:

> 1. **From Hill Climbing:** even if you sometimes act on bad ideas, **always act on good ones**.
> 2. **From the Metropolis Algorithm:** your likelihood of following a bad idea should be **inversely proportional to how bad it is**.
> 3. **From Simulated Annealing:** **front-load your randomness.** Cool rapidly out of a fully random state, use less and less over time, and linger longest as you approach freezing. **Temper yourself — literally.**

The novel's author lived it: years of nomadic "dicing" on a Mediterranean sailboat, then an annealing schedule that cooled into a lake house in upstate New York where he remains in his eighties. *"Once you got somewhere you were happy, you'd be stupid to shake it up any further."*

---

## Transferable rules

1. **Sample when the possibility space is too large to enumerate.** An estimate with known error beats an exact answer you will never compute.
2. **Judge sampling by whether it returns an answer at all**, not by whether it beats exhaustive analysis for precision.
3. **Simulate the process rather than deriving it** when outcomes branch — play the game, run the trial, count what happens.
4. **Use repeated random tests to drive uncertainty arbitrarily low.** Each independent check multiplies down the error; near-certainty is usually cheap.
5. **Decide explicitly what error rate you need** rather than assuming you need none — cryptography settles for one in 10²⁴, and that is a choice.
6. **Trade certainty for time and space deliberately.** Error probability is a third design axis, not a defect.
7. **Prefer random samples to both anecdotes and aggregates.** Selected stories carry no information *because* they were selected; aggregates hide the heterogeneity that matters, and you rarely know which statistic to ask for.
8. **Commit in advance to publishing what the random sample returns**, whatever it says — the pre-commitment is what makes it evidence.
9. **Treat a large quantitative gap as a qualitative one.** "Possible in principle" is not a defence when the cost is astronomically large.
10. **Recognise the local maximum**: nothing nearby improves matters, yet you suspect something far better exists. Nearby-optimal is not optimal.
11. **Accept a temporary worsening to escape.** Some traps require moving *away* from the exit before you can reach it.
12. **Match the escape to the landscape** — jitter for small perturbations, full random restart where local maxima are dense, Metropolis-style occasional bad moves for continuous search.
13. **Anneal: be most random early and least random late**, and slow down as you approach a decision rather than after it.
14. **Never decline a clear improvement**, however random your process otherwise is.
15. **Scale willingness to try a bad option inversely to how bad it is** — this keeps exploration cheap rather than reckless.
16. **Engineer serendipity deliberately.** Random inputs — cards, articles, unfamiliar ingredients — break context and are a reliable technique, not a happy accident.

---

## Cross-references

Ch. 2 explore/exploit — deliberate exploration with a different objective · Ch. 6 Bayes's Rule — inference from samples · Ch. 7 overfitting — randomness as a defence against over-precision · Ch. 8 relaxation — the other main strategy for intractable problems, often used alongside this one.

**Named references:** Buffon (1777) · Pierre-Simon Laplace (1812) · Stanislaw Ulam, John von Neumann, Nicholas Metropolis (Monte Carlo) · Michael Rabin & Gary Miller (primality) · Vaughan Pratt · Agrawal, Kayal & Saxena (2002) · Michael Mitzenmacher · Burton H. Bloom (Bloom filters) · Scott Kirkpatrick & Dan Gelatt (simulated annealing) · John Rawls · Scott Aaronson · Ursula K. Le Guin (Omelas) · GiveDirectly · Salvador Luria · Horace Walpole (serendipity, 1754) · William James (1880) · Donald Campbell (1960) · Ernst Mach · Brian Eno & Peter Schmidt (Oblique Strategies) · Luke Rhinehart / George Cockcroft (*The Dice Man*).
