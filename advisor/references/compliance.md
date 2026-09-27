# Compliance manifests

Every artifact produced in `produce` mode carries a manifest. It is a short header, not
paperwork.

**The point:** a numbered rule is only useful if you can tell, later, which ones a piece of
code actually honoured. Without a manifest, a violation is indistinguishable from an oversight six
months on — and the reviewer has to re-derive the whole design to find out. The manifest converts
"trust me" into something checkable.

The thing it prevents is **silent violation**. Deviating from a rule is often correct; deviating
without saying so is what destroys the audit trail.

## Format

```python
# ─────────────────────────────────────────────────────────────────────────────
# Compliance manifest — generated against corpus 049c7fa15910
#
# Honours:
#   ASSP-05-R7   signals shifted +1 bar (see build_signals, line 41)
#   ASSP-06-R4   P&L accrued before resize (see step_portfolio, line 88)
#   ASSP-06-R12  fractional Kelly, f = 0.33
#   ML4T-16-R8   gross and net reported together
#   ML4T-16-R9   break-even cost 34bp vs assumed 10bp
#
# Violates (deliberately):
#   ML4T-16-R18  exploration and confirmation not separated — this is a research
#                spike on in-sample data only. Results are not evidence of edge.
#
# Unresolved:
#   Cost-model class frozen as spread+slippage; financing and impact not modelled.
#   Capacity untested.
# ─────────────────────────────────────────────────────────────────────────────
```

Three sections, and the last two matter more than the first:

- **Honours** — rule ID, what satisfies it, and where. A pointer to the line makes it verifiable.
- **Violates (deliberately)** — rule ID and the *reason*. If you cannot write a reason, that is not
  a deliberate violation, it is a bug.
- **Unresolved** — assumptions still open, particularly any of the five frozen choices left unset.

Record the corpus fingerprint (from `generated/<domain>/ROUTER.md`). It says which build of the knowledge
base the claims were checked against, so a later reader knows whether the corpus has since moved.

## Scope

Only list rules that genuinely bore on the code. A manifest citing forty rules is noise and nobody
reads it; five to fifteen relevant ones is a document someone will actually check. Prefer the rules
that a reviewer would otherwise have to rediscover.

## For non-code artifacts

Specs and research plans use the same three sections in prose. The `Unresolved` section is the
important one in a spec — it is the list of things that must be settled before implementation, and
it is what the next session picks up.

## Verifying a manifest

The claims are checkable, which is the whole point:

```bash
python3 scripts/lookup.py --rule ASSP-06-R4     # confirm the rule says what the manifest claims
python3 scripts/validate_pack.py                # confirm the corpus itself is intact
```

If a manifest cites an ID that does not resolve, treat the artifact as unreviewed until corrected.
A fabricated citation is a worse defect than a missing one, because it looks like diligence.
