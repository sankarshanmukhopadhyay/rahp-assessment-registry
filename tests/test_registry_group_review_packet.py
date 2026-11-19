import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_group_review_packet as packet

INTENT = json.loads((ROOT / "outbox/pending/spec-dependency-2026-11-16.json").read_text())


class GroupReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.intent = copy.deepcopy(INTENT)
        self.findings = [{
            "finding_id": fid, "repository": INTENT["source_repository"],
            "title": "Trust Tasks source release delta",
            "evidence_urls": [], "state": "open",
        } for fid in INTENT["source_finding_ids"]]
        self.group = {
            "assessment_key": self.intent["assessment_key"],
            "observed_at": self.intent["snapshot_date"],
            "source_observations": [{
                "finding_id": row["finding_id"], "repository": row["repository"]
            } for row in self.findings],
        }
        self.intent["source_group_sha256"] = packet.group_digest(self.group)
        self.render_calls = []

    def render(self, issue, catalog):
        self.assertNotIn("number", issue)
        self.assertEqual(set(catalog), set(INTENT["source_finding_ids"]))
        self.render_calls.append(issue)
        return "## Reviewer judgment packet\n\nFour separate propositions."

    def find(self, body):
        import re
        return re.findall(r"(?<![A-Za-z0-9])([0-9a-f]{20})(?![A-Za-z0-9])", body)

    def execute(self):
        return packet.build(self.intent, [self.group], self.findings,
                            self.render, self.find, toolkit_revision="b"*40)

    def test_exact_group_produces_review_packet_without_issue_impersonation(self):
        text, receipt = self.execute()
        self.assertIn("Reviewer judgment", text)
        self.assertEqual(receipt["finding_count"], 4)
        self.assertEqual(receipt["finding_ids"], INTENT["source_finding_ids"])
        self.assertFalse(receipt["toolkit_issue_number_substituted"])
        self.assertFalse(receipt["registry_case_owner_accepted"])
        self.assertFalse(receipt["toolkit_effectful_consumer_dispatched"])
        self.assertFalse(receipt["cutover_authorized"])
        self.assertIsNone(receipt["assurance_determination"])
        self.assertEqual(len(self.render_calls), 1)

    def test_missing_substituted_or_duplicated_evidence_is_rejected(self):
        bads = [
            lambda: self.findings.pop(),
            lambda: self.findings[0].update(repository="attacker/other"),
            lambda: self.findings.append(copy.deepcopy(self.findings[0])),
            lambda: self.group["source_observations"].pop(),
            lambda: self.group.update(observed_at="2026-11-18"),
            lambda: self.group["source_observations"][0].update(repository="wrong/other"),
            lambda: self.group.update(body="altered original source"),
            lambda: self.intent["source_finding_ids"].reverse(),
        ]
        for mutate in bads:
            with self.subTest(mutate=mutate):
                self.setUp()
                mutate()
                with self.assertRaises(packet.ReviewPacketError):
                    self.execute()
                self.assertEqual(self.render_calls, [])

    def test_no_foreign_worker_or_unstable_revision(self):
        for revision in ("main", "", "z"*40):
            with self.subTest(revision=revision), self.assertRaises(packet.ReviewPacketError):
                packet.build(self.intent, [self.group], self.findings,
                             self.render, self.find, toolkit_revision=revision)
        with self.assertRaisesRegex(packet.ReviewPacketError, "parsed foreign"):
            packet.build(self.intent, [self.group], self.findings,
                         self.render, lambda _: ["not-monitored"],
                         toolkit_revision="b"*40)
        self.assertFalse(self.render_calls)


if __name__ == "__main__":
    unittest.main()
