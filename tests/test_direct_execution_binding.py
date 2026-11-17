import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_direct_execution as binding
from validate_cases import validate


class DirectExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/ondtf/emergency-authority-v1.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/ondtf-emergency-authority.spec.json").read_text())
        cls.ledger = json.loads((ROOT / "ops/assessments/ondtf-emergency-authority.ledger.json").read_text())

    def result(self):
        return {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:test-ondtf-canonical",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED", "terminal": True,
            "outcome": "INDETERMINATE", "reason_code": "evidence-required",
            "evidence": [], "residuals": [{"id": "r1", "summary": "No native evidence"}],
            "lineage": {"clean_room": True, "historical_inputs_used": False,
                        "run": copy.deepcopy(self.spec["run"])},
        }

    def make(self, case=None, spec=None, ledger=None, result=None):
        return binding.create_binding(
            self.case if case is None else case,
            self.spec if spec is None else spec,
            self.ledger if ledger is None else ledger,
            self.result() if result is None else result,
            toolkit_revision=binding.TOOLKIT_REVISION)

    def test_direct_case_valid_without_historical_toolkit_issue(self):
        self.assertEqual(validate(self.case), [])
        receipt = self.make()
        self.assertIsNone(receipt["historical_toolkit_issue_number"])
        self.assertFalse(receipt["controller_cutover_qualified"])
        self.assertFalse(receipt["case_determination_imported"])
        self.assertEqual(receipt, self.make())
        self.assertEqual(receipt, binding.verify_binding(
            receipt, self.case, self.spec, self.ledger, self.result(),
            toolkit_revision=binding.TOOLKIT_REVISION))

    def test_negative_foreign_controller_legacy_anchor(self):
        case = copy.deepcopy(self.case)
        case["owners"]["historical_source_issue"] = (
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/19")
        with self.assertRaisesRegex(binding.DirectBindingError, "historical"):
            self.make(case=case)

    def test_wrong_source_epoch_and_correlated_result_rejected(self):
        bad = [
            ("target", lambda x: x["target"].update(revision="a"*40)),
            ("subject", lambda x: x["subject"].update(id="other-case")),
        ]
        for name, change in bad:
            spec = copy.deepcopy(self.spec)
            change(spec)
            with self.subTest(name=name), self.assertRaises(binding.DirectBindingError):
                self.make(spec=spec)
        for key, value in (
            ("outcome", "PASS"), ("reason_code", "verified"),
            ("correlation_key", "other-epoch"),
            ("assessment_id", ""),
            ("evidence", [{"claimed": "fake"}]),
            ("source_pins", [{"repository": "other/other", "revision": "a"*40}]),
        ):
            result = self.result()
            result[key] = value
            with self.subTest(key=key), self.assertRaises(binding.DirectBindingError):
                self.make(result=result)

    def test_no_unattributed_specialist_or_false_evidence(self):
        case = copy.deepcopy(self.case)
        case["referrals"] = [{"status": "returned"}]
        with self.assertRaises(binding.DirectBindingError):
            self.make(case=case)
        ledger = {"requirements": [{"id": "ONDTF-0001-R1", "result": "PASS"}]}
        with self.assertRaises(binding.DirectBindingError):
            self.make(ledger=ledger)
        case = copy.deepcopy(self.case)
        case["assessment"]["determination"] = "PASS"
        with self.assertRaises(binding.DirectBindingError):
            self.make(case=case)

    def test_forged_receipt_rejected(self):
        receipt = self.make()
        receipt["controller_cutover_qualified"] = True
        with self.assertRaisesRegex(binding.DirectBindingError, "differs"):
            binding.verify_binding(receipt, self.case, self.spec, self.ledger,
                                   self.result(), toolkit_revision=binding.TOOLKIT_REVISION)


if __name__ == "__main__":
    unittest.main()
