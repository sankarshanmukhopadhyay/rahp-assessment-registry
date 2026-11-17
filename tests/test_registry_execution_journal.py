import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_execution_journal as journal
import bind_registry_execution as binding
import registry_intake as gh


class JournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/network-answer-pilot.spec.json").read_text())
        cls.ledger = json.loads((ROOT / "ops/assessments/network-answer-pilot.ledger.json").read_text())

    def record(self):
        result = {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:sample",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
            "terminal": True,
            "outcome": "INDETERMINATE",
            "reason_code": "evidence-required",
            "evidence": [],
            "residuals": [{"id": "one", "summary": "Evidence missing"}],
            "lineage": {"clean_room": True, "historical_inputs_used": False,
                        "run": copy.deepcopy(self.spec["run"])},
        }
        b = binding.create_binding(self.case, self.spec, self.ledger, result,
                                   toolkit_revision=binding.TOOLKIT_REVISION)
        return journal.form_entry(self.case, self.spec, self.ledger, result, b)

    def issue(self):
        return {"number": 4, "state": "open",
                "body": "<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->\n" +
                        self.case["source"]["revision"] + "\n" + self.case["source"]["finding_id"]}

    def comment(self, record, n=100):
        return {"id": n, "html_url": f"https://github.com/{gh.REGISTRY}/issues/4#issuecomment-{n}",
                "body": journal.comment_text(record)}

    def call(self, record=None, *, apply=False, comments=None, post=None, issue=None):
        record = record or self.record()
        return journal.reconcile(record, self.case, "token", apply=apply,
                                 read_issue=lambda: issue if issue is not None else self.issue(),
                                 read_comments_fn=lambda: [] if comments is None else comments(),
                                 post=post)

    def test_dry_run_does_not_post(self):
        calls = []
        x = self.call(apply=False, post=lambda x: calls.append(x))
        self.assertEqual(x["state"], "pending")
        self.assertEqual(calls, [])
        self.assertFalse(x["assurance_determination_imported"])

    def test_replay_existing_record_is_idempotent(self):
        r = self.record()
        calls = []
        x = self.call(r, apply=True, comments=lambda: [self.comment(r)],
                      post=lambda x: calls.append(x))
        self.assertEqual(x["state"], "acknowledged")
        self.assertEqual(x["comment_id"], 100)
        self.assertEqual(calls, [])

    def test_apply_requires_reread_after_post(self):
        r = self.record()
        history = [[], [self.comment(r)]]
        x = self.call(r, apply=True, comments=lambda: history.pop(0),
                      post=lambda body: self.comment(r))
        self.assertEqual(x["state"], "acknowledged")

    def test_post_success_without_readback_fails(self):
        with self.assertRaisesRegex(journal.JournalError, "unacknowledged"):
            self.call(apply=True, comments=lambda: [], post=lambda body: self.comment(self.record()))

    def test_ambiguous_post_recovered_by_remote_owner(self):
        r = self.record()
        history = [[], [self.comment(r)]]
        def fail(body):
            raise gh.IntakeError("HTTP 502")
        x = self.call(r, apply=True, comments=lambda: history.pop(0), post=fail)
        self.assertTrue(x["recovered_ambiguous_post"])

    def test_ambiguous_post_unobserved_remains_failed(self):
        with self.assertRaisesRegex(journal.JournalError, "unacknowledged"):
            self.call(apply=True, comments=lambda: [],
                      post=lambda body: (_ for _ in ()).throw(gh.IntakeError("HTTP 502")))

    def test_conflicting_result_same_execution_identity_fails(self):
        r = self.record()
        bad = self.comment(r)
        bad["body"] = bad["body"].replace("Evidence missing", "Evidence tampered")
        with self.assertRaisesRegex(journal.JournalError, "conflicting"):
            self.call(r, comments=lambda: [bad])

    def test_duplicate_acknowledgment_refused(self):
        r = self.record()
        with self.assertRaisesRegex(journal.JournalError, "multiple execution records"):
            self.call(r, comments=lambda: [self.comment(r), self.comment(r, 101)])

    def test_wrong_owner_stale_source_closed_case_rejected(self):
        for changed in ({"number": 5}, {"state": "closed"}, {"body": "random"}):
            with self.subTest(changed=changed):
                i = {**self.issue(), **changed}
                with self.assertRaises(journal.JournalError):
                    self.call(issue=i)

    def test_forged_pass_and_false_import_rejected(self):
        r = self.record()
        r["canonical_result"]["outcome"] = "PASS"
        with self.assertRaises(journal.JournalError):
            journal.form_entry(self.case, self.spec, self.ledger, r["canonical_result"], r["binding"])
        r = self.record()
        r["binding"]["case_determination_imported"] = True
        with self.assertRaises(binding.BindingError):
            journal.form_entry(self.case, self.spec, self.ledger, r["canonical_result"], r["binding"])

    def test_conflicting_http_response_refused(self):
        r = self.record()
        history = [[], [self.comment(r)]]
        with self.assertRaisesRegex(journal.JournalError, "conflicts"):
            self.call(r, apply=True, comments=lambda: history.pop(0),
                      post=lambda text: self.comment(r, 987))


if __name__ == "__main__":
    unittest.main()
