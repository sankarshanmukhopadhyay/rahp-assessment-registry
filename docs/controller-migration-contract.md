# Registry-to-Toolkit controller migration contract

**Status:** migration analysis and acceptance contract, not an implemented controller cutover. Governing tracker: [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11). The original pilot compatibility gate remains [#2](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/2).

## Verified current coupling

This inventory describes the inspected Toolkit code on 2026-11-17; specific source revisions must be pinned when execution tests are built.

| Consumer | Observed dependency | Migration consequence |
| --- | --- | --- |
| Toolkit `tools/dpip_handoff.py` | `referral_id(source_issue, payload)`, `identity(source_issue, payload)` and `source_data(rahp_repo, rahp_issue, payload)` bind DPIP referral provenance to a numbered RAHP issue. | A Registry case ID cannot be substituted for the issue number without a versioned adapter and legacy-reference resolution. |
| Toolkit `tools/dpip_return_reconcile.py` | Return markers and reconciliation/residual markers bind source and target issue numbers; `ensure_residual` can create a Toolkit issue. | Retargeting alone can lose return deduplication, change residual ownership or create non-development Toolkit issues. |
| Toolkit `.github/workflows/dpip-lifecycle.yml` | Event and dispatch routing use `issue_number` and call issue-based lifecycle, DPIP return and evidence provenance reconciliations. | A Registry-initiated execution needs an explicit controller execution reference that the existing consumer can resolve. |
| Toolkit `tools/evidence_producer_scheduler.py` | Discovers active obligations and optionally selects a numbered issue, then drives issue-based producer execution. | Producer and outbox lifecycles must remain discoverable without external assessment issues in Toolkit after cutover. |
| Toolkit `tools/publish_assessment_issues.py` | `CANONICAL_RAHP_ISSUE_REPOSITORY` is fixed to Toolkit and existing owner detection is issue-marker based. | Do not change the destination constant to Registry as a standalone migration. |
| Registry `scripts/registry_intake.py` | Source-pinned external-case-only planning, exact-key deduplication, and a manually reviewed migrated-finding map; `--apply` is opt-in. | The adapter is not a durable outbox or a controller-return consumer. Its dry-run success is not write/retry qualification. |

## Identity and authority invariants

1. **Case identity:** Registry owns the durable external assessment case and administrative owner. It is not the Toolkit controller's internal execution ID.
2. **Execution identity:** Toolkit remains canonical for RAHP assessment/assurance state and result semantics. A Registry case may reference an attributed execution, but cannot infer a determination from an issue state, a workflow exit code or a schema-valid URL.
3. **Source identity:** Source repository and immutable source revision, finding identity, proposition key and materiality/reassessment triggers remain separately attributable; a new source revision need not create a new case.
4. **Specialist identity:** Existing `rahp-assessor-result/v1` and `rahp-evidence-producer-result/v1` contracts and their source pins, authority, idempotency and correlation remain valid. Existing issue-number-based referrals must resolve unambiguously during migration.
5. **Delivery identity:** Each side effect has a stable delivery/attempt record and auditable acknowledgment. Timeout or partial failure is not a successful handoff. Neither a missing return nor an unavailable producer becomes PASS.
6. **Publisher authority:** Registry becomes the only external case writer **after** verified cutover. Toolkit retains development issues and portable method, not externally owned assessment tracking issues. A disabled or failed Registry publisher may not silently fall back to Toolkit issue creation.
7. **Historical authority:** Original Toolkit issues and their GitHub URLs remain source evidence. Historic closed cases must not be reopened by importing or replaying them.

## Minimum compatibility adapter before the switch

Define and validate an explicit mapping from **Registry case ID + immutable source/referral identity** to **Toolkit execution/controller identity** and any historical Toolkit issue-number anchor. Keep directionality explicit. This mapping must not silently confer RAHP or DPIP assurance authority.

The replacement execution path must demonstrate, through the actual controller consumer rather than a registry-only mock:

- New external case initiation, existing-owner replay and changed-source reassessment without duplicates.
- An ordinary DPIP return with the original v1 contract; a corresponding Lab producer result when a real supported producer path is available.
- Duplicate, delayed, stale, wrong-target, contradicted and unauthenticated/unavailable returns that never advance an unsupported assurance outcome.
- Durable pending delivery, transport error, retry, partial publish and restart recovery; no acknowledgments before externally observable effects.
- Source-pinned controller state, residual owner, referral and evidence receipts that remain traceable from the Registry case.
- Zero new non-development Toolkit issue writes in the qualified post-switch cycle, and a rollback path without dual-active publishers.

## Ordered implementation gates

1. **Capture legacy compatibility fixtures.** Pin Toolkit, Registry, DPIP and Lab revisions. Preserve existing source issue-number/marker behavior as regression evidence; do not rewrite live markers in place.
2. **Expose a stable execution boundary in Toolkit.** Prefer an adapter over a second RAHP engine. Identify the smallest callable/CLI contract that accepts a Registry case reference while retaining canonical controller semantics.
3. **Implement Registry-owned delivery and reconciliation.** Use the existing intake and case model; add persistence and retry semantics before enabling writes. Treat case state, execution state and delivery state separately.
4. **Exercise full return paths.** Test the actual DPIP and producer consumers with positive, negative and cross-run/idempotency cases; demonstrate that historical Toolkit issue references remain resolvable.
5. **Run shadow parity and rollback.** Use identical source pins and inspect findings, event routing, controller outcomes, specialist receipts and external side effects. Explicitly record unexplained differences.
6. **Switch publication authority.** Only after verified acceptance, disable the Toolkit external-case publishers and enforce a development-only Toolkit issue invariant. Prove no late or duplicate publisher writes.

## Non-goals and current qualification

This document does **not** define a replacement result schema, authorize credential retargeting, enable Registry issue writes, remove Toolkit workflows, establish historical full-timeline completeness, or claim operational cutover. [The pinned DTG routing parity run](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/43877660730) establishes a narrower source-routing compatibility claim. Independent assessment and acceptance remain separate from CI and AI-assisted review.

A release is **not warranted** until the Registry has a consumable, verified operational assessment boundary.
