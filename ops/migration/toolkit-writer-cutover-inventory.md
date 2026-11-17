# Toolkit publication cutover inventory (current operational authority)

The [read-only weekly inventory workflow](../../.github/workflows/toolkit-issue-writer-inventory.yml) inspects **live Toolkit main**, pins its Git revision, and checks every workflow exposing `issues: write`, canonical assessment-publisher calls and the currently identified issue-number consumers. The inventory is intentionally **not a cutover approval**.

The current 2026-11-17 baseline covers six external-operation or mixed workflows: `cross-spec-pressure-test.yml`, `distributed-resilience-assessment.yml`, `dpip-lifecycle.yml`, `dtg-portfolio-materiality-handoff.yml`, `instance-watch.yml` and `review-workers.yml`. Across them there are nine effectful assessment publisher invocations (plus a DTG `--self-test` and a DTG `--check-transfers` preflight, neither of which publishes), one controller-incident publisher invocation, and downstream Toolkit issue-number consumers including bounded reviews, DPIP handoff and return reconciliation. Unrecognized issue-write workflows, changed publication counts or missing listed consumers fail the inventory. The two Toolkit instance configurations and publisher's canonical repository restriction remain separate migration blockers.

**Safety interpretation:** passing this inventory proves only that the enumerated active surfaces were found unchanged. It does not assert that non-development Toolkit writes have stopped, nor that Registry has assumed controller/DPIP/Lab obligations. In particular a source-scoped Toolkit publisher switch that leaves `dpip_handoff.py` consuming Toolkit issue numbers is a broken cutover. Conversely, an unexpected additional publisher makes an otherwise plausible cutover unsafe.

For [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11), maintain a one-to-one migration disposition for these writers **and** each specialist/worker correlation path. Before activating Registry case creation: prove Registry's equivalent route for every external write, migrate issue-number consumers to stable accepted case/controller mappings, demonstrate no-loss outbox replay, and enforce a rollback-qualified, mutually exclusive authority switch. Only then replace Toolkit's policy guard and configured destinations. A passing test suite without an executed transaction cannot substitute for this evidence.

## Writer and issue-number consumer cutover dispositions (17 November 2026)

The dispositions below are migration **requirements**, not executed switches.
The current Toolkit transfer ledger remains empty. Do not disable a route until
the replacement consumer and exclusive source ownership are both evidenced.

| Toolkit workflow | Current path | Pilot disposition | Blocking dependency |
| --- | --- | --- | --- |
| `cross-spec-pressure-test.yml` | 1 assessment publisher | Retain in Toolkit until an exact external proposition is accepted | Reclassify development/method findings versus externally owned cases without changing reusable Toolkit review authority |
| `distributed-resilience-assessment.yml` | 1 assessment publisher | Retain in Toolkit until equivalent Registry admission exists | Preserve resilience source identity and non-external/method tasks |
| `dtg-portfolio-materiality-handoff.yml` | 3 effectful publishers: controller, combined, DPIP | **Separate routes:** retain controller execution authority; move only accepted external combined cases and qualified specialist admission | Source-specific event partition, committed Registry durable intake, controller and DPIP case/execution mapping, no partial-batch issue writes |
| `instance-watch.yml` | 4 effectful DTG/CAWG publication calls plus 1 controller-incident writer | External DTG/CAWG observations are candidate Registry cases; controller incidents remain Toolkit-owned until reclassified | Registry-native monitored intake/reassessment and existing review-worker numeric issue references |
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
