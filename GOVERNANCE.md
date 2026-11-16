# Governance and authority contract

## Scope

This independently maintained registry organizes bounded RAHP assessment cases, evidence references, residual risks, decisions and owner handoffs for multiple external systems. It does not speak for ToIP, DTG, OpenVTC, DPIP, or any other upstream maintainer.

## Roles and approvals

- **Registry maintainer:** admits and reconciles cases, approves changes to registry-owned records, resolves ownership disputes and determines whether the registry's *administrative* closure criteria are satisfied.
- **RAHP method/engine maintainer:** owns RAHP method, schema, conformance and executable-engine changes in the Toolkit repository.
- **Assessment reviewer:** makes attributable, source-scoped analytical judgments, noting independence limitations. Self-review is not independent qualification.
- **External specification, implementation and specialist authorities:** alone determine their governed changes and authoritative dispositions. A transfer requires an explicit receiving owner, not just an outbound link.

A GitHub merge is approval of the registry *record*, not independent verification of each referenced runtime claim.

## Non-authority boundaries

The registry must not:
- change RAHP's PASS, FAIL, NOT_APPLICABLE or INDETERMINATE semantics;
- infer recognition, authorization, certification, conformance or implementation correctness from links, signatures, CI or release names alone;
- decide external remediation complete without source-pinned evidence and an authorized source-owner determination;
- claim DPIP privacy approval or interoperability from RAHP-only evidence;
- conflate a closed administrative case with the closure of external residual obligations.

## Decisions and evidence

Every consequential decision records a date, accountable actor, decision scope, rationale, source reference, uncertainty and remaining owner. Source assertions, implementation evidence, actual consumer-path evidence and independent review must remain distinguishable. Missing, stale, conflicting and inaccessible evidence never becomes PASS.

Material case updates should proceed through reviewed pull requests. Reviewers verify provenance and the absence of unsupported assurance claims. This registry's decisions are challengeable and may be corrected in subsequent attributable revisions; historical evidence is not silently rewritten.

## Supersession, reopening and portability

Each case has a stable registry ID and an independently verifiable original-source link. Superseding records point to the earlier ID and preserve its conclusion as-of its source revision. A material upstream change triggers *bounded* reassessment only when it affects the recorded proposition. Routine monitor ticks do not reopen closed cases.

The registry's records are portable JSON and must remain understandable without a hosted application or live integration. No automation may change an authoritative assessment conclusion without a governed decision.

## Security, privacy and retention

Store references, non-sensitive summaries and evidence integrity metadata, not credentials, private messages, raw identity material or secret-bearing transcripts. Public publication is not permission to redistribute restricted evidence. When evidence cannot be safely retained, record its existence, holder, access constraints and `unavailable` or `restricted` status.

## Initial governance status

Working draft. No independent assessment-review delegation or automatic disposal authority has been assigned. The initial pilot does not migrate, close or reopen the Toolkit's source issue.
