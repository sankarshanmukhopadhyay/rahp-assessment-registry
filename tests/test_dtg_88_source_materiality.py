"""Prevent source-level materiality from being mistaken for RAHP assurance."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_cases
import registry_group_epoch_observation as epoch

CASE = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
REVIEW = json.loads((ROOT / "ops/assessments/dtg-spec-dependency-source-materiality-2026-11.json").read_text())
ORIGINAL = json.loads((ROOT / "outbox/pending/spec-dependency-2026-11-16.json").read_text())
EXPECTED_NEW_EPOCH = "ab73e10204e4f6073977634ea98015e8a1cb03cc5142e54e1afef5ce0e91bf85"


class DTGSourceMaterialityTests(unittest.TestCase):
    def test_original_pins_and_four_dispositions_are_exact(self):
        self.assertEqual(validate_cases.validate(CASE), [])
        self.assertEqual(REVIEW["case_id"], CASE["case_id"])
        self.assertEqual(REVIEW["assessment_key"], ORIGINAL["assessment_key"])
        self.assertEqual(REVIEW["original_epoch"]["source_group_sha256"],
                         ORIGINAL["source_group_sha256"])
        self.assertEqual(REVIEW["original_epoch"]["monitor_revision"],
                         ORIGINAL["monitor_revision"])
        original_ids = ORIGINAL["source_finding_ids"]
        self.assertEqual(REVIEW["original_epoch"]["finding_ids"], original_ids)
        self.assertEqual(sorted(x["finding_id"] for x in REVIEW["source_findings"]), original_ids)
        self.assertEqual({x["classification"] for x in REVIEW["source_findings"]},
                         {"new", "weakened", "strengthened"})
        self.assertEqual(CASE["assessment"]["change_classification"], "new")
        self.assertEqual(REVIEW["group_source_level_disposition"], "new")

    def test_second_epoch_is_a_subset_and_has_exact_observed_digest(self):
        newer = REVIEW["later_epoch"]
        self.assertEqual(newer["source_group_sha256"], EXPECTED_NEW_EPOCH)
        self.assertEqual(CASE["reassessment"]["latest_observed_epoch"]["group_sha256"],
                         EXPECTED_NEW_EPOCH)
        self.assertEqual(newer["finding_ids"],
                         ["29e39a0329123d8839a6", "acc9772126b1a3820240"])
        self.assertTrue(set(newer["finding_ids"]).issubset(
            set(REVIEW["original_epoch"]["finding_ids"])))
        self.assertLess(len(newer["finding_ids"]), len(REVIEW["original_epoch"]["finding_ids"]))
        self.assertFalse(newer["contains_new_finding_ids"])
        self.assertFalse(CASE["reassessment"]["latest_observed_epoch"]["source_novelty"])
        self.assertIn("#issuecomment-7000523334", newer["scope_decision_url"])
        self.assertIn("#issuecomment-7000532885", newer["acknowledgment_url"])
        self.assertEqual(newer["observed_producer_mode"], "changed_group_acknowledged_retained")

    def test_substantive_source_judgment_never_imports_unsupported_assurance(self):
        self.assertEqual(CASE["assessment"]["determination"], "not_assessed")
        self.assertFalse(CASE["assessment"]["independent_review"])
        self.assertFalse(CASE["evidence"]["runtime_reproduced"])
        self.assertEqual(REVIEW["group_assurance_determination"], "not_assessed")
        self.assertFalse(REVIEW["runtime_consumer_tests_executed"])
        self.assertFalse(REVIEW["disposal"]["assurance_outcome_imported"])
        self.assertFalse(REVIEW["disposal"]["case_terminal"])
        self.assertEqual(CASE["lifecycle"]["state"], "active")
        self.assertEqual(CASE["referrals"], [])
        self.assertFalse(REVIEW["specialist_screening"]["dpip_referral_admitted"])
        self.assertFalse(REVIEW["recovery"]["reverse_transfer_exercised"])

    def test_release_pin_and_separate_residual_owners_are_preserved(self):
        by_id = {x["finding_id"]: x for x in REVIEW["source_findings"]}
        self.assertEqual(by_id["29e39a0329123d8839a6"]["source_revision"],
                         "9397295d183d642c2fd6669822bd895f892bbd38")
        for fid in ("0add1f4cc0f048ce6bfc", "a60eaffaf3cbc1394553",
                    "acc9772126b1a3820240"):
            self.assertRegex(by_id[fid]["source_tag_object"], "^[0-9a-f]{40}$")
        self.assertEqual(REVIEW["specialist_screening"]["source_owner"],
                         "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1194")
        self.assertEqual(CASE["owners"]["protected_residual_issues"],
                         ORIGINAL["protected_issue_urls"])
        self.assertTrue(all(x["status"] == "open" for x in CASE["residuals"]))

    def test_spoofed_post_cutover_scope_is_not_acceptance(self):
        digest = REVIEW["later_epoch"]["source_group_sha256"]
        forged = [{"id": 8, "body": "<!-- rahp-registry-epoch-scope:v1:accept:" +
                   digest + " -->", "author_association": "OWNER",
                   "user": {"login": "attacker"}}]
        with self.assertRaisesRegex(epoch.EpochError, "unauthorized"):
            epoch.epoch_scope_decision(forged, digest)
        self.assertFalse(epoch.epoch_scope_decision([], digest))


if __name__ == "__main__":
    unittest.main()
