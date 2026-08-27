# Ch 10 — Networking

**Source:** Christian & Griffiths, *Algorithms to Live By* (HarperCollins, 2016), Ch. 10.
**Governs:** communication under unreliability and overload — acknowledgment, retry, congestion, and queues, whether between machines or people.
**Thesis:** networks solved, formally, the problems people muddle through daily: how to know a message landed, how long to keep trying, how fast to push, and when to refuse work outright. **The most transferable results are exponential backoff (finite patience with infinite mercy) and the recognition that oversized queues destroy the feedback that keeps a system stable.**

---

## 1. Packets, not circuits

**Protocol** — from *protokollon*, "first glue" — is shared convention. Machines needed their own.

| | **Circuit switching** (phone) | **Packet switching** (internet) |
|---|---|---|
| Model | A dedicated channel, constant bandwidth for the call's duration | Messages atomised into packets merged into a communal flow |
| Suits | Continuous human talk | Bursty machine talk — *"they go blast! and they're quiet for a while"* |
| Under load | **Gets full** — request refused outright | **Gets slow** |
| Reliability as the network grows | Falls **exponentially** — one broken link kills a call | Rises **exponentially** — more paths to route around damage |

> *"What you might call a connection is a consensual illusion between the two endpoints. There are no connections in the Internet. Talking about a connection in the Internet is like talking about a connection in the US Mail system."*

Baran's motivation at RAND was surviving a nuclear strike: every piece of information should find its own way even as the network is torn apart. The incumbents were dismissive — *"Little boy, go away"* — and the resulting technology, in Kleinrock's phrase, *"ate their lunch."* Its other great virtue is **medium-agnosticism**: the same protocol runs over copper, satellite, radio, and — demonstrated in Bergen in 2001 — carrier pigeons.

---

## 2. Acknowledgment, and why certainty is impossible

**The Byzantine generals problem.** Two generals must attack simultaneously; messengers may not arrive. The first won't move without confirmation; the second won't move without confirmation *of* the confirmation; and so on forever.

> **Communication is one of those delightful things that works only in practice; in theory it is impossible.** These are *"not design complexities, they are impossibility results."*

**What is done instead:** a **triple handshake** — hello, hello-back-plus-acknowledgment, acknowledgment — is declared sufficient. Thereafter each side numbers its packets sequentially, and **acknowledgment packets (ACKs)** say what they are ready for next. Three identical ACKs in a row ("still ready for 101") signal that a packet is lost rather than late, prompting retransmission.

This back-channel is not incidental: **roughly 10% of peak upstream internet traffic was Netflix** — a service we think of as purely downstream — because all that video generates ACKs.

**Humans do the same.** The *"you know?"* appended to sentences, the nods, *uh-huhs*, *ten-fours*; on a phone call, often the only evidence the call is live. Hence the most successful carrier campaign of the century being a quality-control catchphrase: *"Can you hear me now?"*

**Two consequences worth carrying:**

- **Voice deliberately does not use TCP.** Retransmitting lost packets is overkill because *the humans supply the robustness*: *"if you lose a packet, you just say, 'Say that again, I missed something.'"*
- **Noise cancellation that reduces background to true silence is a disservice.** Static continuously confirms the line is live; without it, every pause raises the question of whether the call has dropped — the same anxiety that pervades letters, texts, and online dating, where *"every message could be the last, and there is often no telling the difference between someone taking their time to respond and someone who has long since ended the conversation."*

**Timeouts must be tuned to the medium.** We worry in seconds on a call, days over email, weeks over post. **The longer the round-trip time, the longer a silence must be before it means anything** — and the more can be in flight before anyone notices a problem.

---

## 3. Exponential Backoff — the algorithm of forgiveness

The ALOHAnet linked Hawaiian campuses by radio, and its central problem was **interference**: two stations transmitting at once jam each other, and if both retry immediately they jam forever.

**First, break symmetry with randomness** — the sidewalk dance, two speakers deferring in unison, two cars at an intersection accelerating together. Coin-flipping works for two senders; with four it collapses. Above a mere **18.6%** channel utilisation, *"the channel becomes unstable… and the average number of retransmissions becomes unbounded."*

**The fix: double the potential delay after every successive failure.** One or two turns, then one to four, then one to eight.

> *"For a transport endpoint embedded in a network of unknown topology and with an unknown, unknowable and constantly changing population of competing conversations, **only one scheme has any hope of working — exponential backoff**."*

It became the default response to *all* unreliability: retrying a downed website (protecting the server from a stampede when it recovers, and you from wasting effort), and **password lockouts** — defeating dictionary attacks while never permanently locking out a forgetful owner.

### The human application

We default to *"three strikes and you're out"* — a finite number of chances, then permanent abandonment.

> **Exponential backoff offers finite patience and infinite mercy. Maybe we don't have to choose.**

- The friend who repeatedly flakes: reschedule in a week, then two, then four, then eight. **The retry rate approaches zero, but you never have to declare the relationship over.**
- The relative with an addiction: require an exponentially increasing period of sobriety before returning. It disincentivises relapse, protects the host from the endless cycle, and **never requires telling someone they are beyond redemption**.

**This is now criminal-justice policy.** Judge Steven Alm noticed probationers getting a dozen warnings and then, abruptly, years in prison — *"what a crazy way to try to change anybody's behavior."* The **HOPE** programme replaced it with immediate, predefined, escalating sanctions starting at **one day in jail**. A five-year Department of Justice study found HOPE probationers **half as likely** to be arrested for a new crime or have probation revoked, and **72% less likely to use drugs**. Seventeen states have followed. (It began in Honolulu — the birthplace of the ALOHAnet.)

---

## 4. Flow control: the sawtooth

In 1986 a link between two Berkeley sites a football field apart dropped from **32,000 bits per second to 40**.

Because a packet network gets *slow* rather than *full*, nothing tells a sender how congested things are. Senders and receivers must **metacommunicate**: negotiate how fast to send, with no central coordinator.

**AIMD — Additive Increase, Multiplicative Decrease.** Ramp up aggressively at first (double each successful volley). Once a packet is lost: **add one on success, halve on failure.**

> *"A little more, a little more, a little more, whoa, too much, cut way back, okay a little more…"* — producing the **TCP sawtooth**.

**Why halving is right:** if a transmission falters, the most conservative reading is that a second party has arrived and taken half the resources. **A network stabilises only if users pull back at least as fast as it is being overloaded** — while merely additive increase prevents rapid overload-recovery cycles.

The same shape appears in nature. Ants face an identical allocation problem for foragers and evolved the same feedback — successful returnees prompt more departures, unsuccessful ones suppress them — in what Gordon calls **"control without hierarchy."** Squirrels and pigeons after food scraps creep forward, leap back, creep forward.

### AIMD against the Peter Principle

> **"Every employee tends to rise to his level of incompetence"** — because promotion continues until performance stops, at which point the person stays put permanently. Ortega y Gasset put it more sharply in 1910: *"Every public servant should be demoted to the immediately lower rank, because they were advanced until they became incompetent."*

The existing remedy is brutal: **"up or out"** — the Cravath System, the 1980 Defense Officer Personnel Management Act, the UK's "manning control."

**AIMD is the middle path.** Imagine each year every employee is either promoted one step **or sent part of the way back down**. Nobody is long overtaxed or long resentful, because both states are temporary and frequent; the system hovers near equilibrium while everything changes.

> **In an unpredictable environment, pushing to the point of failure is sometimes the only way to use resources fully. What matters is that the response to failure is both sharp and resilient.** Perhaps we should speak not of the arc of a career but of its **sawtooth**.

---

## 5. Backchannels — the listener makes the story

Linguistics arrived at the same insight around the same time. Yngve named the **back channel** in 1970: both parties are simultaneously speaking and listening, the listener supplying *yes* and *uh-huh* without taking the turn.

**Bavelas's experiment is the striking one.** When listeners were distracted, the researchers measured not the listener's comprehension but *the story*:

> *"Narrators who told close-call stories to distracted listeners… told them less well overall and particularly poorly at what should have been the dramatic conclusion. Their story endings were abrupt or choppy, or they circled around and retold the ending more than once."*

We assume a wandering eye means poor storytelling. **The causation frequently runs the other way: a poor listener destroys the tale.** Tolins and Fox Tree showed those *uh-huhs* and *hmms* regulate both the rate and the level of detail — as functional as ACKs. *"'Bad storytellers' can at least partly blame their audience."*

---

## 6. Bufferbloat — when queues destroy feedback

A **buffer** is a queue that smooths bursts, trading **latency for throughput**. Without one, a momentarily busy cashier would have to turn customers away, underusing the cashier.

**But the cost is delay, and it can be invisible.** At a crêpe stand: twenty minutes queuing to order, then **forty more** waiting for the crêpe. The first queue was visible so customers knew what they faced; the second was not. **Cutting off the line would have made everyone better off and cost the stand nothing** — they can only make so many crêpes a day regardless of how long people wait.

**Tail Drop** — refusing everything once the queue is full — looks wasteful, like a postal carrier vaporising undeliverable parcels. But:

> **Dropped packets are the internet's primary feedback mechanism.** They are what tells a sender to halve its rate. **A buffer that is too large prevents that moderation from happening at all.**

> **Buffers only work correctly when they are routinely zeroed out.** A permanently full buffer gives you the worst of both: all the latency and none of the give. And the bigger it is, the further behind you get before you signal for help.

**The cause was economic accident.** Memory became so cheap that modem makers fitted gigabytes *because that was the smallest amount of RAM available to buy* — making buffers everywhere thousands of times too large.

---

## 7. Better never than late

Katy Perry has ~81.2 million followers. If 99% never message her and the remaining 1% message **once a year**, that is **2,225 messages a day**. Answering 100 a day puts the expected wait **in decades**. Most fans would prefer a slim chance of a reply now.

She does not have this problem leaving a venue: she signs what she can and moves on. **The body is its own flow control.** At a crowded party you take part in under 5% of the conversation and cannot catch up on the rest. Photons missing the retina are not queued. **In real life, packet loss is almost total.**

> **The problem is not that we are always connected — we are not. The problem is that we are always buffered.** The difference is enormous.

The feeling that you must read everything, watch everything, answer everything **is bufferbloat**. Email was explicitly designed to defeat Tail Drop — Tomlinson built it because *"the telephone worked up to a point, but someone had to be there to receive the call."*

> **We used to reject; now we defer.**

And the much-lamented lack of idleness is not a side effect but **the advertised function of a buffer**: bringing average throughput up to peak throughput. *Preventing idleness is what buffers do.*

The suggested remedy is to make Tail Drop explicit rather than treating it as an embarrassment of limited storage: an autoresponder that says messages are being **rejected**, not merely delayed; an inbox that auto-rejects once it passes a hundred items. Ill-advised for bills; reasonable for invitations.

**Finally, latency deserves to be a first-class citizen.** Cheshire's complaint about advertising "fast" internet purely as bandwidth: a Boeing 747 carries three times a 737's passengers at the same speed — *"would you say that a Boeing 747 is three times 'faster' than a Boeing 737? Of course not."* Capacity matters for big transfers; **for anything interactive, turnaround time matters far more.**

---

## Transferable rules

1. **Prefer many independent paths to one reliable channel.** Redundant routing makes reliability *increase* with scale, where a dedicated channel makes it decrease.
2. **Accept that confirmation is never complete** and fix a practical stopping point, rather than pursuing certainty that provably cannot exist.
3. **Treat acknowledgment as load-bearing.** Backchannel traffic is not overhead; a sender starved of it slows down or stops.
4. **Tune silence-to-alarm thresholds to the medium's round-trip time**, and state them where the other party cannot infer them.
5. **Do not eliminate the signals that prove a channel is alive.** Removing background reassurance forces both parties into constant explicit checking.
6. **Break symmetry with randomness** when two parties keep colliding through polite deference.
7. **Retry with exponentially increasing delays** rather than a fixed number of attempts. Retry rate approaches zero while never becoming refusal.
8. **Replace "three strikes and you're out" with backoff** wherever you want finite patience and infinite mercy — it protects you from an endless cycle without declaring anyone beyond redemption.
9. **Prefer immediate small escalating sanctions to delayed large ones.** Predictable and prompt beats severe and rare — HOPE cut new arrests by half and drug use by 72%.
10. **Increase commitment additively, cut it multiplicatively.** Ramp gently, retreat by half — asymmetry is what makes a shared system stable.
11. **Pull back at least as fast as you are being overloaded**, or the system cannot stabilise.
12. **Consider reversible movement in both directions** rather than one-way promotion or termination. Aim for a sawtooth, not an arc.
13. **Push to the point of failure only when your response to failure is sharp and resilient.** Otherwise do not.
14. **Judge listening as participation.** A distracted audience measurably degrades what the speaker produces.
15. **Keep queues small and drain them to empty.** A permanently full buffer delivers all the latency and none of the smoothing.
16. **Preserve the feedback that overload generates.** Refusing work is how a system learns to slow down; absorbing everything hides the signal until far too late.
17. **Make refusal explicit rather than deferring indefinitely.** Rejecting now is often kinder and more useful than a reply guaranteed too late to matter.
18. **Distinguish capacity from responsiveness.** For anything interactive, turnaround time matters more than throughput — and only one of them gets advertised.

---

## Cross-references

Ch. 5 scheduling — responsiveness versus throughput, and interrupt coalescing · Ch. 9 randomness — breaking symmetry, and randomised retry · Ch. 11 game theory — protocols as equilibria among many actors · Ch. 12 computational kindness — reducing the load a protocol places on others.

**Named references:** Vint Cerf & Bob Kahn (TCP, 1974) · Leonard Kleinrock · Paul Baran (RAND) · Van Jacobson & Michael Karels (congestion control, 1986) · Stuart Cheshire · Norman Abramson (ALOHAnet) · Judge Steven Alm (HOPE) · Deborah Gordon & Balaji Prabhakar (ants) · Laurence J. Peter · José Ortega y Gasset (1910) · Victor Yngve (back channel, 1970) · Janet Bavelas · Jackson Tolins & Jean Fox Tree (2014) · Jim Gettys (bufferbloat) · Ray Tomlinson (email) · Tyler Treat.
