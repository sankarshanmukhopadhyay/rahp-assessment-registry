# DTG/VTI materiality candidates after the 16 November Monitor snapshot

**Observation date:** 19 November 2026. **State:** source-level triage; not a
Registry case, reviewed intake intent, canonical controller run, or assurance
determination. Governing migration tracker: [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11).

## Source and authority

The [Portfolio Monitor](https://github.com/sankarshanmukhopadhyay/dtg-portfolio-monitor)
`main` observed at `7e2813c8daf867a21e4064513cc83612726aeb44`
contained November findings for 13 and 16 November, but no later committed
November snapshot. The new sources below were independently inspected via
the upstream GitHub merged PR records on 19 November. They have **not** been
admitted through the Registry's reviewed monitor/intake contract, and the
Monitor's lack of a newer snapshot is not evidence of absence of new material
changes. Do not substitute a PR narrative for executable target evidence.

| Candidate and immutable upstream merge | Specific change and falsifiable materiality question | Overlap / initial route |
| --- | --- | --- |
| [VTI #2765](https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2765), `60f13e96109ddd25fcf0923a4fd1e0c532149470` | VTA refuses to sign as the `did:key` of a held did:webvh update or pre-rotation key, to prevent document-sign authority being repurposed into DID-log authorization. Can stale role state, mixed key aliases, concurrency or alternate signing surfaces recreate the escalation after an operator's grant is revoked? | Existing [Toolkit #827](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/827) concerns named-role/rotation implementation. [#1196](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1196) concerns DID lifecycle. Qualify a delta against these before any new owner. |
| [VTI #2766](https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2766), `018a0acea6ca6177e0ac4693ebe02325d841ef07` | did:webs key-role signing now selects the key for the proof's verification relationship. The PR reports 68 targeted tests but explicitly **no full workspace run or end-to-end VTA/VTC reproduction**. Can a valid signature from the wrong relationship, stored wallet key, stale document or legacy proxy-login path authorize an action? | Compare with closed historical proof-purpose owner [Toolkit #820](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/820) and open [#827](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/827)/[#1196](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1196); do not reopen a historical conclusion by association. |
| [VTI #2768](https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2768), `05f4a26ebb3dab6302a2fb8ad0657fa259e175a3` | A session refusal now preserves the `trust-task-error` document and `stepUpHandoff` for consumers, instead of collapsing the refusal into a string. Does each consuming path preserve refusal versus success, non-authorizing step-up semantics, retry/correlation, and expiry across transport changes? The PR reports targeted/unit/MCP tests and an upstream end-to-end exercise, **not independent RAHP evidence**. | Review against [Toolkit #691](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/691) and Registry [#4](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4), whose positive answer-verification obligations remain separate. |
| [VTI #2453](https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2453), `66a7c2aa362e82cdbbb3b384850d73fa64d97848` | Passkey registration constrains authenticator names to 64 **bytes** across DID-based registration paths after a reproduced YubiKey/CTAP length failure. Are alternative DID encodings and registration entry points covered, and does shortening names preserve account binding without confusing authenticators or users? | Candidate usability/identity-binding regression, not automatically the same assurance severity as the DID-log privilege escalation. Qualify independently before routing. |

These are **candidate propositions**, not four automatically approved Registry cases.
Scope and priority require the exact underlying diff, the monitored
classification or an explicit source-controlled direct intake, source-owner
uniqueness against current Toolkit issues, and one admissible execution
contract. Distinguish source-level reported test results from reproducible
canonical Toolkit evidence. A specialist referral is not implied by a
privacy/security-related change.

## Controlled admission and disposal path

1. Obtain a committed Monitor snapshot newer than 16 November, with immutable
   source finding IDs, routing result, freshness, and source commit URLs; or
   explicitly authorize and implement a separate, source-controlled *direct*
   admission with its own documented authority contract. Do not mislabel
   direct admission as monitored materiality.
2. Run the canonical Toolkit/Registry parity and Registry materiality
   reconciliation against that qualified source. Inspect existing Toolkit
   owners (#827, #1196, #691, #820), Registry #4 and any additional current
   owner before admitting a successor or a new case. A match may require
   reassessment rather than a new issue.
3. Admit only independent, non-duplicated material propositions into a
   Registry case/epoch with immutable source, finding, owner, reviewer, and
   pending evidence obligations. Route canonical Toolkit execution with
   separately recorded result and retain `not_assessed` or `INDETERMINATE`
   until assurance evidence actually supports a judgment.
4. Dispose by explicit preserved / strengthened / weakened / new / uncertain
   classification, evidence references and residual owners. Do not close
   Toolkit historical cases or assert Registry cutover based on a staged
   candidate.

**Migration dependency:** Completing a *new, direct* Registry case is not
evidence that Toolkit's legacy monitored writers are excluded. Full Registry
operational ownership, including source-specific #272 succession, remains
subject to the distinct Tranche A–D gate evidence in Registry #11.
