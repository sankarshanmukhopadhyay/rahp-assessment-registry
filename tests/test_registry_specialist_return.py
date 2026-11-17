import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_specialist_return as bridge
from verify_dpip_legacy_consumer import ConsumerError

DPIP = bridge.DPIP_REPO
PIN = ("OpenVTC/verifiable-trust-infrastructure", "303174f8ca630ca14ddc2cbf5abcb0d10e205c38")


def portable():
    return {
        "schema": "rahp-assessor-result/v1", "assessor": "dpip",
        "assessment_id": "dpip:305", "outcome": "INDETERMINATE",
        "reason_code": "evidence-required", "evidence_used": [],
        "residual_risk": "Insufficient observed evidence.",
        "action_required": "Run target-native countercases.",
        "source_pins": [{"repository": PIN[0], "revision": PIN[1]}],
        "provenance": {"execution_digest": "run1", "setup_digest": "setup1"},
    }


class FakeConsumer:
    def __init__(self):
        self.producer = portable()
        self.returned = copy.deepcopy(self.producer)
        self.conclusion = "INDETERMINATE"
        self.src = {
            "system": "RAHP", "repository": bridge.REGISTRY, "issue": 4,
            "changed_artifact": {"repository": PIN[0], "revision": PIN[1]},
            "source_pins": [{"repository": PIN[0], "revision": PIN[1]}],
            "identities": {"examination_key": "abc123", "referral_id": "rahp-referral:xyz"},
        }

    def yaml_blocks(self, body):
        if "SOURCE-PAYLOAD" in body:
            return [{"source": self.src}]
        if "RETURN-PAYLOAD" in body:
            return [{"dpip_disposition": {
                "conclusion": self.conclusion, "assessor_result": self.returned,
            }}]
        if "EXAMINATION-PAYLOAD" in body:
            return [{"dpip_examination": {"assessor_result": self.producer}}]
        if "EXTRA-SOURCE" in body:
            return [{"source_referral": self.src}]
        return []


class RealContractStub:
    @staticmethod
    def validate_result(value):
        required = ("schema", "assessor", "assessment_id", "outcome", "reason_code",
                    "evidence_used", "residual_risk", "action_required")
        return [f"{k} missing" for k in required
                if k not in value or (k != "evidence_used" and not value.get(k))]


def fixtures():
    case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
    case["referrals"] = [{
        "role": "specialist_assessor", "repository": DPIP,
        "contract": "rahp-assessor-result/v1",
        "issue_url": f"https://github.com/{DPIP}/issues/305",
        "status": "accepted",
    }]
    issue = {
        "number": 4, "state": "open",
        "body": f"<!-- rahp-registry-case:{case['case_id']} -->\n{PIN[0]}\n{PIN[1]}",
    }
    source = [{
        "body": f"<!-- dpip-return:{DPIP}#305 -->\nRETURN-PAYLOAD"
    }]
    digest = hashlib.sha256(source[0]["body"].encode()).hexdigest()[:20]
    dpip = {
        "number": 305, "state": "closed", "body": "SOURCE-PAYLOAD",
        "labels": [{"name": "source:rahp"}, {"name": "run:complete"}],
    }
    comments = [
        {"body": "<!-- dpip-examination:305:exam1 -->\nEXAMINATION-PAYLOAD"},
        {"body": "<!-- dpip-execution-evidence:305:run1 -->"},
        {"body": "<!-- dpip-examination-setup:305:setup1 -->"},
        {"body": f"<!-- rahp-return-outbox:v1:305:{digest} -->"},
        {"body": f"<!-- rahp-return-ack:v2:305:{digest}:dest -->\n"
                 "- destination: `sankarshanmukhopadhyay/rahp-assessment-registry#4`"},
    ]
    return case, issue, source, dpip, comments, FakeConsumer()


class RegistryDPIPAdmissionTests(unittest.TestCase):
    def admit(self, data=None):
        case, issue, source, dpip, comments, consumer = data or fixtures()
        return bridge.qualify(case, issue, source, dpip, comments, consumer, RealContractStub)

    def test_explicit_source_and_real_chain_structure_qualifies_without_import(self):
        receipt = self.admit()
        self.assertEqual(receipt["dpip_outcome_observed"], "INDETERMINATE")
        self.assertFalse(receipt["return_transport_authenticated"])
        self.assertFalse(receipt["case_determination_imported"])
        self.assertFalse(receipt["controller_reconciliation_executed"])

    def test_actual_registry_pilot_has_no_specialist_admission(self):
        case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
        _, issue, source, dpip, comments, consumer = fixtures()
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no unique admitted"):
            bridge.qualify(case, issue, source, dpip, comments, consumer, RealContractStub)

    def test_requested_is_not_accepted(self):
        d = fixtures()
        d[0]["referrals"][0]["status"] = "requested"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "not admitted"):
            self.admit(d)

    def test_duplicate_referrals_fail_closed(self):
        d = fixtures()
        d[0]["referrals"].append(copy.deepcopy(d[0]["referrals"][0]))
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no unique"):
            self.admit(d)

    def test_wrong_specialist_issue_is_not_admitted(self):
        d = fixtures()
        d[0]["referrals"][0]["issue_url"] = f"https://github.com/{DPIP}/issues/304"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no unique"):
            self.admit(d)

    def test_cross_repo_referral_not_admitted(self):
        d = fixtures()
        d[0]["referrals"][0]["repository"] = "attacker/forged"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no unique"):
            self.admit(d)

    def test_prior_case_determination_is_not_silently_overwritten(self):
        d = fixtures()
        d[0]["assessment"]["determination"] = "PASS"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "already has"):
            self.admit(d)

    def test_closed_case_source_rejected(self):
        d = fixtures()
        d[1]["state"] = "closed"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "current/open"):
            self.admit(d)

    def test_wrong_case_issue_rejected(self):
        d = fixtures()
        d[1]["number"] = 1203
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "current/open"):
            self.admit(d)

    def test_missing_live_source_pin_rejected(self):
        d = fixtures()
        d[1]["body"] = "<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "source pin"):
            self.admit(d)

    def test_old_toolkit_source_claim_rejected_even_if_portable_result_valid(self):
        d = fixtures()
        d[5].src["repository"] = "sankarshanmukhopadhyay/rahp-toolkit"
        d[5].src["issue"] = 1116
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "Registry source referral"):
            self.admit(d)

    def test_referral_wrong_source_revision_rejected(self):
        d = fixtures()
        d[5].src["changed_artifact"]["revision"] = "f" * 40
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "changed artifact"):
            self.admit(d)

    def test_referral_source_pins_missing_rejected(self):
        d = fixtures()
        d[5].src["source_pins"] = []
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "source pin"):
            self.admit(d)

    def test_missing_exam_key_rejected(self):
        d = fixtures()
        d[5].src["identities"]["examination_key"] = ""
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "identity"):
            self.admit(d)

    def test_nonterminal_producer_rejected(self):
        d = fixtures()
        d[3]["state"] = "open"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "not a terminal"):
            self.admit(d)

    def test_duplicate_source_referrals_rejected(self):
        d = fixtures()
        d[4].append({"body": "EXTRA-SOURCE"})
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "unique explicit"):
            self.admit(d)

    def test_missing_return_or_outbox_does_not_reconcile(self):
        d = fixtures()
        d[2].clear()
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "canonical DPIP return chain rejected"):
            self.admit(d)

    def test_mismatched_ack_target_rejected(self):
        d = fixtures()
        d[4][-1]["body"] = d[4][-1]["body"].replace("#4", "#1116")
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "canonical DPIP return chain rejected"):
            self.admit(d)

    def test_forged_source_result_disagreement_rejected(self):
        d = fixtures()
        d[5].returned["outcome"] = "PASS"
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "canonical DPIP return chain rejected"):
            self.admit(d)

    def test_missing_execution_provenance_rejected(self):
        d = fixtures()
        d[4][:] = [c for c in d[4] if "dpip-execution-evidence:" not in c["body"]]
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "canonical DPIP return chain rejected"):
            self.admit(d)

    def test_duplicate_delivery_comment_rejected(self):
        d = fixtures()
        d[2].append(copy.deepcopy(d[2][0]))
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "canonical DPIP return chain rejected"):
            self.admit(d)


if __name__ == "__main__":
    unittest.main()
