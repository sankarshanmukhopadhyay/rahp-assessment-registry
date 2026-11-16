import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_toolkit_archive import verify


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((ROOT / "archive/manifest.json").read_text())
        cls.parts = [json.loads((ROOT / p["path"]).read_text())
                     for p in cls.meta["partitions"]]

    def test_complete_baseline(self):
        self.assertEqual(verify(self.meta, self.parts), [])
        self.assertEqual(self.meta["total_issues"], 769)
        self.assertEqual(self.meta["state_counts"], {"open": 57, "closed": 712})

    def test_missing_partition_fails(self):
        parts = copy.deepcopy(self.parts)
        parts[0].pop()
        self.assertIn("partition issue count mismatch", verify(self.meta, parts))

    def test_duplicate_historical_issue_fails(self):
        parts = copy.deepcopy(self.parts)
        parts[0][0]["number"] = parts[1][0]["number"]
        self.assertIn("duplicate source issue IDs", verify(self.meta, parts))

    def test_bad_source_url_fails(self):
        parts = copy.deepcopy(self.parts)
        parts[0][0]["url"] = "https://example.invalid"
        self.assertTrue(any("wrong source URL" in e for e in verify(self.meta, parts)))

    def test_false_full_mirror_claim_fails(self):
        meta = dict(self.meta, full_content_mirror=True)
        self.assertIn("metadata index cannot claim full mirror", verify(meta, self.parts))

    def test_mismatched_open_closed_state_fails(self):
        meta = copy.deepcopy(self.meta)
        meta["state_counts"]["open"] += 1
        self.assertIn("state count mismatch", verify(meta, self.parts))

    def test_pilot_successor_is_necessary(self):
        parts = copy.deepcopy(self.parts)
        for item in parts[0]:
            if item["number"] == 1203:
                del item["registry_successor"]
        self.assertIn("pilot successor lost", verify(self.meta, parts))

    def test_classification_is_not_assurance(self):
        classes = {i["classification"] for part in self.parts for i in part}
        self.assertIn("external-assessment-candidate", classes)
        self.assertIn("development-or-unclassified", classes)


if __name__ == "__main__":
    unittest.main()
