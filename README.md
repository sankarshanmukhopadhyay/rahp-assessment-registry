# RAHP Assessment Registry

A public, independently maintained case-management surface for source-pinned RAHP examinations and their unresolved assurance obligations across trust-system projects.

**Status (19 November 2026):** pilot / working draft. The Registry owns external assessment-case admission, administrative succession and evidence coordination. The first **direct** Registry case is [#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47). The first **accepted source-scoped monitored transfer** is historical Toolkit [#272](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/272) → active Registry [#88](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/88), case `RAHP-AR-DTG-0002`, with authenticated original and later source-epoch receipts. This is administrative case ownership, **not** a portfolio-wide publisher cutover, independent RAHP determination or specialist return. Toolkit retains the canonical RAHP method, engine, validators and execution semantics. The governing unfinished operational migration is [#77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77); its [gate ledger](docs/migration-gate-status.md) retains G1–G6 as unaccepted.

## Start here

1. Read [governance and authority](GOVERNANCE.md) and the [case lifecycle](docs/case-lifecycle.md).
2. Inspect the [network-response pilot case](cases/dtg/network-answer-proof-2026-11.json), its [active Registry owner (#4)](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4) and the [closed historical Toolkit source (#1203)](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203).
3. Validate tracked cases locally with `python3 scripts/validate_cases.py` and `python3 -m unittest discover -s tests -v`.
4. Use the [assessment-case issue template](.github/ISSUE_TEMPLATE/assessment-case.md) only for a genuinely distinct proposition with an accountable owner.

## Ownership and non-authority

| Surface | Owns | Does not own |
| --- | --- | --- |
| [DTG Portfolio Monitor](https://github.com/sankarshanmukhopadhyay/dtg-portfolio-monitor) | Change observations, source consolidation, materiality and monitored-finding disposition | RAHP assessment outcomes |
| [RAHP Toolkit](https://github.com/sankarshanmukhopadhyay/rahp-toolkit) | Portable RAHP method, engine, execution contracts, validators, reconciliation semantics and release qualification | Externally owned case admission or authoritative upstream implementation state |
| **This registry** | Case admission, review scope, evidence references, handoffs, residual ownership, reassessment triggers and administrative case lifecycle | RAHP runtime outcomes or external normative authority |
| External source and specialist repositories | Their own specifications, implementations, remediation and specialist determinations | Other repositories' governance |

A registry case is an indexed, attributed assessment record. Registry coordinates case admission, ownership, evidence references, specialist referrals and reassessment; it consumes canonical Toolkit execution contracts without redefining assurance semantics. It cannot assert PASS simply because upstream CI passed, a monitor ran, or a GitHub issue closed. The full original issue and authoritative evidence remain accessible through durable links. **No issue is automatically transferred or closed by adding a case record.** For executing an assurance examination independently of Registry, start with the [Toolkit adoption guide](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/blob/main/docs/adoption-guide.md).

## Queue migration intake

The [2026-11-16 provisional 58-issue inventory](docs/queue-triage-2026-11-16.md) separates Toolkit-owned work from external case and specialist obligations. It is advisory and does not create or accept any issue handoff.

## Specialist and executable-evidence routing

See [DPIP and Interop Lab referrals](docs/specialist-routing.md) for the existing source-controlled return contracts, testing responsibility and case-referral admission rules.

## Registry DTG live monitoring shadow

The [read-only, scheduled live monitoring shadow](docs/live-shadow-monitoring.md) runs pinned Toolkit monitoring alongside Registry routing, checks source-matched output parity and retains source pins and event outputs. Its read-only materiality-to-case reconciliation identifies existing owners, reviewed pending creation and reassessment requirements without admitting cases or writing issues. It does not replace Toolkit's active publisher or override DPIP/Lab/RAHP controller authority.

## Registry-executed historical source replay

A [pinned, non-publishing DTG routing replay](docs/pinned-dtg-replay.md) invokes the canonical Toolkit implementation from a Registry workflow, without forking assurance semantics. It retains source and decision artifacts and makes no case writes.

## External intake prototype

The [opt-in fail-closed intake adapter](docs/external-intake.md) supports source-pinned external event classification and idempotent registry-issue planning. It is dry-run by default and **not yet wired into the Toolkit's live publisher or DPIP/Lab return paths**.

## Source-controlled intake replay

The [controlled Registry outbox replay](docs/durable-intake-replay.md) persists reviewed source-pinned intake intent in Git and requires an authoritative live issue re-read before acknowledging delivery. Read-only materiality-to-case reconciliation now consumes observed, source-matched routing output and compares it with that reviewed intent. The separate manually dispatched, main-only apply workflow preserves existing-owner replay and additionally permits **only exact, source-qualified direct-first-intake cases** with a committed approval and no historical Toolkit issue; it does not authorize an arbitrary DTG/CAWG publisher transfer. Registry #47 was created through an operator-mediated invocation of that reviewed intake intent and authoritatively re-read; the automated direct-write dispatch is implemented but not yet proven by a real write. There is no automatic materiality-to-outbox enqueue, Registry controller cutover or authenticated Registry-directed DPIP/Lab return.

## Canonical source-pinned pilot assessment

The [Registry-executed RAHP pilot](docs/canonical-registry-assessment.md) invokes the immutable Toolkit controller with the existing source-pinned case and an explicitly empty native-evidence ledger. Its expected result is `INDETERMINATE` / `evidence-required`, not a Registry case PASS or operational cutover.

## First Registry-originated direct assessment

The [ONDTF-GOV-006 case](cases/ondtf/emergency-authority-v1.json) is source-pinned to the v1.0.0 release. Its administrative owner is [Registry #47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47); [the canonical controller workflow](.github/workflows/registry-canonical-assessment.yml) executes the source-pinned assessment with no implementation-native evidence and returns **INDETERMINATE / evidence-required**, retaining an exact case/execution binding. No DPIP or Lab result is claimed. The existing [outbox shadow](.github/workflows/outbox-live-shadow.yml) verifies the live #47 owner without writing issues.

## Historical preservation and operator references

[History locator and inventory](archive/README.md) · [Case succession](docs/case-succession.md) · [Execution migration](docs/execution-migration-plan.md) · [History capture](docs/history-capture.md) · [Full-content staging review](docs/persistent-history-staging.md) · [Execution journal](docs/registry-execution-journal.md) · [Registry native intake](docs/registry-native-intake.md) · [G1–G6 gate status](docs/migration-gate-status.md) · [active cutover #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77).

## Pilot scope and migration status

The initial pilot's **external evidence coordination ownership** was manually transferred from historical Toolkit [#1203](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203) to Registry [#4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4). The first source-scoped **operational administrative transfer** subsequently moved the exact monitored four-finding group from Toolkit [#272](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/272) to Registry [#88](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/88) under Toolkit's monotonic `accepted_group` ledger. The later two-finding Monitor subset received a separately authorized epoch acknowledgment; the actual Toolkit handoff [run #44462670290, attempt 2](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/actions/runs/44462670290) held the Registry-owned group, retained two unrelated events and created no duplicate Toolkit issue. These bounded effects do not reclassify the case's `not_assessed` determination or imply that all external sources are exclusively routed through Registry.

Registry direct-case execution already uses pinned Toolkit contracts, including the ONDTF [#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47) evidence-required example. For the transferred #88 group, the source-level materiality review and upstream/current-VTI baseline tests are distinct from end-to-end target-native assurance; its residuals remain open. **Operational completion is still blocked** by historical-ref Toolkit writer exclusion, eligible Registry→Toolkit execution/identity reconciliation, an independently admitted specialist roundtrip where justified, and governed reverse-transfer evidence. [PR #99](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/pull/99) added read-only historical writer source detection, **not** a server-enforced write fence. No full DTG/CAWG producer, DPIP/Lab return, or universal controller cutover is asserted.

Use the [controller migration contract](docs/controller-migration-contract.md), [current writer inventory](ops/migration/toolkit-writer-cutover-inventory.md), [migration gate ledger](docs/migration-gate-status.md) and open [operational tracker #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77). The closed [predecessor #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11) preserves the original six-gate requirements, **not** their acceptance. Do not retransfer #272, reinterpret historical snapshots as current, or publish a release merely because a source-scoped administrative handoff succeeded.

## Contribution and licensing

See [CONTRIBUTING.md](CONTRIBUTING.md). Code and validation scripts are under Apache-2.0 ([LICENSE](LICENSE)); external evidence remains governed by its own source and licensing. No third-party document is copied into the registry by reference alone.
