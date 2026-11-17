import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_dpip_legacy_consumer as check


class ConsumerStub:
    conclusion = "INDETERMINATE"

    @staticmethod
    def yaml_blocks(body):
        if "BAD-SOURCE" in body:
            return [{"source": {"repository": "other/other", "issue": 999}}]
        return [{"source": {"repository": check.SOURCE_REPO, "issue": 1116}}]

    @classmethod
    def parse_return(cls, comments):
        if not any("dpip-return:" in c.get("body", "") for c in comments):
            return None
        return {"target_repository": check.DPIP_REPO, "target_issue": 305,
                "conclusion": cls.conclusion, "terminal_reason": ""}

    @staticmethod
    def base_state(conclusion, terminal_reason):
        return "evidence-external" if conclusion == "INDETERMINATE" and not terminal_reason else "resolved"

    @staticmethod
    def reconciliation_marker(source, target):
        return f"<!-- rahp-dpip-reconciliation:v4:{source}:{target} -->"


def fixture():
    source = {"number": 1116, "state": "closed"}
    source_comments = [
        {"body": f"<!-- dpip-return:{check.DPIP_REPO}#305 -->"},
        {"body": "<!-- rahp-dpip-reconciliation:v4:1116:305 -->"},
    ]
    targets = {n: {"number": n,
                    "body": f"<!-- rahp-dpip-examination:2538c766a825ef1b2e89 -->\n"
                            f"<!-- rahp-dpip-referral:1116:test -->"} for n in (304, 305)}
    target_comments = {304: [], 305: [{"body":
        f"<!-- rahp-return-ack:v2:305:abc:def -->\n"
        f"- destination: {chr(96)}{check.SOURCE_REPO}#1116{chr(96)}"}]}
    return source, source_comments, targets, target_comments


class DPIPLegacyTests(unittest.TestCase):
    def test_historical_duplicate_preserves_indeterminate(self):
        receipt = check.verify_historical_links(*fixture(), ConsumerStub)
        self.assertTrue(receipt["duplicate_semantic_examination_detected"])
        self.assertTrue(receipt["target_acknowledgement_observed"])
        self.assertFalse(receipt["assurance_pass"])
        self.assertFalse(receipt["registry_controller_cutover_qualified"])

    def test_missing_return_never_becomes_success(self):
        src, comments, targets, target_comments = fixture()
        comments.pop(0)
        with self.assertRaisesRegex(check.ConsumerError, "return"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_wrong_examination_identity_rejected(self):
        src, comments, targets, target_comments = fixture()
        targets[305]["body"] = targets[305]["body"].replace("2538c766a825ef1b2e89", "wrong")
        with self.assertRaisesRegex(check.ConsumerError, "duplicate"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_mismatched_source_provenance_rejected(self):
        src, comments, targets, target_comments = fixture()
        targets[305]["body"] += "\nBAD-SOURCE\n"
        with self.assertRaisesRegex(check.ConsumerError, "provenance"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_no_source_reconciliation_is_not_acknowledged(self):
        src, comments, targets, target_comments = fixture()
        comments.pop(1)
        with self.assertRaisesRegex(check.ConsumerError, "reconciliation"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_no_target_acknowledgement_is_not_delivery(self):
        src, comments, targets, target_comments = fixture()
        target_comments[305] = []
        with self.assertRaisesRegex(check.ConsumerError, "acknowledgement"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_altered_target_acknowledgement_is_not_delivery(self):
        src, comments, targets, target_comments = fixture()
        target_comments[305][0]["body"] = target_comments[305][0]["body"].replace("#1116", "#4")
        with self.assertRaisesRegex(check.ConsumerError, "acknowledgement"):
            check.verify_historical_links(src, comments, targets, target_comments, ConsumerStub)

    def test_unjustified_specialist_pass_is_rejected(self):
        class ForgedPass(ConsumerStub):
            conclusion = "PASS"
        with self.assertRaisesRegex(check.ConsumerError, "promoted"):
            check.verify_historical_links(*fixture(), ForgedPass)


if __name__ == "__main__":
    unittest.main()
