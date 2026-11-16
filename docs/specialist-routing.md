# Specialist referrals and executable evidence routing

## Existing authoritative contracts

The [RAHP adoption guide](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/blob/main/docs/adoption-guide.md) defines an assurance **orchestrator** (RAHP), specialist assessor (DPIP) and optional executable evidence producer (Interop Lab). These roles are capability-driven, not automatically invoked because a repository exists. The registry adds no new authority or terminal assurance state.

| Concern | Canonical authority | Existing result/return contract | Registry responsibility |
| --- | --- | --- | --- |
| RAHP assessment, selection, reconciliation and final determination | [RAHP Toolkit](https://github.com/sankarshanmukhopadhyay/rahp-toolkit) | RAHP controller contracts | Locate case and active controller owner; link returned determination without fabricating it |
| Composed privacy, correlation and minimization | [DPIP](https://github.com/sankarshanmukhopadhyay/dtg-privacy-implementation-profile) | [`rahp-assessor-result/v1`](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/blob/main/schemas/rahp-assessor-result-v1.schema.json), [durable specialist outbox](https://github.com/sankarshanmukhopadhyay/dtg-privacy-implementation-profile/blob/main/docs/rahp-return-operations.md) | Link bounded privacy question, DPIP examination and return status; **never** claim DPIP PASS from metadata |
| Bounded implementation, runtime or composition observations | [Trust Protocol Interop Lab](https://github.com/sankarshanmukhopadhyay/trust-protocol-interop-lab) | [`rahp-evidence-producer-result/v1`](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/blob/main/schemas/rahp-evidence-producer-result-v1.schema.json) | Link producer obligation, native test or evidence manifest, exact execution identity and claim limitations |
| Source changes | [DTG Portfolio Monitor](https://github.com/sankarshanmukhopadhyay/dtg-portfolio-monitor) and authoritative upstream | Source-pinned consolidated findings | Deduplicate into existing case; avoid one issue per source event |
| Remediation and operations | Source owning project/operator | Its own issue, version and decision | Link explicit accepted owner and reassessment trigger |

## Registry referral reference

Cases MAY include a `referrals` array. Each item is a **pointer to one specialist/execution obligation**, not a request that the registry carry out examination or a substitute for the canonical return. Values:

- `role`: `specialist_assessor` (DPIP) or `evidence_producer` (Lab), or a future compatible provider.
- `repository`: repository of the actual producer.
- `contract`: `rahp-assessor-result/v1` or `rahp-evidence-producer-result/v1` respectively.
- `issue_url`: the source issue that owns the examination or evidence obligation.
- `status`: `requested`, `accepted`, `returned`, `blocked`; informational, source-verified at the cited date.
- `result_url` and `result_revision`: required before `returned` can be declared. The registry validator checks presence, **not authenticity, source-pin equality, schema compatibility or admissibility**.

Only a real upstream/specialist source may justify changing a referral's status. Adding a registry item does not create a DPIP examination, Lab job, network token, accepted handoff or authoritative controller return. If cross-repository delivery fails, the producer's retry/outbox remains authoritative.

## Execution and assurance matrix

| Claim | Execution location | Minimum evidence and negative case |
| --- | --- | --- |
| Registry case identity, links and referral shape | Registry `scripts/validate_cases.py` and local unit tests | Valid shape; malformed role, absent owner or fraudulent returned status rejected. Structural validity is not acceptance. |
| Specialist return schema and handoff idempotency | DPIP producer and RAHP controller with shared fixtures | Valid, mismatched, duplicate and missing-source returns; published result ID and target revision; pending outbox on transport failure. |
| Executable obligation feasibility and observations | Interop Lab producer test harness | Target revision, actual runner/environment, evidence class, claim boundary, unavailable/partial execution evidence; no synthetic promotion. |
| RAHP result reconciliation | RAHP controller with pinned specialist and producer artifacts | Correct proposition/assessment binding, stale or contradictory evidence, partial specialist return, no false PASS. |
| Real deployment and composition | Externally provisioned native source/controlled Lab environment | Reproducible positive, negative, restart/failure and effect observations, with observer/scope limitations. Run **only when prerequisites exist**. |
| Governance acceptance | Attributable authorized reviewer/source owner | Decision record and remaining risk; CI cannot make it independent. |

The registry has no requirement to execute target-native tests itself. Avoid fetching private data, rerunning other systems on schedules, or adding cross-repository secrets merely to populate a public case tracker. Evidence packages belong in their producing repository, with references and hashes where available.

## Migration and routing rule

Before any automatic case admission or transfer:
1. Classify source observation against existing proposition and assessment context.
2. Select RAHP-only, specialist, producer or composed route from the evidence obligation.
3. Keep the **RAHP controller** as orchestrator; do not retarget DPIP's existing `RAHP_HANDOFF_TOKEN` to the registry without a separately verified controller-compatibility migration.
4. Link the canonical DPIP/Lab issue and source-pinned evidence producer or return record when it exists.
5. Make one accountable case owner explicit, preserve source issue history, and close old owner only after accepted transfer.
6. Admit only one active case per materially distinct proposition, not one per new commit.

**Current status:** routing model and structural references only. No cross-repo delivery, end-to-end specialist return, operational runtime evidence or independent acceptance has been implemented or claimed. Those are distinct qualification work packages, not a reason to conflate the registry with the RAHP controller.
