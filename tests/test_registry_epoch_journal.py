import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import registry_epoch_journal as journal
from test_registry_epoch_disposition import build, RealContractStub


class EpochJournalTests(unittest.TestCase):
    def qualified(self, issue=305, epoch="epoch-a"):
        case, case_issue, comments, runs, consumer = build([(issue, epoch)])
        record = journal.from_offered_runs(
            case, case_issue, comments, runs, consumer, RealContractStub)[0]
        live_issue = {"number": 4, "html_url": record["registry_case_url"], "state": "open",
                      "body": "<!-- rahp-registry-case:" + case["case_id"] + " -->"}
        return case, record, live_issue

    def comment(self, record, number=120):
        return {"id": number, "html_url": record["registry_case_url"] + "#issuecomment-" + str(number),
                "body": journal.comment_text(record), "user": dict(journal.ACTOR)}

    def test_source_bound_epoch_from_canonical_consumer(self):
        _, record, owner = self.qualified()
        self.assertEqual(record["state"], "observed_unverified")
        self.assertFalse(record["case_determination_imported"])
        self.assertFalse(record["specialist_transport_authenticated"])
        self.assertEqual(journal.reconcile(record, owner, read_comments=lambda: [])["state"], "pending")

    def test_distinct_dpip_numbers_same_epoch_conflict_across_calls(self):
        _, first, owner = self.qualified(304)
        _, second, _ = self.qualified(305)
        self.assertEqual(first["epoch_id"], second["epoch_id"])
        remote = [self.comment(first)]
        with self.assertRaisesRegex(journal.EpochJournalError, "conflicting"):
            journal.reconcile(second, owner, read_comments=lambda: remote)
        self.assertFalse(first["qualified_return"]["case_determination_imported"])

    def test_same_epoch_same_issue_replay_is_idempotent(self):
        _, record, owner = self.qualified()
        read = lambda: [self.comment(record)]
        result = journal.reconcile(record, owner, apply=True, read_comments=read,
                                   post=lambda _: self.fail("must not post again"))
        self.assertEqual(result["state"], "observed")
        self.assertTrue(result["replayed"])

    def test_new_observation_requires_shared_lock(self):
        _, record, owner = self.qualified()
        with self.assertRaisesRegex(journal.EpochJournalError, "exclusive serialized"):
            journal.reconcile(record, owner, apply=True, read_comments=lambda: [],
                              post=lambda _: self.fail("must not write"))

    def test_apply_requires_remote_re_read(self):
        _, record, owner = self.qualified()
        comments = []
        def post(body):
            comments.append(self.comment(record))
            return comments[0]
        result = journal.reconcile(record, owner, apply=True, exclusive_operator_lock=True,
                                   read_comments=lambda: comments[:], post=post)
        self.assertEqual(result["state"], "observed")
        self.assertEqual(len(comments), 1)

    def test_ambiguous_post_recovery(self):
        _, record, owner = self.qualified()
        reads = iter([[], [self.comment(record)]])
        def failed(_):
            raise OSError("simulated transport failure")
        result = journal.reconcile(record, owner, apply=True, exclusive_operator_lock=True,
                                   read_comments=lambda: next(reads), post=failed)
        self.assertTrue(result["recovered_ambiguous_post"])

    def test_unobserved_post_never_acknowledged(self):
        _, record, owner = self.qualified()
        with self.assertRaisesRegex(journal.EpochJournalError, "unacknowledged"):
            journal.reconcile(record, owner, apply=True, exclusive_operator_lock=True,
                              read_comments=lambda: [],
                              post=lambda _: self.comment(record))

    def test_conflicting_issuer_or_duplicate_marker_fails_closed(self):
        _, record, owner = self.qualified()
        one = self.comment(record)
        forged = {**one, "user": {"id": 222, "login": "other"}}
        with self.assertRaisesRegex(journal.EpochJournalError, "authorized"):
            journal.reconcile(record, owner, read_comments=lambda: [forged])
        with self.assertRaisesRegex(journal.EpochJournalError, "more than one"):
            journal.reconcile(record, owner, read_comments=lambda: [one, self.comment(record, 121)])

    def test_changed_source_pin_or_elevated_assurance_rejected(self):
        case, record, _ = self.qualified()
        for attr, value in (
            ("case_determination_imported", True),
            ("return_transport_authenticated", True),
            ("controller_reconciliation_executed", True),
            ("operational_cutover_qualified", True),
        ):
            rec = copy.deepcopy(record["qualified_return"])
            rec[attr] = value
            with self.subTest(attr=attr), self.assertRaises(journal.EpochJournalError):
                journal.record_for(rec, case)
        tampered = copy.deepcopy(record["qualified_return"])
        tampered["source_pin"]["revision"] = "a" * 40
        with self.assertRaisesRegex(journal.EpochJournalError, "source pin"):
            journal.record_for(tampered, case)

    def test_closed_or_foreign_case_cannot_receive_epoch(self):
        _, record, owner = self.qualified()
        for change in ({"state": "closed"}, {"html_url": "https://github.com/other/repo/issues/4"},
                       {"body": "no matching case"}):
            with self.subTest(change=change), self.assertRaises(journal.EpochJournalError):
                journal.reconcile(record, {**owner, **change}, read_comments=lambda: [])


if __name__ == "__main__":
    unittest.main()
