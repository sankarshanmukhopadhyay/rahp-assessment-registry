# Durable Registry execution journal: controlled pilot

This mechanism preserves one **complete normalized canonical Toolkit execution
result and verified case-to-execution binding** as a Registry case issue comment.
The code runs alongside, and does not modify, the existing Toolkit monitoring,
issue publication, DPIP handoff or return consumer.

## Scope, authority and persistence

The source-owned pilot remains Registry issue
[#4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4).
The journal accepts **only** the qualified `RAHP-AR-DTG-0001` run at the
existing immutable Toolkit and target revisions. It independently verifies
the binding against the actual normalized result before publication. The
result remains `INDETERMINATE / evidence-required` because target-native VTN
consumer-path observations are still missing.

The existing `rahp-registry-execution-binding/v1` key identifies an execution
by its canonical assessment/source identity, while the result SHA-256 digest
qualifies the *exact* emitted record. Two different result contents under the
same execution identity are a **conflict**, not an overwrite or a second PASS.

The journal comment stores the complete bounded normalized result plus binding
with the stable marker `rahp-registry-execution:v1:<key>`. GitHub issue
history provides a persistent, reader-accessible case-scoped record, without
relying on finite-lifetime Actions artifacts. It is **not cryptographically
append-only**: authorized actors can edit or delete comments. The tool
rejects a changed comment in a subsequent reconciliation, but it cannot
protect against a privileged actor replacing the history itself. Independent
attestation and retention policy remain future governance dependencies.

## Delivery and replay

The [journal workflow](../.github/workflows/registry-execution-journal.yml)
runs tests and the **actual pinned Toolkit controller** by default with
`issues: read`. It verifies source pins, case identity, outcome,
clean-room lineage and record integrity, and tests the live Registry #4
issue for current open ownership without writing.

An explicit `workflow_dispatch` with `apply=true` on `main` alone
enables a separate job with `issues: write`. It downloads the exact
qualified output from the same Actions run, revalidates it, and attempts
one comment POST. A fresh GET of the case and complete paginated comment
history is required; only an exact, unique, remotely observed comment
acknowledges delivery. If a POST fails after a remote commit, replay can
recover by detecting the exact comment. If it never appears, delivery remains
unacknowledged. Duplicate or conflicting records fail closed.

Both publication and existing intake share the Registry
`registry-case-publication` workflow concurrency group. GitHub's Issues
API does **not** provide an atomic unique-key insert, so competing writers
outside that group are outside the exclusivity guarantee.

## Operations and limits

Use the workflow's dry-run mode to qualify source and remote issue ownership.
Only use its manually authorized write mode for the existing reviewed case
when the public record is suitable to publish. Do **not** make the workflow
a new scheduled public assessment publisher by editing the `if` condition;
a full publication and data-handling review is needed for additional cases.

The journal receipt is an administrative execution observation, **not**
Registry assurance acceptance. It does not update the case JSON
`assessment.determination`, create DPIP/Lab referrals, authenticate any
specialist, trigger Toolkit issue writes, modify source projects, or
establish operational cutover. The full T1 specialist path requires an
authenticated Registry-addressed handoff/return protocol that preserves
the existing v1 contracts and DPIP's durable outbox. No release is
warranted solely from successful journal publication.

## Git-versioned canonical execution preservation

The accepted pilot's complete canonical Toolkit machine result, execution
binding and original qualification receipt from [CI run
43988780802](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/43988780802)
are now retained in
[`ops/executions/RAHP-AR-DTG-0001/rahp-369ffe8e6f037e6235d5.json`](../ops/executions/RAHP-AR-DTG-0001/rahp-369ffe8e6f037e6235d5.json).
Unlike the Actions artifact, this record is present in Git history and remains
available after artifact retention expires. The source workflow run URL is a
provenance *locator*, not an independent attestation of GitHub workflow identity.

The [persistent execution validator](../scripts/verify_persisted_execution.py)
reconstructs the original case-to-execution binding using the existing
canonical Registry qualification contract; checks the stored result digest,
source, identity, required open residuals, explicit no-PASS and no-import
semantics; rejects duplicate record identities and incompatible paths; and,
in the canonical assessment workflow, compares the stored result against a
**fresh invocation of the pinned Toolkit controller**. No new assessment engine
or assessment result schema is introduced.

This is source-controlled, reviewable, tamper-evident *relative to protected Git
history*; it is not an append-only log, independent execution attestation or
production event store. The pilot record remains `INDETERMINATE/evidence-required`.
No DPIP/Lab return, external case status change or new Toolkit issue is
implied. New cases must have an explicitly versioned and qualified execution
contract before expanding the current pilot-specific validator.

## Delivery acknowledgment publisher identity

A matching marker and identical JSON text are **not** proof that a publication
worker wrote the comment: public issues may accept comments from other GitHub
accounts. The journal therefore accepts an existing publication receipt only
when the GitHub API exposes both the expected `github-actions[bot]` account
login and its stable numeric user ID `41898282`, and the comment URL resolves
to the expected issue and comment ID in this Registry. Missing actor metadata,
lookalike markers, mismatched IDs, foreign URLs and contradictory results
fail closed. The same check applies when recovering a POST that timed out after
remote delivery.

The actor check establishes the **GitHub-reported posting identity**, not proof
of a specific workflow run, independently attested action or approval. Another
workflow with write permissions to this repository could still post as GitHub
Actions; the primary control remains restricted `issues:write` on the manual
publication job, protected branch/review governance, and the source-bound
result contract. Production-grade actor/run attribution and exclusive publication
must be demonstrated before enabling broader automated case writing.
