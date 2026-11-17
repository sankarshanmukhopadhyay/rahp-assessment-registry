import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_history_locator as locator


class LocatorTests(unittest.TestCase):
    def test_real_archive_and_accepted_succession(self):
        record = locator.verify(ROOT)
        self.assertEqual(record["source_issues"], 769)
        self.assertGreaterEqual(record["accepted_succession"], 1)
        self.assertGreaterEqual(record["direct_cases_excluded"], 1)
        self.assertFalse(record["live_source_resolvability_verified"])
        self.assertFalse(record["independent_gate_accepted"])

    def fixture(self, task):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archive/snapshots").mkdir(parents=True)
            (root / "cases").mkdir()
            original = {"number": 1203, "state": "closed",
                        "url": locator.TOOLKIT + "1203",
                        "registry_successor": locator.REGISTRY + "4"}
            path = "archive/snapshots/toolkit-issues-2026-11-16-p1.json"
            (root / path).write_text(json.dumps([original]))
            manifest = {"schema": locator.SNAPSHOT_SCHEMA,
                        "source_repository": "sankarshanmukhopadhyay/rahp-toolkit",
                        "total_issues": 1, "state_counts": {"open": 0, "closed": 1},
                        "partitions": [{"path": path, "expected_issues": 1}]}
            (root / "archive/manifest.json").write_text(json.dumps(manifest))
            case = {"case_id": "one",
                    "owners": {"handoff": "accepted",
                               "historical_source_issue": locator.TOOLKIT + "1203",
                               "current_active_issue": locator.REGISTRY + "4"}}
            (root / "cases/one.json").write_text(json.dumps(case))
            return task(root, path, case)

    def test_missing_historical_source_fails(self):
        def mutate(root, path, case):
            case["owners"]["historical_source_issue"] = locator.TOOLKIT + "1204"
            (root / "cases/one.json").write_text(json.dumps(case))
            with self.assertRaisesRegex(locator.LocatorError, "not represented"):
                locator.verify(root)
        self.fixture(mutate)

    def test_wrong_snapshot_mapping_fails(self):
        def mutate(root, path, case):
            source = json.loads((root / path).read_text())
            source[0]["registry_successor"] = locator.REGISTRY + "99"
            (root / path).write_text(json.dumps(source))
            with self.assertRaisesRegex(locator.LocatorError, "successor mapping"):
                locator.verify(root)
        self.fixture(mutate)

    def test_two_cases_cannot_claim_historical_source(self):
        def mutate(root, path, case):
            other = copy.deepcopy(case)
            other["case_id"] = "other"
            (root / "cases/other.json").write_text(json.dumps(other))
            with self.assertRaisesRegex(locator.LocatorError, "ambiguous"):
                locator.verify(root)
        self.fixture(mutate)

    def test_duplicate_source_metadata_rejected(self):
        def mutate(root, path, case):
            source = json.loads((root / path).read_text())
            (root / path).write_text(json.dumps(source * 2))
            m = json.loads((root / "archive/manifest.json").read_text())
            m["total_issues"] = 2
            m["state_counts"]["closed"] = 2
            m["partitions"][0]["expected_issues"] = 2
            (root / "archive/manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(locator.LocatorError, "duplicate"):
                locator.verify(root)
        self.fixture(mutate)

    def test_direct_case_without_historical_owner_is_valid(self):
        def mutate(root, path, case):
            (root / "cases/direct.json").write_text(json.dumps({
                "case_id": "direct", "owners": {"admission": "direct",
                "handoff": "not_applicable"}}))
            self.assertEqual(locator.verify(root)["direct_cases_excluded"], 1)
        self.fixture(mutate)


if __name__ == "__main__":
    unittest.main()
