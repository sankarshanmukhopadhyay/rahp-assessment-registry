# Controlled Registry intake replay

## Current ownership and executable admission paths (23 November 2026)

Toolkit external-case publication is now assigned to Registry by the protected-main `instances/dtg/external-case-publication.json` policy (Toolkit [#1256](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/pull/1256)). Legacy Toolkit external-case workflow registrations are disabled or historically absent, with a receiving-side server-registration and in-flight-run gate corrected in Registry [#119](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/pull/119). Toolkit remains authoritative for RAHP methods and canonical execution, not new external-case issue admission.

[The controlled intake workflow](../.github/workflows/registry-outbox-replay.yml) has **three distinct** routes: ordinary `registry_outbox.py` replay of an existing approved owner (no new case), explicitly approved `registry_direct_intake.py` for a novel direct-source proposition, and `registry_monitored_intake.py` for an **exact source-qualified, committed, approved** monitored intent. The monitored route also independently establishes all four current Toolkit writers disabled, absence/disablement of retired registrations, drained historical writes and unique Registry case ownership. A `workflow_dispatch` on Registry `main` with `apply=true` and exactly one appropriate intake mode is needed for an effectful issue POST. The workflow's read-only preflight does not authorize publication by itself.

The 23 November Toolkit materiality observer successfully consumed a recent Monitor snapshot, but its only retained source item was a controller requiring non-issue execution state; no combined or DPIP external-case event qualified. Current monitored-authorization admissions and Toolkit incremental review-event arrays were empty at that observation. **Do not fabricate a case, bypass the admission ledger, repurpose a controller as an assessment issue or infer PASS.** See [Registry #77](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/77) for source reconciliation and remaining live acceptance work.

**Historical note:** the preparatory instructions below document pre-activation restriction phases. In particular, statements that the Toolkit publisher is still authoritative or that external publication has not yet switched are historical; the currently operative distinction is **active Registry owner policy versus unqualified new-case admission**. Earlier source-bound holds, replay caveats, and immutable evidence requirements still apply.


This is a **source-controlled, Registry-only publication transport**. It is not a
RAHP controller, DPIP result consumer, Interop Lab producer or general
material-change cutover. It does not decide whether an assessment has passed.

## Queue authority and delivery

An approved change to `outbox/pending/<name>.json` records one durable,
source-pinned external assessment intake intent using
`rahp-registry-pending-intake/v1`. The manifest is persistent in Git; Actions
artifacts are additional evidence, not the queue of record.

The [Registry durable intake replay workflow](../.github/workflows/registry-outbox-replay.yml)
accepts a reviewed manifest path and defaults to **dry-run**. Its PR and
qualification job has only **Issues-read** privileges. An explicit main-branch
`workflow_dispatch` with `apply=true` is required to start a separate
Issues-write job. **External publication ownership has switched to Registry, but this does not approve any specific new case.** A new direct or monitored first-case POST requires the appropriate reviewed source intent, authority ledger, live source/owner verification, explicit selected intake mode and publication-side guard checks. The ordinary replay route remains existing-owner-only. Every effectful route re-reads the owner; none writes to Toolkit.

The general-purpose `registry_outbox.py` transport still refuses unqualified first-case creation on direct `--apply` invocation. The separately governed `registry_direct_intake.py` and `registry_monitored_intake.py` routes implement first admission under their own current authorization ledgers. An internal `allow_new_case` fixture for the generic outbox is not a production operator override.

The delivery algorithm:

1. Re-read the complete Registry issue set; refuse duplicate keyed owners,
   closed owners and unverified ownership of the migrated pilot.
2. If an open owner exists, require its body to cite the *same exact* source
   revision and finding. A new revision under an existing proposition is
   **not** silently considered assessed or delivered; return an explicit
   reassessment-required failure.
3. If no owner exists and apply is false, retain the pending manifest with no
   write.
4. On explicit apply, attempt one Registry-only POST, then **re-read** issue
   history. Success requires one unambiguous open owner with the submitted
   source/finding identity and a durable issue URL. HTTP 201 alone is not
   acknowledgment. A failed/lost POST acknowledgment may be recovered by
   observing the owner; an unresolved ambiguous delivery remains pending.
5. Preserve a machine-readable `receipt.json` as Actions evidence. Source
   intent remains Git-committed for deterministic replay; the issue record,
   not the CI result, is the observed owner.

### Operator commands

```sh
python3 scripts/validate_cases.py
python3 -m unittest discover -s tests -v

# In CI/Actions, REGISTRY_INTAKE_TOKEN must be provided by the Registry runner.
python3 scripts/registry_outbox.py \
  --manifest outbox/pending/network-answer-pilot.json \
  --receipt build/outbox/receipt.json

# Direct apply is existing-owner-only; both the Python transport and the\n# controlled workflow block new cases until cutover is qualified.
python3 scripts/registry_outbox.py \
  --manifest outbox/pending/network-answer-pilot.json \
  --receipt build/outbox/receipt.json --apply
```

The seeded pilot must resolve existing Registry #4, not produce another issue.
A new-case `pending` intent cannot be applied from the controlled workflow
while Toolkit can still publish external-case issues; this prevents dual-active
publication even if the operator supplies a plausible source-controlled
manifest. GitHub's lack of an atomic unique-key issue creation API remains a
separate concurrency limitation.
Do not use unreviewed new-case manifests to exercise `apply`.

## Limitations and further gates

This transport implements **replayable single-intent publication**, not a
generic distributed exactly-once queue. Duplicate prevention assumes every
Registry publisher uses the same workflow concurrency group or an equivalent
exclusive publication lock. External concurrent writers are not covered by
GitHub's issue API. A long-running transaction, human review of new
material changes and acceptance of a specialist return remain separate.

There is no unattended materiality-to-approved-outbox enqueue or demonstrated full first-monitored-case cycle. The Toolkit external-case writers are administratively disabled, but Toolkit-local controller execution, historical issue-number consumers and specialist coordination remain distinct. Source-scoped historical succession (Toolkit #272 → Registry #88) has executed; the new-case execution/return/reversal acceptance gates remain open. The original generic outbox pilot alone has no RAHP result. Do not declare end-to-end G1–G6 acceptance from publication ownership.

A new source revision matching an existing case needs a governed
reassessment/append protocol, not an automatic replacement or forged
completion receipt. Full shadow parity, controller/producer compatibility,
rollback and human acceptance remain the gates in [issue #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11).

## Source-matched materiality admission (read-only operational consumer)

The Registry's [materiality intake consumer](../scripts/registry_materiality_intake.py)
now runs inside the **live dual-router DTG shadow** using the freshest
Toolkit-qualified, Monitor-verified source snapshot and the actual Registry
routing output. It requires the exact routed finding JSON to match its source
record, refuses duplicate findings, and tests the proposed intake against
the existing Git-committed `rahp-registry-pending-intake/v1` intent.
The proposal must contain a 40-hex immutable source revision demonstrably
present as an exact `/commit/<sha>` evidence URL in that finding. Its source
URL and external owner must also match the observed source repository.

An explicitly reviewed intent can result in four **non-mutating** decisions:

- `existing_owner`: source-pinned finding maps to exactly one open Registry
  case and the existing case body acknowledges that precise revision/finding.
- `pending_reviewed_creation`: a reviewed source observation has no current
  Registry owner. The *existing* controlled durable outbox remains the only
  authorized issue-writing transport; this result is **not** permission to
  write while Toolkit is still an active external case publisher.
- `no_new_case_for_covered_route`: an observed reviewed route is already\n  marked `covered` or `no-action`; even explicit case-intake metadata cannot\n  convert that disposition into a new issue.\n- `reassessment_required`: a newer material observation maps to a reviewed
  durable proposition owner, but its changed source revision/finding is not
  yet represented. No issue is reopened, no new case created, no original
  case result overwritten. A separate accountable reassessment acceptance
  is required.
- `outside_observed_materiality`: the committed reviewed intent is not
  present in the current source snapshot/routing. It does **not** prove the
  absence of other material changes. All other routed observations remain
  unadmitted and are counted in the receipt.

The reviewed `dtg:network:trust-task-answer-verification` proposition now
resolves to Registry #4 **by both stable proposition key and original
finding ID**, so a later source/finding under the same proposition cannot
silently create a second Registry case. A changed revision is instead
marked `reassessment_required`. This does not imply revalidation of new
runtime behavior.

The CI workflow has only `contents:read` and `issues:read`. It preserves
the materiality admission receipt beside source, source-qualifier and both
router outputs; it cannot create issues or invoke DPIP. The actual manual
outbox dispatcher remains a separately authorized pathway. Its historical
tests prove one-write/readback and ambiguous POST recovery using controlled
fixtures, **not** an actual new live case creation. Source-materiality
observation alone does not confer that operational authority.

The current approved pilot is from the 2026-11-13 source. It may be absent
from a later valid Monitor snapshot. That is a legitimate
`outside_observed_materiality` state, **not** success for the new
materiality intake backlog, which must be explicitly reviewed before
the Registry assumes new case ownership.

### Remaining acceptance for #11

Actual Registry case publication for **a newly admitted** material source,
governed changed-source reassessment append/retry, full Toolkit-versus-Registry
materiality journal side-effect parity and coordinated disabling/rollback of
the existing Toolkit issue publisher remain unqualified. A green read-only
consumer is not a complete authority switch.

## Qualified direct-first-intake lane (November 2026)

The manual `registry-outbox-replay.yml` workflow has a separate
`direct_intake` input for source-qualified cases that have **no** historical
Toolkit owner. It uses `registry_direct_intake.py` to verify the approved
`ops/migration/direct-intake-authorizations.json` record, the identical
committed `outbox/pending/*.json` manifest on Registry `main`, the actual
source commit, a live Toolkit owner scan and stable branch heads. Direct
authority is limited to the exact approved source proposition; ordinary
DTG/CAWG transfer remains blocked. A write is permitted only on an explicit
main-branch workflow dispatch with `apply=true` and `direct_intake=true`.

Case [#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47)
was first created by a bounded, operator-mediated GitHub transport from the
committed ONDTF intent, then separately re-read and source-verified. This
**does not** prove that the automated dispatch creation branch has completed a
real POST. The read-only live outbox shadow independently verifies #47 through
`registry_outbox.py`, including the exact source and proposition marker.
Repeated replay must remain owner observation, not issue creation.

Neither administrative issue creation nor the canonical controller's
evidence-required result demonstrates specialist execution, independent
assurance, publication exclusivity for monitored DTG sources, or rollback of
the wider Toolkit writer fleet.

## Direct-case identity binding for specialist compatibility (19 November 2026)

The reviewed direct-source admission route uses a separate,
versioned `rahp-registry-direct-intake-authority/v2` ledger. Each exact
authorization now includes an immutable, source-controlled `case_id`
(`RAHP-AR-...`) matching the pending intent. The live issue creator
renders **both** `<!-- registry-assessment-key:... -->` and
`<!-- rahp-registry-case:... -->` before its first POST. The latter
is required by the canonical Registry-directed specialist-return
consumer; an issue that lacks it cannot be treated as an accepted case.

Historical Toolkit-transfer and generic `rahp-registry-pending-intake/v1`
events that do not use the direct admission route retain their existing
contracts. A direct intake without a reviewed case ID, or with an
unapproved, withdrawn, mismatched or v1-only authorization, is rejected
before any issue write. Replay of an existing direct owner also
requires its exact case marker. No numeric Registry issue identifier
is repurposed as a Toolkit execution/referral issue.

The source-controlled ONDTF and VTI direct manifests are migrated
together with the authority ledger. Their live owners, Registry
[#47](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47)
and [#79](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/79),
were reconciled to their canonical case IDs. The controlled
`registry-outbox-replay` PR preflight now verifies those **real
read-only owner paths**, without triggering a DPIP/Lab referral,
importing a determination or claiming producer cutover.
