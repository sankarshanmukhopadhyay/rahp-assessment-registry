import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops/dtg"))
from dtg_portfolio_routing import combined_event, combined_source_evidence

SHA = "b"*40


class RegistryRouterSourceTests(unittest.TestCase):
    def event(self, fid, urls):
        return {"finding": {"finding_id": fid,
                            "repository": "OpenVTC/verifiable-trust-infrastructure",
                            "title": fid, "evidence_urls": urls}}

    def test_commit_only_pins_and_unresolved_group_remainder(self):
        rows = [self.event("commit-observed", [
            "https://github.com/OpenVTC/verifiable-trust-infrastructure/commit/" + SHA]),
                self.event("release-only", [
            "https://github.com/OpenVTC/verifiable-trust-infrastructure/releases/tag/v1"])]
        event = combined_event("data-room-custody-lifecycle", rows, "2026-11-16")
        self.assertEqual(event["assessment_key"],
                         "dtg:portfolio:combined:data-room-custody-lifecycle")
        self.assertEqual(event["unanchored_finding_ids"], ["release-only"])
        self.assertEqual(event["source_pins"], [{"repository":
            "OpenVTC/verifiable-trust-infrastructure", "revision": SHA}])
        self.assertNotIn("transfer_authorized", event)

    def test_order_independence_and_no_foreign_source_pinning(self):
        rows = [self.event("b", []), self.event("a", [
            "https://github.com/other/repo/commit/" + SHA])]
        self.assertEqual(combined_source_evidence(rows),
                         combined_source_evidence(list(reversed(rows))))
        self.assertEqual(combined_source_evidence(rows)["source_pins"], [])

    def test_malformed_and_duplicate_findings_refused(self):
        rows = [self.event("x", []), self.event("x", [])]
        with self.assertRaises(ValueError):
            combined_source_evidence(rows)
        bad = self.event("id", ["valid", None])
        with self.assertRaises(ValueError):
            combined_source_evidence([bad])


if __name__ == "__main__":
    unittest.main()
