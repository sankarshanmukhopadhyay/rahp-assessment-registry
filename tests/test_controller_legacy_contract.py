import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_controller_legacy_contract as preflight


class LegacyControllerIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(
            (ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text(encoding="utf-8")
        )

    def test_historical_pilot_has_no_dispatch_authority(self):
        result = preflight.historical_pilot(self.original)
        self.assertEqual(result["legacy_issue_number"], 1203)
        self.assertEqual(result["controller_anchor"], "historical_only")
        self.assertIsNone(result["active_execution_id"])
        self.assertFalse(result["eligible_for_dispatch"])

    def test_false_assurance_claim_fails_closed(self):
        case = copy.deepcopy(self.original)
        case["assessment"]["determination"] = "PASS"
        with self.assertRaisesRegex(preflight.PreflightError, "unsupported"):
            preflight.historical_pilot(case)

    def test_fake_imported_result_fails_closed(self):
        case = copy.deepcopy(self.original)
        case["assessment"]["imported_result"] = {"uri": "https://example.org/result"}
        with self.assertRaisesRegex(preflight.PreflightError, "unsupported"):
            preflight.historical_pilot(case)

    def test_changed_legacy_anchor_rejected(self):
        case = copy.deepcopy(self.original)
        case["owners"]["historical_source_issue"] = (
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/4"
        )
        with self.assertRaisesRegex(preflight.PreflightError, "historic"):
            preflight.historical_pilot(case)

    def test_case_number_is_not_controller_number(self):
        case = copy.deepcopy(self.original)
        case["owners"]["current_active_issue"] = (
            "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/1203"
        )
        with self.assertRaisesRegex(preflight.PreflightError, "ownership"):
            preflight.historical_pilot(case)

    def test_source_revision_and_finding_mismatch_rejected(self):
        for key, value in (("revision", "a" * 40), ("finding_id", "foreign-finding")):
            with self.subTest(key=key):
                case = copy.deepcopy(self.original)
                case["source"][key] = value
                with self.assertRaisesRegex(preflight.PreflightError, "source revision"):
                    preflight.historical_pilot(case)

    def test_new_specialist_return_requires_requalification(self):
        case = copy.deepcopy(self.original)
        case["referrals"] = [{"status": "returned"}]
        with self.assertRaisesRegex(preflight.PreflightError, "referrals"):
            preflight.historical_pilot(case)

    def test_malformed_case_rejected(self):
        for value in (None, [], {}, {"owners": 1}):
            with self.subTest(value=value), self.assertRaises(preflight.PreflightError):
                preflight.historical_pilot(value)


if __name__ == "__main__":
    unittest.main()
