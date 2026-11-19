"""Actual accepted DTG #88 cannot inherit an unrelated DPIP disposition."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_specialist_return as specialist
import registry_dpip_live_reconcile as live
import registry_group_epoch_observation as epochs

CASE = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
MATERIALITY = json.loads((ROOT / "ops/assessments/dtg-spec-dependency-source-materiality-2026-11.json").read_text())


class RegistryDTGSpecialistBoundaryTests(unittest.TestCase):
    def test_actual_case_refuses_unadmitted_historical_or_foreign_specialist(self):
        self.assertEqual(CASE["case_id"], "RAHP-AR-DTG-0002")
        self.assertEqual(CASE["referrals"], [])
        for issue_number in (1, 304, 305, 307):
            with self.subTest(issue_number=issue_number):
                with self.assertRaisesRegex(
                        specialist.SpecialistAdmissionError, "no unique admitted"):
                    specialist.admitted_referral(CASE, {"number": issue_number})

    def test_live_adapter_fails_before_reading_unapproved_dpip_issue(self):
        fetch_calls = []
        def forbid_fetch(url):
            fetch_calls.append(url)
            raise AssertionError("unadmitted referral must never hit GitHub")
        with self.assertRaisesRegex(specialist.SpecialistAdmissionError,
                                    "no unique admitted"):
            live.verify_live(CASE, 304, consumer=None, assessor_contract=None,
                             fetch=forbid_fetch)
        self.assertEqual(fetch_calls, [])

    def test_source_level_new_does_not_import_a_specialist_or_controller_result(self):
        self.assertEqual(CASE["assessment"]["change_classification"], "new")
        self.assertEqual(CASE["assessment"]["determination"], "not_assessed")
        self.assertFalse(CASE["assessment"]["independent_review"])
        self.assertEqual(CASE["referrals"], [])
        self.assertFalse(MATERIALITY["specialist_screening"]["dpip_referral_admitted"])
        self.assertFalse(MATERIALITY["disposal"]["assurance_outcome_imported"])
        self.assertFalse(MATERIALITY["recovery"]["reverse_transfer_exercised"])
        self.assertEqual(CASE["reassessment"]["latest_observed_epoch"]["review_state"],
                         "source_review_completed_runtime_evidence_required")

    def test_epoch_approval_has_exact_digest_and_missing_is_not_success(self):
        epoch = MATERIALITY["later_epoch"]
        digest = epoch["source_group_sha256"]
        history = [{
            "id": 7000523334,
            "user": {"login": "sankarshanmukhopadhyay", "type": "User"},
            "author_association": "OWNER",
            "body": "<!-- rahp-registry-epoch-scope:v1:accept:" + digest + " -->",
        }]
        self.assertTrue(epochs.epoch_scope_decision(history, digest))
        self.assertFalse(epochs.epoch_scope_decision(history, "0"*64))
        rejected = copy.deepcopy(history)
        rejected[0]["user"]["login"] = "unrelated-user"
        with self.assertRaisesRegex(epochs.EpochError, "unauthorized"):
            epochs.epoch_scope_decision(rejected, digest)
        withdrawn = copy.deepcopy(history)
        withdrawn.append({
            "id": 7000523335,
            "user": {"login": "sankarshanmukhopadhyay"},
            "author_association": "OWNER",
            "body": "<!-- rahp-registry-epoch-scope:v1:withdraw:" + digest + " -->",
        })
        self.assertFalse(epochs.epoch_scope_decision(withdrawn, digest))


if __name__ == "__main__":
    unittest.main()
