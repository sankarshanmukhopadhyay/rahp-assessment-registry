import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_dpip_legacy_consumer as v


def portable():
    return {
        "schema": "rahp-assessor-result/v1", "assessor": "dpip", "assessment_id": "dpip:305",
        "outcome": "INDETERMINATE", "reason_code": "evidence-required",
        "evidence_used": [], "residual_risk": "Insufficient observed evidence.",
        "action_required": "Run target-native two-context test.",
        "source_pins": [{
            "repository": "OpenVTC/verifiable-trust-infrastructure",
            "revision": "324d325e7e75c33d658bc10104867d2eca0dc6d7",
        }],
        "provenance": {"execution_digest": "run1", "setup_digest": "setup1"},
    }


class FakeConsumer:
    def __init__(self, p=None):
        self.p = copy.deepcopy(p or portable())
        self.returned = copy.deepcopy(self.p)
        self.conclusion = self.p["outcome"]

    def yaml_blocks(self, body):
        if "RETURN-PAYLOAD" in body:
            return [{"dpip_disposition": {"conclusion": self.conclusion,
                                         "assessor_result": self.returned}}]
        if "EXAMINATION-PAYLOAD" in body:
            return [{"dpip_examination": {"assessor_result": self.p}}]
        return []


class FakeCanonicalSchema:
    @staticmethod
    def validate_result(value):
        required = ("schema", "assessor", "assessment_id", "outcome", "reason_code",
                    "evidence_used", "residual_risk", "action_required")
        return [x + " missing" for x in required if not value.get(x) and x != "evidence_used"]


def fixture():
    source = [{"body":
        "<!-- dpip-return:sankarshanmukhopadhyay/dtg-privacy-implementation-profile#305 -->\nRETURN-PAYLOAD"}]
    d = hashlib.sha256(source[0]["body"].encode()).hexdigest()[:20]
    target = {305: [
        {"body": "<!-- dpip-examination:305:exam1 -->\nEXAMINATION-PAYLOAD"},
        {"body": "<!-- dpip-execution-evidence:305:run1 -->"},
        {"body": "<!-- dpip-examination-setup:305:setup1 -->"},
        {"body": f"<!-- rahp-return-outbox:v1:305:{d} -->"},
        {"body": f"<!-- rahp-return-ack:v2:305:{d}:dest -->\n"
                 "- destination: `sankarshanmukhopadhyay/rahp-toolkit#1116`"},
    ]}
    return source, target


class PortableReturnTests(unittest.TestCase):
    def test_valid_real_contract_shape_does_not_claim_registry_delivery(self):
        r = v.verify_portable_historical_return(*fixture(), FakeConsumer(), FakeCanonicalSchema)
        self.assertEqual(r["portable_outcome"], "INDETERMINATE")
        self.assertTrue(r["dpip_ack_matches_outbox"])
        self.assertFalse(r["registry_destination_tested"])
        self.assertFalse(r["independent_specialist_authentication"])

    def test_substituted_payload_content_invalidates_outbox_digest(self):
        s, t = fixture()
        s[0]["body"] += "\nATTACK"
        with self.assertRaisesRegex(v.ConsumerError, "outbox"):
            v.verify_portable_historical_return(s, t, FakeConsumer(), FakeCanonicalSchema)

    def test_missing_source_return_is_not_assurance(self):
        s, t = fixture()
        with self.assertRaisesRegex(v.ConsumerError, "source"):
            v.verify_portable_historical_return([], t, FakeConsumer(), FakeCanonicalSchema)

    def test_duplicate_return_marker_is_not_accepted(self):
        s, t = fixture()
        with self.assertRaisesRegex(v.ConsumerError, "duplicate"):
            v.verify_portable_historical_return(s + s, t, FakeConsumer(), FakeCanonicalSchema)

    def test_wrong_portable_assessor_identity_rejected(self):
        s, t = fixture()
        p = portable()
        p["assessment_id"] = "dpip:304"
        with self.assertRaisesRegex(v.ConsumerError, "identity"):
            v.verify_portable_historical_return(s, t, FakeConsumer(p), FakeCanonicalSchema)

    def test_inconsistent_producer_and_source_result_rejected(self):
        s, t = fixture()
        c = FakeConsumer()
        c.returned["reason_code"] = "different-result"
        with self.assertRaisesRegex(v.ConsumerError, "differs"):
            v.verify_portable_historical_return(s, t, c, FakeCanonicalSchema)

    def test_inconsistent_disposition_conclusion_rejected(self):
        s, t = fixture()
        c = FakeConsumer()
        c.conclusion = "PASS"
        with self.assertRaisesRegex(v.ConsumerError, "contradicts"):
            v.verify_portable_historical_return(s, t, c, FakeCanonicalSchema)

    def test_invalid_canonical_schema_rejected(self):
        s, t = fixture()
        p = portable()
        del p["action_required"]
        with self.assertRaisesRegex(v.ConsumerError, "canonical portable assessor validation failed"):
            v.verify_portable_historical_return(s, t, FakeConsumer(p), FakeCanonicalSchema)

    def test_stale_or_wrong_producer_source_pin_rejected(self):
        s, t = fixture()
        p = portable()
        p["source_pins"][0]["revision"] = "f" * 40
        with self.assertRaisesRegex(v.ConsumerError, "source-pinned"):
            v.verify_portable_historical_return(s, t, FakeConsumer(p), FakeCanonicalSchema)

    def test_missing_producer_execution_receipt_rejected(self):
        s, t = fixture()
        t[305] = [x for x in t[305] if "dpip-execution-evidence:" not in x["body"]]
        with self.assertRaisesRegex(v.ConsumerError, "execution_digest"):
            v.verify_portable_historical_return(s, t, FakeConsumer(), FakeCanonicalSchema)

    def test_missing_source_specific_ack_rejected(self):
        s, t = fixture()
        t[305][-1]["body"] = t[305][-1]["body"].replace("#1116", "#4")
        with self.assertRaisesRegex(v.ConsumerError, "acknowledgment"):
            v.verify_portable_historical_return(s, t, FakeConsumer(), FakeCanonicalSchema)

    def test_duplicate_outbox_receipt_rejected(self):
        s, t = fixture()
        t[305].append(dict(t[305][-2]))
        with self.assertRaisesRegex(v.ConsumerError, "outbox"):
            v.verify_portable_historical_return(s, t, FakeConsumer(), FakeCanonicalSchema)


if __name__ == "__main__":
    unittest.main()
