import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_group_epoch_observation as epoch
import registry_group_observation_ack as ack

INTENT = json.loads((ROOT / "outbox/pending/spec-dependency-2026-11-16.json").read_text())
OWNER = "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/88"


class NewEpochTests(unittest.TestCase):
    def setUp(self):
        self.intent = copy.deepcopy(INTENT)
        self.transfer = {
            "state": "accepted_group",
            "assessment_key": self.intent["assessment_key"],
            "toolkit_issue_url": self.intent["toolkit_current_issue_url"],
            "registry_issue_url": OWNER,
            "monitor_revision": self.intent["monitor_revision"],
            "snapshot_date": self.intent["snapshot_date"],
            "finding_ids": self.intent["source_finding_ids"],
            "group_sha256": self.intent["source_group_sha256"],
            "maintainer_scope_sha256": self.intent["maintainer_scope_sha256"],
        }
        self.ledger = {"schema": "rahp-registry-transfers/v1",
                       "transfers": [self.transfer]}
        self.group = {
            "assessment_key": self.intent["assessment_key"],
            "observed_at": "2026-11-18",
            "source_observations": [
                {"finding_id": fid, "repository": INTENT["source_repository"]}
                for fid in INTENT["source_finding_ids"][:2]],
        }
        self.findings = [
            {"finding_id": item["finding_id"],
             "repository": item["repository"],
             "state": "open",
             "materiality": "high",
             "assurance_impact": "potentially-breaking"}
            for item in self.group["source_observations"]]
        self.issue = {"number": 88, "state": "open", "html_url": OWNER,
                      "body": ("<!-- registry-assessment-key:" +
                               self.intent["assessment_key"] + " -->\n" +
                               "<!-- rahp-registry-monitored-group:v1:" +
                               self.intent["source_group_sha256"] + " -->\n" +
                               self.intent["toolkit_current_issue_url"])}
        self.rev = "a" * 40
        self.posts = []

    def observation(self, **kwargs):
        return epoch.observe(
            self.intent, [self.group], self.findings,
            self.ledger, self.issue, kwargs.pop("comments", []),
            self.rev, **kwargs)

    def test_new_epoch_remains_pending_until_replayable_ack(self):
        dry = self.observation()
        self.assertEqual(dry["state"], "pending")
        self.assertFalse(dry["observation_acknowledged"])
        self.assertFalse(dry["issue_written"])
        self.assertFalse(dry["cutover_authorized"])
        self.assertIsNone(dry["assurance_determination"])
        self.assertNotEqual(dry["source_group_sha256"],
                            self.intent["source_group_sha256"])

    def test_success_and_timeout_after_commit_use_durable_comment_identity(self):
        digest = epoch.group_digest(self.group)
        url = OWNER + "#issuecomment-731"
        comment = {"id": 731, "html_url": url,
                   "body": epoch.acknowledgment_body({
                       "source_group_sha256": digest,
                       "registry_issue_url": OWNER,
                       "monitor_revision": self.rev,
                       "snapshot_date": "2026-11-18",
                       "finding_ids": [x["finding_id"] for x in self.findings]}),
                   "user": {"login": "github-actions[bot]", "type": "Bot"}}
        def timed_out(body):
            self.posts.append(body)
            raise RuntimeError("HTTP timeout after committed POST")
        receipt = self.observation(
            apply=True, post=timed_out, reread=lambda: [comment])
        self.assertEqual(receipt["state"], "observed")
        self.assertEqual(receipt["comment_url"], url)
        self.assertTrue(receipt["recovered_after_ambiguous_post"])
        self.assertTrue(receipt["issue_written"])
        self.assertEqual(len(self.posts), 1)
        duplicate = self.observation(comments=[comment])
        self.assertEqual(duplicate["state"], "observed")
        self.assertFalse(duplicate["issue_written"])
        self.assertFalse(duplicate["cutover_authorized"])

    def test_missing_or_forged_comments_are_not_accepted(self):
        digest = epoch.group_digest(self.group)
        comment = {"id": 731, "html_url": OWNER + "#issuecomment-731",
                   "body": "<!-- rahp-registry-observation:v1:" + digest + " -->",
                   "user": {"login": "other", "type": "User"}}
        with self.assertRaisesRegex(ack.AckError, "authenticated"):
            self.observation(comments=[comment])
        self.assertEqual(self.observation()["state"], "pending")
        with self.assertRaisesRegex(epoch.EpochError, "durably"):
            self.observation(apply=True, post=lambda _: {"id": 731},
                             reread=lambda: [])

    def test_no_transfer_or_unchanged_group_mints_no_ack(self):
        self.ledger["transfers"] = []
        self.assertEqual(self.observation()["state"], "inactive_no_accepted_transfer")
        self.ledger["transfers"] = [self.transfer]
        self.transfer["state"] = "reserved_group"
        self.assertEqual(self.observation()["state"], "inactive_no_accepted_transfer")
        self.transfer["state"] = "accepted_group"
        self.transfer["group_sha256"] = epoch.group_digest(self.group)
        self.assertEqual(self.observation()["state"], "no_changed_group")

    def test_falsified_source_and_owner_rejected_before_any_post(self):
        edits = [
            lambda: self.group["source_observations"].append(copy.deepcopy(
                self.group["source_observations"][0])),
            lambda: self.findings[0].update(repository="attacker/repository"),
            lambda: self.findings[0].update(materiality="informational"),
            lambda: self.findings[0].update(state="closed"),
            lambda: self.group.update(observed_at="unknown"),
            lambda: self.issue.update(html_url=OWNER.replace("/88", "/89")),
            lambda: self.issue.update(number=47),
            lambda: self.issue.update(body="forged owner"),
            lambda: self.transfer.update(monitor_revision="f" * 40),
        ]
        for mutate in edits:
            with self.subTest(mutate=mutate):
                self.setUp()
                mutate()
                with self.assertRaises(ValueError):
                    self.observation(apply=True, post=lambda _: self.fail("no POST"),
                                     reread=lambda: [])


if __name__ == "__main__":
    unittest.main()
