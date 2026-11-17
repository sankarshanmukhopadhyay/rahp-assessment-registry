import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests")]
import registry_dpip_live_reconcile as reader
import registry_epoch_journal as journal
import registry_specialist_return as bridge
from test_registry_epoch_disposition import build, RealContractStub


class LiveRegistryDPIPTests(unittest.TestCase):
    def setup_accepted(self):
        case, owner, returns, runs, consumer = build([(305, "epoch-305")])
        owner["html_url"] = case["owners"]["current_active_issue"]
        target, comments = runs[0]
        self.live = {"case": case, "owner": owner, "source_returns": returns,
                     "target": target, "target_comments": comments,
                     "consumer": consumer}
        return case

    def fetch(self, url):
        if url.endswith("/rahp-assessment-registry/issues/4"):
            return self.live["owner"]
        if url.endswith("/dtg-privacy-implementation-profile/issues/305"):
            return self.live["target"]
        if "/rahp-assessment-registry/issues/4/comments?" in url:
            return self.live["source_returns"]
        if "/dtg-privacy-implementation-profile/issues/305/comments?" in url:
            return self.live["target_comments"]
        raise AssertionError("unreviewed API endpoint " + url)

    def test_existing_accepted_source_is_qualified_read_only(self):
        case = self.setup_accepted()
        receipt = reader.verify_live(case, 305, self.live["consumer"],
                                     RealContractStub, fetch=self.fetch)
        self.assertEqual(receipt["state"], "pending")
        self.assertTrue(receipt["canonical_toolkit_consumer_used"])
        self.assertFalse(receipt["assurance_determination_imported"])
        self.assertFalse(receipt["controller_reconciliation_executed"])

    def test_same_observation_replays_persisted_epoch_without_new_write(self):
        case = self.setup_accepted()
        record = journal.from_offered_runs(
            case, self.live["owner"], self.live["source_returns"],
            [(self.live["target"], self.live["target_comments"])],
            self.live["consumer"], RealContractStub)[0]
        marker = {"id": 101,
                  "html_url": record["registry_case_url"] + "#issuecomment-101",
                  "body": journal.comment_text(record),
                  "user": {**journal.ACTOR, "type": "Bot", "url": "https://api.github.com/users/bot"}}
        self.live["source_returns"].append(marker)
        receipt = reader.verify_live(case, 305, self.live["consumer"],
                                     RealContractStub, fetch=self.fetch)
        self.assertEqual(receipt["state"], "observed")
        self.assertTrue(receipt["replayed"])

    def test_no_referral_fails_before_network(self):
        case = self.setup_accepted()
        case["referrals"] = []
        with self.assertRaises(bridge.SpecialistAdmissionError):
            reader.verify_live(case, 305, self.live["consumer"],
                               RealContractStub, fetch=lambda _: self.fail("no fetch"))

    def test_wrong_epoch_and_closed_registry_owner_fail(self):
        case = self.setup_accepted()
        self.live["target"]["number"] = 306
        with self.assertRaises(bridge.SpecialistAdmissionError):
            reader.verify_live(case, 305, self.live["consumer"],
                               RealContractStub, fetch=self.fetch)
        case = self.setup_accepted()
        self.live["owner"]["state"] = "closed"
        with self.assertRaises(bridge.SpecialistAdmissionError):
            reader.verify_live(case, 305, self.live["consumer"],
                               RealContractStub, fetch=self.fetch)

    def test_unaccepted_real_pilot_never_qualifies(self):
        case = reader.read_case("cases/dtg/network-answer-proof-2026-11.json")
        with self.assertRaises(bridge.SpecialistAdmissionError):
            reader.verify_live(case, 305, None, None,
                               fetch=lambda _: self.fail("no request"))

    def test_case_paths_are_repo_controlled(self):
        for path in ("../cases/foo.json", "/tmp/foo.json", "cases/../cases/dtg/foo.json",
                     "cases/dtg/UPPER.json"):
            with self.subTest(path=path), self.assertRaises(reader.LiveDPIPError):
                reader.read_case(path)


if __name__ == "__main__":
    unittest.main()
