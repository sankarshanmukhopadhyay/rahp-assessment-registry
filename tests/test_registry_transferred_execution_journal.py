import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_transferred_execution_journal as journal
import bind_transferred_execution as binding

PIN = "b" * 40


class AcceptedGroupReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/dtg-spec-dependency-transferred.spec.json").read_text())
        cls.evidence = {"requirements": []}
        src = cls.case["source"]
        cls.transfers = {"schema": "rahp-registry-transfers/v1", "transfers": [{
            "state": "accepted_group", "assessment_key": binding.KEY,
            "toolkit_issue_url": binding.TK_ISSUE,
            "registry_issue_url": binding.REG_ISSUE,
            "monitor_revision": binding.MONITOR_REVISION,
            "snapshot_date": src["observed_on"],
            "group_sha256": binding.GROUP_SHA256,
            "finding_ids": list(binding.FINDING_IDS),
            "maintainer_scope_sha256": binding.SCOPE_SHA256,
        }]}

    def result(self):
        return {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:source88-execution",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "terminal": True,
            "outcome": "INDETERMINATE",
            "reason_code": "evidence-required",
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
            "evidence": [], "residuals": [{"id": "gap", "summary": "No target-native evidence"}],
            "lineage": {"clean_room": True, "historical_inputs_used": False,
                        "run": copy.deepcopy(self.spec["run"])},
        }

    def record(self, *, result=None, binding_receipt=None, case=None, transfers=None):
        result = self.result() if result is None else result
        case = self.case if case is None else case
        transfers = self.transfers if transfers is None else transfers
        bound = binding.bind(case, transfers, self.spec, self.evidence, result,
                             engine_revision=binding.ENGINE_REVISION,
                             transfer_ledger_revision=PIN)
        return journal.record_for(case, transfers, self.spec, self.evidence,
                                  result, bound if binding_receipt is None else binding_receipt,
                                  engine_revision=binding.ENGINE_REVISION,
                                  transfer_ledger_revision=PIN)

    def issue(self):
        return {"number": 88, "state": "open", "html_url": binding.REG_ISSUE,
                "body": "\n".join((f"<!-- rahp-registry-case:{binding.CASE_ID} -->",
                                  f"<!-- registry-assessment-key:{binding.KEY} -->",
                                  binding.GROUP_SHA256, binding.TK_ISSUE))}

    def comment(self, record, number=19):
        return {"id": number, "html_url": binding.REG_ISSUE + f"#issuecomment-{number}",
                "body": journal.render(record),
                "user": {"login": "github-actions[bot]", "id": 41898282}}

    def call(self, record=None, *, apply=False, comments=None, post=None,
             issue=None, lock=False, token="read-token"):
        record = self.record() if record is None else record
        return journal.reconcile(record, token, apply=apply, exclusive_lock=lock,
                                 get_issue=lambda: self.issue() if issue is None else issue,
                                 get_comments=lambda: [] if comments is None else comments(),
                                 post=post)

    def test_readonly_actual_binding_has_distinct_case_and_engine_ids(self):
        rec = self.record()
        self.assertEqual(rec["case_id"], binding.CASE_ID)
        self.assertEqual(rec["historical_toolkit_issue_url"], binding.TK_ISSUE)
        self.assertEqual(rec["canonical_result"]["outcome"], "INDETERMINATE")
        self.assertEqual(rec["binding"]["registry_case_url"], binding.REG_ISSUE)
        self.assertEqual(rec["binding"]["toolkit_execution_id"], "rahp:source88-execution")
        self.assertTrue(all(rec[k] is False for k in (
            "assessment_imported", "specialist_return_received",
            "toolkit_legacy_issue_worker_dispatched", "controller_cutover_qualified")))
        self.assertEqual(self.call(rec)["state"], "pending")

    def test_matching_authorized_replay_performs_no_second_post(self):
        rec = self.record()
        writes = []
        out = self.call(rec, apply=True, lock=True, comments=lambda: [self.comment(rec)],
                        post=lambda body: writes.append(body))
        self.assertEqual(out["state"], "acknowledged")
        self.assertTrue(out["replay"])
        self.assertEqual(writes, [])

    def test_authorized_return_requires_post_and_durable_reread(self):
        rec = self.record()
        history = [[], [self.comment(rec)]]
        seen = []
        out = self.call(rec, apply=True, lock=True, comments=lambda: history.pop(0),
                        post=lambda body: (seen.append(body), self.comment(rec))[1])
        self.assertEqual(out["state"], "acknowledged")
        self.assertFalse(out["replay"])
        self.assertEqual(seen, [journal.render(rec)])

    def test_ambiguous_http_timeout_recovers_only_observed_receipt(self):
        rec = self.record()
        history = [[], [self.comment(rec)]]
        def fail(_):
            raise TimeoutError("transport timeout")
        out = self.call(rec, apply=True, lock=True, comments=lambda: history.pop(0), post=fail)
        self.assertTrue(out["recovered_ambiguous_post"])
        with self.assertRaisesRegex(journal.ReturnError, "not durably"):
            self.call(rec, apply=True, lock=True, comments=lambda: [], post=fail)

    def test_denies_effectful_write_without_exclusive_publisher_lock(self):
        rec = self.record()
        with self.assertRaisesRegex(journal.ReturnError, "serialized"):
            self.call(rec, apply=True, post=lambda _: self.fail("unexpected POST"))

    def test_conflicting_result_same_source_epoch_denied(self):
        rec = self.record()
        changed = self.result()
        changed["assessment_id"] = "rahp:different"
        other = self.record(result=changed)
        self.assertEqual(rec["epoch_id"], other["epoch_id"])
        with self.assertRaisesRegex(journal.ReturnError, "conflicting"):
            self.call(rec, comments=lambda: [self.comment(other)])
        with self.assertRaisesRegex(journal.ReturnError, "conflicting"):
            self.call(other, comments=lambda: [self.comment(rec)])

    def test_duplicated_marker_and_forged_actor_are_not_replay(self):
        rec = self.record()
        with self.assertRaisesRegex(journal.ReturnError, "duplicate"):
            self.call(rec, comments=lambda: [self.comment(rec), self.comment(rec, 20)])
        foreign = self.comment(rec)
        foreign["user"] = {"id": 12345, "login": "github-actions[bot]"}
        with self.assertRaisesRegex(journal.ReturnError, "expected workflow actor"):
            self.call(rec, comments=lambda: [foreign])
        foreign = self.comment(rec)
        foreign["user"] = {"id": 41898282, "login": "untrusted"}
        with self.assertRaisesRegex(journal.ReturnError, "expected workflow actor"):
            self.call(rec, comments=lambda: [foreign])

    def test_wrong_url_or_duplicate_foreign_source_denied(self):
        rec = self.record()
        foreign = self.comment(rec)
        foreign["html_url"] = foreign["html_url"].replace("/issues/88", "/issues/272")
        with self.assertRaisesRegex(journal.ReturnError, "acknowledgment identity"):
            self.call(rec, comments=lambda: [foreign])
        for item in ({"state": "closed"}, {"number": 272},
                     {"html_url": binding.TK_ISSUE}, {"body": "foreign identity"}):
            with self.subTest(item=item), self.assertRaises(journal.ReturnError):
                self.call(rec, issue={**self.issue(), **item})

    def test_wrong_or_forged_binding_never_becomes_return(self):
        good = self.record()
        forged = copy.deepcopy(good["binding"])
        forged["case_determination_imported"] = True
        with self.assertRaises(journal.ReturnError):
            self.record(binding_receipt=forged)
        positive = self.result()
        positive["outcome"] = "PASS"
        with self.assertRaises(binding.TransferBindingError):
            self.record(result=positive)
        stale = copy.deepcopy(self.transfers)
        stale["transfers"][0]["state"] = "reserved_group"
        with self.assertRaises(binding.TransferBindingError):
            self.record(transfers=stale)

    def test_unknown_remote_history_is_not_success(self):
        rec = self.record()
        with self.assertRaisesRegex(journal.ReturnError, "history unavailable"):
            self.call(rec, comments=lambda: None)
        with self.assertRaisesRegex(journal.ReturnError, "token missing"):
            self.call(rec, token="")
        with self.assertRaisesRegex(journal.ReturnError, "malformed"):
            self.call(rec, comments=lambda: ["invalid"])

    def test_only_owner_main_manual_or_exact_epoch_push_can_publish(self):
        good = {
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": binding.REGISTRY,
            "GITHUB_ACTOR": "sankarshanmukhopadhyay",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
        }
        journal.require_write_context(good)
        approved = {**good, "GITHUB_EVENT_NAME": "push",
                    "REGISTRY_RETURN_COMMIT_MESSAGE":
                    "Registry-Case-88-Return-Authorization: " + binding.GROUP_SHA256}
        journal.require_write_context(approved)
        negatives = [
            {**good, "GITHUB_REF": "refs/heads/old-branch"},
            {**good, "GITHUB_REPOSITORY": binding.TOOLKIT},
            {**good, "GITHUB_ACTOR": "unknown-actor"},
            {**good, "GITHUB_EVENT_NAME": "pull_request"},
            {**approved, "REGISTRY_RETURN_COMMIT_MESSAGE": ""},
            {**approved, "REGISTRY_RETURN_COMMIT_MESSAGE":
             "Registry-Case-88-Return-Authorization: " + "a" * 64},
            {**approved, "GITHUB_ACTOR": "other"},
            {**approved, "GITHUB_REF": "refs/tags/legacy"},
        ]
        for bad in negatives:
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    journal.ReturnError, "owner-authorized"):
                journal.require_write_context(bad)

    def test_no_post_response_without_remote_observation(self):
        rec = self.record()
        with self.assertRaisesRegex(journal.ReturnError, "not durably"):
            self.call(rec, apply=True, lock=True, comments=lambda: [],
                      post=lambda _: self.comment(rec))
        history = [[], [self.comment(rec)]]
        with self.assertRaisesRegex(journal.ReturnError, "conflicts"):
            self.call(rec, apply=True, lock=True, comments=lambda: history.pop(0),
                      post=lambda _: self.comment(rec, 111))


if __name__ == "__main__":
    unittest.main()
