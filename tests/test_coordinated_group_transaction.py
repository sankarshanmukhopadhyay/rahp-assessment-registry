"""Interruption/retry regression using the existing Registry successor and ack APIs.

The simulated GitHub transport is deliberately non-authoritative. This verifies
composition and idempotent recovery, not a live authority transfer or DPIP/Lab.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_monitored_group_delivery as delivery
import registry_group_observation_ack as ack
import test_registry_monitored_group_delivery as fixtures

CONTEXT = {"GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main",
           "GITHUB_REPOSITORY": delivery.REG, "GITHUB_EVENT_NAME": "workflow_dispatch"}


class TransferRecoveryTests(unittest.TestCase):
    def setUp(self):
        source = fixtures.DeliveryTests("test_accepted_group_and_valid_fence_does_not_claim_cutover")
        source.setUp()
        self.source = source
        self.intent = source.intent
        self.event = source.group
        self.candidate = source.candidate
        self.owner_url = "https://github.com/" + delivery.REG + "/issues/88"
        self.comments = []
        self.posts = {"owner": 0, "ack": 0}
        original_fetch = source.transport()

        def get(url):
            if url.startswith(delivery.API + delivery.REG + "/issues/88/comments?"):
                return self.comments
            return original_fetch(url)
        self.get = get

    def create_owner(self, payload):
        self.posts["owner"] += 1
        self.source.registry.append({
            "number": 88, "state": "open", "html_url": self.owner_url,
            **payload,
        })
        raise TimeoutError("GitHub stored issue before response was lost")

    def create_ack(self, body):
        self.posts["ack"] += 1
        self.comments.append({
            "id": 318, "html_url": self.owner_url + "#issuecomment-318",
            "body": body, "user": {"login": "github-actions[bot]", "type": "Bot"},
            "author_association": "NONE",
        })
        raise TimeoutError("GitHub stored comment before response was lost")

    def owner_delivery(self, *, apply=False, post=None):
        return delivery.deliver(
            self.intent, self.event, self.candidate, "test-token",
            apply=apply, fetch=self.get, post=post)

    def observation(self, *, apply=False, post=None):
        return ack.acknowledge(
            self.intent, self.event, self.candidate, "test-token",
            apply=apply, get=self.get, post=post)

    def test_interruption_after_owner_and_ack_recovers_without_duplicate(self):
        with patch.dict(os.environ, CONTEXT, clear=True):
            first = self.owner_delivery(
                apply=True, post=self.create_owner)
            self.assertTrue(first["recovered_after_ambiguous_post"])
            self.assertEqual(first["owner_url"], self.owner_url)
            self.assertFalse(first["cutover_authorized"])
            # A crash at this point has an owner, but no observation receipt.
            before_ack = self.observation()
            self.assertEqual(before_ack["state"], "pending")
            self.assertFalse(before_ack["current_observation_acknowledged"])
            replay = self.owner_delivery(
                apply=True, post=lambda _: self.fail("duplicate owner POST"))
            self.assertEqual(replay["owner_url"], self.owner_url)
            acknowledged = self.observation(
                apply=True, post=self.create_ack)
            self.assertTrue(acknowledged["recovered_after_ambiguous_post"])
            final = self.observation(
                apply=True, post=lambda _: self.fail("duplicate comment POST"))
        self.assertTrue(final["current_observation_acknowledged"])
        self.assertFalse(final["toolkit_publication_switched"])
        self.assertFalse(final["cutover_authorized"])
        self.assertEqual(self.posts, {"owner": 1, "ack": 1})
        for url in [self.intent["toolkit_current_issue_url"],
                    self.intent["toolkit_historical_issue_url"],
                    *self.intent["protected_issue_urls"]]:
            self.assertIn(url, self.source.registry[0]["body"])

    def test_revoked_reservation_after_owner_fails_closed(self):
        with patch.dict(os.environ, CONTEXT, clear=True):
            self.owner_delivery(apply=True, post=self.create_owner)
            self.source.ledger["transfers"] = []
            with self.assertRaisesRegex(delivery.DeliveryError, "reserved_group"):
                self.observation(apply=True, post=lambda _: self.fail("no ack"))
        self.assertEqual(self.posts, {"owner": 1, "ack": 0})

    def test_conflicting_or_spoofed_observation_is_not_acknowledged(self):
        with patch.dict(os.environ, CONTEXT, clear=True):
            self.owner_delivery(apply=True, post=self.create_owner)
            self.comments.append({
                "id": 318, "html_url": self.owner_url + "#issuecomment-318",
                "body": ack.PREFIX + self.intent["source_group_sha256"] + " -->",
                "user": {"login": "untrusted", "type": "User"},
            })
            with self.assertRaisesRegex(ack.AckError, "authenticated"):
                self.observation()
        self.assertEqual(self.posts["ack"], 0)


if __name__ == "__main__":
    unittest.main()
