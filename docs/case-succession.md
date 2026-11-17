# Operational case succession: preserving Toolkit history

The original Toolkit issue URL remains the durable GitHub historical identity, even after external assessment coordination moves to a Registry issue. Do **not** transfer GitHub issue numbers, mirror all issue bodies, delete original records, scrub comments or bulk-reopen closed historical issues. References in upstream specifications and resolutions continue to resolve to Toolkit.

For an accepted case handoff, the case's existing `owners` contract supplies:
- `historical_source_issue`: original Toolkit issue URL, retaining the original case narrative and external references;
- `current_active_issue`: Registry successor issue URL for future external case work;
- `registry`: operational coordination repository;
- `execution`: canonical Toolkit method/controller authority that is **not** automatically transferred by a case succession link;
- `handoff: accepted`: administrative succession only, not proof of execution, specialist result, CI cutover, or RAHP PASS.

The source issue should have a **non-destructive forward link** to the Registry successor, preferably an appended comment. The Registry successor must link back to the source. The pilot uses Toolkit [#1203](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203), Registry [#4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4), and case record `RAHP-AR-DTG-0001`. Toolkit #1203 retains its historical issue number and contents.

The existing case validator now rejects accepted handoffs with malformed/out-of-bound owner URLs, absent Toolkit history, or incorrectly transferred execution authority, and detects two accepted case records claiming the same Registry issue. This is **structural** validation, not live confirmation that GitHub links still resolve; the source forward link must be checked from the live issue. The pilot remains `not_assessed`, and no Toolkit publisher suppression or Registry new-case publishing is enabled by these checks.

For future cases, first establish a uniquely accepted proposition and Registry case owner. If several assessments share findings or a Toolkit wrapper, do not infer one-to-one ownership from a single finding ID. Preserve cross-issue relations and residual duties explicitly before transferring source-specific writes. Further workflow consolidation should occur only once substitute checks preserve the existing invariants; no new scheduled workflow is needed for this step.

## Local metadata locator qualification

`python3 scripts/validate_history_locator.py` verifies the complete committed
769-issue metadata inventory against its partition counts, canonical historical
URLs and every source-controlled case with `handoff: accepted`. It rejects
missing or conflicting historical sources, incorrect successor mappings, and
duplicate acceptance. New Registry-originated direct cases require no fictional
Toolkit historical owner. This check is also included in ordinary validation.

The result does **not** verify live source-link accessibility, past comments or
events, independent source authorship, post-snapshot changes, or independent Gate
1 acceptance. Full issue-body republication is not necessary for this locator
contract. The original GitHub issues retain their authoritative history.
