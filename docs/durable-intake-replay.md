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
accepts a reviewed manifest path and defaults to **dry-run**. Explicit
`apply=true` enables a Registry-only GitHub issue POST. The workflow uses the
Registry's repository-scoped token and serializes against the existing pilot
intake workflow. It never writes to Toolkit.

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

# Only after explicit review and authorization; writes only Registry issues.
python3 scripts/registry_outbox.py \
  --manifest outbox/pending/network-answer-pilot.json \
  --receipt build/outbox/receipt.json --apply
```

The seeded pilot must resolve existing Registry #4, not produce another issue.
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
