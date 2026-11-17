import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_cases", ROOT / "scripts/validate_cases.py")
validate_cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_cases)


class CaseSuccessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = json.loads(
            (ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text()
        )

    def test_actual_pilot_has_accepted_but_non_assurance_succession(self):
        self.assertEqual(validate_cases.validate(self.pilot), [])
        self.assertEqual(self.pilot["owners"]["handoff"], "accepted")
        self.assertEqual(self.pilot["assessment"]["determination"], "not_assessed")
        self.assertIn("/rahp-toolkit/issues/1203",
                      self.pilot["owners"]["historical_source_issue"])

    def test_wrong_historical_repository_fails(self):
        case = copy.deepcopy(self.pilot)
        case["owners"]["historical_source_issue"] = (
            "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/1203"
        )
        self.assertIn("accepted handoff requires canonical Toolkit historical issue URL",
                      validate_cases.validate(case))

    def test_missing_historical_url_fails(self):
        case = copy.deepcopy(self.pilot)
        case["owners"].pop("historical_source_issue")
        self.assertIn("accepted handoff requires canonical Toolkit historical issue URL",
                      validate_cases.validate(case))

    def test_external_successor_is_not_accepted(self):
        case = copy.deepcopy(self.pilot)
        case["owners"]["current_active_issue"] = "https://github.com/other/other/issues/4"
        self.assertIn("accepted handoff requires canonical Registry successor issue URL",
                      validate_cases.validate(case))

    def test_engine_authority_cannot_be_conflated_with_coordination(self):
        case = copy.deepcopy(self.pilot)
        case["owners"]["execution"] = case["owners"]["registry"]
        self.assertIn("accepted coordination handoff must not imply RAHP engine transfer",
                      validate_cases.validate(case))

    def test_unsupported_pass_rejected(self):
        case = copy.deepcopy(self.pilot)
        case["assessment"]["determination"] = "PASS"
        self.assertIn("accepted handoff cannot invent assurance outcome",
                      validate_cases.validate(case))

    def test_two_cases_cannot_claim_same_successor_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = copy.deepcopy(self.pilot)
            second = copy.deepcopy(self.pilot)
            second["case_id"] = "RAHP-AR-DTG-0002"
            second["source"]["finding_id"] = "other-finding"
            Path(tmp, "first.json").write_text(json.dumps(first))
            Path(tmp, "second.json").write_text(json.dumps(second))
            self.assertTrue(any("multiple accepted case records" in err
                                for err in validate_cases.run(Path(tmp))))

    def test_no_unconditional_historical_copy_required(self):
        case = copy.deepcopy(self.pilot)
        case.pop("historical_issue_body", None)
        case.pop("historical_comments", None)
        self.assertEqual(validate_cases.validate(case), [])


if __name__ == "__main__":
    unittest.main()
