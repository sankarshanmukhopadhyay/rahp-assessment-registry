# Registry examination-epoch observation journal

The Registry #11 G4 batch-level DPIP return qualifier now has a bounded,
**case-scoped persistent observation contract** in
[`scripts/registry_epoch_journal.py`](../scripts/registry_epoch_journal.py).
It first consumes `registry_specialist_return.qualify_epoch` (which invokes the
canonical Toolkit portable-result checker), then derives an epoch ID from
Registry case ID, pinned source identity and semantic examination key.
A source-qualified result is recorded as `observed_unverified`, never as a
Registry assurance determination.

The journal can compare a new observation with **all remotely persisted
case comments**, rejecting multiple markers, changed DPIP issue numbers or
outcomes for the same epoch, forged publisher identity and invalid
acknowledgment URLs. Repeating the identical existing record is idempotent.
A write requires the same `registry-case-publication` serialization boundary
used by Registry's other case publishers; only an authoritative matching
re-read acknowledges a POST. Ambiguous transport without a matching remote
record remains unacknowledged.

This module is **not yet wired to an operational Registry-directed DPIP
return**. There is no real accepted Registry privacy referral in the current
pilot cases. The tests use the actual portable-result consumer entrypoint with
source-qualified synthetic Registry references and adversarial duplicates
modelled on historical DPIP #304/#305. GitHub issue comments cannot provide
atomic multi-repository locking; independent writers bypassing the common
serialization lock could still race.

The persisted record is not independent specialist authentication, controller
reconciliation, a PASS, permission to publish a new case, or proof of G4
acceptance. Do not activate a journal write for a fabricated specialist result.
