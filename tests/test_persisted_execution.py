import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_persisted_execution as v

RECORD = ROOT / "ops/executions/RAHP-AR-DTG-0001/rahp-369ffe8e6f037e6235d5.json"


class PersistedCanonicalExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(v.CASE.read_text())
        cls.spec = json.loads(v.SPEC.read_text())
        cls.ledger = json.loads(v.LEDGER.read_text())
        cls.record = json.loads(RECORD.read_text())

    def check(self, rec):
        return v.check_record(rec, self.case, self.spec, self.ledger)

    def test_source_result_and_binding_reproducible(self):
        self.assertEqual(self.check(copy.deepcopy(self.record)),
                         "rahp-execution:b41e27c36da98ad39b285333174d3b5e")
        self.assertEqual(v.validate_all(), 1)

    def test_exact_controller_output_matches(self):
        self.assertEqual(v.check_record(self.record, self.case, self.spec, self.ledger,
                                        actual_result=copy.deepcopy(self.record["result"])),
                         self.record["binding"]["binding_key"])

    def test_falsified_new_result_detected(self):
        bad = copy.deepcopy(self.record)
        bad["result"]["inference"] = "PASS without evidence"
        with self.assertRaises(v.RecordError):
            self.check(bad)

    def test_forged_outcome_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["result"]["outcome"] = "PASS"
        with self.assertRaises(v.RecordError):
            self.check(bad)

    def test_wrong_source_revision_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["result"]["source_pins"][0]["revision"] = "a" * 40
        with self.assertRaises(v.RecordError):
            self.check(bad)

    def test_forged_imported_flag_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["binding"]["case_determination_imported"] = True
        with self.assertRaises(v.RecordError):
            self.check(bad)

    def test_changed_result_digest_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["binding"]["result_sha256"] = "0" * 64
        with self.assertRaises(v.RecordError):
            self.check(bad)

    def test_wrong_provenance_run_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["source_workflow_run"] = "https://github.com/someone/other/actions/runs/1"
        with self.assertRaisesRegex(v.RecordError, "provenance"):
            self.check(bad)

    def test_forged_qualification_rejected(self):
        bad = copy.deepcopy(self.record)
        bad["qualification"]["registry_assessment_imported"] = True
        with self.assertRaisesRegex(v.RecordError, "qualification"):
            self.check(bad)

    def test_missing_qualification_rejected(self):
        bad = copy.deepcopy(self.record)
        del bad["qualification"]
        with self.assertRaisesRegex(v.RecordError, "keys"):
            self.check(bad)

    def test_fresh_execution_drift_rejected(self):
        actual = copy.deepcopy(self.record["result"])
        actual["residuals"] = []
        with self.assertRaisesRegex(v.RecordError, "fresh controller"):
            v.check_record(self.record, self.case, self.spec, self.ledger,
                           actual_result=actual)

    def test_duplicate_execution_identity_in_repository_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dir = root / "RAHP-AR-DTG-0001"
            dir.mkdir()
            data = json.dumps(self.record)
            (dir / "rahp-369ffe8e6f037e6235d5.json").write_text(data)
            (dir / "extra.json").write_text(data)
            with self.assertRaisesRegex(v.RecordError, "duplicate"):
                v.validate_all(root)

    def test_wrong_file_identity_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dir = root / "RAHP-AR-DTG-0001"
            dir.mkdir()
            (dir / "not-the-controller-id.json").write_text(json.dumps(self.record))
            with self.assertRaisesRegex(v.RecordError, "filename"):
                v.validate_all(root)

    def test_wrong_case_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dir = root / "WRONG-CASE"
            dir.mkdir()
            (dir / "rahp-369ffe8e6f037e6235d5.json").write_text(json.dumps(self.record))
            with self.assertRaisesRegex(v.RecordError, "directory"):
                v.validate_all(root)


if __name__ == "__main__":
    unittest.main()
