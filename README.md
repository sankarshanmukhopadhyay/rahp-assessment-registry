# RAHP Assessment Registry

A public, independently maintained case-management surface for source-pinned RAHP examinations and their unresolved assurance obligations across trust-system projects.

**Status:** pilot / working draft. This repository does not certify systems, govern upstream specifications, or execute the RAHP engine.

## Start here

1. Read [governance and authority](GOVERNANCE.md) and the [case lifecycle](docs/case-lifecycle.md).
2. Inspect the [network-response pilot case](cases/dtg/network-answer-proof-2026-11.json) and its [source owner](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203).
3. Validate tracked cases locally with `python3 scripts/validate_cases.py` and `python3 -m unittest discover -s tests -v`.
4. Use the [assessment-case issue template](.github/ISSUE_TEMPLATE/assessment-case.md) only for a genuinely distinct proposition with an accountable owner.

## Ownership and non-authority

| Surface | Owns | Does not own |
| --- | --- | --- |
| [DTG Portfolio Monitor](https://github.com/sankarshanmukhopadhyay/dtg-portfolio-monitor) | Change observations, source consolidation, materiality and monitored-finding disposition | RAHP assessment outcomes |
| [RAHP Toolkit](https://github.com/sankarshanmukhopadhyay/rahp-toolkit) | Portable RAHP method, engine, contracts, validators and release qualification | Authoritative upstream implementation state |
| **This registry** | Case admission, review scope, evidence references, handoffs, residual ownership, reassessment triggers and administrative case lifecycle | RAHP runtime outcomes or external normative authority |
| External source and specialist repositories | Their own specifications, implementations, remediation and specialist determinations | Other repositories' governance |

A registry case is an indexed, attributed assessment record. It cannot assert PASS simply because upstream CI passed, a monitor ran, or a GitHub issue closed. The full original issue and authoritative evidence remain accessible through durable links. **No issue is automatically transferred or closed by adding a case record.**

## Queue migration intake

The [2026-11-16 provisional 58-issue inventory](docs/queue-triage-2026-11-16.md) separates Toolkit-owned work from external case and specialist obligations. It is advisory and does not create or accept any issue handoff.

## Specialist and executable-evidence routing

See [DPIP and Interop Lab referrals](docs/specialist-routing.md) for the existing source-controlled return contracts, testing responsibility and case-referral admission rules.

## Registry-executed historical source replay

A [pinned, non-publishing DTG routing replay](docs/pinned-dtg-replay.md) invokes the canonical Toolkit implementation from a Registry workflow, without forking assurance semantics. It retains source and decision artifacts and makes no case writes.

## External intake prototype

The [opt-in fail-closed intake adapter](docs/external-intake.md) supports source-pinned external event classification and idempotent registry-issue planning. It is dry-run by default and **not yet wired into the Toolkit's live publisher or DPIP/Lab return paths**.

## Pilot scope

The initial pilot is a **shadow record** of the already open RAHP Toolkit issue [#1203](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203). This is intentionally not a second active remediation owner. After the case model and reviewer workflow are accepted, a separately governed migration may establish this registry as the sole active owner.

Current stage: one manually reviewed subject, no ingestion service, no new monitoring workflow, no automatic GitHub issue creation, no bulk migration, no release claim.

## Contribution and licensing

See [CONTRIBUTING.md](CONTRIBUTING.md). Code and validation scripts are under Apache-2.0 ([LICENSE](LICENSE)); external evidence remains governed by its own source and licensing. No third-party document is copied into the registry by reference alone.
