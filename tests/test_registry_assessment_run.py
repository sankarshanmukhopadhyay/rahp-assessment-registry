import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_registry_assessment_run as q


class CanonicalRunQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/network-answer-pilot.spec.json").read_text())
        cls.ledger = json.loads((ROOT / "ops/assessments/network-answer-pilot.ledger.json").read_text())

    def sample(self):
        return {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:example",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "outcome": "INDETERMINATE",
            "reason_code": "evidence-required",
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
            "evidence": [],
            "residuals": [{"summary": "Required evidence unavailable."}]
        }

    def test_absent_evidence_remains_indeterminate(self):
        receipt = q.check(self.case, self.spec, self.ledger, self.sample())
        self.assertEqual(receipt["result_outcome"], "INDETERMINATE")
        self.assertFalse(receipt["registry_assessment_imported"])
        self.assertFalse(receipt["controller_cutover_qualified"])

    def test_false_pass_is_rejected(self):
        result = self.sample()
        result["outcome"] = "PASS"
        with self.assertRaisesRegex(q.QualificationError, "INDETERMINATE"):
            q.check(self.case, self.spec, self.ledger, result)

    def test_wrong_revision_is_rejected(self):
        result = self.sample()
        result["source_pins"][0]["revision"] = "f" * 40
        with self.assertRaisesRegex(q.QualificationError, "pins"):
            q.check(self.case, self.spec, self.ledger, result)

    def test_foreign_subject_is_rejected(self):
        result = self.sample()
        result["subject"] = {"type": "network-response-consumer", "id": "other"}
        with self.assertRaisesRegex(q.QualificationError, "subject"):
            q.check(self.case, self.spec, self.ledger, result)

    def test_discovered_evidence_without_ledger_is_rejected(self):
        result = self.sample()
        result["evidence"] = [{"claim": "verified"}]
        with self.assertRaisesRegex(q.QualificationError, "contradiction"):
            q.check(self.case, self.spec, self.ledger, result)

    def test_changed_residual_contract_is_rejected(self):
        spec = copy.deepcopy(self.spec)
        spec["assurance_contract"]["required_evidence"] = ["DTG-0001-R1"]
        with self.assertRaisesRegex(q.QualificationError, "required evidence"):
            q.check(self.case, spec, self.ledger, self.sample())

    def test_fake_imported_result_is_rejected(self):
        case = copy.deepcopy(self.case)
        case["assessment"]["determination"] = "PASS"
        with self.assertRaisesRegex(q.QualificationError, "silently"):
            q.check(case, self.spec, self.ledger, self.sample())

    def test_nonempty_ledger_requires_requalification(self):
        ledger = {"requirements": [{"requirement_id": "DTG-0001-R1"}]}
        with self.assertRaisesRegex(q.QualificationError, "unexpectedly"):
            q.check(self.case, self.spec, ledger, self.sample())


if __name__ == "__main__":
    unittest.main()
