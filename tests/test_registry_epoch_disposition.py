"""One qualified disposition per exact source/examination epoch (Registry #11 gate 4).

Models the historical Toolkit #1116 -> DPIP #304/#305 hazard: two numbered DPIP
issues carrying the same semantic examination key must not become two
independent authoritative outcomes on a Registry case.
"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import registry_specialist_return as bridge
from test_registry_specialist_return import DPIP, PIN, RealContractStub, portable


class MapConsumer:
    """Dispatch canned YAML blocks by a per-issue marker embedded in comment bodies."""

    def __init__(self):
        self.table = {}

    def yaml_blocks(self, body):
        for tag, blocks in self.table.items():
            if tag in body:
                return blocks
        return []


def add_run(consumer, number, exam_key, outcome="INDETERMINATE", returned_outcome=None):
    result = portable()
    result["assessment_id"] = f"dpip:{number}"
    result["outcome"] = outcome
    result["provenance"] = {"execution_digest": f"run{number}", "setup_digest": f"setup{number}"}
    returned = copy.deepcopy(result)
    if returned_outcome is not None:
        returned["outcome"] = returned_outcome
    source = {
        "system": "RAHP", "repository": bridge.REGISTRY, "issue": 4,
        "changed_artifact": {"repository": PIN[0], "revision": PIN[1]},
        "source_pins": [{"repository": PIN[0], "revision": PIN[1]}],
        "identities": {"examination_key": exam_key, "referral_id": f"rahp-referral:r{number}"},
    }
    consumer.table[f"SOURCE-PAYLOAD-{number}"] = [{"source": source}]
    consumer.table[f"RETURN-PAYLOAD-{number}"] = [{"dpip_disposition": {
        "conclusion": outcome, "assessor_result": returned}}]
    consumer.table[f"EXAMINATION-PAYLOAD-{number}"] = [{"dpip_examination": {
        "assessor_result": result}}]
    source_return = {"body": f"<!-- dpip-return:{DPIP}#{number} -->\nRETURN-PAYLOAD-{number}"}
    digest = hashlib.sha256(source_return["body"].encode()).hexdigest()[:20]
    issue = {
        "number": number, "state": "closed", "body": f"SOURCE-PAYLOAD-{number}",
        "labels": [{"name": "source:rahp"}, {"name": "run:complete"}],
    }
    comments = [
        {"body": f"<!-- dpip-examination:{number}:exam{number} -->\nEXAMINATION-PAYLOAD-{number}"},
        {"body": f"<!-- dpip-execution-evidence:{number}:run{number} -->"},
        {"body": f"<!-- dpip-examination-setup:{number}:setup{number} -->"},
        {"body": f"<!-- rahp-return-outbox:v1:{number}:{digest} -->"},
        {"body": f"<!-- rahp-return-ack:v2:{number}:{digest}:dest -->\n"
                 "- destination: `sankarshanmukhopadhyay/rahp-assessment-registry#4`"},
    ]
    return source_return, issue, comments


def build(specs):
    """specs: list of (issue number, examination key[, kwargs]). Returns qualify_epoch args."""
    case = json.loads((ROOT / "cases/dtg/network-answer-proof-2026-11.json").read_text())
    case["referrals"] = [{
        "role": "specialist_assessor", "repository": DPIP,
        "contract": "rahp-assessor-result/v1",
        "issue_url": f"https://github.com/{DPIP}/issues/{spec[0]}",
        "status": "accepted",
    } for spec in specs]
    case_issue = {
        "number": 4, "state": "open",
        "body": f"<!-- rahp-registry-case:{case['case_id']} -->\n{PIN[0]}\n{PIN[1]}",
    }
    consumer = MapConsumer()
    returns, runs = [], []
    for spec in specs:
        kwargs = spec[2] if len(spec) > 2 else {}
        source_return, issue, comments = add_run(consumer, spec[0], spec[1], **kwargs)
        returns.append(source_return)
        runs.append((issue, comments))
    return case, case_issue, returns, runs, consumer


class EpochDispositionTests(unittest.TestCase):
    def qualify(self, specs, runs_override=None):
        case, case_issue, returns, runs, consumer = build(specs)
        return bridge.qualify_epoch(case, case_issue, returns,
                                    runs if runs_override is None else runs_override(runs),
                                    consumer, RealContractStub)

    def test_single_run_qualifies_with_examination_identity(self):
        receipts = self.qualify([(305, "exam-key-a")])
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["examination_key"], "exam-key-a")
        self.assertEqual(receipts[0]["source_referral_id"], "rahp-referral:r305")
        self.assertFalse(receipts[0]["case_determination_imported"])

    def test_distinct_examination_epochs_remain_independent(self):
        receipts = self.qualify([(304, "exam-key-a"), (305, "exam-key-b")])
        self.assertEqual({r["examination_key"] for r in receipts}, {"exam-key-a", "exam-key-b"})

    def test_duplicate_epoch_across_issue_numbers_has_no_single_disposition(self):
        with self.assertRaises(bridge.SpecialistAdmissionError) as ctx:
            self.qualify([(304, "exam-key-a"), (305, "exam-key-a")])
        message = str(ctx.exception)
        self.assertIn("duplicate examination epoch", message)
        # The historical duplicates stay traceable rather than silently dropped.
        self.assertIn(f"{DPIP}/issues/304", message)
        self.assertIn(f"{DPIP}/issues/305", message)

    def test_duplicate_epoch_with_conflicting_outcomes_is_rejected(self):
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "duplicate examination epoch"):
            self.qualify([(304, "exam-key-a", {"outcome": "INDETERMINATE"}),
                          (305, "exam-key-a", {"outcome": "FAIL"})])

    def test_whitespace_variant_of_examination_key_is_still_the_same_epoch(self):
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "duplicate examination epoch"):
            self.qualify([(304, "exam-key-a"), (305, "  exam-key-a  ")])

    def test_identical_retry_of_one_issue_is_idempotent(self):
        receipts = self.qualify([(305, "exam-key-a")], lambda runs: runs + runs)
        self.assertEqual(len(receipts), 1)

    def test_one_forged_run_rejects_the_whole_set(self):
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError,
                                    "canonical DPIP return chain rejected"):
            self.qualify([(304, "exam-key-a"),
                          (305, "exam-key-b", {"returned_outcome": "PASS"})])

    def test_empty_offer_is_rejected(self):
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no specialist runs"):
            self.qualify([(305, "exam-key-a")], lambda runs: [])

    def test_unadmitted_second_issue_cannot_ride_along(self):
        case, case_issue, returns, runs, consumer = build([(304, "exam-key-a"), (305, "exam-key-b")])
        case["referrals"] = case["referrals"][:1]  # only #304 is admitted
        with self.assertRaisesRegex(bridge.SpecialistAdmissionError, "no unique admitted"):
            bridge.qualify_epoch(case, case_issue, returns, runs, consumer, RealContractStub)


if __name__ == "__main__":
    unittest.main()
