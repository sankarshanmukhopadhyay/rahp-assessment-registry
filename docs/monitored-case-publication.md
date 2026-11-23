# Monitored external-case publication: operator contract

This document is an operational control for the RAHP Toolkit → Registry
external-case writer cutover, tracked in
[issue #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77).
The [root README](../README.md) describes enduring case responsibilities,
not cutover status.

## Two independent authorities

The Toolkit's protected-main
[`external-case-publication.json`](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/blob/main/instances/dtg/external-case-publication.json)
selects whether canonical **external assessment-case** mutations are permitted
in Toolkit. The default is `owner: toolkit`. A protected-main change to
`owner: registry` is an authority switch and MUST NOT precede an independently
usable Registry receiving path.

The Registry's
[`monitored-intake-authorizations.json`](../ops/migration/monitored-intake-authorizations.json)
authorizes **individual exact source-qualified cases**, not every materiality
signal. The ledger starts empty. An approval requires a source revision,
assessment key, case ID, finding ID, exact pending manifest and SHA-256 evidence
digest. Neither this ledger nor a maintainer comment alone proves the
corresponding Toolkit writer has been retired.

## Source and write sequence

1. Preserve a real monitor observation and independently review whether the
   proposition is materially distinct. Commit one `rahp-registry-pending-intake/v1`
   manifest under `outbox/pending/`, including `case_id` and
   `source_evidence_sha256`. The source repository must be authoritative
   for its own commit. Keep the source record and SHA-256 digest independently
   retrievable; a signed review cannot replace the underlying evidence.
   Registry independently retrieves the accepted `instances/{dtg,cawg}/generated/review-events.json`
   batch at the exact current Toolkit protected-main SHA, requires a unique
   `assessment_key`, canonicalizes the complete matching event as sorted
   compact UTF-8 JSON, and recomputes `source_evidence_sha256`. The source
   event's `repository` and `new` commit must equal the approved Registry
   scope, `finding_id` must equal the first 20 hex digits of the full digest,
   and its labels must designate a material assessment rather than change triage.
   Missing accepted events, changed digests, or duplicate keys fail closed.
2. Approve the exact manifest fields in the Registry's monitored authorization
   ledger through normal protected-main review. Absence, withdrawal,
   substitution or duplicate approval is a rejection.
3. Prepare the **new read-only observation route** before retiring a
   workflow that still performs observation or legitimate Toolkit-local
   work. A current/old external-case writer must not remain executable
   from registered historical tags or branches under a write-capable token.
   Preserve separate `dtg-assurance-reconcile.yml` local incidents.
4. Apply the Toolkit external publication policy change to `registry`
   through protected main. The canonical Toolkit publisher then reads that
   policy from live current main *at each issue mutation boundary* and
   refuses external issue writes. The two monitored jobs skip their
   current issue-number-based case/DPIP effects without discarding the
   retained observation artifacts. An old branch's unpatched code cannot
   be assumed to honor this policy.
5. Disable the superseded **external writer workflow registrations**, confirm
   each expected old/current registration is inactive through the GitHub
   Actions API, and drain queued/in-progress/waiting/requested/pending runs.
   The Toolkit-only incident workflow is not in this list. Source audits
   alone do not establish runtime exclusion.
6. Dispatch
   [the controlled outbox workflow](../.github/workflows/registry-outbox-replay.yml)
   on `main` with `monitored_intake=true` and the exact committed manifest.
   First run `apply=false`; inspect the qualification receipt, including
   the current Toolkit and Registry commit pins and all disabled registration
   identities. The workflow's write step is limited to `apply=true`.
   It requalifies source and server-side writer exclusion before invoking
   the canonical outbox and acknowledges only a unique observed Registry
   issue, never an HTTP response alone.
7. Replay the same committed manifest. It must identify the **same** owner
   without a second POST. A changed evidence digest or missing exact case
   identity must fail closed. Bind subsequent canonical Toolkit execution
   using its independent immutable execution/result identifiers, not a
   substituted GitHub issue number. Keep genuine DPIP/Lab referrals under
   their independent source and return authority.

## Failure and rollback boundaries

The system has **no cross-repository atomic GitHub Issues transaction**.
Workflow concurrency serializes participating Registry publishers but does
not control unrelated credentials. The live server registration and
quiescence preflights establish a bounded operational exclusion, not a
cryptographic cross-repository lock. No general cutover PASS should be
asserted without checking other independent issue-write credentials and
completed old-ref dispatch denial.

A missing source pin, inactive/ambiguous approval, wrong owner, active
old writer, changed main, lost POST response or absent unique Registry owner
is a **stop**, not Toolkit fallback. Keep the committed pending manifest and
reconcile the authoritative Registry issue history before trying again.

Reverse transfer is a separate governed operation. Disable Registry's
monitored write route and drain its executions **before** restoring Toolkit
external publication authority, retain case and execution evidence, and
require fresh protected-main approval. Never remove the historical accepted
transfer ledger to simulate rollback.

No monitored case or specialist outcome is created by landing these
preparatory files. No assurance PASS, issue-ownership cutover acceptance or
release follows solely from green CI.
