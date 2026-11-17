# Registry #11 completion-gate status

**Status:** working ledger, not an acceptance record. Governing tracker: [Registry #11](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/11). Observed against Registry `main` at `50d8cd2` (2026-11-17) plus the evidence cited in #11's comments. Update this file in the same PR that moves a gate; a PR should state which row it moves and which executable-path gap it closes.

**Rules of this ledger**

- A row is *evidence* only when it is an executed run, a merged test or a live re-read. Design documents, preflights and schema validity are listed separately as *preparation*.
- A gate is closed only by the independent reviewer recorded below. CI, a monitor run and AI-assisted review do not close a gate (#11 disqualifiers).
- No gate row may assert an RAHP PASS. Registry #4 (`RAHP-AR-DTG-0001`) remains `not_assessed`; Registry #47 (ONDTF-GOV-006) has only an `INDETERMINATE / evidence-required` canonical result.

| Role | Holder |
| --- | --- |
| Independent reviewer for gate acceptance | **Not yet named. Required before the first automated production write (gate 5).** |
| Operator for live dispatch and rollback | Repository maintainer |

## Gate 1. Historical continuity and provenance

| | |
| --- | --- |
| Evidence | 769-issue metadata inventory (712 closed, 57 open) in [`archive/`](../archive/README.md). Toolkit #1203 carries a non-destructive forward link to Registry #4, and #4 and its case record link back; the case validator rejects incomplete accepted succession ([case succession](case-succession.md), PR #43). |
| Preparation | Full-content staging and its aggregate-only screening ([persistent history staging](persistent-history-staging.md), PR #42); PR #17 remains unmerged. |
| Unproven | Reverse links for any case beyond #4; full comment/event/attachment fidelity (not required by default: the gate asks for a locator and index); manual privacy review of any republication. |
| Next executable step | Fix the gate-1 acceptance criterion as *locator completeness plus reverse links for every transferred case*, add a validator check that every accepted `historical_source_issue` appears in the archive inventory, and leave PR #17 unmerged unless a separate privacy review authorizes republication. |

## Gate 2. Exact monitored-source parity

| | |
| --- | --- |
| Evidence | Pinned DTG routing parity (run 43877660730); live dual-router parity on the 2026-11-16 snapshot with byte-identical output for all five output classes (run 43993512587, PR #31). |
| Unproven | Parity across a second, later snapshot; parity under an unmapped-event or stale-snapshot countercase on the live path; the Toolkit's own failed monitor run (43871548910) is not explained by parity. |
| Next executable step | Run the parity comparison on a second pinned snapshot and retain the countercase receipts next to the first. |

## Gate 3. Operational workflow migration with bounded CI cost

| | |
| --- | --- |
| Evidence | Every Registry workflow now has `timeout-minutes`, and read-only workflows supersede only stale PR runs (this change). Write workflows already share the non-cancelling `registry-case-publication` group. |
| Preparation | Toolkit writer inventory: six issue-writing workflows, nine **effectful** canonical publisher call sites, one non-writing `--self-test` and one non-writing `--check-transfers` preflight and one controller-incident call site remain Toolkit-owned ([inventory](../ops/migration/toolkit-writer-cutover-inventory.md)). Preflight does not count as publisher authority. |
| Unproven | One authoritative owner per case across the fleet; migration disposition for each writer and each worker correlation path. |
| Decisions needed | (a) Exit criterion for the twice-daily `dtg-live-shadow` schedule: proposed *retire the cron after the gate-6 shadow cycle completes or after N consecutive clean cycles, whichever is first; keep dispatch*. (b) Whether the weekly writer-inventory schedule is kept or replaced by dispatch plus path triggers, since #11 asks to avoid schedules for one-time checks. |
| Next executable step | Record the one-to-one writer disposition table the inventory document calls for, then settle (a) and (b). |

## Gate 4. DPIP/Lab delivery and result compatibility

| | |
| --- | --- |
| Evidence | Real historical return replay for Toolkit #1116 with DPIP #304/#305, including the duplicate-epoch hazard; canonical portable-result validation; read-only Registry-addressed admission evaluator (PR #30); **within a single offered run set**, `qualify_epoch` rejects duplicate source/examination epochs across DPIP issue numbers and permits idempotent replay of the same issue (`tests/test_registry_epoch_disposition.py`); it does **not** enforce persistent cross-dispatch uniqueness. |
| Unproven | A live Registry-addressed DPIP return; authenticated return transport; a persisted per-epoch uniqueness ledger across separate invocations and concurrent workers; a Lab `rahp-evidence-producer-result/v1` path; controller reconciliation of a Registry-addressed return. |
| Next executable step | Admit one source-bound DPIP referral on a Registry case with an accepted credential scope, deliver it once, retain negative-path receipts (duplicate, delayed, stale, wrong-target) through the actual consumer. |

## Gate 5. Registry-native issue writes with recoverable delivery

| | |
| --- | --- |
| Evidence | Registry #47 exists, was re-read and source-verified, and the read-only outbox shadow re-verifies it. It was created by a bounded, operator-mediated transport, **not** by the automated dispatch branch. Reservation qualification re-reads Toolkit and Registry `main` at pinned commits and rejects branch drift. |
| Unproven | A real POST from the automated direct-intake branch; ambiguous-POST recovery (timeout or partial failure followed by a re-read that finds, not duplicates, the issue); least-privilege token scope as executed; absence of any Toolkit fallback. |
| Next executable step | Dispatch the main-only apply path for one approved intake record with a fault-injected ambiguous response, and retain the receipt showing re-read-then-acknowledge with no second issue. Name the independent reviewer first. |

## Gate 6. Shadow run, exclusive switch and rollback

| | |
| --- | --- |
| Evidence | None executed. |
| Preparation | Toolkit transfer-publication guard and multi-batch DTG preflight (Toolkit PR #1210, #1211) were merged with an empty ledger at the time of #11 comments 24 and 25. Confirm the current ledger state before relying on this. |
| Unproven | Exclusive publication across all Toolkit writers including in-flight runs; protection under a non-empty ledger; rollback without dual-active publishers; one full real material-change cycle with no duplicate external writes. |
| Next executable step | Only after gate 5's first write: one monitored cycle with a non-empty ledger, an in-flight Toolkit run, and a rehearsed rollback. |

## Milestones

Milestone A (first functioning Registry-owned assessment) is **not** achieved: #47 has a canonical `INDETERMINATE / evidence-required` result and no specialist or native evidence. Milestone B requires all six gates above. No release is warranted before then.
