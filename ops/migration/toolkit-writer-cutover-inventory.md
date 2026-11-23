# Toolkit publication cutover inventory (current operational authority)

The [read-only weekly inventory workflow](../../.github/workflows/toolkit-issue-writer-inventory.yml) inspects **live Toolkit main**, pins its Git revision, and checks every workflow exposing `issues: write`, canonical assessment-publisher calls and the currently identified issue-number consumers. The inventory is intentionally **not a cutover approval**.

The audited **current-workflow inventory** covers six external-operation or mixed workflows: `cross-spec-pressure-test.yml`, `distributed-resilience-assessment.yml`, `dpip-lifecycle.yml`, `dtg-materiality-main.yml`, `instance-monitor-main.yml` and `review-workers.yml`. The retired `dtg-portfolio-materiality-handoff.yml` and `instance-watch.yml` remain historical-dispatch concerns rather than current source paths. Across them there are nine effectful assessment publisher invocations (plus a DTG `--self-test` and a DTG `--check-transfers` preflight, neither of which publishes), one controller-incident publisher invocation, and downstream Toolkit issue-number consumers including bounded reviews, DPIP handoff and return reconciliation. Unrecognized issue-write workflows, changed publication counts or missing listed consumers fail the inventory. The two Toolkit instance configurations and publisher's canonical repository restriction remain separate migration blockers.

**Safety interpretation:** passing this inventory proves only that the enumerated active surfaces were found unchanged. It does not assert that non-development Toolkit writes have stopped, nor that Registry has assumed controller/DPIP/Lab obligations. In particular a source-scoped Toolkit publisher switch that leaves `dpip_handoff.py` consuming Toolkit issue numbers is a broken cutover. Conversely, an unexpected additional publisher makes an otherwise plausible cutover unsafe.

For [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11), maintain a one-to-one migration disposition for these writers **and** each specialist/worker correlation path. Before activating Registry case creation: prove Registry's equivalent route for every external write, migrate issue-number consumers to stable accepted case/controller mappings, demonstrate no-loss outbox replay, and enforce a rollback-qualified, mutually exclusive authority switch. Only then replace Toolkit's policy guard and configured destinations. A passing test suite without an executed transaction cannot substitute for this evidence.

## 23 November 2026: live workflow-name drift and quiescence boundary

The active Toolkit `main` issue writers now include
`dtg-materiality-main.yml` and `instance-monitor-main.yml`. Their retired
predecessor paths, `dtg-portfolio-materiality-handoff.yml` and
`instance-watch.yml`, remain relevant to historical queued or in-flight
workflow observations, but cannot substitute for the current names.

Registry's `verify_toolkit_writer_quiescence.py` now derives its current
workflow paths from the existing audited `EXPECTED` producer/consumer inventory
and retains the two predecessor paths as additional blockers. A live
`instance-monitor-main.yml` run is therefore counted as an active writer,
not reported as quiescent. The regression tests exercise all listed current
and historical paths through the same `evaluate()` function used by the
operator qualification.

This correction closes a **false-negative classification defect**, not the
exclusive-writer cutover gate. A clean nonterminal-run snapshot remains a
point-in-time observation; it does not disable future dispatches, prove
historical workflow retirement, ensure source-qualified Registry delivery,
or establish an atomic GitHub issue write. Source-scoped Toolkit #272 →
Registry #88 already has an accepted-group ledger entry, but the broader
producer and consumer migration under Registry #77 remains unresolved.
No additional Registry publication or Toolkit suppression is authorized by
this inventory correction.

## Writer and issue-number consumer cutover dispositions (current paths; historical requirements)

The dispositions below are migration **requirements**, not executed switches.
The live Toolkit transfer ledger contains the accepted source-scoped Toolkit #272 → Registry #88 group. Do not disable another route until
the replacement consumer and exclusive source ownership are both evidenced.

| Toolkit workflow | Current path | Pilot disposition | Blocking dependency |
| --- | --- | --- | --- |
| `cross-spec-pressure-test.yml` | 1 assessment publisher | Retain in Toolkit until an exact external proposition is accepted | Reclassify development/method findings versus externally owned cases without changing reusable Toolkit review authority |
| `distributed-resilience-assessment.yml` | 1 assessment publisher | Retain in Toolkit until equivalent Registry admission exists | Preserve resilience source identity and non-external/method tasks |
| `dtg-materiality-main.yml` | 3 effectful publishers: controller, combined, DPIP | **Separate routes:** retain controller execution authority; move only accepted external combined cases and qualified specialist admission | Source-specific event partition, committed Registry durable intake, controller and DPIP case/execution mapping, no partial-batch issue writes |
| `instance-monitor-main.yml` | 4 effectful DTG/CAWG publication calls plus 1 controller-incident writer | External DTG/CAWG observations are candidate Registry cases; controller incidents remain Toolkit-owned until reclassified | Registry-native monitored intake/reassessment and existing review-worker numeric issue references |
| `dpip-lifecycle.yml` | No assessment publisher; Toolkit issue-number consumer | Preserve legacy historical Toolkit subscriptions; add a separate Registry-addressed qualified consumer when ready | Stable Registry case/execution/referral identity, authenticated return transport, persistent epoch acknowledgment |
| `review-workers.yml` | No assessment publisher; combined/repository review consumers | Keep historical issue-number consumption while introducing explicit Registry case mapping | Avoid replacing a Toolkit issue number with a Registry issue number without contract-bound adapter |

**Operational switch invariant:** an accepted Registry owner must have a
durable, uniquely replayable intake record before Toolkit suppresses an
external event. Preserve unmatched and unresolved events, fail closed on
unknown authority, and prove that no in-flight Toolkit writer can re-create the
same case. A POST timeout is not a basis for falling back to Toolkit.

**Next executable slice:** select a real source-qualified monitored proposition
that is not entangled with the #1194/#1208 shared findings; identify its exact
controller and specialist consumer paths. Implement the narrow producer
partition and stable adapter, test with existing historical markers and the
real monitored input, and run the authorized cutover only after independent
review and rollback disposition. No new production source is admitted by this
inventory.

## Source and consumer recheck (19 November 2026)

The verified GitHub `main` heads remain Toolkit
`35035303c830c68e7cb759195fb223b0ff9e4255` and Registry
`70affaa3797bdcd527a24b50f27ac94d71202cb7`. The live
`instances/dtg/registry-transfers.json` still has an empty `transfers`
array. These are observation-time facts, not durable writer exclusion.

Both committed Registry cases,
[`RAHP-AR-DTG-0001`](../../cases/dtg/network-answer-proof-2026-11.json)
and [`RAHP-AR-ONDTF-0001`](../../cases/ondtf/emergency-authority-v1.json),
have empty `referrals` arrays and `not_assessed` determinations. Neither
is a genuine admitted Registry-directed DPIP/Lab return candidate. Toolkit
#272 remains ineligible for actual combined-review/DPIP dispatch under the
canonical selectors established by Registry #71/#72. Search results showing
other Toolkit issues with `assessment-required` do not establish a Registry
admission, dispatch authority, or specialist referral.

**Stop disposition:** The manual Registry successor workflow's read-only
nonterminal-run check observes current quiescence but cannot freeze future
Toolkit dispatch or fence older workflow code. No verified, enforceable
future-dispatch freeze and drain mechanism was established at this checkpoint.
Do not write the `reserved_group` ledger entry or invoke `apply=true`
on this evidence. For G4, admit a *separate* source-pinned specialist
proposition only after actual referral scope, target acceptance and Toolkit
controller reconciliation are demonstrable. No G1–G6 gate changes state by
virtue of this recheck.

## Controlled #272 transaction rehearsal: mandatory stop conditions

This is an **operator sequence**, not a live cutover command. Run it only
against the original 2026-11-16 four-finding source pins and exact maintainer
scope. The Toolkit transfer ledger must remain empty until the required
exclusion and consumer evidence has been obtained. The merged safeguards
([Toolkit #1218](https://github.com/sankarshanmukhopadhyay/rahp-toolkit/pull/1218),
[Registry #67](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/pull/67))
are preparatory controls, not authorization to activate.

1. **Inventory and freeze.** Re-read both `main` commits and the six
   workflow/nine effectful publisher inventory. Establish a documented means
   of stopping *new* affected Toolkit issue writes, including schedules,
   push/dispatch triggers and older workflow checkouts. Drain or cancel
   in-flight writers, and confirm that no independent publisher can resume.
   The Registry nonterminal-run inspection only observes a point in time;
   it neither disables future runs nor establishes a distributed lock.
   **Stop** if future writers cannot be excluded.
2. **Qualify source and consumers.** Re-run exact Monitor commit, four
   findings, group SHA-256 and maintainer scope acceptance. Re-read Toolkit
   #272 (open), #615 (historical closed) and independent #282/#826/#837.
   Identify the actual controller, reviewer, DPIP and Lab consumers of
   Toolkit issue numbers. Do not substitute a Registry number for a Toolkit
   execution/referral number. **Stop** if a first-party consumer cannot
   resolve a stable source-to-case-to-execution mapping.
3. **Rehearse before writing.** Use source-pinned original and journal-enriched
   event fixtures to demonstrate that a `reserved_group` holds only the
   selected group and publishes unrelated events, including when the next
   snapshot has no matched group or an unqualified changed group. Prove
   malicious/stale/malformed and owner-conflict cases fail closed. Confirm
   protected source URLs survive replay.
4. **Reservation and owner transaction (not yet authorized).** Only after
   the preceding exclusions, commit the exact `reserved_group` record and
   recheck that all active publishers will enforce it. The Registry's
   serialized guarded successor/acknowledgment workflow must then requalify
   current source, reservation, unique owner, authenticated maintainer
   decision and writer quiescence before any issue POST. On timeout, re-read
   the authoritative Registry issue/comment inventories and resume the same
   operation; never invent a second owner or treat an ambiguous result as
   success. Maintain the reservation while its outcome is uncertain.
5. **Acceptance and original consumer preservation (blocked).** An
   `accepted_group` transition must contain the actual unique Registry
   successor URL and unchanged group/owner pins. Toolkit selection must
   independently authenticate the current Registry observation acknowledgment
   before excluding the accepted group. Existing #272 and protected residuals
   remain separately resolvable; current controller and specialist contracts
   must have an executed, version-pinned compatibility receipt. The present
   candidate does **not** satisfy this condition.
6. **Interruption and reverse-transfer review (blocked).** Recover every
   crash point before and after Registry owner creation, acknowledgment and
   accepted routing. An accepted or reserved ledger entry must not be removed
   to resume Toolkit. A future reverse transfer requires positive evidence
   that the Registry writer is fenced, all accepted source observations remain
   durable and a new governed authority decision establishes Toolkit
   reactivation. No such reverse-transfer implementation is currently
   accepted.

**Acceptance evidence:** record pinned Toolkit/Registry commits, source digest,
active-run inventory and stop mechanism, unique owner and observation URLs,
retained/held event counts, first-party consumer receipts, recovery trials and
negative cases. A green CI result or a clean quiescence snapshot alone cannot
close G3, G5 or G6. Missing evidence means stop, not rollback by deletion.
