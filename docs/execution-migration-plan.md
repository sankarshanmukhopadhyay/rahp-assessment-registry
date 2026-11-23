# RAHP assessment operations migration: authority and cutover gates

## Operational checkpoint (23 November 2026)

This document is the **operator migration plan**, not reader-facing Registry
README material. The authoritative active work tracker remains
[Registry #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77);
the evidence ledger is [migration-gate-status.md](migration-gate-status.md).

**Verified and accepted within their narrow bounds:**

- Toolkit [PR #1248](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/pull/1248)
  exercised a real GitHub App-authored, DCO-signed, native-check state PR,
  merged through protected main. Post-merge `reconcile`, `local_incidents`,
  `validate`, build and Pages checks succeeded. This proves **Toolkit state
  persistence**, not Registry external-case publication exclusivity.
- Toolkit's transfer ledger retains the source-qualified, accepted
  Toolkit #272 → Registry #88 group. This does not grant authority to
  re-admit or retransfer its historical owner.
- Registry [PR #106](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/pull/106)
  corrected the pre-publication quiescence guard to recognize current
  `dtg-materiality-main.yml` and `instance-monitor-main.yml` paths as
  well as retired names. A clean snapshot is still **not a dispatch fence**.

**Remaining authority switch conditions:** independently verify all current and
historical writer dispatch routes are excluded during handover, preserve
legitimate Toolkit-local controller and development issues, demonstrate
Registry new-case delivery/readback and interruption-safe replay using an
admitted source-qualified case, and exercise canonical Toolkit consumer
identity mapping. DPIP/Lab specialist return requires an independently
admitted applicable proposition; never create one merely to check a box.
A governed reverse-owner operation must reject simultaneous Registry/Toolkit
writes. Until those conditions are met, leave existing fences in effect and
do not claim universal Registry case ownership, G1–G6 acceptance, or a release.

**Names and source authority:** the earlier document and historical evidence
below deliberately refer to `dtg-portfolio-materiality-handoff.yml` and
`instance-watch.yml`; the current live workflows are
`dtg-materiality-main.yml` and `instance-monitor-main.yml`. Current writer
counts and consumer inventory are maintained in
[the operational writer inventory](../ops/migration/toolkit-writer-cutover-inventory.md),
not inferred from dated examples below.

## Final activation contract: conditions and ordered go/no-go decisions

This is the bounded **execution contract for the eventual authority switch**,
not evidence that the switch has occurred. It is governed by
[Registry #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77)
and [G1–G6](migration-gate-status.md). An already accepted source case (#88)
cannot be used to manufacture new-case admission evidence, and unrelated
Toolkit-local controller incidents remain legitimate.

The final activation must use the existing Toolkit and Registry source contracts.
No generic issue-number substitution, duplicate RAHP engine, unreviewed specialist
referral, or branch-protection exception is permitted. Stop at the first failed
condition, retain original observations and intent, and keep both producer states
visible rather than claiming a completed switch.

| Ordered stage | Positive evidence required before advancing | Failure disposition |
| --- | --- | --- |
| 1. Source and destination scope | Exact case key, upstream revision, material findings, owner/previous owner, residuals, fresh maintainer authorization and existing-owner comparison. Existing #88 remains singly owned. | Retain observed source; no new case. |
| 2. Exclusive old-writer exclusion | Current Toolkit external/mixed issue-publishing jobs lose external issue mutation authority for the admitted scope, **without** disabling accepted-state local incident writes. Old workflow registrations, branch/tag dispatch paths, independent writer credentials and in-flight runs must be checked under an enforceable exclusion. | Toolkit stays active for untransferred keys; Registry new-case writes remain blocked. |
| 3. Durable Registry delivery | Committed source-qualified pending intent; unique owner read from full live Registry history; one authorized serialized POST when needed; read-after-write owner acknowledgment; timeout-after-commit and replay; no duplicate on a repeated or changed epoch. | Keep pending outbox; do not fall back to Toolkit publication. |
| 4. Canonical execution binding | Immutable Registry case and source scope bound to a Toolkit-native controller execution and raw/normalized result; separate case ID, execution ID, historical Toolkit issue URL and specialist ID; replay and wrong-namespace negative checks. | Keep case as `not_assessed`, or retain the actual qualified `INDETERMINATE` execution record without importing PASS. |
| 5. Specialist applicability | Independently admitted source-specific DPIP/Lab proposition **if applicable**, authorized transport and source/epoch/referral-bound return consumed by canonical Toolkit semantics; contradictory/duplicate/stale negatives. If not applicable to the chosen case, preserve the explicit non-referral decision; that does not qualify global specialist interoperability. | Retain residual with independent owner; do not fabricate a referral or import a specialist PASS. |
| 6. Reversible owner handover | Authoritative Registry owner and acknowledgment, Toolkit transfer guard, exclusion of Registry writes before any governed return, preserved historical issue URLs and nondeletion of accepted transfer evidence. Demonstrate interrupted transfer and return with both sides independently read back. | Quarantine writes and retain evidence; no dual-active publishers or rollback-by-ledger-deletion. |
| 7. Live operational verification | One fresh materially relevant source cycle proves observation → qualified Registry owner/reassessment → canonical execution binding → residual/terminal disposition, with zero duplicate Toolkit external-case writes and intact Toolkit-local incidents; checks and protection pass. | Reopen gate evidence, not an assessment PASS. |

The *activation tranche* can be final only if it includes both the switch and
these observed acceptance results. A source-code PR or test-only rehearsal
cannot satisfy an effectful gate. In particular, the independently governed
specialist round trip cannot be promised in advance if no genuine accepted
specialist proposition exists. It is legitimate to leave that specific
interoperability gate open and operate the subset that is independently
qualified; it is not legitimate to label full G1–G6 cutover complete.

### Current readiness and activation blockers

[Toolkit #1248](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/pull/1248)
proves App-authored state persistence and protected-main reconciliation.
[Registry #106](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/pull/106)
prevents false quiescence from obsolete workflow names.
[Toolkit #1250](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/pull/1250)
refuses stale current-code Actions issue mutations. The
[all-ref writer audit](../ops/migration/toolkit-writer-cutover-inventory.md)
now enumerates historical source exposure and preserves legitimate local
incidents. Existing transferred case #88 has a source-pinned Toolkit
`INDETERMINATE/evidence-required` execution return and a distinct accepted
administrative owner; it is not proof of general Registry case publication.

**Not yet established:** server-enforced old-ref/future-dispatch exclusion,
universal Registry new-case producer activation, reusable first-party controller
consumer eligibility across newly admitted external cases, genuine
Registry-directed specialist return where warranted, and tested exclusive
reverse transfer. Until each relevant condition is positively proved,
maintain the current source-specific guards and conditional intake authority.

## Boundary

**Toolkit retains canonical portable RAHP methods, engine, schemas, reusable inference/validation algorithms, SDK, developer tests, security and release governance.** Registry takes operational *application* of those capabilities: monitored-source adapters, DTG/CAWG instance routing, materiality review, assessment execution scheduling and artifacts, controller correlation, DPIP/Interop Lab handoffs, issue publication and full history. The registry should invoke a **pinned Toolkit engine contract**, not fork a second assurance engine or change result semantics.

## Migration inventory

| Existing Toolkit components | Registry responsibility | Gate |
| --- | --- | --- |
| `fetch_dtg_portfolio_snapshot.py`, `dtg_portfolio_baseline.py`, `dtg_portfolio_routing.py`, `materiality_journal_gate.py`, `finding_model.py`, instance DTG policy | Monitoring input qualification and source-pinned materiality routing | exact same snapshot/digest, normalization, unmapped events and freshness failures |
| `dtg-portfolio-materiality-handoff.yml`, `instance-watch.yml`, `review-workers.yml` | Operational intake, workflow triggers and controller-side execution without Toolkit non-dev issue writes | one active case; replay, failures, retry, and negative outcomes |
| `publish_assessment_issues.py`, `publish_dtg_controller_incidents.py`, `reconcile_assessment_issues.py`, `validate_issue_publication_policy.py` | Registry case publication, historical reassessment and archive | all old keys mapped and no duplicate or reopened Toolkit external issue |
| `dpip_handoff.py`, `dpip_lifecycle*.py`, `dpip_return_reconcile.py`, `evidence_producer_scheduler.py`, `evidence_provenance_router.py` | Controller-compatible DPIP and Lab routing/returns | original v1 contracts, durable outbox, idempotency, wrong-issuer/late/stale/duplicate return rejection |
| `combined_review_worker.py`, `dtg_repository_review_worker.py`, `cross-spec-pressure-test.yml`, `clean-room-assessment.yml` | Registry-owned execution scheduling and target-specific records, using Toolkit portable execution library | fixture parity and actual target-native positive/negative evidence |
| `assurance.py`, `assessment_controller.py`, `assurance_fsm.py`, `engine_contract.py`, portable `method/`, schemas | **Stay in Toolkit**; exported/tested versioned dependency | stable or explicitly versioned callable/result contract, independent consumer reproduction |

## Non-negotiable verification

1. **Complete historical classification.** Baseline every source GitHub issue including closed records, but do not equate the archive pointer inventory with a full-content mirror. Preserve comments, attachments and historical as-of semantics before declaring archival completeness.
2. **Pinned-input parity.** Run *both* old and registry pipelines on identical snapshots/revisions. Compare all generated events, digest, source-pin, normalization, reassessment, controller IDs and limitations; investigate every delta.
3. **Specialist and producer assurance.** For DPIP `rahp-assessor-result/v1` and Lab `rahp-evidence-producer-result/v1`, demonstrate idempotent duplicate/late, unavailable, failed, stale and adversarial results across the actual consumer path. No schema-valid self-attested PASS.
4. **Registry-native write and replay.** Use least-privilege token, persistent outbox, no-loss retry and evidence receipts; distinguish case ID from engine execution identity. GitHub Action green does not equal assurance PASS.
5. **Shadow operation.** Exercise a whole material-change cycle with native and registry consumers; prove zero unexplained differences and no effects outside the test boundary.
6. **Atomic authority cutover.** Change the hard-coded Toolkit publisher, `validate_issue_publication_policy.py`, DTG/CAWG configs, review workers and workflow dispatches in a coordinated, testable switch with rollback and no double writes.
7. **Historical completion.** Classify external, mixed and development cases individually; keep Toolkit development issues there. Closed external cases can be indexed and mirrored as closed archival records, without fabricating new open obligations or dropping source history.
8. **Post-cutover invariant.** Automatic monitoring may never create or reopen non-development Toolkit issues; registry owns all assessment records and can identify provenance and residual status.

## Current evidence

[Registry #4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4) owns the manually transferred pilot. Registry intake run [43871859400](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/43871859400) established read-only live deduplication and 35 passing tests; it did *not* verify write-mode creation, controller returns or actual runtime assurance. Toolkit monitor run [43871548910](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/actions/runs/43871548910) failed closed because the required fresh snapshot was absent. A direct repository switch would violate the issue-based DPIP controller dependency.

## Decision

**No blind code copy, bulk issue transfer, hard-coded repository rewrite or premature switch.** First make the archival baseline trustworthy and exercise a pinned source replay; then migrate the operations runner and preserve RAHP portable engine authority. Keep legacy workflow operational until parity and rollback criteria are met. No release warranted yet.

## First new-case ordering: reservation qualification

Before creating a Registry successor issue, Toolkit must have a source-controlled
`reserved` ledger entry that prevents the Toolkit issue publisher from modifying
the exact proposition. The reservation contains the historical Toolkit issue,
the exact Registry `outbox/pending/*.json` path, source revision and finding ID.

Registry now provides a **read-only** check on that prerequisite:

```sh
REGISTRY_INTAKE_TOKEN=<authorized read token> python3 scripts/registry_outbox.py \
  --manifest outbox/pending/qualified-case.json \
  --receipt build/outbox/reservation.json --qualify-reservation
```

This re-reads live Toolkit `main` at a pinned commit, validates the committed
transfer ledger, exact case/finding/source pins and historical Toolkit issue,
and rejects a branch-head change during verification. It does **not** create
a Registry issue and must not be treated as operational publication
authorization or an assurance conclusion. The existing `--apply` route
remains blocked for new cases.

**Remaining live transaction dependency:** the Toolkit and Registry workflow
coordinator must demonstrate exclusive publication across *all* relevant
Toolkit writers (including in-flight runs) and preserve first-party controller,
DPIP and reviewer correlation before Registry production issue POST is enabled.
A successful read-only reservation check alone does not establish those facts.

### Committed-intent cross-check

The Registry reservation qualifier also reads the pending-intake JSON from
**Registry `main` at an immutable commit** and compares its parsed record
exactly with the supplied manifest. It rereads Registry `main` before
acknowledging qualification and rejects branch drift. Local files or PR-only
manifests do not confer authority even when Toolkit contains a reservation.
The result is read-only; it cannot publish an issue or establish cutover.
