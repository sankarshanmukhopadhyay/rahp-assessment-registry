# Fail-closed external assessment intake (opt-in)

This bounded adapter prepares a future case-routing cutover without replacing the RAHP controller. The canonical developer/engine, DPIP specialist and Interop Lab evidence-producer paths remain untouched.

`scripts/registry_intake.py` accepts only an explicit `kind: external_assessment` event with a stable assessment key, proposition, exact 40-character source revision, source repository and URL, finding ID and responsible external owner. It never accepts a RAHP assurance outcome or specialist return. Other event types are rejected; they do **not** fall back to creating a Toolkit issue.

The adapter uses a repository-bound GitHub endpoint and enumerates all existing registry issues to deduplicate by `<!-- registry-assessment-key:... -->`. A closed owner is a **hard stop** pending governed reassessment; no automatic re-open or successor is implied. A duplicate in the input batch or registry history is an error. The default is **dry-run**, with an explicit `--apply` required for writes.

## Dry-run with offline fixture

```sh
python3 scripts/registry_intake.py --events /path/to/external-events.json --issue-snapshot /path/to/registry-issues.json
python3 -m unittest discover -s tests -v
```

For live owner enumeration, supply `REGISTRY_INTAKE_TOKEN` with narrowly scoped access to this registry's Issues API. `--apply` is a separate deliberate action. Do not assume the Toolkit workflow's default GitHub token can write here. Do not store tokens in cases, manifests, issue bodies or logs.

### Minimal event

```json
{
  "kind": "external_assessment",
  "assessment_key": "dtg:case:example-001",
  "title": "Verify network-signed response",
  "proposition": "Unverified responses must not authorize a consequential action.",
  "source_repository": "OpenVTC/verifiable-trust-infrastructure",
  "source_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source_url": "https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2439",
  "finding_id": "example-finding-001",
  "responsible_owner": "OpenVTC/verifiable-trust-infrastructure"
}
```

The example revision is synthetic and **not** usable as deployment evidence. Real events require true pinned revisions.

## Exclusions and cutover criteria

- No background/scheduled workflow is enabled. No issue is created by merging the adapter.
- The adapter does not establish whether an event is genuinely new versus an existing historical RAHP case; the publisher and migration inventory must reconcile proposition identity first. Existing pilot [RAHP-AR-DTG-0001](../cases/dtg/network-answer-proof-2026-11.json) is not automatically matched to a new assessment key.
- No DPIP or Lab return is sent or received. RAHP's existing controller remains the only authority to reconcile those results. Registry case linkage is not a substitute for controller result transport.
- On API failure, no success receipt is produced. **The caller must retain the original pending work durably**; this adapter does not provide an outbox and must not be enabled as an unattended sole delivery path until one exists.
- If applying multiple events, writes are not atomic. If a later event fails, earlier events may already exist; a retry deduplicates by key. This is not a transaction guarantee.
- A future live cutover requires an outbox, historical-key mapping (including #1203 → registry #4), proper least-privilege token, consumer-path integration tests, and disabling Toolkit-side external issue creation **only after** valid replacement and DPIP/Lab reconciliation are proven.

[Registry issue #2](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/2) remains the acceptance gate for the full development-only Toolkit invariant.
