"""Persisted Registry #88 provenance, historical identity and non-assurance boundary."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
INTENT = json.loads((ROOT / "outbox/pending/spec-dependency-2026-11-16.json").read_text())


class TransferredCaseTests(unittest.TestCase):
    def test_exact_group_case_provenance_and_historical_owner(self):
        from sys import path
        path.insert(0, str(ROOT / "scripts"))
        import validate_cases
        self.assertEqual(validate_cases.validate(CASE), [])
        self.assertEqual(CASE["owners"]["handoff"], "accepted")
        self.assertEqual(CASE["owners"]["current_active_issue"],
                         "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/88")
        self.assertEqual(CASE["owners"]["historical_source_issue"],
                         INTENT["toolkit_current_issue_url"])
        self.assertEqual(CASE["owners"]["historical_wrapper_issue"],
                         INTENT["toolkit_historical_issue_url"])
        self.assertEqual(CASE["owners"]["protected_residual_issues"],
                         INTENT["protected_issue_urls"])
        self.assertEqual(CASE["source"]["revision"], INTENT["monitor_revision"])
        self.assertEqual(CASE["source"]["finding_ids"], INTENT["source_finding_ids"])
        self.assertEqual(CASE["source"]["group_sha256"], INTENT["source_group_sha256"])

    def test_administrative_transfer_is_not_an_assurance_success(self):
        self.assertEqual(CASE["assessment"]["determination"], "not_assessed")
        self.assertFalse(CASE["assessment"]["independent_review"])
        self.assertFalse(CASE["evidence"]["runtime_reproduced"])
        self.assertEqual(CASE["referrals"], [])
        self.assertEqual(CASE["assessment"]["change_classification"], "new")
        self.assertEqual({x["status"] for x in CASE["residuals"]}, {"open"})


if __name__ == "__main__":
    unittest.main()
