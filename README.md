# RAHP Assessment Registry

A public, independently maintained case-management surface for source-pinned RAHP examinations and their unresolved assurance obligations across trust-system projects.

**Status:** pilot / working draft. Historical external-case succession is demonstrated by Registry #4; the first source-qualified **direct** Registry case is [#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47). Direct-case publication and canonical Toolkit execution have been observed, but full DTG/CAWG producer transfer and authenticated DPIP/Lab return cutover remain unqualified. This repository does not certify systems, govern upstream specifications or own the canonical RAHP engine. Registry Actions can invoke pinned Toolkit routing code; that is not a Registry-native RAHP assurance determination or a live controller cutover.

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

[History locator and inventory](archive/README.md) · [Case succession](docs/case-succession.md) · [Execution migration](docs/execution-migration-plan.md) · [History capture](docs/history-capture.md) · [Full-content staging review](docs/persistent-history-staging.md) · [Execution journal](docs/registry-execution-journal.md) · [Registry native intake](docs/registry-native-intake.md).

## Pilot scope and migration status

The initial pilot's **external evidence coordination ownership was manually transferred** from historical, now-closed [Toolkit #1203](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203) to active [Registry #4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4). The case remains `not_assessed`; its residual evidence obligations are open. This is not a transfer of source remediation or canonical Toolkit assessment authority.

Registry now runs read-only monitoring, pinned source-routing/parity and source-matched materiality-to-case reconciliation. It has also **admitted a single direct-source ONDTF case** [#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47), bound its evidence-required result to a canonical Toolkit execution and preserved the intake record. **Automated DTG/CAWG publication cutover remains blocked** pending coordinated source partition, producer fencing and first-party consumer migration. Toolkit's operational case publisher and specialist-return paths remain active; Registry controller orchestration and authenticated Registry-directed DPIP/Lab delivery and return reconciliation have **not** cut over. The broader historical archive is subject to separate verification. No bulk migration or release claim is asserted.

The [controller migration contract](docs/controller-migration-contract.md) records the observed legacy issue-number coupling and the executable acceptance conditions required before a publisher switch; [issue #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11) tracks the operational migration.

## Contribution and licensing

See [CONTRIBUTING.md](CONTRIBUTING.md). Code and validation scripts are under Apache-2.0 ([LICENSE](LICENSE)); external evidence remains governed by its own source and licensing. No third-party document is copied into the registry by reference alone.
