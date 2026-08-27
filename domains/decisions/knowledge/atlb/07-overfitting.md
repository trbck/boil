# Ch 7 — Overfitting

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 7.
**Governs:** how hard to think, how many factors to weigh, and how much to trust any measurement standing in for what you actually care about.
**Thesis:** **a better fit to the data you have is not a better prediction.** Wherever the thing you can measure differs from the thing you care about — which is nearly always — optimising harder makes results worse, not merely less efficient. Deliberately thinking less is often the rational move.

---

## 1. The demonstration

Fit models to ten years of marital-satisfaction data:

| Model | Fit to the data | What it predicts beyond the data |
|---|---|---|
| **One factor** (line) | Misses many points | Decline continues forever → infinite misery |
| **Two factors** (curve) | Good | Post-honeymoon decline, then levels off — **what psychologists actually believe** |
| **Nine factors** | **Passes through every point exactly** | Misery at the altar, an abrupt rise, a roller-coaster, a cliff at year ten |

The nine-factor model uses strictly more information than the two-factor model and fits perfectly. It is also useless.

**The tell is instability.** Add small random noise — simulating re-running the survey with different people — and the nine-factor model **gyrates wildly** while the one- and two-factor models barely move.

> **Too simple** fails to capture the pattern: no straight line can fit a curve.
> **Too complex** becomes oversensitive to the particular points you happened to observe.
> Extra factors do not merely offer diminishing returns — **they can make predictions dramatically worse.**

**When would maximum complexity be right?** Only with copious, perfectly representative, error-free data measuring exactly what you care about. If any of those fails, fitting tightly is overfitting.

---

## 2. The idolatry of data

> **Overfitting is a kind of idolatry of data — worshipping what you can measure in place of what matters.**

The gap is everywhere: you predict what will please your future self using what matters to you now (Gilbert: we *"pay good money to remove the tattoos that we paid good money to get"*); you forecast a stock from what correlated with its price in the past; you judge your email by your own read-through rather than the recipient's.

**Every metric in your life is a proxy.** Considering more factors and modelling them harder therefore risks **optimising the wrong thing more efficiently**.

### The catalogue

| Domain | Proxy | How it breaks |
|---|---|---|
| **Diet** | Taste, for nutrition | Fat/sugar/salt were reasonable signals for 200,000 years. Food manufacturing severed the link, so we can **overfit taste** — our agency lets us get exactly what we want when we don't want quite the right thing |
| **Fitness** | Low body fat, high muscle | Extreme dieting and steroids make you *the picture* of health, and only the picture |
| **Fencing** | Electronic scoring button | Flexible blades "flick" the button; athletes overfit tactics to scorekeeping and the sport stops teaching swordsmanship |
| **Business** | KPIs | *"The company will build whatever the CEO decides to measure"* (Altman). Jobs: *"incentive structures create all sorts of consequences you can't anticipate"* |
| **Web** | Page views | Cost-per-impression incentivises cramming ads, slideshows and clickbait — winning short-term, driving readers away. *"Friends don't let friends measure Page Views. Ever."* (Kaushik) |
| **Training** | Drill repetition | **Training scars** — see below |

**Ridgway's 1950s catalogue of "Dysfunctional Consequences of Performance Measurements":** placement staff measured on interviews conducted rushed through meetings without helping anyone find work; investigators on monthly quotas picked easy cases at month end rather than urgent ones; factory supervisors focused on production metrics neglected maintenance and set up future catastrophe.

> **These are not failures to achieve management goals. They are the opposite: the ruthless and clever optimisation of the wrong thing.**

**Training scars** are the lethal version. Officers found spent brass in their pockets after gunfights with no memory of putting it there — good etiquette on a firing range. Some were found dead with brass in hand, *"dying in the middle of an administrative procedure that had been drilled into them."* FBI agents reflexively fired two shots and holstered regardless of whether they had hit anything or whether a threat remained. One officer disarmed an assailant and instinctively **handed the gun back**, exactly as he had done with trainers in practice.

---

## 3. Detecting it: cross-validation

Overfitting presents as a theory that fits *perfectly*, which makes it hard to spot from the inside.

**Cross-validation:** assess not just fit to the data you were given, but **generalisation to data you have not seen**. Paradoxically this means using *less* data — hold two points back, fit to the other eight, and see whether the complex model that nails the eight wildly misses the two. Those held-back points are canaries.

**The deeper version is cross-validating the *metric itself* against a different kind of evaluation.**

- **Schools:** keep standardised tests for their economy of scale, but assess a small random fraction — one student per class — by essay or oral exam. If standardised scores rise while the non-standardised sample moves the other way, that is an unambiguous signal that **teaching to the test** has set in.
- **Military and police:** occasional *unfamiliar* cross-training assessments reveal whether accuracy and reaction time generalise, warning where training scars are forming.

---

## 4. Fighting it: penalise complexity

Overfitting is oversensitivity to the data you saw, so the fix is to weigh fit against complexity — **regularization**.

Occam's razor is the intuition; **Tikhonov** made it mathematical by adding a penalty term, so a more complex model must be **significantly** better, not merely better, to earn its complexity.

**The Lasso** (Tibshirani, 1996) penalises the total weight of the factors, driving as many as possible **to exactly zero**. Only factors with real impact survive — turning a nine-factor model into a robust two- or three-factor one.

**Nature is full of Lassos:**

- **Metabolism** — the brain burns a fifth of daily calories, so its abilities must more than pay that bill. We are *"as brainy as we have needed to be, but not extravagantly more so."*
- **Neural firing** — brains appear to minimise how many neurons fire at once.
- **Language** — complexity is punished by the effort of speaking and the listener's attention. Business plans compress to elevator pitches; advice becomes proverbial only if concise.
- **Memory** — anything to be remembered must pass through its Lasso.

---

## 5. Heuristics are not a retreat from rationality

**Markowitz won a Nobel for mean-variance portfolio optimisation. For his own retirement savings he split contributions 50/50 between stocks and bonds** — *"I visualized my grief if the stock market went way up and I wasn't in it… My intention was to minimize my future regret."*

This looks like a rational model abandoned under pressure. It is the opposite.

> Applying optimal allocation requires good estimates of statistical properties. Errors in those estimates produce very different allocations and can *increase* risk. **A 50/50 split is unaffected by any data you have observed — so there is no way it can overfit.**

The decision rule the chapter offers:

> **If you know the expected mean and variance, use the optimisation — the optimal algorithm is optimal for a reason. But when the odds of estimating them correctly are low, and the model puts heavy weight on those untrustworthy quantities, an alarm should go off: it is time to regularize.**

Gigerenzer and Brighton: *"In contrast to the widely held view that less processing reduces accuracy, the study of heuristics shows that less information, computation, and time can in fact improve accuracy."*

---

## 6. Early stopping — regularizing by time

The other lever is not the model's final complexity but **how fast you let it adapt**.

Many algorithms find the single most important factor first, then the next, and so on — so simply **stopping short** caps complexity before overfitting appears.

> **More time means more complexity.** Giving yourself longer to decide does not guarantee a better decision, but it does guarantee you will consider more factors, more hypotheticals, more pros and cons — and therefore risk overfitting.

**Tom's lectures:** ten hours of preparation per hour of class in his first semester; far less in his second. **Students preferred the second.** The extra hours had gone into details that only confused them — he had been using his own taste as a proxy for his students', a reasonable approximation **not worth overfitting**.

### History as a regularizer

Evolution changes slowly, so organisms carry their history: **decussation** (left body controlled by right brain) from an ancestral 180° twist; mammalian ear bones **repurposed from reptile jawbones**. These look suboptimal.

> **We should not want evolution to fully optimise an organism to every shift in its niche** — that would make it extremely sensitive to the next shift. Having to reuse existing materials is a useful restraint. **Being constrained by the past makes us less perfectly adjusted to the present we know, but keeps us robust for the future we don't.**

**Tradition plays this role in culture.** Information now moves fast enough that a single study can become a supermarket aisle within six months — soy milk quadrupling, then displaced by almond; coconut water up three-hundred-fold; kale up 40% in a year, having been salad-bar *decoration* the year before.

> A bit of conservatism buffers against the boom-and-bust of fads. **Jump toward the bandwagon, by all means — but not necessarily on it.**

---

## 7. When to think less

> **How early to stop depends on the gap between what you can measure and what matters.**

- **Full facts, no error, and you can assess what you actually care about** → don't stop early. The complexity is warranted.
- **High uncertainty, limited data, unclear how the work will be judged** → **stop early.** It is not worth perfecting against your own idiosyncratic guess at what perfection means.

> **The greater the uncertainty, and the bigger the gap between the measurable and the important, the more you should prefer simplicity and the earlier you should stop.**

Fried and Hansson regularize by **stroke size**: sketch with a thick Sharpie, not a fine pen. *"Pen points are too fine. They're too high-resolution. They encourage you to worry about things that you shouldn't worry about yet… You end up focusing on things that should still be out of focus."*

Mintzberg: *"What would happen if we started from the premise that we can't measure what matters and go from there? Then instead of measurement we'd have to use something very scary: it's called judgment."*

**Darwin, finally, was not the overthinker he appears.** He stopped deliberating **exactly when his notes reached the bottom of the diary page** — regularizing to the page. *Anything that doesn't make the page doesn't make the decision.* And the considerations that actually decided him — children and companionship — were **the first two he listed**. The book budget was a distraction.

> **Going with your first instinct can be the rational solution.** The more complex, unstable and uncertain the decision, the more rational it becomes.

---

## Transferable rules

1. **Judge a model by how it generalises, never by how well it fits what you already have.** Perfect fit is a warning sign, not a result.
2. **Test stability under perturbation.** Re-fit with slight noise or a different sample; a model that swings wildly is overfitted regardless of its fit statistics.
3. **Add a factor only if it is significantly better, not merely better.** Complexity must earn its place against an explicit penalty.
4. **Name the gap between your metric and your goal before optimising.** Every measurement is a proxy; the size of that gap determines how hard you should push.
5. **Assume that anything you measure and reward will be optimised — including in ways you did not intend.** Perverse outcomes are usually competent optimisation of a badly chosen target.
6. **Cross-validate on held-out data**, and additionally **cross-validate the metric itself** against a different, harder-to-game evaluation applied to a small sample.
7. **Treat divergence between your primary metric and your spot-check as the alarm**: rising scores with falling independent assessment means the target has been gamed.
8. **Drive weak factors to zero rather than shrinking them.** A short list of things that matter beats a long list of things that might.
9. **Prefer a rule that ignores the data when your estimates are unreliable.** A strategy that never fits the data cannot overfit it — which is why 50/50 can beat optimisation.
10. **Run the regularize check explicitly**: are the quantities I am relying on hard to estimate, and does my method put heavy weight on them? If yes, simplify.
11. **Treat time spent deliberating as a complexity knob.** More time means more factors and more overfitting, not automatically a better decision.
12. **Bound deliberation in advance** — to a page, a timebox, a fixed number of factors — and decide when the bound is reached.
13. **Trust the first factors you generate.** If the earliest considerations are the most important, later ones mostly add noise.
14. **Match your tool's resolution to your certainty.** Use a blunt instrument early; fine detail invites precision you have not earned.
15. **Value historical constraint as robustness, not as inefficiency.** Being imperfectly adapted to the present is what survives changes in the present.
16. **Discount fast-moving consensus.** Rapid information flow enables rapid overfitting at the scale of a whole culture.

---

## Cross-references

Ch. 2 explore/exploit — the cost of chasing every novelty · Ch. 5 scheduling — metrics dictating behaviour, and the cost of over-deliberating · Ch. 6 Bayes's Rule — good priors substituting for more data · Ch. 8 relaxation — deliberately solving an easier problem · Ch. 9 randomness — sampling as a defence against over-precision.

**Named references:** Charles Darwin (1838 marriage diary) · Benjamin Franklin ("Moral or Prudential Algebra") · Daniel Gilbert · V. F. Ridgway (1956) · Steve Jobs · Sam Altman · Avinash Kaushik · Dave Grossman (training scars) · Andrey Tikhonov (regularization) · Robert Tibshirani (the Lasso, 1996) · Harry Markowitz · Gerd Gigerenzer & Henry Brighton · Jason Fried & David Heinemeier Hansson · Henry Mintzberg · Samuel Revusky & Erwin Bedarf.
