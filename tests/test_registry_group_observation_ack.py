import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_group_observation_ack as ack

class AckTests(unittest.TestCase):
    def setUp(self):
        self.intent = {"assessment_key": "dtg:portfolio:combined:spec-dependency-alignment",
                       "source_group_sha256": "a"*64}
        self.event = {"assessment_key": self.intent["assessment_key"]}
        self.candidate = {}
        self.owner = "https://github.com/" + ack.REG + "/issues/88"
        self.rows = []
        self.calls = []
    def fetch(self, url):
        if "/issues/88/comments?" in url:
            return self.rows
        raise AssertionError("unexpected read: " + url)
    def comment(self, id=125, actor="github-actions[bot]"):
        return {"id": id, "html_url": self.owner + "#issuecomment-" + str(id),
                "body": ack.PREFIX + self.intent["source_group_sha256"] + " -->",
                "user": {"login": actor, "type": "Bot" if actor.endswith("[bot]") else "User"},
                "author_association": "OWNER" if actor == "sankarshanmukhopadhyay" else "NONE"}
    def stub(self, *args, **kwargs):
        return {"state": "owner_observed", "owner_url": self.owner}
    def test_no_owner_or_uncertain_ack_never_proves_delivery(self):
        with patch.object(ack.group, "deliver", return_value={
                "state": "ready_for_delivery", "owner_url": None}):
            with self.assertRaisesRegex(ack.AckError, "successor"):
                ack.acknowledge(self.intent, self.event, self.candidate,
                                "token", get=self.fetch)
    def test_read_only_does_not_create_comment(self):
        with patch.object(ack.group, "deliver", self.stub):
            receipt = ack.acknowledge(self.intent, self.event, self.candidate,
                     "token", get=self.fetch, post=lambda _: self.fail("must not POST"))
        self.assertEqual(receipt["state"], "pending")
        self.assertFalse(receipt["cutover_authorized"])
    def test_live_comment_replay_is_idempotent(self):
        self.rows.append(self.comment())
        with patch.object(ack.group, "deliver", self.stub):
            receipt = ack.acknowledge(self.intent, self.event, self.candidate,
                     "token", get=self.fetch)
        self.assertTrue(receipt["current_observation_acknowledged"])
        self.assertFalse(receipt["toolkit_publication_switched"])
    def test_ambiguous_post_recovers_after_source_pinned_comment(self):
        good = {"GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main",
                "GITHUB_REPOSITORY": ack.REG, "GITHUB_EVENT_NAME": "workflow_dispatch"}
        def post(body):
            self.calls.append(body)
            self.rows.append(self.comment())
            raise TimeoutError("commit succeeded; response lost")
        with patch.dict(os.environ, good, clear=True), patch.object(ack.group, "deliver", self.stub):
            receipt = ack.acknowledge(self.intent, self.event, self.candidate,
                      "token", apply=True, get=self.fetch, post=post)
            second = ack.acknowledge(self.intent, self.event, self.candidate,
                      "token", apply=True, get=self.fetch,
                      post=lambda _: self.fail("duplicate acknowledgment"))
        self.assertTrue(receipt["recovered_after_ambiguous_post"])
        self.assertTrue(second["current_observation_acknowledged"])
        self.assertEqual(len(self.calls), 1)
    def test_wrong_actor_duplicate_or_wrong_comment_refused(self):
        self.rows = [self.comment(actor="untrusted")]
        with patch.object(ack.group, "deliver", self.stub):
            with self.assertRaisesRegex(ack.AckError, "authenticated"):
                ack.acknowledge(self.intent, self.event, self.candidate, "token", get=self.fetch)
            self.rows = [self.comment(), self.comment(id=126)]
            with self.assertRaisesRegex(ack.AckError, "unique"):
                ack.acknowledge(self.intent, self.event, self.candidate, "token", get=self.fetch)
            self.rows = [self.comment()]
            self.rows[0]["html_url"] += "-forged"
            with self.assertRaisesRegex(ack.AckError, "identity"):
                ack.acknowledge(self.intent, self.event, self.candidate, "token", get=self.fetch)

if __name__ == "__main__":
    unittest.main()
