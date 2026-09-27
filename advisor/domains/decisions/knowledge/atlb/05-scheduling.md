# Ch 5 — Scheduling

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 5.
**Governs:** what to do, in what order, on a single machine — which is to say, how one person spends a day.
**Thesis:** **you cannot have a plan until you have chosen a metric.** Every optimal scheduling rule is optimal *for one objective*, and the popular time-management advice that appears to contradict itself is mostly a set of correct answers to different questions.

---

## 1. The founding observation

> **If you have a single machine and you are going to do all your tasks, every possible ordering takes exactly the same total time.**

Order is irrelevant to duration. So a schedule cannot be "better" until you say better *at what*.

> **Before you can have a plan, you must first choose a metric.**

That single move dissolves most of the apparent contradiction between time-management gurus: *Getting Things Done* (do any two-minute task immediately), *Eat That Frog!* (hardest first), *The Now Habit* (schedule leisure first) and William James (nothing is so fatiguing as an uncompleted task) are optimising different quantities.

*(Historical note: Johnson's 1954 laundry/bookbinding result — shortest wash first, shortest dry last, working inward from both ends — was scheduling's first optimal algorithm. It applies to two machines; the harder and more personal case is one.)*

---

## 2. Pick the metric, get the algorithm

| If you want to minimise… | Use | Note |
|---|---|---|
| **Maximum lateness** | **Earliest Due Date** | Task *durations are irrelevant* — you do not even need to know them |
| **Number of late tasks** | **Moore's Algorithm** | Schedule by due date; when you would fall behind, **drop the largest already-scheduled item** |
| **Sum of completion times** | **Shortest Processing Time** | Shrinks the to-do list fastest; matches GTD's two-minute rule |
| **Weighted sum of completion times** | **Highest importance ÷ duration first** | The general-purpose default |

Two of these deserve emphasis:

**Earliest Due Date's surprise** is that duration does not enter the calculation at all. In a service setting where each arrival's "due date" is the moment they walk in, it reduces to first-come-first-served.

**Moore's Algorithm is indifferent to what happens to the dropped items.** Once something is going to be late, its order among the other late things does not matter — do them all at the end in any order. (In a kitchen: skip the watermelon that takes six servings, and everything after it arrives sooner.)

### The density rule

Divide importance by duration; work from highest to lowest. The practical form:

> **Only prioritise a task that takes twice as long if it is twice as important.**

The same ratio recurs everywhere: fee ÷ project size = hourly rate; calories ÷ foraging time in animal behaviour; and in debt reduction, **the "debt avalanche"** (attack the highest interest rate) is the weighted rule, while **the "debt snowball"** (clear the smallest balances) is unweighted Shortest Processing Time. Which is correct depends entirely on whether the burden is the *amount* of debt or the *number* of bills — a metric choice, not a fact.

---

## 3. Procrastination is an optimal solution to the wrong problem

This is the chapter's most useful reframing.

Procrastination is usually diagnosed as laziness or avoidance. But clearing a pile of trivia while a large project waits is **precisely optimal behaviour under unweighted Shortest Processing Time** — it minimises the number of outstanding tasks as fast as possible.

> **It is not a bad strategy for getting things done. It is a great strategy for the wrong metric.**

Rosenbaum's 2014 experiment shows the same instinct without any avoidance at all: asked to carry one of two buckets down a hallway, people picked up the *near* bucket and carried it the whole way, passing the one they could have carried a fraction of the distance. The authors call it **pre-crastination** — "the hastening of subgoal completion, even at the expense of extra physical effort."

**Interfaces impose metrics on you.** An unread-count badge weights every message equally, which makes answering the easiest emails first the *correct* response to the objective on screen.

> **Live by the metric, die by the metric.** If the badge cannot be made to reflect your real priorities, and you cannot resist minimising any number placed in front of you — turn the badge off.

---

## 4. When the least important thing is the most important

Doing the weightiest thing first is *still* not sufficient.

**Priority inversion**, from Mars Pathfinder, 1997: a low-priority task holds a resource; a high-priority task needs it and blocks; the scheduler, finding the high-priority task unable to run, works through **medium-priority** tasks instead — while the thing blocking everything sits at the back of the queue. Pathfinder repeatedly reset itself, losing days of work.

**The fix, beamed across the solar system: priority inheritance.** A task blocking a high-priority resource *temporarily becomes* the highest-priority thing in the system.

The general case is a **precedence constraint** — one task cannot start until another finishes.

> *"Things which matter most must never be at the mercy of things which matter least"* has the ring of wisdom, **but sometimes it is simply false.** When the trivial thing blocks the vital one, the trivial thing *is* the vital one.

Everyday instances: you cannot leave the house until the children eat, and they cannot eat until you remember the spoon. You cannot return the van until you return the equipment, which you need to finish the repair — so the un-urgent repair is the most urgent task on the list.

**Lawler's 1968 result:** Earliest Due Date still works under precedence constraints — but you must build the schedule **back to front**, repeatedly placing last whichever unblocked task has the latest due date.

---

## 5. Most scheduling problems have no efficient solution

Shortest Processing Time plus precedence constraints turns out to be **intractable** — no efficient algorithm is believed to exist.

And the boundary is startlingly fragile. Moore's Algorithm is efficient when late items are equally important, and **intractable the moment they are not**. Being unable to start a task before a certain time — a perfectly ordinary constraint, like not putting the bins out before Tuesday — pushes nearly every otherwise-solvable problem over the line.

**The landscape:** about **7%** of scheduling problems remain unclassified. Of the 93% understood, only **9% can be solved efficiently** and **84% are provably intractable**.

> If perfectly managing your calendar feels overwhelming, that is because **it actually is**.

---

## 6. Preemption, uncertainty, and the burden of clairvoyance

**Being able to switch tasks mid-flight changes everything.** Problems made intractable by start-time constraints become efficiently solvable again, using the same classic rules with one modification: when a new task becomes available, compare it to the current one and switch only if it wins on your metric (sooner due date; or shorter remaining time).

**And the rules survive not knowing the future.** Even when tasks arrive unpredictably, preemptive Earliest Due Date and preemptive Shortest Processing Time remain optimal on average.

The **weighted preemptive rule** is the closest thing scheduling theory has to a skeleton key:

> Each time work arrives, **divide its importance by its duration. If that exceeds the same figure for what you are doing, switch. Otherwise carry on.**

Under certain assumptions this simultaneously optimises the weighted sum of completion times, the weighted number of late jobs, *and* the weighted lateness.

**The counterintuitive payoff:** optimising those same metrics is *intractable* if you know all start times and durations in advance.

> **There are cases where clairvoyance is a burden.** Perfect foreknowledge can make the perfect schedule practically impossible to compute, while reacting as work arrives is easy — and nearly as good.
>
> **When the future is foggy, you do not need a calendar. You need a to-do list.**

---

## 7. Preemption is not free

Every switch costs a **context switch**: bookmarking the current state, choosing what is next, and reloading. None of this advances any task. **It is metawork, and it is pure loss.**

For machines the cost is microseconds; **for humans it is minutes**, plus errors.

> **Anyone you interrupt more than a few times an hour is in danger of doing no work at all.**

Work requiring the whole system in mind — programming, writing — carries the largest switching costs. Hence sixteen-hour days being more than twice as productive as eight-hour ones; hence blocking less than ninety minutes for writing being close to useless, since the first half hour is spent reloading "now, where was I?"; hence Pruhs: *"If it's less than an hour I'll just do errands instead."*

### Thrashing

Add tasks past a critical threshold and the system does not degrade gradually — **it falls off a cliff**. The juggler given one ball too many does not drop that ball; **he drops everything**.

The mechanism is scheduling meeting caching: each task's working set evicts the others', so the machine spends all its time swapping and none working. **Real work drops to effectively zero**, which also makes it nearly impossible to climb out.

The human version is recognisable: *wanting to stop everything just to write down everything you are supposed to be doing, but not being able to spare the time.* Panic by way of hyperactivity.

**Three ways out, in order of availability:**

1. **Get more memory** — prevention, not cure, and unavailable for human attention.
2. **Learn to say no.** Denning's rule: refuse to admit a job whose working set does not fit. Sensible, and a luxury when you cannot throttle demand.
3. **Work dumber.** Choosing what to do next is itself metawork that can swamp the work. Repeatedly scanning n emails for the most important costs **O(n²)** — an inbox three times as full takes nine times as long — and swaps every message through your mind before you answer any. **In a thrashing state, doing tasks in the wrong order beats doing nothing**, so answer in arbitrary order. The Linux team did exactly this: they replaced their scheduler with one less clever about priorities that more than made up for it by computing them faster.

---

## 8. Responsiveness versus throughput

These two are not compatible, and the trade-off is the reason some jobs exist at all: **receptionists are responsive so that others may have throughput.**

Operating systems guarantee every process a slice of each period — but if slices shrink below the cost of a context switch, the system spends the whole period switching. **So modern schedulers enforce a minimum slice length** and let the period stretch instead. Everyone waits longer for a turn, but each turn is long enough to accomplish something.

The human form of a minimum slice is **timeboxing** or **pomodoros**.

How long should the slice be? Throughput alone says: as long as possible. Responsiveness caps it. Operating systems resolve this by mining psychophysics for the exact millisecond threshold at which a human notices lag — and checking on you no more often than that.

> **Stay on a single task as long as possible without dropping below the minimum acceptable responsiveness. Decide how responsive you need to be — then be no more responsive than that.**

### Interrupt coalescing

Batch interruptions rather than servicing each as it arrives. If bills are never due sooner than 31 days after arrival, pay them all on one day a month. If no correspondent needs an answer within 24 hours, check mail once a day.

**The postal system supplies this for free** — one delivery a day means you can be interrupted by mail at most once daily, and it demands no responsiveness finer than 24 hours. **Office hours** coalesce student interruptions; **the much-maligned weekly meeting** is one of the better defences against unplanned context switches.

Knuth is the limiting case: no email address since 1990, postal mail reviewed every three months, faxes every six, and six years of bug reports fixed in a single batch. *"I do one thing at a time. This is what computer scientists call batch processing — the alternative is swapping in and out. I don't swap in and out."*

---

## Transferable rules

1. **Choose the metric before choosing the schedule.** Without one, no ordering is better than another, and conflicting productivity advice cannot be adjudicated.
2. **To minimise the worst delay, work by earliest due date** — and note that task durations are irrelevant to this rule, so you need not estimate them.
3. **To minimise how many things are late, drop the largest scheduled item the moment you fall behind**, and stop worrying about the order of anything already late.
4. **To shrink a backlog fastest, do the shortest task first.**
5. **To act on what matters, order by importance divided by duration** — only prioritise something twice as long if it is twice as important.
6. **Decide whether you are minimising the amount or the count** before choosing a strategy — it is the difference between the debt avalanche and the debt snowball, and neither is universally right.
7. **Read procrastination as a metric error, not a character flaw.** Clearing trivia is optimal behaviour for minimising task *count*; fix the objective rather than the discipline.
8. **Audit the metrics your tools impose on you.** Unread badges silently weight everything equally; if you cannot change what they count, remove them.
9. **Watch for priority inversion** — if the important thing is stalled, find what is blocking it, and promote the blocker to the priority of the thing it blocks.
10. **Treat a blocking trivial task as the most important task.** "Never let what matters most be at the mercy of what matters least" is false under precedence constraints.
11. **Schedule back to front when tasks have prerequisites**, placing last the unblocked task with the latest due date.
12. **Expect most real scheduling problems to be intractable** — 84% of classified ones are — and use these rules as good starting points rather than expecting optimality.
13. **Prefer reacting to planning when the future is uncertain.** Foreknowledge can make the optimal schedule uncomputable while on-the-fly rules stay easy and nearly as good.
14. **Count context switches as pure loss.** Interrupting someone more than a few times an hour can reduce their output to nothing.
15. **Protect blocks long enough to reload context** — for demanding work, anything under about ninety minutes is largely spent on reloading.
16. **Recognise thrashing by its signature**: full effort, no progress, and no spare capacity to reorganise. Performance collapses rather than degrading.
17. **When thrashing, lower the quality of your prioritisation, not your effort.** Choosing what to do next can cost more than doing it; arbitrary order beats paralysis.
18. **Refuse work whose working set will not fit**, before the collapse rather than after.
19. **Set a minimum time slice** and honour it, so that responsiveness cannot consume throughput entirely.
20. **Be exactly as responsive as required and no more**, then batch everything else — coalesce bills, mail and messages into scheduled passes rather than servicing each interrupt on arrival.

---

## Cross-references

Ch. 1 optimal stopping — when to stop deliberating and act · Ch. 4 caching — the working sets whose collision causes thrashing · Ch. 7 overfitting — why more deliberation can hurt · Ch. 8 relaxation — what to do once a problem is proven intractable · Ch. 11 game theory — responsiveness norms as equilibria.

**Named references:** Frederick Taylor (Scientific Management) · Henry Gantt · Selmer Johnson (1954) · Moore's Algorithm · Eugene Lawler (1968, precedence constraints) · Jan Karel Lenstra · Mars Pathfinder / JPL (1997 priority inversion) · Peter Denning (thrashing) · Peter Zijlstra (Linux scheduler) · Kirk Pruhs · David Rosenbaum (pre-crastination, 2014) · Laura Albert McLay · Peter Norvig · Donald Knuth · Jason Fried.
