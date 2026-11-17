# Live DTG monitoring shadow: operational execution boundary

The Registry owns the read-only [live monitoring shadow workflow](../.github/workflows/dtg-live-shadow.yml). On the same UTC cadence as the existing Toolkit monitoring workflow it uses Toolkit's **authoritative** two-day freshness fetch and semantic routing implementation, checked out at commit `18a421cb627535b14ae1dd0a468c64e38d1e8ac9`. It also pins the current Portfolio Monitor checkout revision and refuses to use the fetched snapshot unless it matches that checkout's exact observed date and JSON content.

The workflow retains source and provenance plus routed, combined, DPIP and unresolved event sets. Its negative tests reject race/mismatched content, future/stale source, missing source and unpinned engine. It has only `contents:read` GitHub permission, so no case writes or DPIP/Lab transport can occur. A failed freshness check is a real missing evidence condition, **not a successful empty monitor period**.

This is a **shadow run** alongside the existing Toolkit consumer until the parity and cutover gates in [execution migration plan](execution-migration-plan.md) are met. It is not a second authoritative assessor, does not claim runtime conformance, and does not transfer old issue ownership. The Toolkit publisher still needs a verified registry-native replacement and non-issue controller/DPIP/Lab correlation before its issue-writing paths can be disabled.

## Live dual-router parity (same fresh source)

The same scheduled, read-only shadow workflow now also executes the **Registry
DTG routing implementation** with its Registry-owned policy and normalization
configuration, on precisely the same fetched snapshot and date as the canonical
Toolkit router. Both output sets are preserved under `build/live/toolkit/`
and `build/live/registry/` alongside the original source, and
[`compare_dtg_routing_outputs.py`](../scripts/compare_dtg_routing_outputs.py)
fails on any byte-level difference in `routing.json`, `combined-events.json`,
`dpip-events.json`, `unresolved.json`, or `compositions.txt`. A missing
output or an empty routed result is not accepted as proof of parity.

The workflow first requires Toolkit's existing **two-day UTC source freshness**
contract; the source must also match the checked-out Monitor repository on the
claimed snapshot date. Its `dual-router-parity.json` receipt records both
routers' output digests, the source snapshot SHA-256, Toolkit/Registry/Monitor
commit revisions, routing and normalization policy digests, and a no-write
scope. If the Monitor is stale or absent, the run **fails** rather than reporting
a successful empty observation period. The workflow is also invoked on
relevant pull requests to make live compatibility falsifiable before merge.

### What this establishes

A passing live run supports **exact route-output parity for its observed
source snapshot** and pinned engine and configuration revisions. It advances
the monitored-source comparison gate in [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11),
but it does not itself qualify materiality-journal side effects, end-to-end
case coalescence/reassessment, specialist result delivery, or a sustained
multi-snapshot history under changed source revisions. Historical frozen parity
CI remains separately available for deterministic reproduction. Neither
workflow opens issues or delegates execution authority, and neither replaces
the existing Toolkit materiality publisher.

## Reviewed intake set reconciliation

The live shadow now reconciles **all reviewed JSON manifests** committed to `outbox/pending/` against a single source-pinned snapshot, routed output and live Registry owner read. Duplicate keys, duplicate source finding IDs, ambiguous case ownership and unexpected manifest files fail closed. The receipt distinguishes findings without reviewed intent from those without a **confirmed existing Registry case owner**; reviewed pending creation is not case admission. This remains read-only and cannot authorize publication, specialist delivery, assurance PASS or cutover.

## Toolkit transfer-candidate lineage

The live shadow also examines [Toolkit #1194](../ops/migration/candidates/toolkit-1194.json) against the exact routed finding groups and generated combined/DPIP publication keys. It verifies source-observed immutable commit links and inspects the existing Toolkit owner and paginated comments for exact finding references. A textual issue reference does **not** establish publisher identity, accepted transfer, or suppression authority. The `toolkit-1194-transfer-lineage.json` receipt explicitly retains absent source pins and unmatched publication keys and cannot authorize any write or cutover.

The companion [Data Rooms successor #1208](../ops/migration/candidates/toolkit-1208.json) is audited independently against the same live source. Its shared finding identities with #1194 are recorded in `candidate-overlap.json`. Neither the complete routed group nor a narrow assessment owner is automatically entitled to absorb the other's obligations; mapping and accepted transfer remain separate gates. An `UNMAPPED` or `covered/no-action` candidate finding now carries an explicit non-admission blocker rather than an apparently empty blocker list.

## Supplemental annotated release-tag evidence

The three release/tag observations in successor #1208 lack a direct commit link in the **original Monitor snapshot**. The live shadow separately checks the [reviewed annotated-tag evidence](../ops/migration/evidence/toolkit-1208-release-tags.json) against the exact source release URL, current GitHub tag reference, immutable annotated tag object and commit target. A moved/reforged tag fails closed. Verified tag-to-commit resolution **supplements**, but does not rewrite or retroactively strengthen, the original source record; two distinct tag observations may legitimately resolve to the same commit. Neither result imports assurance PASS nor authorizes case transfer.

## Source-specific combined event provenance

Both routers now emit structured per-finding commit-source evidence in grouped
combined-review events while preserving their original route classification,
assessment keys and human-readable bodies. Unpinned release/tag observations
remain explicitly unanchored. See the exact input and output digests in the
existing two-router parity receipt before using this metadata for admission.
This does not independently qualify a group owner or activate any Toolkit
publisher suppression or DPIP/Lab authority migration.
