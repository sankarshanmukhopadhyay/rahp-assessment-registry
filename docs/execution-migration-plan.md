# RAHP assessment operations migration: authority and cutover gates

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
