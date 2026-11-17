# Controlled Registry intake replay

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
Issues-write job. **Until the Toolkit external-case publisher has an accepted,
verified coordinated cutover, new Registry issue creation is blocked by this
workflow even when a reviewed manifest exists.** The write-scoped job may
reconcile an already existing owner, which requires a second authoritative
live re-read. It never writes to Toolkit.

The Python transport also refuses new-case creation on direct `--apply` invocation while the existing Toolkit publisher remains authoritative. The internal `allow_new_case` test injection exercises the future one-POST/readback consumer path under controlled fixtures, **not** a production operator authorization interface. An accepted transfer and coordinated publisher-suppression evidence must precede any future production authorization mechanism.

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

There is no automatic materiality-to-outbox enqueue, no Registry controller
execution mapping, no DPIP/Lab handoff or return reconciliation, no historical
issue migration, and no assertion that Toolkit's operational publishers are
disabled. The accepted pilot has no RAHP result. Do not declare the
development-only Toolkit invariant or cutover complete.

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
