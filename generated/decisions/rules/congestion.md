# Rules — Networking, queues and congestion

`18` rules · ~365 words · ~492 tokens

Cite by ID. `primary` rules come from books; `derived` rules come from your own notes and research and must never silently override a primary rule — if they conflict, say so.

### ATLB-10 — Networking

<sub>Algorithms to Live By</sub>

- **ATLB-10-R1** — **Prefer many independent paths to one reliable channel.** Redundant routing makes reliability *increase* with scale, where a dedicated channel makes it decrease.
- **ATLB-10-R2** — **Accept that confirmation is never complete** and fix a practical stopping point, rather than pursuing certainty that provably cannot exist.
- **ATLB-10-R3** — **Treat acknowledgment as load-bearing.** Backchannel traffic is not overhead; a sender starved of it slows down or stops.
- **ATLB-10-R4** — **Tune silence-to-alarm thresholds to the medium's round-trip time**, and state them where the other party cannot infer them.
- **ATLB-10-R5** — **Do not eliminate the signals that prove a channel is alive.** Removing background reassurance forces both parties into constant explicit checking.
- **ATLB-10-R6** — **Break symmetry with randomness** when two parties keep colliding through polite deference.
- **ATLB-10-R7** — **Retry with exponentially increasing delays** rather than a fixed number of attempts. Retry rate approaches zero while never becoming refusal.
- **ATLB-10-R8** — **Replace "three strikes and you're out" with backoff** wherever you want finite patience and infinite mercy — it protects you from an endless cycle without declaring anyone beyond redemption.
- **ATLB-10-R9** — **Prefer immediate small escalating sanctions to delayed large ones.** Predictable and prompt beats severe and rare — HOPE cut new arrests by half and drug use by 72%.
- **ATLB-10-R10** — **Increase commitment additively, cut it multiplicatively.** Ramp gently, retreat by half — asymmetry is what makes a shared system stable.
- **ATLB-10-R11** — **Pull back at least as fast as you are being overloaded**, or the system cannot stabilise.
- **ATLB-10-R12** — **Consider reversible movement in both directions** rather than one-way promotion or termination. Aim for a sawtooth, not an arc.
- **ATLB-10-R13** — **Push to the point of failure only when your response to failure is sharp and resilient.** Otherwise do not.
- **ATLB-10-R14** — **Judge listening as participation.** A distracted audience measurably degrades what the speaker produces.
- **ATLB-10-R15** — **Keep queues small and drain them to empty.** A permanently full buffer delivers all the latency and none of the smoothing.
- **ATLB-10-R16** — **Preserve the feedback that overload generates.** Refusing work is how a system learns to slow down; absorbing everything hides the signal until far too late.
- **ATLB-10-R17** — **Make refusal explicit rather than deferring indefinitely.** Rejecting now is often kinder and more useful than a reply guaranteed too late to matter.
- **ATLB-10-R18** — **Distinguish capacity from responsiveness.** For anything interactive, turnaround time matters more than throughput — and only one of them gets advertised.

