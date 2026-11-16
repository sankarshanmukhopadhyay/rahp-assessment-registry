import sys
import unittest
from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_cases import validate, run


class CaseValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())

    def test_pilot_valid(self):
        self.assertEqual(validate(self.pilot), [])
        self.assertEqual(run(), [])

    def test_missing_source_pin_rejected(self):
        case = deepcopy(self.pilot)
        del case["source"]["revision"]
        self.assertIn("missing source pin", validate(case))

    def test_substantive_assurance_must_be_imported(self):
        case = deepcopy(self.pilot)
        case["assessment"]["determination"] = "INDETERMINATE"
        self.assertIn("RAHP determination requires matching attributable imported result reference", validate(case))

    def test_unverified_terminal_outcome_rejected(self):
        case = deepcopy(self.pilot)
        case["assessment"]["determination"] = "PASS"
        self.assertIn("RAHP determination requires matching attributable imported result reference", validate(case))
        self.assertIn("PASS requires verified evidence", validate(case))

    def test_invalid_field_type_fails_cleanly(self):
        case = deepcopy(self.pilot)
        case["source"] = "unexpected"
        self.assertIn("missing source pin", validate(case))

    def test_terminal_superseded_with_open_residual_rejected(self):
        case = deepcopy(self.pilot)
        case["owners"]["handoff"] = "accepted"
        case["lifecycle"]["state"] = "superseded"
        self.assertIn("terminal case cannot retain open residuals", validate(case))

    def test_false_pass_rejected(self):
        case = deepcopy(self.pilot)
        case["assessment"]["determination"] = "PASS"
        self.assertIn("PASS requires verified evidence", validate(case))

    def test_open_residual_cannot_be_closed(self):
        case = deepcopy(self.pilot)
        case["lifecycle"]["state"] = "closed"
        self.assertTrue(any("closed case" in e or "unaccepted" in e for e in validate(case)))

    def test_unaccepted_handoff_cannot_be_superseded(self):
        case = deepcopy(self.pilot)
        case["lifecycle"]["state"] = "superseded"
        self.assertIn("unaccepted handoff cannot be terminal", validate(case))


if __name__ == "__main__":
    unittest.main()
