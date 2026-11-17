import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_group_reference_continuity as locator
import registry_monitored_group_delivery as delivery
import registry_group_observation_ack as ack


class ReferenceContinuityTests(unittest.TestCase):
    def setUp(self):
        self.intent = json.loads((ROOT / delivery.INTENT_PATH).read_text())
        self.url = locator.REGISTRY_URL + "88"
        self.owner = {"number": 88, "html_url": self.url, "state": "open",
                      "body": delivery.body(self.intent)}
        self.delivery = {
            "state": "owner_observed", "owner_url": self.url,
            "source_group_sha256": self.intent["source_group_sha256"]}
        self.comment = {
            "id": 431, "html_url": self.url + "#issuecomment-431",
            "body": ack.PREFIX + self.intent["source_group_sha256"] + " -->",
            "user": {"login": "github-actions[bot]", "type": "Bot"}}
        self.observed = {
            "state": "observed", "current_observation_acknowledged": True,
            "registry_issue_url": self.url,
            "source_group_sha256": self.intent["source_group_sha256"],
            "comment_url": self.comment["html_url"]}
        self.toolkit = {}
        for number in (272, 615, 282, 826, 837):
            self.toolkit[number] = {
                "number": number, "html_url": locator.TOOLKIT_URL + str(number),
                "state": "closed" if number == 615 else "open",
                "body": (locator.KEY_MARK + "\n" +
                         "\n".join(self.intent["source_finding_ids"]))
                        if number == 272 else locator.KEY_MARK if number == 615
                        else "Independent residual obligation"}
        self.comments = [self.comment]

    def fetch(self, url):
        if url == locator.ROOT + locator.REG + "/issues/88":
            return self.owner
        if url.startswith(locator.ROOT + locator.REG + "/issues/88/comments?"):
            return self.comments
        prefix = locator.ROOT + locator.TK + "/issues/"
        if url.startswith(prefix):
            number = int(url[len(prefix):])
            return self.toolkit.get(number)
        raise AssertionError("unexpected GitHub API: " + url)

    def check(self):
        return locator.locate(self.intent, self.delivery, self.observed, get=self.fetch)

    def test_all_real_source_references_remain_distinct_and_resolvable(self):
        result = self.check()
        self.assertTrue(result["all_references_live_and_distinct"])
        self.assertEqual(result["toolkit_current_issue_url"], locator.TOOLKIT_URL + "272")
        self.assertEqual(len(result["independent_residual_urls"]), 3)
        self.assertEqual(result["authenticated_observation_url"], self.comment["html_url"])
        for key in ("controller_issue_number_adapter_executed",
                    "reviewer_issue_number_adapter_executed",
                    "specialist_return_transport_authenticated",
                    "cutover_authorized"):
            self.assertFalse(result[key])
        self.assertIsNone(result["assurance_determination"])

    def test_unacknowledged_or_wrong_registry_owner_refused(self):
        self.observed["current_observation_acknowledged"] = False
        with self.assertRaisesRegex(locator.LocatorError, "unacknowledged"):
            self.check()
        self.observed["current_observation_acknowledged"] = True
        self.delivery["owner_url"] = locator.REGISTRY_URL + "89"
        with self.assertRaisesRegex(locator.LocatorError, "mismatch"):
            self.check()

    def test_missing_or_rewritten_legacy_references_refused(self):
        self.owner["body"] = self.owner["body"].replace(
            self.intent["protected_issue_urls"][0], "not-the-residual")
        with self.assertRaisesRegex(locator.LocatorError, "backlinks"):
            self.check()
        self.owner["body"] = delivery.body(self.intent)
        self.toolkit[615]["state"] = "open"
        with self.assertRaisesRegex(locator.LocatorError, "lifecycle"):
            self.check()
        self.toolkit[615]["state"] = "closed"
        self.toolkit[272]["body"] = locator.KEY_MARK
        with self.assertRaisesRegex(locator.LocatorError, "lost source"):
            self.check()

    def test_spoofed_ack_and_changed_group_never_count(self):
        self.comment["user"] = {"login": "attacker", "type": "User"}
        with self.assertRaisesRegex(ack.AckError, "authenticated"):
            self.check()
        self.comment["user"] = {"login": "github-actions[bot]", "type": "Bot"}
        self.observed["source_group_sha256"] = "f" * 64
        with self.assertRaisesRegex(locator.LocatorError, "mismatch"):
            self.check()

    def test_missing_protected_issue_is_not_success(self):
        del self.toolkit[826]
        with self.assertRaisesRegex(locator.LocatorError, "unavailable"):
            self.check()


if __name__ == "__main__":
    unittest.main()
