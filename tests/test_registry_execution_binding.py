import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_registry_execution as binding


class RegistryExecutionBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/network-answer-pilot.spec.json").read_text())
        cls.ledger = json.loads((ROOT / "ops/assessments/network-answer-pilot.ledger.json").read_text())

    def result(self):
        return {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:test-pinned-execution",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
            "terminal": True,
            "outcome": "INDETERMINATE",
            "reason_code": "evidence-required",
            "evidence": [],
            "residuals": [{"id": "r1", "summary": "Runtime evidence unavailable"}],
            "lineage": {"clean_room": True, "historical_inputs_used": False,
                        "run": copy.deepcopy(self.spec["run"])}
        }

    def bind(self, result=None, revision=binding.TOOLKIT_REVISION):
        return binding.create_binding(self.case, self.spec, self.ledger,
                                      self.result() if result is None else result,
                                      toolkit_revision=revision)

    def test_replay_deterministic(self):
        expected = self.bind()
        self.assertEqual(expected, self.bind())
        self.assertFalse(expected["case_determination_imported"])
        self.assertFalse(expected["external_specialist_authenticated"])
        self.assertFalse(expected["delivery_acknowledged"])
        self.assertFalse(expected["controller_cutover_qualified"])
        self.assertEqual(expected["result_outcome"], "INDETERMINATE")

    def test_verify_exact_replay(self):
        result = self.result()
        receipt = self.bind(result)
        self.assertEqual(receipt, binding.verify_binding(receipt, self.case, self.spec,
                                                         self.ledger, result,
                                                         toolkit_revision=binding.TOOLKIT_REVISION))

    def test_modified_result_invalidates_receipt(self):
        result = self.result()
        receipt = self.bind(result)
        result["residuals"][0]["summary"] = "Substituted conclusion"
        with self.assertRaisesRegex(binding.BindingError, "mismatches"):
            binding.verify_binding(receipt, self.case, self.spec, self.ledger, result,
                                   toolkit_revision=binding.TOOLKIT_REVISION)

    def test_forged_approval_flag_invalidates_receipt(self):
        result = self.result()
        receipt = self.bind(result)
        receipt["case_determination_imported"] = True
        with self.assertRaisesRegex(binding.BindingError, "mismatches"):
            binding.verify_binding(receipt, self.case, self.spec, self.ledger, result,
                                   toolkit_revision=binding.TOOLKIT_REVISION)

    def test_unknown_receipt_field_rejected(self):
        result = self.result()
        receipt = self.bind(result)
        receipt["specialist_pass"] = True
        with self.assertRaisesRegex(binding.BindingError, "fields"):
            binding.verify_binding(receipt, self.case, self.spec, self.ledger, result,
                                   toolkit_revision=binding.TOOLKIT_REVISION)

    def test_false_pass_not_bound(self):
        result = self.result()
        result["outcome"] = "PASS"
        with self.assertRaises(binding.BindingError):
            self.bind(result)

    def test_nonterminal_not_bound(self):
        result = self.result()
        result["terminal"] = False
        with self.assertRaisesRegex(binding.BindingError, "not terminal"):
            self.bind(result)

    def test_missing_execution_identity_rejected(self):
        result = self.result()
        result["assessment_id"] = ""
        with self.assertRaisesRegex(binding.BindingError, "assessment identity"):
            self.bind(result)

    def test_stale_engine_revision_rejected(self):
        with self.assertRaisesRegex(binding.BindingError, "qualified pin"):
            self.bind(revision="a"*40)

    def test_substituted_case_owner_rejected(self):
        case = copy.deepcopy(self.case)
        case["owners"]["current_active_issue"] = "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/5"
        with self.assertRaises(binding.BindingError):
            binding.create_binding(case, self.spec, self.ledger, self.result(),
                                   toolkit_revision=binding.TOOLKIT_REVISION)

    def test_substituted_source_revision_rejected(self):
        case = copy.deepcopy(self.case)
        case["source"]["revision"] = "b"*40
        with self.assertRaises(binding.BindingError):
            binding.create_binding(case, self.spec, self.ledger, self.result(),
                                   toolkit_revision=binding.TOOLKIT_REVISION)

    def test_lineage_must_be_clean_room_and_no_history(self):
        for changed in ({"clean_room": False}, {"historical_inputs_used": True}, {"historical_inputs_used": None}):
            with self.subTest(changed=changed):
                result = self.result()
                result["lineage"].update(changed)
                with self.assertRaises(binding.BindingError):
                    self.bind(result)


if __name__ == "__main__":
    unittest.main()
