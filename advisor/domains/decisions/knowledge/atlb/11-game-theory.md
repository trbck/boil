# Ch 11 — Game Theory

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 11.
**Governs:** decisions where the outcome depends on what other people do — and where the cost of strategising is itself part of the price.
**Thesis:** a stable equilibrium is not a good one. When the rules produce a bad outcome, **do not try to play better — change the game**. And prefer games where honesty is the dominant strategy, because then you need not model anyone else at all.

---

## 1. Recursion — the hall of mirrors

Keynes: *"successful investing is anticipating the anticipations of others."* A stock's value is not what people think it is worth but **what people think people think it is worth** — and his beauty-contest example goes further: *"We have reached the third degree where we devote our intelligences to anticipating what average opinion expects the average opinion to be. And there are some, I believe, who practice the fourth, fifth, and higher degrees."*

Computer science bounds this. **Turing's halting problem (1936)**: no program can determine in general whether another will terminate, except by simulating it and risking never terminating itself.

> **Any system — machine or mind — that simulates something as complex as itself has its resources maxed out, more or less by definition.**

Poker players call it **levelling**: *"Level one is 'I know.' Two is 'you know that I know.' Three, 'I know that you know that I know.'"* Dwan once bet $479,500 on the worst hand in Hold'em while *telling his opponent he held it* — and won the pot.

**Two practical limits on going deeper:**

- **Do not out-level your opponent.** *"You really only want to play one level above your opponent. If you play too far above… you're going to think they have information that they don't actually have."*
- **Recursion can be weaponised.** Grandmaster Nakamura, in a three-minute blitz game against the engine Rybka, gridlocked the board and made meaningless moves as fast as he could click. **The computer burned its clock searching for variations that did not exist.** Then he opened the position and crushed it. Poker professionals do the same thing deliberately — luring an opponent into *"a levelling war against themselves."*

**The escape is to stop modelling and compute the equilibrium instead:** *"I always start by knowing or trying to know what Nash is."*

---

## 2. Equilibrium exists — and cannot be found

An **equilibrium** is a set of strategies where neither player wants to deviate given the other's play. Rock-paper-scissors: throw each a third of the time, and nothing better exists.

**Nash proved in 1951 that every two-player game has at least one.** Myerson rates its impact as *"comparable to that of the discovery of the DNA double helix."*

**But mathematics studies truth; computer science studies complexity.** Knowing an equilibrium exists says nothing about reaching it. Roughgarden's complaint: *"Okay, but we're computer scientists, right? Give us something we can use. Don't just tell me that it's there; tell me how to find it."*

**Papadimitriou and colleagues proved (2005–2008) that finding Nash equilibria is intractable.**

> This is the load-bearing consequence: **if the players cannot find the equilibrium, the designer cannot use it to predict their behaviour.** *"If an equilibrium concept is not efficiently computable, much of its credibility as a prediction of the behavior of rational agents is lost."*
>
> Or, in Kamal Jain's compression: **"If your laptop cannot find it, neither can the market."**

Aaronson draws the political corollary: if the existence theorem is considered relevant to arguments about markets versus intervention, **the intractability theorem should be considered equally relevant.**

---

## 3. Stable is not good — and the price of anarchy

**The prisoner's dilemma.** Defecting beats cooperating *no matter what the other does* — making it not merely an equilibrium but a **dominant strategy**, which is powerful precisely because it *avoids recursion entirely*: you need not get inside anyone's head.

And yet both rational players end up serving five years instead of walking free with half a million each.

> **The equilibrium for players all acting rationally in their own interest may not be the outcome that is best for those players.**

Algorithmic game theory quantifies the damage as **the price of anarchy** — the gap between coordinated and uncoordinated outcomes.

| Game | Price of anarchy |
|---|---|
| Prisoner's dilemma | **Effectively infinite** — raise the stakes arbitrarily and the dominant strategy is unchanged |
| **Selfish routing** (traffic, internet packets) | **4/3** — a free-for-all is only **33% worse** than perfect top-down coordination |

The routing result (Roughgarden & Tardos, 2002) explains why the internet works without a central authority: **coordination would not add much.** It also deflates a popular hope — perfectly coordinated self-driving commutes would be only ¾ as congested as today's. *"The optimist proclaims that we live in the best of all possible worlds; and the pessimist fears this is true."*

> **A low price of anarchy means a system is about as good on its own as it would be if managed. A high price means things could be fine with coordination — but without intervention you are courting disaster.**

---

## 4. The tragedy of the commons

Hardin scaled the dilemma to a village: each herder gains fully from one more animal while the harm is diffuse, so everyone overgrazes and the commons is destroyed.

**The same structure, with no villain required:**

- **Leaded petrol** — *"Given what everyone else is doing, how much worse really are you personally if you put leaded gasoline in your own car? Not that much worse. It's the prisoner's dilemma."*
- **Emissions** — every firm and nation gains from being marginally more reckless; if all are, the Earth is ravaged **and nobody gains any relative advantage.**
- **Unlimited vacation policies.** Everyone wants maximum holiday *and* wants to take slightly less than their peers to look committed. Everyone takes their baseline from everyone else and subtracts. **The Nash equilibrium is zero.** *"It's a race to the bottom."*
- **Shop opening hours.** One shopkeeper opening Sundays takes the other's customers; the equilibrium is everyone working all the time. In 2014, retailers cascaded into Thanksgiving openings — Kmart opened at 6 a.m. and stayed open **42 hours**.

> **You cannot shift a dominant strategy from within.** The stability that defines the equilibrium is exactly what damns it. **The solution has to come from outside the game.**

---

## 5. Mechanism design — change the game

**Reverse game theory:** rather than asking what behaviour a set of rules produces, ask **what rules produce the behaviour you want.**

Return the prisoners to their cells and add a Godfather who kills informants. **You have made every outcome worse — and made everyone better off**, because the equilibrium moved: both cooperate and walk away rich.

> **You can worsen every outcome — death on one hand, taxes on the other — and improve everyone's life by shifting the equilibrium.**

**The shopkeepers** cannot rely on a verbal truce, which collapses the moment one needs cash. But they *can* act as their own don: a binding contract that any Sunday proceeds go to the other shop. **By worsening the bad equilibrium they create a better one.**

**The instructive failure:** Evernote offered employees **$1,000 to take a vacation.** Game-theoretically this misses the point — *"if a million-dollar heist ends up with both thieves in jail, so does a ten-million-dollar heist."* Sweetening the payoff without moving the equilibrium changes nothing, because the prize being competed for is the promotion won by appearing marginally more loyal than one's peers.

> **The fix costs nothing: make a minimum amount of vacation compulsory.** *"If he can't change the race, he can still change the bottom."*

**This is the argument for designers** — a CEO, a binding contract, a league commissioner, a government, a god. Imagine the NBA if teams could score at any moment between October and June: *"haggard, cadaverous players, in extreme sleep debt… War is like this."* Even Wall Street closes at 4:00 p.m. sharp so that nobody is ambushed by a competitor pushing toward a sleepless equilibrium. **In this sense the stock market is more a sport than a war.**

Religion does this directly. *"Remember the Sabbath day"* solves the shopkeepers' problem exactly, and omniscience is an unusually strong enforcement guarantee — *"there's no Godfather quite like God the Father."* **Constraints that reduce your options do not merely simplify decisions; they can yield better outcomes.**

---

## 6. Mechanism design by evolution — emotions as commitments

**The California redwoods are a tragedy of the commons.** They are tall only because they are competing to be taller. Dawkins: the canopy is *"an aerial meadow… raised on stilts,"* gathering the same photons it would gather lying on the ground, with most of the energy wasted on the stilts. A truce would leave the whole forest better off.

But in nature there is no authority outside the game. So where could cooperation come from? **From something the individual cannot control.**

Consider two people acting against their own interest: a man spending ten minutes writing a vindictive review of a broken vacuum, and a woman tackling a thief to recover a stranger's $40 at risk of serious injury — when she could simply have handed the man two twenties.

> Both are **individually irrational and socially valuable.** We all want to live somewhere pickpocketing does not pay and bad products earn bad reputations. *"Perhaps each of us, individually, would be better off being the kind of person who can always make a detached, calculated decision… But all of us are better off living in a society in which such defiant stands are common."*

**Emotion is mechanism design in the species.** Precisely *because* feelings are involuntary, **they enable contracts that need no outside enforcement.** Frank: *"If people expect us to respond irrationally to the theft of our property, we will seldom need to, because it will not be in their interests to steal it."*

*(And lawsuits are not the civilised substitute for retribution — prosecuting often costs more than can ever be recovered. They are the developed society's means of self-destructive retaliation.)*

**Love works the same way.** The commitment problem — why invest in something the other party might rationally leave? — is only partly solved by contracts. *"The worry that people will leave relationships because it may later become rational for them to do so is largely erased if it is not rational assessment that binds them in the first place."*

> **Love is like organised crime: it changes the structure of the game so the equilibrium becomes the outcome that works best for everybody.**
>
> Shaw asked of marriage, *"If the prisoner is happy, why lock him in?"* **Happiness is the lock.**

And marriage is a prisoner's dilemma **where you choose your accomplice** — which is why the capacity to fall involuntarily in love makes you a more attractive partner. *"Your capacity for heartbreak… is the very quality that makes you such a trusty accomplice."*

---

## 7. Information cascades — how bubbles form without villains

Watching others is normally rational: it adds their information to yours. **But you observe actions, not beliefs** — and their actions may be based on yours.

**The mechanism** (Bikhchandani, Hirshleifer & Welch): ten firms bid on oil-drilling rights. One has a promising survey and bids high. The second, with an ambiguous survey, reads that bid optimistically and bids higher. The third has a *weak* survey but now sees two apparently independent votes of confidence, so discounts its own data. By the fourth, the consensus has **unglued from reality**.

> *"Something very important happens once somebody decides to follow blindly his predecessors independently of his own information signal, and that is that **his action becomes uninformative to all later decision makers**. Now the public pool of information is no longer growing."*

**No single bidder acted irrationally, and the result is catastrophe.** This is a rational theory of bubbles, fads and herd behaviour — and it explains why, after the 2007–2009 mortgage crisis, *everyone* felt unfairly blamed for doing what they were supposed to do. **Catastrophes can happen when no one is at fault.**

The pure form: *The Making of a Fly* listed at **$23,698,655.93** on Amazon, because two sellers priced algorithmically off each other (×0.99830 and ×1.27059) with no ceiling. The 2010 flash crash may be the same mechanism — Cramer's live incredulity (*"That is not a real price"*) is private information holding out against public.

**Three defences:**

1. **Be wary when public information exceeds private information** — when you know more about *what* people are doing than *why*, and are more concerned with fitting the consensus than fitting the facts. *"When you're mostly looking to others to set a course, they may well be looking right back at you."*
2. **Actions are not beliefs.** Cascades form when we misread confidence from behaviour. If you suppress a doubt and act anyway, **broadcast the doubt** — otherwise others cannot distinguish your reluctance from enthusiasm.
3. **Some games have irredeemably bad rules.** Recognising that may not help once you are in one, but it helps you avoid entering.

*And for the contrarian: you will be wrong more often than the herd — but sticking to your convictions creates a positive externality, keeping your behaviour informative. **There may come a time when you save the entire herd.***

---

## 8. Vickrey auctions and the revelation principle

**Sealed-bid first-price auctions are recursion machines.** The winner overpays, so you shade your bid by predicting others' valuations — who are shading theirs by predicting yours.

**The Vickrey auction:** sealed bids, highest bidder wins, **but pays the second-highest bid.**

> **Bidding your true value is the dominant strategy.** Bidding more risks overpaying; bidding less risks losing for no gain, since the price you pay does not depend on your bid. It is **strategy-proof**: honesty is optimal *regardless of whether anyone else is honest.*

This is the mirror image of the prisoner's dilemma — there, defection was dominant; here, **honesty is**. And **you do not need to strategise or recurse at all.**

It also costs the seller nothing: **revenue equivalence** shows average sale prices converge with the first-price auction. *In effect, the auction shades every bid optimally on the bidders' behalf.*

**Myerson's revelation principle generalises it:** *any* game requiring strategic misrepresentation can be transformed into one requiring nothing but honesty. The proof is intuitive — if you would tell a trusted agent your true preferences and let them handle the strategy, then **build that agent's behaviour into the rules**. Nisan: *"If you don't want your clients to optimize against you, you'd better optimize for them. That's the whole proof."*

---

## 9. The cost of strategising is part of the price

> **Being obligated to strategise is itself a large part of what we pay to compete with one another** — and nowhere more so than when we must get inside each other's heads.

Sartre's *"Hell is other people"* was not about malice but about complication: *"Into whatever I say about myself someone else's judgment always enters."*

The chapter's revision: as Keynes noted, **popularity is a recursive hall of mirrors, but beauty in the eye of the beholder is not.**

> **Adopting a strategy that does not require anticipating, predicting or reading into others is one way to cut the Gordian knot of recursion. Sometimes that strategy is not just easier — it is optimal.**
>
> If changing strategy does not help, change the game. If you cannot change the game, choose which games you play. **Seek out games where honesty is the dominant strategy. Then just be yourself.**

---

## Transferable rules

1. **Stop escalating levels of "what do they think I think."** Simulating a system as complex as yourself exhausts your resources by definition.
2. **Play one level above your opponent, not more.** Over-modelling attributes information to people who do not have it, and makes your own signals unreadable.
3. **Watch for opponents who profit from your deliberation.** Where thinking is costly and time-bounded, an adversary can win by giving you nothing worth thinking about.
4. **Compute the equilibrium instead of reading the person** where one is available — but treat "an equilibrium exists" as no guarantee anyone can find it.
5. **Discount predictions built on equilibria that are intractable to compute.** If it cannot be found, it cannot be relied on as a forecast of behaviour.
6. **Never assume a stable outcome is a good one.** Stability is what makes bad equilibria resistant, not what makes them desirable.
7. **Prefer dominant strategies where they exist** — they remove the need to model anyone else at all.
8. **Estimate the price of anarchy before demanding coordination.** Sometimes central control adds only a third; sometimes its absence is ruinous.
9. **Recognise the commons structure**: private gain, diffuse harm, and a race that leaves everyone worse off with no relative advantage gained.
10. **Do not try to fix a bad equilibrium from inside it.** Change the rules, or find an outside authority who can.
11. **Making outcomes worse can make everyone better off** if it moves the equilibrium. Constraints are not merely costs.
12. **Sweetening a payoff without moving the equilibrium accomplishes nothing.** Check whether your incentive changes the *structure* or merely the stakes.
13. **Set floors rather than offering rewards** in races to the bottom — a compulsory minimum costs nothing and works where a bonus fails.
14. **Bind yourself deliberately.** Contracts, schedules, closing times and commitments are equilibrium-shifting devices, not just restrictions.
15. **Treat involuntary commitment as an asset.** A reputation for responding disproportionately deters exploitation; predictability of feeling substitutes for external enforcement.
16. **Beware when public information exceeds private information** — when you know what others are doing but not why, you may be joining a cascade rather than learning.
17. **Broadcast your doubts even when you act with the crowd**, so your action does not read as confidence and stop being informative.
18. **Remember that a cascade requires no irrationality or malice.** Assigning blame after a collapse may simply be the wrong frame.
19. **Design for truthfulness.** If you do not want people optimising against you, optimise for them — any game requiring strategic misrepresentation can in principle be rebuilt so that honesty dominates.
20. **Count strategising as a cost of the game itself**, and prefer arrangements that let you act on what you actually want.

---

## Cross-references

Ch. 1 optimal stopping — commitment under irreversibility, and the marriage problem revisited here · Ch. 6 Bayes's Rule — reading evidence that others have contaminated · Ch. 7 overfitting — incentives being optimised against · Ch. 10 networking — protocols as equilibria and the price of selfish routing · Ch. 12 computational kindness — reducing the strategising you impose on others.

**Named references:** John Maynard Keynes (beauty contest) · Alan Turing (halting problem, 1936) · John Nash (1951) · Roger Myerson (revelation principle) · Christos Papadimitriou · Tim Roughgarden & Éva Tardos (price of anarchy, 2002) · Scott Aaronson · Kamal Jain · Garrett Hardin (1968) · Ken Binmore · Avrim Blum · Robert Frank · Richard Dawkins · Sushil Bikhchandani, David Hirshleifer & Ivo Welch (information cascades) · William Vickrey · Noam Nisan · Paul Milgrom · Dan Smith & Vanessa Rousso (poker) · Hikaru Nakamura vs. Rybka (2008) · Jean-Paul Sartre.
