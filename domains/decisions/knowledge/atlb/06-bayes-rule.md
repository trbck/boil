# Ch 6 — Bayes's Rule

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 6.
**Governs:** predicting from very little evidence — often a single observation — and knowing which prediction rule the situation calls for.
**Thesis:** **the shape of the prior decides the prediction rule.** Three distributions give three completely different, mutually contradictory rules of thumb, and picking the wrong one is the main way single-observation forecasts go wrong. Our days are full of *small* data, and we handle it well only because our priors are quietly rich.

---

## 1. Reasoning backward

Bayes's move: to infer the cause from the effect, **first reason forward from each hypothesis** and ask how probable the observed evidence would be if that hypothesis were true. That probability is the **likelihood**.

Three winning tickets in three tries:

| Hypothesis | Chance of seeing 3/3 |
|---|---|
| All tickets win | 100% |
| Half win | ⅛ |
| 1 in 1,000 wins | 1 in a billion |

So "all win" is **exactly 8×** likelier than "half win", and "half win" is **125 million×** likelier than "1 in 1,000". Intuition already suspected the ordering; Bayes supplies the ratios.

**Laplace closed the gap** from ratios between hypotheses to a single number:

> **Laplace's Law:** expected success rate = **(w + 1) / (n + 2)**

One win from one try → **2/3**, not 100%. Three wins from three → 4/5. Ten from twenty → 50%, matching intuition. It works identically with one observation or a trillion: after ~1.6 trillion consecutive sunrises, tomorrow's is indistinguishable from certain.

**Bayes's Rule proper** combines prior and likelihood by multiplication. Nine fair coins and one two-headed coin in a bag; you draw one and flip heads. The two-headed coin is twice as likely to produce heads, but the fair coin was nine times likelier to be drawn — so it is **4.5× more likely** you hold a fair coin.

> **The rule requires a prior. You cannot multiply by a number you do not have.** Priors have been called biased and unscientific, but going into a situation with a genuinely blank slate is rare.

---

## 2. The Copernican Principle — and why it sometimes fails

Gott's question at the Berlin Wall: *where in this thing's lifetime have I arrived?* Assume nothing special about your arrival, so on average you arrive **halfway** — and therefore:

> **Best guess: it will last as long as it already has.**

Eight-year-old wall → eight more years (it stood twenty). It predicts the USA to ~2255, Google to ~2032, and your friend's one-month-old relationship to last about another month.

**And it is plainly wrong sometimes.** It predicts a 90-year-old man will reach 180, and a 6-year-old boy will die at 12.

**Why:** the Copernican Principle *is* Bayes's Rule with an **uninformative prior**. Hypotheses shorter than the observed age are ruled out; enormously long ones are possible but require an improbable coincidence in your timing. It is reasonable exactly when you know nothing — including not knowing what timescale even applies — and unreasonable precisely when you *do* know something, because then you can do better.

*The same reasoning independently produced Jeffreys's tramcar estimate (double the serial number) and the WWII German tank problem, where serial numbers predicted 246 tanks/month against aerial reconnaissance's 1,400. **The true figure was 245.***

---

## 3. Three distributions, three rules — the core of the chapter

| Distribution | Character | Rule | Example |
|---|---|---|---|
| **Power-law** (scale-free) | No natural scale; most below the mean, a few enormous | **Multiplicative** — multiply what you've seen by a constant | Movie grosses (×1.4); uninformative prior (×2) |
| **Normal** (Gaussian) | Clusters around a natural value | **Average** — predict the mean; once past it, predict a little more | Life spans, heights, film running times |
| **Erlang** (memoryless) | Intervals between independent events | **Additive** — predict a constant amount more, always | Radioactive decay, phone calls, congressional terms |

Worked: a film that has grossed $6M → expect ~$8.4M. A 90-year-old → expect 94. A 6-year-old → expect 77 (slightly above the population average, since he has survived infancy).

**Power laws arise from preferential attachment** — the rich getting richer. Most-linked sites gain links; biggest cities gain residents; most prestigious firms gain clients.

### The surprise structure follows directly

This is the most portable idea in the chapter:

- **Power-law:** the longer it has gone on, the longer it is expected to continue — so the event is **most surprising right before it happens**. An institution grows more venerable every year, which is exactly why its collapse is always stunning.
- **Normal:** surprising when **early**; once past the average it feels **overdue**, and waiting increases expectation.
- **Erlang:** **never** more or less surprising, whatever has happened.

The gambling corollary: under a memoryless distribution there is **no right time to quit**. You are not rewarded for ending on a high note and there is no tipping point for cutting losses. Kenny Rogers's "know when to walk away" has no answer here — which may partly explain such games' addictiveness.

### Gould's case — why the shape matters more than the average

Told that half of patients with his cancer died within eight months, Gould read further and found the distribution was **strongly right-skewed with a long tail**. Under a normal distribution the Average Rule would have forecast about eight months. Under a power-law, the Multiplicative Rule says **the longer he lived, the more evidence that he would live longer**. He lived twenty more years.

> A median tells you almost nothing without the shape around it.

---

## 4. Small data is big data in disguise

Asked to predict life spans, movie grosses and terms in office from a single number, **people's predictions closely matched Bayes's Rule applied to the real distributions** — using the multiplicative, average and additive rules in the right domains without knowing they exist.

> **We predict well from one observation because our priors are rich.** We absorb them from the world rather than gathering them deliberately.

This also runs in reverse: you can *reverse-engineer* people's priors from their predictions. Asked about being on hold, people predicted a total wait about **1⅓×** what they had waited — implying they hold a **power-law** prior for hold times.

**The exception proves the rule.** In the same study, predictions failed badly on one topic: the reigns of Egyptian pharaohs (actually Erlang). People simply lacked the exposure.

> **Good predictions require good priors.** Our judgments betray our expectations, and our expectations betray our experience.

---

## 5. The marshmallow test, re-read

The children who waited a while and *then* caved look irrational — why suffer and lose the treat anyway?

**Unless waits are power-law distributed.** Then a long wait predicts an even longer one, and **cutting your losses is correct**. Under a normal distribution the Average Rule says hold on, the experimenter is due back any moment.

> **The ability to resist temptation may be as much a matter of expectations as of willpower.**

The Rochester experiment tested this directly: before the marshmallow, an experimenter promised better art supplies and either delivered or did not. **Children who had learned the adult was unreliable ate the marshmallow sooner.**

> Failing the test — and the worse life outcomes correlated with it — may reflect having learned that adults disappear for arbitrary intervals. *"Learning self-control is important, but it's equally important to grow up in an environment where adults are consistently present and trustworthy."*

---

## 6. Protecting your priors

Priors are normally well calibrated because experience delivers events at their true frequencies. A desert dweller overestimates sand, a polar dweller snow — each well tuned to their niche.

> **Language breaks this.** We talk about what is *interesting*, and interesting means uncommon. Events are experienced at their proper frequencies; **stories are not.** Anyone who survives a lightning strike retells it for life, and others retell it after them.

Mechanical reproduction — printing, broadcast, social media — amplifies the distortion:

- You have probably seen roughly as many crashed planes as crashed cars — but the cars were beside you on the road and the planes were on another continent, delivered by screen. US commercial plane deaths since 2000 would not half-fill Carnegie Hall; US car deaths over the same period exceed the entire population of Wyoming.
- The US murder rate **fell 20%** across the 1990s while gun violence on American news **rose 600%**.

> **The representation of events in media does not track their frequency in the world.** To predict well without having to think about which rule applies, **protect your priors — which may mean turning off the news.**

---

## Transferable rules

1. **Identify the distribution before choosing a prediction rule.** Multiplicative, Average and Additive give contradictory answers; nearly all single-observation errors are shape errors, not arithmetic errors.
2. **Use the Multiplicative Rule for scale-free quantities** — grosses, wealth, city sizes, durations of unfamiliar things. The longer it has run, the longer to expect.
3. **Use the Average Rule for quantities with a natural scale** — predict the mean, and a little beyond once the mean is passed.
4. **Use the Additive Rule for memoryless processes** — predict a constant increment, and stop looking for the right moment to quit, because there isn't one.
5. **Apply Laplace's Law, (w+1)/(n+2), for a rate from few trials.** One success from one attempt is 2/3, not certainty.
6. **Never quote a median without the shape of its tail.** A right-skewed distribution turns "half die within eight months" into a very different personal forecast.
7. **Use "it will last as long as it has lasted" only when you genuinely know nothing** — including not knowing the timescale. Where you have real knowledge, this rule is actively misleading.
8. **Calibrate surprise to the distribution.** Under a power law, be *most* alarmed when a long-running thing has run longest; venerability is not safety.
9. **State your prior explicitly, even as a guess.** Bayes cannot run without one, and refusing to name it does not remove it.
10. **Reverse-engineer priors from predictions.** What someone expects reveals the distribution their experience taught them, and is measurable where direct data is not.
11. **Distrust your predictions in domains where you lack exposure.** Failure is not an inference error but an absent prior.
12. **Read apparent impatience as a possible forecast, not a character defect.** Giving up early is rational when waits are scale-free or the source is unreliable.
13. **Treat reliability as an input to other people's patience.** Consistently keeping promises changes what others can rationally afford to wait for.
14. **Guard the inputs that form your priors.** Media frequency is not world frequency; a diet of the unusual will systematically miscalibrate you.

---

## Cross-references

Ch. 1 optimal stopping — the full-information case depends on knowing the distribution · Ch. 2 explore/exploit — estimating an option's value from sparse evidence · Ch. 7 overfitting — why a rich prior beats more data · Ch. 9 randomness — sampling when the distribution is unknown.

**Named references:** Thomas Bayes (essay published posthumously, 1763, via Richard Price) · Pierre-Simon Laplace (1774; *Philosophical Essay on Probabilities*) · J. Richard Gott III (Copernican Principle) · Harold Jeffreys (tramcars) · the German tank problem · Carl Friedrich Gauss · Agner Krarup Erlang · Stephen Jay Gould ("The Median Isn't the Message") · Walter Mischel (marshmallow test) · Joe McGuire & Joe Kable · the Rochester reliability study · Barry Glassner · Tom Griffiths & Josh Tenenbaum (prediction experiments).
