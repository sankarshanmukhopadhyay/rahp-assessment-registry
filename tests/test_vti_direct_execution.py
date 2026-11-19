"""The VTI direct Registry case is runnable but cannot import an invented PASS."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_direct_execution as binding
from validate_cases import validate

CASE = json.loads((ROOT / "cases/dtg/vti-session-refusal-2026-11.json").read_text())
SPEC = json.loads((ROOT / "ops/assessments/vti-session-refusal.spec.json").read_text())
LEDGER = json.loads((ROOT / "ops/assessments/vti-session-refusal.ledger.json").read_text())


def canonical_negative_result():
    return {
        "schema": "rahp-assurance-run-state/v1",
        "assessment_id": "rahp:vti-refusal-evidence-required",
        "correlation_key": SPEC["run"]["lineage_prefix"],
        "subject": copy.deepcopy(SPEC["subject"]),
        "source_pins": [copy.deepcopy(SPEC["target"])],
        "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
        "terminal": True,
        "outcome": "INDETERMINATE",
        "reason_code": "evidence-required",
        "evidence": [],
        "residuals": [{"id": "unmet", "summary": "source is not operational evidence"}],
        "lineage": {"clean_room": True, "historical_inputs_used": False,
                    "run": copy.deepcopy(SPEC["run"])},
    }


class VTIDirectExecutionTests(unittest.TestCase):
    def bind(self, case=None, spec=None, ledger=None, result=None):
        return binding.create_binding(
            CASE if case is None else case,
            SPEC if spec is None else spec,
            LEDGER if ledger is None else ledger,
            canonical_negative_result() if result is None else result,
            toolkit_revision=binding.TOOLKIT_REVISION)

    def test_real_case_contract_and_source_pin(self):
        self.assertEqual(validate(CASE), [])
        self.assertEqual(CASE["owners"]["current_active_issue"],
                         "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/79")
        self.assertEqual(CASE["owners"]["admission"], "direct")
        self.assertNotIn("historical_source_issue", CASE["owners"])
        self.assertEqual(set(SPEC["assurance_contract"]["required_evidence"]),
                         {r["id"] for r in CASE["residuals"]})
        self.assertEqual(SPEC["target"]["revision"], CASE["source"]["revision"])
        self.assertEqual(LEDGER, {"requirements": []})
        receipt = self.bind()
        self.assertEqual(receipt["result_outcome"], "INDETERMINATE")
        self.assertFalse(receipt["case_determination_imported"])
        self.assertFalse(receipt["controller_cutover_qualified"])
        self.assertIsNone(receipt["historical_toolkit_issue_number"])

    def test_false_success_and_foreign_identity_fail_closed(self):
        for key, value in (
            ("outcome", "PASS"),
            ("reason_code", "verified"),
            ("correlation_key", "registry:another-case"),
            ("evidence", [{"type": "synthetic-PASS"}]),
            ("source_pins", [{"repository": "other/repo", "revision": "a" * 40}]),
        ):
            result = canonical_negative_result()
            result[key] = value
            with self.subTest(key=key), self.assertRaises(binding.DirectBindingError):
                self.bind(result=result)

    def test_wrong_case_or_unsupported_referral_fails(self):
        case = copy.deepcopy(CASE)
        case["owners"]["current_active_issue"] = "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/79"
        with self.assertRaises(binding.DirectBindingError):
            self.bind(case=case)
        case = copy.deepcopy(CASE)
        case["referrals"] = [{"status": "accepted"}]
        with self.assertRaises(binding.DirectBindingError):
            self.bind(case=case)
        case = copy.deepcopy(CASE)
        case["assessment"]["determination"] = "PASS"
        with self.assertRaises(binding.DirectBindingError):
            self.bind(case=case)
        with self.assertRaises(binding.DirectBindingError):
            self.bind(ledger={"requirements": [{"id": "VTI-0001-R1", "outcome": "PASS"}]})


if __name__ == "__main__":
    unittest.main()
