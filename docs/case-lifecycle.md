# Assessment case identity and lifecycle

## Admission

One case describes a materially distinct assurance proposition for a defined subject and source context. If a new observation affects the same proposition, append source provenance and assess applicability before opening another case. A change marker is not a defect.

A case must include stable `case_id`, `subject`, `proposition`, `source`, `owners`, `lifecycle`, `evidence`, `assessment`, `residuals` and `reassessment` fields. The current validator checks structural and key cross-field invariants; it is not a normative RAHP schema or a substitute for a human assessment.

## Separate dimensions

- **Administrative lifecycle:** `proposed`, `active`, `waiting_external`, `superseded`, `closed`. These describe ownership and coordination.
- **Evidence state:** `unverified`, `partially_verified`, `verified`, `unavailable`, `contradictory`. These describe attributable availability/adequacy, not truth of every claim.
- **Assessment determination:** `not_assessed`, `PASS`, `FAIL`, `NOT_APPLICABLE`, `INDETERMINATE`. Except `not_assessed`, these are RAHP determinations imported with attributable source evidence; registry administration never invents one.
- **Source-level change classification:** `new`, `preserved`, `strengthened`, `weakened`, `uncertain`. This is analytical classification, not conformance.

A case with unresolved residuals can be *administratively* closed only when every residual has a durable, explicitly accepted receiving owner and the closeout says that outstanding assurance has not passed. `closed` does not set `PASS`.

## Receipt and handoff

1. Observe consolidated source finding and compare existing case identities.
2. Identify proposition, authoritative source revision, applicable protocol/release and consuming context.
3. Confirm distinct registry owner versus source-system, RAHP implementation and specialist owners.
4. Assess evidence against the target's positive, negative and false-success paths.
5. Record dated disposition, residual dependencies and retest trigger.
6. Transfer only with an acknowledged owner and original issue reference.
7. Recheck that an old source issue is not falsely represented as resolved before closing it.

Case records are version-controlled snapshots. Use precise source pointers and retain the original issue history; do not bulk copy comment trails into JSON.

## Initial pilot acceptance

- Validate one real source-pinned case with both positive and negative structural checks.
- Verify a newcomer can trace the finding, upstream change and remaining case owner.
- Demonstrate that missing evidence cannot become assurance PASS or administrative terminalization.
- Leave the original Toolkit issue active until a separate handoff is explicitly accepted.
- Do not activate automation or bulk transfers before evaluating the pilot.
