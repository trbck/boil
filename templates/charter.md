---
project: <dirname>
type: business            # business | life
status: candidate         # candidate | active | parked | killed
stage: L0
score: 0.0
north_star: "<the ONE metric, e.g. '€ MRR' or 'days/week actually used'>"
north_star_current: "0"
kill_by: <YYYY-MM-DD>     # date by which kill criteria are evaluated
created: <YYYY-MM-DD>
last_audit: <YYYY-MM-DD>
---

# Charter — <project>

<!-- /boil init interview: answer these, then delete the questions.
  1. In one sentence: what does this do, for whom?
  2. Why will THAT person pay / why will future-you keep using it?
  3. Why can't ChatGPT / an existing product do this for them already?
  4. What is the north-star metric, and what value makes this a success?
  5. What is the SMALLEST version that could move that metric?
  6. Kill criteria: what outcome by what date means we stop?
  7. Non-goals: what will this deliberately NOT do (the scope fence)?
  8. What has to be true outside of code (users found where? priced how?)?
  9. What does L5 look like concretely (€/month, or daily-life role)?
 10. Which currently active project does this displace, and why is that right?
-->

## Goal
<one paragraph: what, for whom, and the payoff>

## Why this wins
<why the target person pays / keeps using it; why not solved by AI or incumbents>

## North star
**Metric:** <metric> · **Success:** <target value + date> · **Now:** <current value>

## Kill criteria (pre-committed)
- Kill/park if <observable outcome> is not true by <date>.
- Kill immediately if <invalidating discovery>.

## Non-goals (scope fence)
- This will NOT <tempting adjacent feature>.
- This will NOT <second one>.

## Distribution & money (the non-code plan)
- First 10 users come from: <specific channel>
- Pricing hypothesis: <€X for Y>
- First euro is charged when: <observable trigger, e.g. "L3 gate green">

## Post-mortem
<!-- only filled when status → killed: 3 lines — what we believed, what was true, what to reuse -->
