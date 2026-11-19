import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_transferred_execution as binding


class TransferredBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
        cls.spec = json.loads((ROOT / "ops/assessments/dtg-spec-dependency-transferred.spec.json").read_text())
        cls.evidence = {"requirements": []}
        src = cls.case["source"]
        cls.transfer = {"schema": "rahp-registry-transfers/v1", "transfers": [{
            "state": "accepted_group",
            "assessment_key": binding.KEY,
            "toolkit_issue_url": binding.TK_ISSUE,
            "registry_issue_url": binding.REG_ISSUE,
            "monitor_revision": src["revision"],
            "snapshot_date": src["observed_on"],
            "group_sha256": src["group_sha256"],
            "finding_ids": copy.deepcopy(src["finding_ids"]),
            "maintainer_scope_sha256": binding.SCOPE_SHA256
        }]}

    def result(self):
        return {
            "schema": "rahp-assurance-run-state/v1",
            "assessment_id": "rahp:source-88-test",
            "correlation_key": self.spec["run"]["lineage_prefix"],
            "subject": copy.deepcopy(self.spec["subject"]),
            "source_pins": [copy.deepcopy(self.spec["target"])],
            "terminal": True, "outcome": "INDETERMINATE",
            "reason_code": "evidence-required",
            "state": "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED",
            "evidence": [], "residuals": [{"id": "missing-1"}],
            "lineage": {"clean_room": True, "historical_inputs_used": False,
                        "run": copy.deepcopy(self.spec["run"])}
        }

    def make(self, *, case=None, transfer=None, spec=None, evidence=None, result=None):
        return binding.bind(
            self.case if case is None else case,
            self.transfer if transfer is None else transfer,
            self.spec if spec is None else spec,
            self.evidence if evidence is None else evidence,
            self.result() if result is None else result,
            engine_revision=binding.ENGINE_REVISION,
            transfer_ledger_revision="b" * 40
        )

    def test_accepted_source_produces_non_authorizing_binding(self):
        receipt = self.make()
        self.assertEqual(receipt["registry_case_url"], binding.REG_ISSUE)
        self.assertEqual(receipt["historical_toolkit_issue_url"], binding.TK_ISSUE)
        self.assertEqual(receipt["source_finding_ids"], self.case["source"]["finding_ids"])
        self.assertEqual(receipt["result_outcome"], "INDETERMINATE")
        self.assertTrue(all(value is False for name, value in receipt.items()
                            if name in ("case_determination_imported",
                                        "source_transfer_authority_extended",
                                        "registry_to_toolkit_dispatch_authorized",
                                        "specialist_return_authenticated",
                                        "controller_cutover_qualified")))
        self.assertEqual(receipt, self.make())

    def test_bad_transfer_state_owner_and_group_refused(self):
        for key, value in (("state", "reserved_group"),
                           ("registry_issue_url", binding.REG_ISSUE.replace("/88", "/272")),
                           ("group_sha256", "c" * 64),
                           ("monitor_revision", "c" * 40)):
            transfer = copy.deepcopy(self.transfer)
            transfer["transfers"][0][key] = value
            with self.subTest(key=key), self.assertRaises(binding.TransferBindingError):
                self.make(transfer=transfer)

    def test_numeric_namespace_substitution_refused(self):
        for field, value in (("current_active_issue", binding.TK_ISSUE),
                             ("historical_source_issue", binding.REG_ISSUE),
                             ("execution", binding.REGISTRY),
                             ("handoff", "reserved")):
            case = copy.deepcopy(self.case)
            case["owners"][field] = value
            with self.subTest(field=field), self.assertRaises(binding.TransferBindingError):
                self.make(case=case)

    def test_source_epoch_or_case_membership_drift_refused(self):
        for key, value in (("revision", "a" * 40),
                           ("group_sha256", "d" * 64),
                           ("observed_on", "2026-11-18"),
                           ("finding_ids", self.case["source"]["finding_ids"][:2])):
            case = copy.deepcopy(self.case)
            case["source"][key] = value
            with self.subTest(key=key), self.assertRaises(binding.TransferBindingError):
                self.make(case=case)

    def test_false_success_specialist_and_evidence_refused(self):
        for field, value in (("outcome", "PASS"), ("reason_code", "verified"),
                             ("evidence", [{"faked": True}]),
                             ("correlation_key", "different"),
                             ("source_pins", [{"repository": "x/y", "revision": "a"*40}]),
                             ("terminal", False)):
            result = self.result()
            result[field] = value
            with self.subTest(field=field), self.assertRaises(binding.TransferBindingError):
                self.make(result=result)
        case = copy.deepcopy(self.case)
        case["referrals"] = [{"status": "returned"}]
        with self.assertRaises(binding.TransferBindingError):
            self.make(case=case)
        with self.assertRaises(binding.TransferBindingError):
            self.make(evidence={"requirements": [{"claim": "PASS"}]})

    def test_coordinated_case_and_transfer_substitution_refused(self):
        case = copy.deepcopy(self.case)
        transfer = copy.deepcopy(self.transfer)
        case["source"]["group_sha256"] = "d" * 64
        transfer["transfers"][0]["group_sha256"] = "d" * 64
        spec = copy.deepcopy(self.spec)
        spec["run"]["lineage_prefix"] = "registry:" + binding.CASE_ID + ":" + "d" * 64
        result = self.result()
        result["correlation_key"] = spec["run"]["lineage_prefix"]
        result["lineage"]["run"] = copy.deepcopy(spec["run"])
        with self.assertRaises(binding.TransferBindingError):
            self.make(case=case, transfer=transfer, spec=spec, result=result)
        case = copy.deepcopy(self.case)
        spec = copy.deepcopy(self.spec)
        case["source"]["repository"] = "attacker/monitor"
        spec["target"]["repository"] = "attacker/monitor"
        result = self.result()
        result["source_pins"] = [copy.deepcopy(spec["target"])]
        with self.assertRaises(binding.TransferBindingError):
            self.make(case=case, spec=spec, result=result)

    def test_direct_case_is_not_silently_accepted(self):
        case = copy.deepcopy(self.case)
        case["owners"]["handoff"] = "not_applicable"
        with self.assertRaises(binding.TransferBindingError):
            self.make(case=case)

    def test_assessment_identity_and_required_evidence_mismatch_refused(self):
        spec = copy.deepcopy(self.spec)
        spec["subject"]["id"] = "RAHP-AR-DTG-0001"
        with self.assertRaises(binding.TransferBindingError):
            self.make(spec=spec)
        spec = copy.deepcopy(self.spec)
        spec["assurance_contract"]["required_evidence"] = ["DTG-0002-R1"]
        with self.assertRaises(binding.TransferBindingError):
            self.make(spec=spec)
        result = self.result()
        result["lineage"]["historical_inputs_used"] = True
        with self.assertRaises(binding.TransferBindingError):
            self.make(result=result)


if __name__ == "__main__":
    unittest.main()
