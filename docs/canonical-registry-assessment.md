# Canonical RAHP assessment execution from Registry: network-answer pilot

This bounded workflow invokes the **existing canonical Toolkit controller** at
immutable revision `70298566dc897669e22bf37759843d6b7c0597d2`,
using the already owned Registry [case #4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4)
and exact OpenVTC implementation revision
`303174f8ca630ca14ddc2cbf5abcb0d10e205c38`.

The [pilot specification](../ops/assessments/network-answer-pilot.spec.json)
binds the two unresolved requirements `DTG-0001-R1` and `DTG-0001-R2`.
The [evidence ledger](../ops/assessments/network-answer-pilot.ledger.json)
is explicitly empty because this repository does not yet have verified
target-native positive/negative VTN consumer execution evidence. It would be
incorrect to populate this ledger using upstream unit tests, source-level
implementation observations or a synthetic assertion.

The [workflow](../.github/workflows/registry-canonical-assessment.yml)
invokes `toolkit/tools/autonomous_assurance_controller.py` with the case-specific
specification and ledger. The resulting machine and human artifacts are preserved,
alongside a [source/assurance qualification receipt](../scripts/verify_registry_assessment_run.py).
The validator requires `INDETERMINATE` with reason `evidence-required`,
matching source revision and subject, no forged evidence or Registry PASS.
Negative tests attempt source substitution, fabricated PASS, contradictory
evidence and false import.

**Interpretation:** An actual canonical controller invocation establishes that
the Registry can execute a source-pinned RAHP assessment *with no evidence*,
and the controller records the resulting unresolved assurance state. It does
not prove the target's behavior, specialist or producer return compatibility,
a current deployment boundary, runtime suitability or automated case lifecycle.

The existing Registry case deliberately remains `not_assessed` until an
attributable controller result has been reviewed and explicitly imported under
the case's governed result-reference contract. No automatic import or issue
state change is made by this workflow.

Next: obtain source-pinned consumer-path observations for each residual,
reconcile them through the canonical RAHP engine and, if applicable, the
DPIP/Interop Lab contract. The operational cutover remains blocked on the
full set of [issue #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11)
conditions. **No release warranted.**

## Case-to-execution binding receipt

The workflow also generates `build/registry-assessment/execution-binding.json`
from the *actual canonical Toolkit result* using
[`bind_registry_execution.py`](../scripts/bind_registry_execution.py).
This receipt records the Registry case and owner URL, source finding and
immutable revision, Toolkit revision, canonical assessment and correlation IDs,
and the SHA-256 digest of the normalized machine result. A deterministic
binding key is derived from those identities. An independent verification pass
recomputes both the identity and result digest and refuses changed or unknown
fields.

The binding expressly sets `case_determination_imported=false`,
`external_specialist_authenticated=false`, `delivery_acknowledged=false`
and `controller_cutover_qualified=false`. It is an executable **reference
integrity** boundary for later Registry-to-Toolkit mapping; it is not a
signature, issuer-authentication proof, specialist return receipt, Registry
case mutation or assurance determination. Its reproducibility depends on
the pinned execution inputs and the retained workflow artifact.

Before enabling live specialist returns, a future Registry controller must
use this source/execution distinction and add authenticated, source-pinned
return routing, durable acknowledgments, conflict handling and owner
reconciliation. Do not mistake a matching SHA-256 hash of locally supplied
data for external authority.
