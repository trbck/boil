# Ch 0 — Introduction: Algorithms to Live By

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Introduction.
**Governs:** the frame for every other chapter — what an algorithm is, when borrowing one from computer science is legitimate, and what the book actually claims.
**Thesis:** the hardest problems in human life have the **same computational structure** as the hardest problems in computer science, because both are what happens when a finite agent acts in finite space and time. Where the structures match, the algorithms transfer.

---

## 1. The apartment hunt — a solved problem people agonise over

San Francisco: listings appear and vanish within minutes, and the keys go to whoever gets a deposit cheque into the landlord's hand first. You cannot compare and then choose. **Each apartment must be taken or refused on the spot, irrevocably.**

The dilemma is genuine, not a failure of nerve:

> How can you know an apartment is the best unless you have a baseline? And how can you build a baseline **except by viewing — and losing — apartments**?
>
> *"How do you make an informed decision when the very act of informing it jeopardizes the outcome?"*

Asked this, most people correctly say the answer is some balance between looking and leaping. **What they cannot say is what the balance is.** There is one:

> **Thirty-seven percent.** Spend 37% of the search noncommittally calibrating — cheque book at home — then commit immediately to the first option that beats everything seen so far.

This is not an intuitively satisfying compromise. **It is the provably optimal solution**, and apartment hunting is only one instance of the class: how many times to circle the block before parking; how far to push a risky venture before cashing out; how long to hold out for a better offer. *Optimal stopping is also the science of serial monogamy.*

> *"They don't need a therapist; they need an algorithm. The therapist tells them to find the right, comfortable balance between impulsivity and overthinking. The algorithm tells them the balance is thirty-seven percent."*

---

## 2. The claim, stated precisely

There is a set of problems every person faces **as a direct result of living in finite space and time**: what to do and leave undone in a day or a decade; how much mess to tolerate; what balance of new experiences against favourites makes the most fulfilling life.

**These are not uniquely human.** For half a century, computer scientists have been solving the same dilemmas in a different vocabulary: how a processor should allocate attention with minimum overhead, when to switch tasks and how many to take on, how to use limited memory, whether to gather more data or act on what it has.

**"Algorithm" is not a machine word.** It is *"a finite sequence of steps used to solve a problem"* — much broader and far older than the computer. It comes from al-Khwārizmī, whose ninth-century *al-Jabr wa'l-Muqābala* also gives us "algebra"; the earliest known mathematical algorithm is a four-thousand-year-old Sumerian clay tablet describing long division. **Following a recipe, a knitting pattern, or the strike sequence that puts an edge on a flint are all executing algorithms.** *"Algorithms have been a part of human technology ever since the Stone Age."*

---

## 3. Three levels of payoff

| Level | What you get |
|---|---|
| **Immediate** | Concrete solutions to specific problems — when to look and when to leap (optimal stopping), how to balance novelty and favourites (explore/exploit), how to arrange an office (sorting), fill a closet (caching), fill your time (scheduling) |
| **Conceptual** | A vocabulary for the deeper principles. Sagan: *"Science is a way of thinking much more than it is a body of knowledge."* Even where life is too messy for a numerical answer, **intuitions honed on the simpler form of the problem clarify the key issues** |
| **Foundational** | Something about the nature of mind, the meaning of rationality, and how to live |

---

## 4. What modern computers actually do — and why it matters

The objection writes itself: computers are coldly mechanical, applying rigid deductive logic, exhaustively enumerating options, grinding out the exact right answer however long it takes. **Turing defined computation by analogy to a human working carefully through a long calculation to an unmistakably right answer.** Who would want to live that way?

> **That is not what modern computers do when they face a hard problem.**

Arithmetic is not the challenge. Conversing with people, repairing a corrupted file, winning at Go — *"problems where the rules aren't clear, some of the required information is missing, or finding exactly the right answer would require considering an astronomical number of possibilities"* — are. And the algorithms developed for those have moved computers **away from exhaustive calculation** toward **comfort with chance, deliberate trades of time against accuracy, and approximation.**

**This reframes the behavioural-economics story.** That account says we are irrational and error-prone because of buggy, idiosyncratic brain hardware. It leaves a question unanswered: *why are four-year-olds still better than million-dollar supercomputers at vision, language and causal reasoning?*

> **The computational account says something different: life is full of problems that are simply hard, and our mistakes often say more about the intrinsic difficulty of the problem than about the fallibility of the brain.**

Humans consistently face the *hardest* cases studied in the field — decisions under uncertainty, time pressure, partial information, and a rapidly changing world. For some of these, **no efficient always-right algorithm exists, and for some it appears none can.**

---

## 5. The hard-won precepts

What decades of collision with intractable problems produced sounds nothing like a mathematician forcing the world into clean lines:

> **Don't always consider all your options. Don't necessarily go for the outcome that seems best every time. Make a mess on occasion. Travel light. Let things wait. Trust your instincts and don't think too long. Relax. Toss a coin. Forgive, but don't forget. To thine own self be true.**

*"And unlike most advice, it's backed up by proofs."*

**The interdisciplinary note:** designing algorithms for humans has no natural disciplinary home — it draws on computer science, mathematics, engineering, statistics, operations research, and then on cognitive science, psychology and economics. The book's method was to ask the people who invented the famous algorithms of the last fifty years **how their own research changed the way they lived** — from finding spouses to sorting socks.

---

## Transferable rules

1. **Ask first whether the problem has a known structure.** Many everyday dilemmas are recognised, named, and solved classes — not novel personal predicaments.
2. **Distinguish problems where information can be gathered freely from those where gathering it costs the option.** The second class has entirely different optimal strategies.
3. **Treat "find the right balance" as an unfinished answer.** The useful version specifies where the balance is.
4. **Do not equate rigour with exhaustiveness.** For hard problems the best available methods use approximation, randomness and early stopping *by design*.
5. **Trade accuracy against time deliberately** rather than treating any shortfall from optimal as failure.
6. **Read a mistake as evidence about the problem before reading it as evidence about yourself.** Difficulty is a property of problems, and many are provably hard.
7. **Expect the hard cases.** Uncertainty, deadlines, partial information and a changing world are the normal human condition, not the exception.
8. **Borrow the vocabulary even when you cannot borrow the numbers.** Naming the structure — stopping, explore/exploit, caching, scheduling — is most of the benefit when the situation is too messy to quantify.
9. **Judge process, not only outcome.** A provably optimal method still fails often; that is not evidence against the method.

---

## Cross-references

Ch. 1 optimal stopping — the 37% rule in full, with its variants and its 63% failure rate · Ch. 2 explore/exploit · Ch. 3 sorting · Ch. 4 caching · Ch. 5 scheduling · Ch. 8 relaxation and Ch. 9 randomness — where "hard problem" gets its formal meaning · Ch. 12 conclusion — process versus outcome, and computational kindness.

**Named references:** al-Khwārizmī (9th c.) · Alan Turing · Carl Sagan · Brian Christian & Tom Griffiths (the authors' own backgrounds: computer science/philosophy/English, and psychology/statistics at UC Berkeley).
