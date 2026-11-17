import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_monitored_group_delivery as delivery
import verify_maintainer_cutover_acceptance as scope
from test_maintainer_cutover_acceptance import fixture, comment

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.intent = json.loads((ROOT / delivery.INTENT_PATH).read_text())
        self.candidate = fixture()
        self.candidate["candidate_sha256"] = self.intent["candidate_sha256"]
        self.candidate["source_group_sha256"] = self.intent["source_group_sha256"]
        self.candidate["source_evidence_sha256"] = self.intent["source_evidence_sha256"]
        self.group = {"assessment_key": self.intent["assessment_key"],
                      "source_observations": [
                          {"finding_id": i, "repository": self.intent["source_repository"]}
                          for i in self.intent["source_finding_ids"]]}
        # Fixtures exercise mechanics; production checks the actual canonical digest.
        self.intent["source_group_sha256"] = delivery.contract.digest(self.group)
        self.candidate["source_group_sha256"] = self.intent["source_group_sha256"]
        self.ledger = {"schema": "rahp-registry-transfers/v1", "transfers": [{
            "state": "reserved_group", "assessment_key": self.intent["assessment_key"],
            "toolkit_issue_url": self.intent["toolkit_current_issue_url"],
            "registry_intent_path": delivery.INTENT_PATH,
            "monitor_revision": self.intent["monitor_revision"],
            "snapshot_date": self.intent["snapshot_date"],
            "finding_ids": self.intent["source_finding_ids"],
            "group_sha256": self.intent["source_group_sha256"]}]}
        self.comments = [comment(self.candidate)]
        self.tk = [{"number": 272, "state": "open", "body": delivery.owners.MARKER}]
        self.registry = []
    def check(self):
        return delivery.qualify(self.intent, self.group, self.candidate, self.comments,
                                self.ledger, self.registry, self.tk)
    def test_accepted_group_and_valid_fence_does_not_claim_cutover(self):
        owner, approval = self.check()
        self.assertIsNone(owner)
        self.assertEqual(approval["status"], "accepted")
        self.assertIsNone(self.intent["registry_successor_issue_url"])
    def test_no_reservation_or_changed_group_fails(self):
        self.ledger["transfers"] = []
        with self.assertRaisesRegex(delivery.DeliveryError, "reserved_group"):
            self.check()
        self.setUp()
        self.ledger["transfers"][0]["group_sha256"] = "f"*64
        with self.assertRaises(delivery.DeliveryError):
            self.check()
    def test_wrong_maintainer_and_withdrawal_fail(self):
        self.comments = []
        with self.assertRaisesRegex(delivery.DeliveryError, "maintainer"):
            self.check()
        self.setUp()
        self.comments.append(comment(self.candidate, number=200, action="withdraw"))
        with self.assertRaises(delivery.DeliveryError):
            self.check()
    def test_duplicate_toolkit_and_conflicting_registry_owner(self):
        self.tk.append({"number": 999, "state": "open", "body": delivery.owners.MARKER})
        with self.assertRaisesRegex(delivery.DeliveryError, "ambiguous"):
            self.check()
        self.setUp()
        self.registry = [{"number": 42, "state": "open",
                          "html_url": "https://github.com/" + delivery.REG + "/issues/42",
                          "body": delivery.intake.marker(self.intent["assessment_key"])}]
        with self.assertRaisesRegex(delivery.DeliveryError, "different event"):
            self.check()
    def test_exact_owner_replay_requires_full_source(self):
        original = {"number": 42, "state": "open",
                    "html_url": "https://github.com/" + delivery.REG + "/issues/42",
                    "body": delivery.body(self.intent)}
        self.registry = [original]
        owner, _ = self.check()
        self.assertEqual(owner["number"], 42)
        original["body"] = original["body"].replace(self.intent["source_finding_ids"][0], "missing")
        with self.assertRaisesRegex(delivery.DeliveryError, "finding"):
            self.check()
    def test_write_requires_main_only_dispatch(self):
        proper = {"GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main",
                  "GITHUB_REPOSITORY": delivery.REG, "GITHUB_EVENT_NAME": "workflow_dispatch"}
        delivery.require_write_context(proper)
        for name, value in (("GITHUB_REF", "refs/heads/branch"),
                            ("GITHUB_REPOSITORY", "wrong/repo"),
                            ("GITHUB_EVENT_NAME", "pull_request")):
            with self.assertRaises(delivery.DeliveryError):
                delivery.require_write_context({**proper, name: value})
    def test_group_has_no_single_finding_compatibility_shortcut(self):
        text = delivery.body(self.intent)
        for finding_id in self.intent["source_finding_ids"]:
            self.assertIn(finding_id, text)
        self.assertNotIn("assurance_determination: PASS", text)

if __name__ == "__main__":
    unittest.main()
